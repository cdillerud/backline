"""Isolated synthetic account bootstrap: never claim existing non-demo bands."""
import importlib
import pytest
from fastapi.testclient import TestClient

def test_authenticated_demo_requires_secret_and_fresh_database(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_DB",str(tmp_path/"demo.sqlite"))
    monkeypatch.setenv("BACKLINE_ACCOUNTS_ENABLED","1")
    monkeypatch.setenv("BACKLINE_DEMO_SEED","1")
    monkeypatch.setenv("BACKLINE_DEMO_ACCOUNTS","1")
    monkeypatch.setenv("BACKLINE_DEMO_PASSWORD","synthetic-password-not-for-production")
    import src.app as mod
    app=importlib.reload(mod)
    with app.db() as con:
        bands=con.execute("SELECT id,name FROM bands").fetchall()
        assert len(bands)==1 and bands[0]["name"]=="The Drunk Uncles (Demo)"
        assert con.execute("SELECT count(*) FROM users").fetchone()[0]==1
        assert con.execute("SELECT count(*) FROM discussion_threads").fetchone()[0]==1
        assert con.execute("SELECT count(*) FROM discussion_posts").fetchone()[0]==1
        assert con.execute("SELECT count(*) FROM event_rsvps").fetchone()[0]==1
        assert con.execute("SELECT count(*) FROM events WHERE kind='Rehearsal'").fetchone()[0]==1
        assert con.execute("SELECT count(*) FROM setlists").fetchone()[0]==1
        assert con.execute("SELECT count(*) FROM setlist_songs").fetchone()[0]==3
        assert con.execute("SELECT count(*) FROM workspace_tasks").fetchone()[0]==2
    client=TestClient(app.app)
    assert client.get("/api/bands").status_code==401
    login=client.post("/api/auth/login",json={"email":"demo-owner@example.test","password":"synthetic-password-not-for-production"})
    assert login.status_code==200,login.text
    token=login.json()["access_token"]
    headers={"Authorization":"Bearer "+token}
    assert client.get("/api/bands",headers=headers).status_code==200
    band_id=bands[0]["id"]
    assert client.get(f"/api/bands/{band_id}/discussions").status_code==401
    threads=client.get(f"/api/bands/{band_id}/discussions",headers=headers)
    assert threads.status_code==200,threads.text
    assert len(threads.json())==1
    thread_id=threads.json()[0]["id"]
    posts=client.get(f"/api/bands/{band_id}/discussions/{thread_id}/posts",headers=headers)
    assert posts.status_code==200,posts.text
    assert len(posts.json())==1
    events=client.get(f"/api/bands/{band_id}/events",headers=headers)
    assert events.status_code==200,events.text
    rsvps=client.get(f"/api/bands/{band_id}/events/{events.json()[0]['id']}/rsvps",headers=headers)
    assert rsvps.status_code==200,rsvps.text
    assert len(rsvps.json())==1
    # Calendar creation, band-scoped rescheduling, and access control.
    meeting=client.post(f"/api/bands/{band_id}/events",headers=headers,json={
        "kind":"Meeting","title":"Synthetic planning meeting","date":"2026-11-11",
        "venue":"Practice room","time":"19:00"})
    assert meeting.status_code==201,meeting.text
    meeting_id=meeting.json()["id"]
    assert client.put(f"/api/bands/{band_id}/events/{meeting_id}/reschedule",
        json={"date":"2026-11-12"}).status_code==401
    move=client.put(f"/api/bands/{band_id}/events/{meeting_id}/reschedule",
        headers=headers,json={"date":"2026-11-12"})
    assert move.status_code==200,move.text
    updated=client.get(f"/api/bands/{band_id}/events",headers=headers).json()
    assert next(e for e in updated if e["id"]==meeting_id)["date"]=="2026-11-12"
    assert next(e for e in updated if e["id"]==meeting_id)["kind"]=="Meeting"
    edit=client.put(f"/api/bands/{band_id}/events/{meeting_id}",headers=headers,json={
        "kind":"Meeting","title":"Updated synthetic planning meeting",
        "date":"2026-11-13","venue":"Revised room","time":"18:30","status":"Confirmed"})
    assert edit.status_code==200,edit.text
    updated=client.get(f"/api/bands/{band_id}/events",headers=headers).json()
    saved=next(e for e in updated if e["id"]==meeting_id)
    assert (saved["title"],saved["date"],saved["kind"],saved["status"]) == (
        "Updated synthetic planning meeting","2026-11-13","Meeting","Confirmed")
    assert client.put(f"/api/bands/{band_id}/events/{meeting_id}",json={
        "kind":"Meeting","title":"Forbidden","date":"2026-11-14"}).status_code==401

    assert client.put(f"/api/bands/{band_id}/events/999999/reschedule",
        headers=headers,json={"date":"2026-11-12"}).status_code==404
    app.init_db()  # restart does not duplicate accounts or tasks
    with app.db() as con:
        assert con.execute("SELECT count(*) FROM users").fetchone()[0]==1
        assert con.execute("SELECT count(*) FROM workspace_tasks").fetchone()[0]==2
    assert client.get("/api/bands",headers={"Authorization":"Bearer "+token}).status_code==200

def test_authenticated_demo_rejects_legacy_bands(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_DB",str(tmp_path/"legacy.sqlite"))
    monkeypatch.setenv("BACKLINE_ACCOUNTS_ENABLED","0")
    monkeypatch.delenv("BACKLINE_DEMO_ACCOUNTS",raising=False)
    monkeypatch.delenv("BACKLINE_DEMO_SEED",raising=False)
    import src.app as mod
    app=importlib.reload(mod)
    monkeypatch.setenv("BACKLINE_ACCOUNTS_ENABLED","1")
    monkeypatch.setenv("BACKLINE_DEMO_SEED","1")
    monkeypatch.setenv("BACKLINE_DEMO_ACCOUNTS","1")
    monkeypatch.setenv("BACKLINE_DEMO_PASSWORD","synthetic-password-not-for-production")
    with pytest.raises(RuntimeError,match="refuses existing non-demo data"):
        app.init_db()
