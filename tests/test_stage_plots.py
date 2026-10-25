import importlib
from fastapi.testclient import TestClient

def test_stage_plot_and_inputs_are_scoped_and_validated(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_DB",str(tmp_path/"stage.db"))
    monkeypatch.setenv("BACKLINE_LOCAL_DEV","1")
    import src.app as module
    importlib.reload(module)
    client=TestClient(module.app)
    band=client.post("/api/bands",json={"name":"Band"}).json()["id"]
    other=client.post("/api/bands",json={"name":"Other"}).json()["id"]
    gig=client.post(f"/api/bands/{band}/events",json={
        "kind":"Gig","title":"Live","date":"2026-11-14"}).json()["id"]
    endpoint=f"/api/bands/{band}/gigs/{gig}/stage"
    stage={"notes":"Downstage is y=100","items":[{"label":"Lead vocal","kind":"vocal","x":50,"y":85}],
           "inputs":[{"channel":1,"source":"Lead vocal","microphone":"SM58","stand":"boom"}]}
    assert client.get(endpoint).json()["inputs"]==[]
    assert client.put(endpoint,json=stage).json()["input_count"]==1
    assert client.get(endpoint).json()["items"][0]["x"]==50
    svg=client.get(endpoint+".svg")
    assert svg.status_code==200
    assert 'Lead vocal' in svg.text
    csv=client.get(f"/api/bands/{band}/gigs/{gig}/inputs.csv")
    assert csv.status_code==200
    assert "Channel,Source" in csv.text and "Lead vocal" in csv.text
    assert client.put(endpoint,json={**stage,"inputs":stage["inputs"]*2}).status_code==422
    assert client.put(endpoint,json={**stage,"items":[{**stage["items"][0],"x":101}]}).status_code==422
    assert client.get(f"/api/bands/{other}/gigs/{gig}/stage").status_code==404
    assert client.put(f"/api/bands/{other}/gigs/{gig}/stage",json=stage).status_code==404
