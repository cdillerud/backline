"""Rehearse schema initialization on a verified copy; never modify the source DB."""
import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from .backup_db import backup

TABLES=("bands","members","events","songs","transactions","settlements","settlement_shares","setlists","setlist_songs")
def counts(path):
    with sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro",uri=True) as con:
        existing={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return {t:con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES if t in existing}

def rehearse(source):
    source=Path(source)
    if not source.is_file():raise ValueError("Existing database required")
    before=counts(source)
    with tempfile.TemporaryDirectory(prefix="backline-rehearsal-") as folder:
        copy=Path(folder)/"staging.db"
        evidence=backup(source,copy)
        env={**os.environ,"BACKLINE_DB":str(copy),"BACKLINE_ACCOUNTS_ENABLED":"0","BACKLINE_LOCAL_DEV":"1"}
        proc=subprocess.run([sys.executable,"-c","import src.app"],env=env,
            capture_output=True,text=True,timeout=40)
        if proc.returncode:
            raise RuntimeError("Isolated app schema initialization failed: "+proc.stderr[-2000:])
        after=counts(copy)
        if before!=after:
            raise RuntimeError(f"Existing row counts changed: {before} -> {after}")
        with sqlite3.connect(copy) as con:
            if con.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise RuntimeError("Staging copy integrity check failed")
            created={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        expected={"users","band_users","sessions","band_invites","account_recovery",
                  "booking_leads","booking_activity","gig_market_findings","gig_campaign_drafts"}
        missing=expected-created
        if missing:raise RuntimeError("Missing migrated tables: "+", ".join(sorted(missing)))
        return {"result":"PASS","source_unchanged":True,"preexisting_rows":before,
                "snapshot_sha256":evidence["sha256"],"schema_verified":True}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",required=True)
    args=parser.parse_args()
    try:print(json.dumps(rehearse(args.source),indent=2));return 0
    except (ValueError,sqlite3.Error,RuntimeError,subprocess.TimeoutExpired) as e:
        print("REHEARSAL FAILED: "+str(e),file=sys.stderr);return 1

if __name__=="__main__":
    raise SystemExit(main())
