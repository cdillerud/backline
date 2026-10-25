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

def fingerprints(path):
    """Hash ordered, typed data from every existing application table."""
    import hashlib
    import struct
    result={}
    with sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro",uri=True) as db:
        names=[r[0] for r in db.execute("""SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name""")]
        for name in names:
            quoted='"'+name.replace('"','""')+'"'
            fields=[r[1] for r in db.execute("PRAGMA table_info("+quoted+")")]
            if not fields:continue
            rows=db.execute("SELECT * FROM "+quoted+" ORDER BY rowid")
            digest=hashlib.sha256()
            count=0
            for row in rows:
                count+=1
                for value in row:
                    kind=b'N' if value is None else (b'B' if isinstance(value,bytes) else b'S')
                    payload=b'' if value is None else (value if isinstance(value,bytes) else str(value).encode('utf-8'))
                    digest.update(kind+struct.pack('>Q',len(payload))+payload)
            result[name]={'rows':count,'sha256':digest.hexdigest(),'columns':fields}
    return result

def rehearse(source):
    source=Path(source)
    if not source.is_file():raise ValueError("Existing database required")
    before=counts(source)
    original=fingerprints(source)
    with tempfile.TemporaryDirectory(prefix="backline-rehearsal-") as folder:
        copy=Path(folder)/"staging.db"
        evidence=backup(source,copy)
        env={**os.environ,"BACKLINE_DB":str(copy),"BACKLINE_ACCOUNTS_ENABLED":"0","BACKLINE_LOCAL_DEV":"1"}
        proc=subprocess.run([sys.executable,"-c","import src.app"],env=env,
            capture_output=True,text=True,timeout=40)
        if proc.returncode:
            raise RuntimeError("Isolated app schema initialization failed: "+proc.stderr[-2000:])
        after=counts(copy)
        migrated=fingerprints(copy)
        mutations={name for name in original if migrated.get(name)!=original[name]}
        if mutations:raise RuntimeError('Existing data changed: '+', '.join(sorted(mutations)))
        changed={name:(count,after.get(name)) for name,count in before.items() if after.get(name)!=count}
        if changed:
            raise RuntimeError(f"Existing row counts changed: {changed}")
        with sqlite3.connect(copy) as con:
            if con.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise RuntimeError("Staging copy integrity check failed")
            violations=con.execute('PRAGMA foreign_key_check').fetchall()
            if violations:raise RuntimeError('Foreign key violations found')
            created={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        expected={"users","band_users","sessions","band_invites","account_recovery",
                  "booking_leads","booking_activity","gig_market_findings","gig_campaign_drafts"}
        missing=expected-created
        if missing:raise RuntimeError("Missing migrated tables: "+", ".join(sorted(missing)))
        return {"result":"PASS","source_unchanged":True,"preexisting_rows":before,
                "snapshot_sha256":evidence["sha256"],"schema_verified":True,"records_verified":True,"foreign_keys_verified":True}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",required=True)
    args=parser.parse_args()
    try:print(json.dumps(rehearse(args.source),indent=2));return 0
    except (ValueError,sqlite3.Error,RuntimeError,subprocess.TimeoutExpired) as e:
        print("REHEARSAL FAILED: "+str(e),file=sys.stderr);return 1

if __name__=="__main__":
    raise SystemExit(main())
