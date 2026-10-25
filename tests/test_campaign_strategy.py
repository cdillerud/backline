import importlib
from fastapi.testclient import TestClient
from src.campaign_strategy import strategy,drafts

def test_campaign_strategy_marks_market_claims_as_hypotheses():
    gig={"date":"2026-11-14","venue":"The Room","title":"A Gig"}
    band={"name":"The Drunk Uncles"}
    nearby=[{"event_date":"2026-11-14","title":"Another Show","source_url":"https://example.com/event"}]
    output=drafts(gig,band,nearby)
    assert output["generated_by"]=="deterministic_template"
    assert output["published"] is False
    assert output["strategy"]["angles"][1]["confidence"]=="medium"
    assert output["strategy"]["angles"][1]["evidence"][0]["url"]=="https://example.com/event"
    assert all("Another Show" not in item["body"] for item in output["drafts"])
    assert "Admission or ticket information" in output["verification_required"]

def test_generated_drafts_are_never_auto_approved(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_DB",str(tmp_path/"studio.db"))
    monkeypatch.setenv("BACKLINE_LOCAL_DEV","1")
    import src.app as app_module
    importlib.reload(app_module)
    client=TestClient(app_module.app)
    band=client.post("/api/bands",json={"name":"Test Band"}).json()["id"]
    gig=client.post(f"/api/bands/{band}/events",json={
        "kind":"Gig","title":"Weekend","date":"2026-11-14","venue":"A Venue"}).json()["id"]
    prefix=f"/api/bands/{band}/gigs/{gig}/campaign"
    result=client.post(prefix+"/generate")
    assert result.status_code==200,result.text
    assert len(result.json()["draft_ids"])==3
    assert result.json()["published"] is False
    assert all(row["status"]=="draft" for row in client.get(prefix).json())
    draft_id=result.json()["draft_ids"][0]
    revision=client.patch(f"{prefix}/{draft_id}",json={
        "angle":"Edited angle","body":"Edited copy for review"})
    assert revision.status_code==200,revision.text
    assert client.get(prefix).json()[2]["body"]=="Edited copy for review"
    with app_module.db() as con:
        saved=con.execute("SELECT previous_body FROM gig_campaign_revisions WHERE draft_id=?",
                          (draft_id,)).fetchone()
        assert saved and saved[0]!="Edited copy for review"
    assert client.patch(f"{prefix}/{draft_id}",json={"angle":"","body":"copy"}).status_code==422
    assert client.post(f"{prefix}/{draft_id}/approve",json={"note":"Reviewed"}).status_code==200
    assert client.patch(f"{prefix}/{draft_id}",json={
        "angle":"Try again","body":"Should not change"}).status_code==409

    assert client.post(f"/api/bands/{band+10000}/gigs/{gig}/campaign/generate").status_code==404

def test_band_voice_changes_generated_copy(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_DB",str(tmp_path/"voice.db"))
    monkeypatch.setenv("BACKLINE_LOCAL_DEV","1")
    import src.app as app_module
    import importlib
    importlib.reload(app_module)
    client=TestClient(app_module.app)
    band=client.post("/api/bands",json={"name":"Voice Band"}).json()["id"]
    gig=client.post(f"/api/bands/{band}/events",json={"kind":"Gig",
        "title":"Tonight","date":"2026-11-14","venue":"Small Club"}).json()["id"]
    voice=client.put(f"/api/bands/{band}/marketing-voice",
        json={"tagline":"Loud and local.","tone":"gritty"})
    assert voice.status_code==200,voice.text
    assert client.get(f"/api/bands/{band}/marketing-voice").json()["tone"]=="gritty"
    assert client.put(f"/api/bands/{band}/marketing-voice",
        json={"tagline":"x","tone":"unsupported"}).status_code==422
    assert client.post(f"/api/bands/{band}/gigs/{gig}/campaign/generate").status_code==200
    rows=client.get(f"/api/bands/{band}/gigs/{gig}/campaign").json()
    assert any("Loud and local." in r["body"] for r in rows)
