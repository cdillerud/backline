import base64
import importlib
from fastapi.testclient import TestClient

def test_show_files_are_private_to_gig_and_band(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_DB",str(tmp_path/"files.db"))
    monkeypatch.setenv("BACKLINE_LOCAL_DEV","1")
    import src.app as module
    importlib.reload(module)
    client=TestClient(module.app)
    first=client.post("/api/bands",json={"name":"First"}).json()["id"]
    second=client.post("/api/bands",json={"name":"Second"}).json()["id"]
    event=client.post(f"/api/bands/{first}/events",json={
        "kind":"Gig","title":"Show","venue":"Club","date":"2026-11-14"}).json()["id"]
    pdf=b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\n%%EOF"
    path=f"/api/bands/{first}/gigs/{event}/files"
    data={"filename":"Band Contract.pdf","category":"contract",
          "data_base64":base64.b64encode(pdf).decode()}
    uploaded=client.post(path,json=data)
    assert uploaded.status_code==201,uploaded.text
    file_id=uploaded.json()["id"]
    assert client.get(path).json()[0]["category"]=="contract"
    got=client.get(f"{path}/{file_id}/download")
    assert got.status_code==200 and got.content==pdf
    assert got.headers["cache-control"]=="no-store"
    assert client.get(f"/api/bands/{second}/gigs/{event}/files").status_code==404
    assert client.get(f"/api/bands/{second}/gigs/{event}/files/{file_id}/download").status_code==404
    assert client.post(path,json={**data,"category":"unsupported"}).status_code==422
    assert client.post(path,json={**data,"data_base64":"not-valid"}).status_code==422
