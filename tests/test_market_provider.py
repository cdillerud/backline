import json
import importlib
from fastapi.testclient import TestClient
from src.market_provider import normalized,discover

SAMPLE={"_embedded":{"events":[{"name":"Nearby Concert","url":"https://www.ticketmaster.com/event/test","dates":{"start":{"localDate":"2026-11-14"}},"_embedded":{"venues":[{"name":"Local Theater"}]},"classifications":[{"segment":{"name":"Music"}}]}]}}

def test_adapter_requires_explicit_enablement(monkeypatch):
    monkeypatch.delenv("BACKLINE_MARKET_DISCOVERY_ENABLED",raising=False)
    monkeypatch.setenv("TICKETMASTER_API_KEY","sample")
    from fastapi import HTTPException
    import pytest
    with pytest.raises(HTTPException) as err:
        discover("Minneapolis","2026-11-14",lambda req:json.dumps(SAMPLE).encode())
    assert err.value.status_code==503

def test_adapter_normalizes_sources_and_keeps_secret_server_side(monkeypatch):
    monkeypatch.setenv("BACKLINE_MARKET_DISCOVERY_ENABLED","1")
    monkeypatch.setenv("TICKETMASTER_API_KEY","test-secret")
    def fetch(request):
        assert request.full_url.startswith("https://app.ticketmaster.com/")
        assert "apikey=test-secret" in request.full_url
        return json.dumps(SAMPLE).encode()
    result=discover("Minneapolis","2026-11-14",fetch)
    assert result[0]["title"]=="Nearby Concert"
    assert result[0]["venue"]=="Local Theater"
    assert "test-secret" not in str(result)

def test_discovery_persists_and_deduplicates_source(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_DB",str(tmp_path/"research.db"))
    monkeypatch.setenv("BACKLINE_LOCAL_DEV","1")
    import src.app as module
    importlib.reload(module)
    import src.ai_studio as studio
    studio.discover=lambda city,day:normalized(SAMPLE)
    client=TestClient(module.app)
    band=client.post("/api/bands",json={"name":"Band"}).json()["id"]
    gig=client.post(f"/api/bands/{band}/events",json={
        "kind":"Gig","title":"Gig","date":"2026-11-14"}).json()["id"]
    path=f"/api/bands/{band}/gigs/{gig}/market"
    assert client.post(path+"/discover?city=Minneapolis").json()["added"]==1
    assert client.post(path+"/discover?city=Minneapolis").json()["status"]=="cached"
    rows=client.get(path).json()
    assert len(rows)==1
    assert rows[0]["source_url"]=="https://www.ticketmaster.com/event/test"
