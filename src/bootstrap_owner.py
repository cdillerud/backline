"""Offline, explicit owner bootstrap. Never expose this operation over HTTP.

Run only against a backed-up database, on a trusted host with environment credentials:
  BACKLINE_DB=/path/to/backline.db BACKLINE_OWNER_EMAIL=... \
  BACKLINE_OWNER_NAME=... BACKLINE_OWNER_PASSWORD=... \
  python -m src.bootstrap_owner --band-id 1

This does not migrate or silently claim all existing bands.
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path
from .accounts import hash_password, account_tables

def bootstrap(path, email, name, password, band_id):
    database=Path(path)
    if not database.is_file():
        raise ValueError("Existing SQLite database required; refusing to create a new one")
    if not email or '@' not in email or not name.strip():
        raise ValueError("Valid email and display name required")
    con=sqlite3.connect(str(database), timeout=10)
    con.row_factory=sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        # Must not create tables as a side effect until app migration is reviewed.
        tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required={'bands','users','band_users'}
        if not required.issubset(tables):
            raise ValueError("Account migration missing; run app schema initialization first")
        con.execute("BEGIN IMMEDIATE")
        band=con.execute("SELECT id FROM bands WHERE id=?",(band_id,)).fetchone()
        if not band:
            raise ValueError("Specified band does not exist")
        owners=con.execute("SELECT COUNT(*) FROM band_users WHERE band_id=? AND role='owner'",(band_id,)).fetchone()[0]
        if owners:
            raise ValueError("Band already has an owner; refusing reassignment")
        normalized=email.strip().lower()
        user=con.execute("SELECT id FROM users WHERE email=?",(normalized,)).fetchone()
        if user:
            raise ValueError("Email already exists; use owner-reviewed membership management")
        row=con.execute("INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)",
           (normalized,name.strip(),hash_password(password)))
        con.execute("INSERT INTO band_users(band_id,user_id,role) VALUES(?,?,?)",
            (band_id,row.lastrowid,'owner'))
        con.commit()
        return {"band_id":band_id,"owner_email":normalized}
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def main():
    parser=argparse.ArgumentParser(description="Explicit offline first owner for one existing band")
    parser.add_argument("--band-id",type=int,required=True)
    args=parser.parse_args()
    try:
        result=bootstrap(os.environ.get("BACKLINE_DB",""),
            os.environ.get("BACKLINE_OWNER_EMAIL",""),
            os.environ.get("BACKLINE_OWNER_NAME",""),
            os.environ.get("BACKLINE_OWNER_PASSWORD",""),
            args.band_id)
    except (ValueError,sqlite3.Error) as error:
        print(f"Owner bootstrap denied: {error}",file=sys.stderr)
        return 1
    print(f"Owner created for band {result['band_id']} ({result['owner_email']})")
    return 0

if __name__=="__main__":
    sys.exit(main())
