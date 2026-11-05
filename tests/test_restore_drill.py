import sqlite3
import pytest
from src.restore_drill import restore_drill

def test_restore_drill_preserves_snapshot(tmp_path):
    path=tmp_path/'snapshot.db'
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE bands (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO bands VALUES(1,'The Drunk Uncles')")
    before=path.read_bytes()
    result=restore_drill(path)
    assert result['result']=='PASS'
    assert result['records_verified'] is True
    assert result['foreign_keys_verified'] is True
    assert result['tables_checked']==1
    assert path.read_bytes()==before
    assert len(result['snapshot_sha256'])==64
    assert len(result['restored_sha256'])==64
    # SQLite online backups preserve database contents, not physical file bytes.

def test_restore_drill_rejects_missing_snapshot(tmp_path):
    with pytest.raises(ValueError,match='not found'):
        restore_drill(tmp_path/'missing.db')
