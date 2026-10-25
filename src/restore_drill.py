"""Isolated Backline SQLite restore drill. Never overwrites an existing database."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from .backup_db import backup

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as file:
        for chunk in iter(lambda:file.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def restore_drill(snapshot):
    snapshot=Path(snapshot)
    if not snapshot.is_file():
        raise ValueError('Snapshot not found')
    with sqlite3.connect(f'file:{snapshot.resolve()}?mode=ro',uri=True) as con:
        if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('Source snapshot integrity check failed')
    with tempfile.TemporaryDirectory(prefix='backline-restore-') as folder:
        destination=Path(folder)/'restored.db'
        evidence=backup(snapshot,destination)
        with sqlite3.connect(destination) as con:
            if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise ValueError('Restored database integrity check failed')
            foreign_keys=con.execute('PRAGMA foreign_key_check').fetchall()
            if foreign_keys:raise ValueError('Restored database has foreign key violations')
        from .rehearse_migration import fingerprints
        original=fingerprints(snapshot)
        restored=fingerprints(destination)
        if original!=restored:
            raise ValueError('Restored records differ from snapshot')
        return {'result':'PASS','restored_in_isolation':True,'records_verified':True,
                'foreign_keys_verified':True,'snapshot_sha256':sha256(snapshot),
                'restored_sha256':evidence['sha256'],'tables_checked':len(original)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--snapshot',required=True)
    args=p.parse_args()
    try:
        print(json.dumps(restore_drill(args.snapshot),indent=2))
        return 0
    except (ValueError,sqlite3.Error,OSError) as err:
        print('RESTORE DRILL FAILED: '+str(err),file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
