"""Account session and band authorization for opt-in v0.2 staging.

Requires BACKLINE_ACCOUNTS_ENABLED=1; otherwise retains the v0.1 preview gate.
Tokens are random, stored as hashes, and expire. Never enable in production
without migrating/claiming legacy data through a separately reviewed process.
"""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

BAND_PATH = re.compile(r"^/api/bands/(\d+)(?:/|$)")
ROLES = {"owner", "manager", "treasurer", "member", "viewer"}
WRITE = {"POST", "PUT", "PATCH", "DELETE"}
FINANCE = {"finance", "transactions", "settlements", "settle"}
SESSION_SECONDS = 60 * 60 * 24 * 7

def account_tables(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE,
      display_name TEXT NOT NULL, password_hash TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS band_users (
      band_id INTEGER NOT NULL REFERENCES bands(id),
      user_id INTEGER NOT NULL REFERENCES users(id),
      role TEXT NOT NULL CHECK(role IN ('owner','manager','treasurer','member','viewer')),
      PRIMARY KEY (band_id,user_id)
    );
    CREATE TABLE IF NOT EXISTS sessions (
      token_hash TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id),
      expires_at INTEGER NOT NULL
    );
    """)
    
def hash_password(password):
    if len(password) < 12 or len(password)>1024:
        raise HTTPException(422, "Password must be 12 to 1024 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return "scrypt$" + salt.hex() + "$" + digest.hex()

def verify_password(password, stored):
    try:
        scheme, salt, digest = stored.split("$")
        if scheme != "scrypt": return False
        calc = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(calc, bytes.fromhex(digest))
    except (ValueError, TypeError, OverflowError):
        return False

def make_session(con, user_id):
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode()).hexdigest()
    con.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
                (digest,user_id,int(time.time())+SESSION_SECONDS))
    return token

def authenticate(con, bearer):
    digest=hashlib.sha256(bearer.encode()).hexdigest()
    row=con.execute("""SELECT u.id,u.email,u.display_name FROM sessions s
      JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?""",
      (digest,int(time.time()))).fetchone()
    return dict(row) if row else None

def authorized(con, user_id, band_id, method, path):
    row=con.execute("SELECT role FROM band_users WHERE user_id=? AND band_id=?",
                    (user_id,band_id)).fetchone()
    if not row: return False
    role=row["role"]
    if method not in WRITE: return True if (not any("/"+x in path for x in FINANCE)) else role in {"owner","manager","treasurer"}
    if role in {"owner","manager"}: return True
    if role == "treasurer":
        return any("/"+x in path for x in FINANCE)
    return False

def install_accounts(app, db):
    @app.middleware("http")
    async def accounts_guard(request: Request, call_next):
        if os.getenv("BACKLINE_ACCOUNTS_ENABLED") != "1":
            return await call_next(request)
        path=request.url.path
        if path=="/api/health" or path=="/api/auth/login":
            return await call_next(request)
        # When accounts are enabled, no anonymous access to static assets or API.
        auth=request.headers.get("authorization","")
        if not auth.startswith("Bearer "):
            return JSONResponse({"detail":"Account login required"},status_code=401)
        with db() as con:
            user=authenticate(con,auth[7:])
            if not user:
                return JSONResponse({"detail":"Invalid or expired session"},status_code=401)
            request.state.user=user
            m=BAND_PATH.match(path)
            if m and not authorized(con,user["id"],int(m.group(1)),request.method,path):
                return JSONResponse({"detail":"Band access denied"},status_code=403)
            if path=="/api/bands" and request.method in WRITE:
                # New-band creation is handled separately with atomic owner assignment.
                return await call_next(request)
        return await call_next(request)
