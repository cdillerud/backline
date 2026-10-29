import importlib
from fastapi.testclient import TestClient

def test_advancement_status_and_scope(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_DB",str(tmp_path/"advance.db"))
    monkeypatch.setenv("BACKLINE_LOCAL_DEV","1")
    import src.app as module
    importlib.reload(module)
    client=TestClient(module.app)
    band=client.post("/api/bands",json={"name":"Show Band"}).json()["id"]
    other=client.post("/api/bands",json={"name":"Other Band"}).json()["id"]
    gig=client.post(f"/api/bands/{band}/events",json={
        "kind":"Gig","title":"Sunday Show","date":"2026-11-15","venue":"Club"}).json()["id"]
    path=f"/api/bands/{band}/gigs/{gig}/advance"
    assert client.get(path).json()["status"]=="draft"
    assert client.get(f"/api/bands/{other}/gigs/{gig}/advance").status_code==404
    assert client.put(path,json={"status":"confirmed"}).status_code==422
    pending={"timezone":"America/Chicago","status":"awaiting_venue","venue_contact":"Pat",
             "load_in":"17:00","soundcheck":"18:00","doors":"19:00",
             "show_time":"20:00","open_questions":"Is parking available?"}
    assert client.put(path,json=pending).status_code==200
    assert client.get(path).json()["open_questions"]=="Is parking available?"
    pending["status"]="confirmed"
    assert client.put(path,json=pending).status_code==422
    pending["open_questions"]=""
    assert client.put(path,json=pending).json()["status"]=="confirmed"
    assert client.get(path).json()["status"]=="confirmed"
    assert client.put(f"/api/bands/{other}/gigs/{gig}/advance",json=pending).status_code==404
