import importlib
from fastapi.testclient import TestClient

def test_tour_ordering_and_travel_warnings(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_DB",str(tmp_path/"tour.db"))
    monkeypatch.setenv("BACKLINE_LOCAL_DEV","1")
    import src.app as module
    importlib.reload(module)
    client=TestClient(module.app)
    band=client.post("/api/bands",json={"name":"Touring Band"}).json()["id"]
    other=client.post("/api/bands",json={"name":"Other"}).json()["id"]
    gig=client.post(f"/api/bands/{band}/events",json={
        "kind":"Gig","title":"Opening night","date":"2026-11-13","venue":"First Club"}).json()["id"]
    tour=client.post(f"/api/bands/{band}/tours",json={"name":"Fall tour"}).json()["id"]
    base=f"/api/bands/{band}/tours/{tour}"
    next_day={"date":"2026-11-14","city":"Madison","region":"WI","status":"hold","venue":"Second Club"}
    assert client.post(base+"/stops",json=next_day).status_code==201
    first={"date":"2026-11-13","city":"Minneapolis","region":"MN","event_id":gig,
           "status":"confirmed","venue":"First Club"}
    assert client.post(base+"/stops",json=first).status_code==201
    route=client.get(base+"/route")
    assert route.status_code==200,route.text
    result=route.json()
    assert [s["city"] for s in result["stops"]]==["Minneapolis","Madison"]
    assert result["warnings"][0]["type"]=="overnight_transfer"
    assert result["drive_time_status"]=="not_calculated"
    assert client.post(base+"/stops",json={**first,"date":"2026-11-15"}).status_code==422
    assert client.post(base+"/stops",json=first).status_code==409
    assert client.get(f"/api/bands/{other}/tours/{tour}/route").status_code==404
    assert client.post(f"/api/bands/{other}/tours/{tour}/stops",json=next_day).status_code==404
