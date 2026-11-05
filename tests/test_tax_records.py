import importlib
from fastapi.testclient import TestClient

def test_mileage_and_neutral_year_end_export(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_DB",str(tmp_path/"tax.db"))
    monkeypatch.setenv("BACKLINE_LOCAL_DEV","1")
    import src.app as module
    importlib.reload(module)
    client=TestClient(module.app)
    band=client.post("/api/bands",json={"name":"Band"}).json()["id"]
    other=client.post("/api/bands",json={"name":"Other"}).json()["id"]
    gig=client.post(f"/api/bands/{band}/events",json={
        "kind":"Gig","title":"Show","date":"2026-11-14","venue":"Venue"}).json()["id"]
    record={"date":"2026-11-14","purpose":"Travel to show","origin":"Minneapolis MN",
            "destination":"Madison WI","miles":270.5,"event_id":gig}
    response=client.post(f"/api/bands/{band}/trips",json=record)
    assert response.status_code==201,response.text
    assert client.post(f"/api/bands/{other}/trips",json=record).status_code==422
    assert len(client.get(f"/api/bands/{band}/trips?year=2026").json())==1
    csv=client.get(f"/api/bands/{band}/tax-export/2026")
    assert csv.status_code==200
    assert "mileage" in csv.text and "270.50" in csv.text
    assert "Madison WI" in csv.text
    assert "Travel to show" in csv.text
    assert client.get(f"/api/bands/{other}/tax-export/2026").status_code==200
    assert "Madison WI" not in client.get(f"/api/bands/{other}/tax-export/2026").text
