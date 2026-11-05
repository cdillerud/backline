import sqlite3
from src.rehearse_migration import rehearse

def test_migration_rehearsal_leaves_original_intact(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_LOCAL_DEV","1")
    db=tmp_path/"legacy.db"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE bands(id INTEGER PRIMARY KEY,name TEXT NOT NULL,genre TEXT NOT NULL DEFAULT '',description TEXT NOT NULL DEFAULT '')")
        c.execute("INSERT INTO bands(name,genre,description) VALUES('Legacy band','Rock','Preserve')")
    original=db.read_bytes()
    result=rehearse(db)
    assert result["result"]=="PASS"
    assert result["records_verified"] is True
    assert result["foreign_keys_verified"] is True
    assert result["source_unchanged"] is True
    assert result["preexisting_rows"]["bands"]==1
    assert db.read_bytes()==original

def test_fingerprints_detect_same_count_edits(tmp_path):
    from src.rehearse_migration import fingerprints
    p=tmp_path/"fingerprint.db"
    with sqlite3.connect(p) as db:
        db.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, label TEXT)")
        db.execute("INSERT INTO sample VALUES(1,'before')")
    before=fingerprints(p)
    with sqlite3.connect(p) as db:
        db.execute("UPDATE sample SET label='after' WHERE id=1")
    assert fingerprints(p)["sample"]["rows"]==before["sample"]["rows"]
    assert fingerprints(p)["sample"]["sha256"]!=before["sample"]["sha256"]
