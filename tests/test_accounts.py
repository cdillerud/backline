"""Opt-in account permission tests. Not a production launch certification."""
import importlib
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient


def test_scoped_accounts_and_no_cross_band_access(monkeypatch):
    with tempfile.TemporaryDirectory() as temp:
        monkeypatch.setenv("BACKLINE_DB", str(Path(temp) / "accounts.db"))
        monkeypatch.setenv("BACKLINE_ACCOUNTS_ENABLED", "1")
        import src.app as application
        importlib.reload(application)
        from src.accounts import hash_password
        with application.db() as con:
            first=con.execute("INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)",
                ("one@example.test","One",hash_password("long-secret-one-123"))).lastrowid
            second=con.execute("INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)",
                ("two@example.test","Two",hash_password("long-secret-two-123"))).lastrowid
            b1=con.execute("INSERT INTO bands(name) VALUES('First band')").lastrowid
            b2=con.execute("INSERT INTO bands(name) VALUES('Second band')").lastrowid
            con.execute("INSERT INTO band_users VALUES(?,?,?)",(b1,first,"owner"))
            con.execute("INSERT INTO band_users VALUES(?,?,?)",(b2,second,"owner"))
        with TestClient(application.app) as client:
            assert client.get("/api/bands").status_code == 401
            # Invalid credentials are counted and eventually throttled.
            for attempt in range(4):
                bad=client.post("/api/auth/login",json={"email":"blocked@example.test","password":"wrong"})
                assert bad.status_code==401
            bad=client.post("/api/auth/login",json={"email":"blocked@example.test","password":"wrong"})
            assert bad.status_code==401
            assert client.post("/api/auth/login",json={"email":"blocked@example.test","password":"wrong"}).status_code==429
            response=client.post("/api/auth/login",json={"email":"one@example.test","password":"bad"})
            assert response.status_code == 401
            response=client.post("/api/auth/login",json={
                "email":"one@example.test","password":"long-secret-one-123"})
            assert response.status_code == 200
            h={"Authorization":"Bearer "+response.json()["access_token"]}
            visible=client.get("/api/bands",headers=h).json()
            assert [b["id"] for b in visible] == [b1]
            assert client.get(f"/api/bands/{b2}/members",headers=h).status_code == 403
            assert client.post(f"/api/bands/{b2}/members",headers=h,
                json={"name":"Infiltrator"}).status_code == 403
            assert client.get(f"/api/bands/{b2}/finance",headers=h).status_code == 403
            assert client.get(f"/api/bands/{b2}/bookings",headers=h).status_code == 403
            assert client.get(f"/api/bands/{b2}/booking-followups",headers=h).status_code == 403
            assert client.get(f"/api/bands/{b2}/gigs/123/market",headers=h).status_code == 403
            assert client.post(f"/api/bands/{b2}/bookings",headers=h,
                json={"venue":"Denied venue"}).status_code == 403
            assert client.post(f"/api/bands/{b2}/gigs/123/campaign",headers=h,
                json={"channel":"Email","angle":"No","body":"Denied"}).status_code == 403
            with application.db() as db:
                db.execute("INSERT INTO band_users VALUES(?,?,?)",(b1,second,"member"))
            second_login=client.post("/api/auth/login",json={
                "email":"two@example.test","password":"long-secret-two-123"}).json()
            h2={"Authorization":"Bearer "+second_login["access_token"]}
            assert client.get(f"/api/bands/{b1}/members",headers=h2).status_code == 200
            assert client.get(f"/api/bands/{b1}/finance",headers=h2).status_code == 403
            assert client.post(f"/api/bands/{b1}/bookings",headers=h2,
                json={"venue":"No member writes"}).status_code == 403
            assert client.post(f"/api/bands/{b1}/gigs/123/market",headers=h2,
                json={"title":"No","source_url":"https://example.com",
                "event_date":"2026-11-14"}).status_code == 403
            assert client.post(f"/api/bands/{b1}/members",headers=h,
                json={"name":"Allowed"}).status_code == 201
            created=client.post("/api/bands",headers=h,json={"name":"New act"})
            assert created.status_code == 201
            new_id=created.json()["id"]
            assert client.get(f"/api/bands/{new_id}/members",headers=h).status_code == 200
            assert client.get("/api/bands",headers=h).status_code == 200
            assert client.post("/api/auth/logout",headers=h).status_code == 200
            assert client.get("/api/auth/me",headers=h).status_code == 401
            assert client.post("/api/auth/logout",headers=h).status_code == 401
    monkeypatch.delenv("BACKLINE_ACCOUNTS_ENABLED",raising=False)
    importlib.reload(application)
