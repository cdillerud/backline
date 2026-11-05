import sqlite3
import pytest
from src.backup_db import backup

def test_sqlite_verified_snapshot_preserves_records(tmp_path):
    source=tmp_path/'source.db'
    target=tmp_path/'snapshots'/'backup.db'
    with sqlite3.connect(source) as db:
        db.execute('CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)')
        db.execute("INSERT INTO sample(value) VALUES ('important record')")
    result=backup(source,target)
    assert result['integrity']=='ok'
    assert result['bytes']>0
    assert len(result['sha256'])==64
    with sqlite3.connect(target) as restored:
        assert restored.execute('SELECT value FROM sample').fetchone()[0]=='important record'
    with pytest.raises(ValueError,match='already exists'):
        backup(source,target)
    with pytest.raises(ValueError,match='must differ'):
        backup(source,source)
    assert target.exists()
