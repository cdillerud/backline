import importlib
from fastapi.testclient import TestClient

def test_reusable_show_packet_and_band_isolation(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_DB",str(tmp_path/"show_ops.db"))
    monkeypatch.setenv("BACKLINE_LOCAL_DEV","1")
    import src.app as module
    importlib.reload(module)
    client=TestClient(module.app)
    band=client.post("/api/bands",json={"name":"Drunk Uncles"}).json()["id"]
    other=client.post("/api/bands",json={"name":"Other Band"}).json()["id"]
    event=client.post(f"/api/bands/{band}/events",json={
        "kind":"Gig","title":"Friday Night","date":"2026-11-14","venue":"Club"}).json()["id"]
    defaults=client.get("/api/show-document-defaults").json()
    assert set(defaults)=={"technical_rider","hospitality_rider","show_advance","day_of_show","tour_call_sheet","settlement_sheet"}
    body={"kind":"technical_rider","title":"Our stage setup",
          "sections":[{"heading":"Inputs","body":"Two guitars, bass, drums, vocals"}]}
    made=client.post(f"/api/bands/{band}/show-templates",json=body)
    assert made.status_code==201,made.text
    template=made.json()["id"]
    assert client.post(f"/api/bands/{other}/gigs/{event}/packet",
        json={"kind":"technical_rider","template_id":template}).status_code==404
    endpoint=f"/api/bands/{band}/gigs/{event}/packet"
    created=client.post(endpoint,json={"kind":"technical_rider","template_id":template})
    assert created.status_code==201,created.text
    document=created.json()["id"]
    assert client.post(endpoint,json={"kind":"technical_rider"}).status_code==409
    assert client.get(endpoint).json()[0]["sections"]==body["sections"]
    updated={"title":"Updated rider","sections":[{"heading":"Monitor mixes","body":"Four wedges"}]}
    assert client.put(f"/api/bands/{band}/show-templates/{template}",json=updated).status_code==200
    assert client.get(endpoint).json()[0]["sections"]==body["sections"]
    assert client.put(f"{endpoint}/{document}",json=updated).json()["status"]=="draft"
    assert client.post(f"{endpoint}/{document}/ready").json()=={"status":"ready","sent":False}
    assert client.put(f"{endpoint}/{document}",json=updated).json()["status"]=="draft"
    assert client.get(f"/api/bands/{other}/gigs/{event}/packet").status_code==404
    assert client.get(endpoint).json()[0]["status"]=="draft"

def test_show_packet_requires_a_gig(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_DB",str(tmp_path/"rehearsal.db"))
    monkeypatch.setenv("BACKLINE_LOCAL_DEV","1")
    import src.app as module
    importlib.reload(module)
    client=TestClient(module.app)
    band=client.post("/api/bands",json={"name":"Band"}).json()["id"]
    rehearsal=client.post(f"/api/bands/{band}/events",json={
        "kind":"Rehearsal","title":"Practice","date":"2026-11-14"}).json()["id"]
    assert client.post(f"/api/bands/{band}/gigs/{rehearsal}/packet",
        json={"kind":"day_of_show"}).status_code==404

def test_downloadable_pdf_scoped_to_band_and_gig(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_DB",str(tmp_path/"pdf.db"))
    monkeypatch.setenv("BACKLINE_LOCAL_DEV","1")
    import src.app as module
    importlib.reload(module)
    client=TestClient(module.app)
    band=client.post("/api/bands",json={"name":"Example Quartet"}).json()["id"]
    other=client.post("/api/bands",json={"name":"Other Group"}).json()["id"]
    event=client.post(f"/api/bands/{band}/events",json={
        "kind":"Gig","title":"Evening Showcase","date":"2026-11-14","venue":"Demo Theater"}).json()["id"]
    endpoint=f"/api/bands/{band}/gigs/{event}/packet"
    assert client.post(endpoint,json={"kind":"day_of_show"}).status_code==201
    stage={"notes":"Bring 2 DI boxes", "items":[{"label":"Lead guitar","kind":"guitar","x":35,"y":50}],
           "inputs":[{"channel":1,"source":"Lead vocal","microphone":"SM58","stand":"Boom","notes":"Center"}]}
    saved=client.put(f"/api/bands/{band}/gigs/{event}/stage",json=stage)
    assert saved.status_code==200,saved.text
    response=client.get(endpoint+".pdf")
    assert response.status_code==200,response.text
    assert response.headers["content-type"].startswith("application/pdf")
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["cache-control"]=="no-store"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content)>1500
    assert client.get(f"/api/bands/{other}/gigs/{event}/packet.pdf").status_code==404
    assert client.get(f"/api/bands/{band}/gigs/999999/packet.pdf").status_code==404
