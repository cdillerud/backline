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
    CREATE TABLE IF NOT EXISTS login_attempts (
      email_key TEXT PRIMARY KEY,
      failures INTEGER NOT NULL DEFAULT 0,
      window_started INTEGER NOT NULL,
      blocked_until INTEGER NOT NULL DEFAULT 0
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

LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_FAILURES = 5
LOGIN_LOCK_SECONDS = 15 * 60

def login_locked(con, email, now=None):
    now=int(time.time()) if now is None else now
    row=con.execute("SELECT blocked_until FROM login_attempts WHERE email_key=?",(hashlib.sha256(email.encode()).hexdigest(),)).fetchone()
    return bool(row and row["blocked_until"] > now)

def login_failure(con, email, now=None):
    now=int(time.time()) if now is None else now
    key=hashlib.sha256(email.encode()).hexdigest()
    row=con.execute("SELECT failures,window_started FROM login_attempts WHERE email_key=?",(key,)).fetchone()
    failures=(row["failures"]+1) if row and now-row["window_started"]<LOGIN_WINDOW_SECONDS else 1
    started=row["window_started"] if row and now-row["window_started"]<LOGIN_WINDOW_SECONDS else now
    blocked=now+LOGIN_LOCK_SECONDS if failures>=LOGIN_MAX_FAILURES else 0
    con.execute("""INSERT INTO login_attempts(email_key,failures,window_started,blocked_until)
      VALUES(?,?,?,?) ON CONFLICT(email_key) DO UPDATE SET failures=excluded.failures,
      window_started=excluded.window_started,blocked_until=excluded.blocked_until""",
      (key,failures,started,blocked))

def login_success(con, email):
    con.execute("DELETE FROM login_attempts WHERE email_key=?",(hashlib.sha256(email.encode()).hexdigest(),))

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
    if not row:
        return False
    role=row["role"]
    # Explicit route segments, not substring checks: no bypass through nested paths.
    parts=path.strip("/").split("/")
    resource=parts[3] if len(parts)>3 else ""
    financial=resource in {"finance","transactions","settlements"} or (
        resource=="events" and "settle" in parts)
    marketing=resource=="gigs"
    booking=resource in {"bookings","booking-followups"}
    if method not in WRITE:
        if financial:
            return role in {"owner","manager","treasurer"}
        return role in ROLES
    if role in {"owner","manager"}:
        return True
    if role=="treasurer":
        return financial
    # Member and viewer can read their workspace, not mutate any data.
    return False

def install_accounts(app, db):
    @app.middleware("http")
    async def accounts_guard(request: Request, call_next):
        if os.getenv("BACKLINE_ACCOUNTS_ENABLED") != "1":
            return await call_next(request)
        path=request.url.path
        if path in ("/","/api/health","/api/auth/login","/api/auth/accept-invite","/api/auth/recover") or path.startswith("/static/"):
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
        return await call_next(request)
