"""Single-use, expiring invitation primitives. Tokens are never stored in plaintext."""
import hashlib
import secrets
import time
from fastapi import HTTPException
from .accounts import hash_password

INVITE_ROLES={"manager","treasurer","member","viewer"}
def setup(con):
    con.execute("""CREATE TABLE IF NOT EXISTS band_invites (
        token_hash TEXT PRIMARY KEY,
        band_id INTEGER NOT NULL REFERENCES bands(id),
        email TEXT NOT NULL,
        role TEXT NOT NULL,
        expires_at INTEGER NOT NULL,
        used_at INTEGER,
        created_by INTEGER NOT NULL REFERENCES users(id),
        created_at INTEGER NOT NULL
    )""")

def create(con,band_id,creator_id,email,role,now=None):
    now=int(time.time()) if now is None else now
    email=email.strip().lower()
    if role not in INVITE_ROLES or not email or '@' not in email:
        raise HTTPException(422,'Invalid invitation')
    membership=con.execute("SELECT role FROM band_users WHERE band_id=? AND user_id=?",
                           (band_id,creator_id)).fetchone()
    if not membership or membership['role'] not in {'owner','manager'}:
        raise HTTPException(403,'Manager permission required')
    if membership['role']=='manager' and role=='manager':
        raise HTTPException(403,'Only owners can invite managers')
    token=secrets.token_urlsafe(32)
    con.execute("""INSERT INTO band_invites
       (token_hash,band_id,email,role,expires_at,created_by,created_at)
       VALUES(?,?,?,?,?,?,?)""",
       (hashlib.sha256(token.encode()).hexdigest(),band_id,email,role,now+7*86400,creator_id,now))
    return token

def accept(con,token,email,name,password,now=None):
    now=int(time.time()) if now is None else now
    key=hashlib.sha256(token.encode()).hexdigest()
    row=con.execute("""SELECT * FROM band_invites WHERE token_hash=?
        AND used_at IS NULL AND expires_at>?""",(key,now)).fetchone()
    if not row or row['email']!=email.strip().lower():
        raise HTTPException(400,'Invitation invalid or expired')
    if con.execute("SELECT id FROM users WHERE email=?",(row['email'],)).fetchone():
        raise HTTPException(409,'Existing accounts require signed-in invitation acceptance')
    password_hash=hash_password(password)
    created=con.execute("INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)",
                         (row['email'],name.strip(),password_hash))
    con.execute("INSERT INTO band_users(band_id,user_id,role) VALUES(?,?,?)",
                (row['band_id'],created.lastrowid,row['role']))
    con.execute("UPDATE band_invites SET used_at=? WHERE token_hash=? AND used_at IS NULL",(now,key))
    return {'band_id':row['band_id'],'role':row['role']}

def accept_existing(con,token,user_id,now=None):
    """Redeem an invitation only for the currently signed-in matching email."""
    now=int(time.time()) if now is None else now
    key=hashlib.sha256(token.encode()).hexdigest()
    invitation=con.execute("""SELECT * FROM band_invites
        WHERE token_hash=? AND used_at IS NULL AND expires_at>?""",(key,now)).fetchone()
    user=con.execute("SELECT email FROM users WHERE id=?",(user_id,)).fetchone()
    if not invitation or not user or user["email"].strip().lower()!=invitation["email"]:
        raise HTTPException(400,"Invitation invalid or not intended for this account")
    existing=con.execute("SELECT 1 FROM band_users WHERE band_id=? AND user_id=?",
        (invitation["band_id"],user_id)).fetchone()
    if existing:
        raise HTTPException(409,"Already a member of this band")
    con.execute("INSERT INTO band_users(band_id,user_id,role) VALUES(?,?,?)",
        (invitation["band_id"],user_id,invitation["role"]))
    con.execute("UPDATE band_invites SET used_at=? WHERE token_hash=? AND used_at IS NULL",
        (now,key))
    return {"band_id":invitation["band_id"],"role":invitation["role"]}
