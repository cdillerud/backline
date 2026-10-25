"""Owner-assisted account recovery. No public reset-token issuance or email channel.

A band owner may generate a one-time recovery code for an existing member.
The code expires after 30 minutes. Its hash is stored, not the code.
"""
import hashlib
import secrets
import time
from fastapi import HTTPException
from .accounts import hash_password

def setup(con):
    con.execute("""CREATE TABLE IF NOT EXISTS account_recovery (
       token_hash TEXT PRIMARY KEY,
       user_id INTEGER NOT NULL REFERENCES users(id),
       issuer_id INTEGER NOT NULL REFERENCES users(id),
       expires_at INTEGER NOT NULL,
       redeemed_at INTEGER,
       created_at INTEGER NOT NULL
    )""")

def issue(con, issuer_id, band_id, target_email, now=None):
    now=int(time.time()) if now is None else now
    issuer=con.execute("SELECT role FROM band_users WHERE user_id=? AND band_id=?",
                       (issuer_id,band_id)).fetchone()
    if not issuer or issuer["role"]!="owner":
        raise HTTPException(403,"Band owner permission required")
    target=con.execute("""SELECT u.id FROM users u
       JOIN band_users bu ON u.id=bu.user_id
       WHERE bu.band_id=? AND u.email=?""",(band_id,target_email.strip().lower())).fetchone()
    if not target:
        raise HTTPException(404,"Member account not found")
    # Do not allow an owner to use this path to reset another owner.
    target_roles=[r["role"] for r in con.execute("SELECT role FROM band_users WHERE user_id=?",
                                                  (target["id"],))]
    if "owner" in target_roles:
        raise HTTPException(403,"Owner accounts require separate verified recovery")
    token=secrets.token_urlsafe(32)
    con.execute("DELETE FROM account_recovery WHERE user_id=?",(target["id"],))
    con.execute("""INSERT INTO account_recovery(token_hash,user_id,issuer_id,expires_at,created_at)
                   VALUES(?,?,?,?,?)""",
                (hashlib.sha256(token.encode()).hexdigest(),target["id"],issuer_id,now+1800,now))
    return token

def redeem(con, token, new_password, now=None):
    now=int(time.time()) if now is None else now
    digest=hashlib.sha256(token.encode()).hexdigest()
    row=con.execute("""SELECT user_id FROM account_recovery
                       WHERE token_hash=? AND redeemed_at IS NULL AND expires_at>?""",
                    (digest,now)).fetchone()
    if not row:
        raise HTTPException(400,"Recovery code invalid or expired")
    new_hash=hash_password(new_password)
    con.execute("UPDATE users SET password_hash=? WHERE id=?",(new_hash,row["user_id"]))
    con.execute("DELETE FROM sessions WHERE user_id=?",(row["user_id"],))
    con.execute("DELETE FROM account_recovery WHERE user_id=?",(row["user_id"],))
    return {"recovered":True,"sessions_revoked":True}
