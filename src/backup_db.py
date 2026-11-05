"""Create a consistent SQLite backup, verify its integrity, and emit SHA-256 evidence.

Usage: python -m src.backup_db --source /data/backline.db --destination /secure/backups/backline-YYYYMMDD.db
This is an *onsite* backup only. Copy snapshots into encrypted offsite storage as a separate approved step.
Never use untrusted destination paths from a web request.
"""
import argparse
import hashlib
import os
from pathlib import Path
import sqlite3
import sys

def backup(source, destination):
    source=Path(source)
    destination=Path(destination)
    if not source.is_file():
        raise ValueError('Source SQLite database not found')
    if source.resolve()==destination.resolve():
        raise ValueError('Backup destination must differ from source')
    if destination.exists():
        raise ValueError('Backup destination already exists; refusing overwrite')
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Open an exclusively created target to avoid a race against another backup.
    fd=os.open(str(destination),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    os.close(fd)
    try:
        with sqlite3.connect(f'file:{source.resolve()}?mode=ro',uri=True) as src:
            with sqlite3.connect(str(destination)) as dst:
                src.backup(dst)
        with sqlite3.connect(f'file:{destination.resolve()}?mode=ro',uri=True) as check:
            result=check.execute('PRAGMA integrity_check').fetchone()[0]
            if result!='ok':
                raise ValueError('Backup failed integrity check: '+str(result))
        digest=hashlib.sha256()
        with destination.open('rb') as reader:
            for part in iter(lambda:reader.read(1024*1024),b''):
                digest.update(part)
        return {'path':str(destination),'bytes':destination.stat().st_size,'sha256':digest.hexdigest(),'integrity':'ok'}
    except Exception:
        destination.unlink(missing_ok=True)
        raise

def main():
    parser=argparse.ArgumentParser(description='Backline SQLite verified snapshot')
    parser.add_argument('--source',required=True)
    parser.add_argument('--destination',required=True)
    args=parser.parse_args()
    try:
        evidence=backup(args.source,args.destination)
    except (ValueError,sqlite3.Error,OSError) as err:
        print('Backup failed: '+str(err),file=sys.stderr)
        return 1
    for key,val in evidence.items():
        print(f'{key}: {val}')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
