"""Private show-linked PDF records, with band and gig authorization."""
import base64
import binascii
import hashlib
import re
from fastapi import APIRouter,HTTPException,Response
from pydantic import BaseModel,Field
router=APIRouter()
MAX_BYTES=3*1024*1024
CATEGORIES={"contract","stage_plot","input_list","technical_rider","hospitality_rider","receipt","w9","insurance","other"}
class DocumentUpload(BaseModel):
    filename:str=Field(min_length=5,max_length=140)
    category:str
    data_base64:str=Field(min_length=16,max_length=4200000)
def setup(con):
    con.execute("""CREATE TABLE IF NOT EXISTS show_documents (
      id INTEGER PRIMARY KEY,
      band_id INTEGER NOT NULL REFERENCES bands(id),
      event_id INTEGER NOT NULL REFERENCES events(id),
      filename TEXT NOT NULL,category TEXT NOT NULL,sha256 TEXT NOT NULL,
      content BLOB NOT NULL,uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
def attach(db):
    def assert_gig(con,band,event):
        if not con.execute("SELECT 1 FROM events WHERE id=? AND band_id=? AND kind='Gig'",(event,band)).fetchone():
            raise HTTPException(404,"Gig not found")
    @router.get('/api/bands/{band_id}/gigs/{event_id}/files')
    def list_files(band_id:int,event_id:int):
        with db() as con:
            assert_gig(con,band_id,event_id)
            return [dict(row) for row in con.execute("""SELECT id,filename,category,sha256,
                length(content) AS size_bytes,uploaded_at FROM show_documents
                WHERE band_id=? AND event_id=? ORDER BY id DESC""",(band_id,event_id))]
    @router.post('/api/bands/{band_id}/gigs/{event_id}/files',status_code=201)
    def upload_file(band_id:int,event_id:int,data:DocumentUpload):
        if data.category not in CATEGORIES:raise HTTPException(422,"Invalid category")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _().-]{0,135}\.pdf",data.filename,re.I):
            raise HTTPException(422,"PDF filename required")
        try:raw=base64.b64decode(data.data_base64,validate=True)
        except (ValueError,binascii.Error):raise HTTPException(422,"Invalid encoding") from None
        if not 12<=len(raw)<=MAX_BYTES or not raw.startswith(b"%PDF-"):
            raise HTTPException(422,"Invalid or oversized PDF")
        digest=hashlib.sha256(raw).hexdigest()
        with db() as con:
            assert_gig(con,band_id,event_id)
            row=con.execute("""INSERT INTO show_documents(band_id,event_id,filename,category,sha256,content)
                VALUES(?,?,?,?,?,?)""",(band_id,event_id,data.filename,data.category,digest,raw))
            return {"id":row.lastrowid,"sha256":digest,"size_bytes":len(raw)}
    @router.get('/api/bands/{band_id}/gigs/{event_id}/files/{file_id}/download')
    def download_file(band_id:int,event_id:int,file_id:int):
        with db() as con:
            assert_gig(con,band_id,event_id)
            row=con.execute("""SELECT filename,content FROM show_documents WHERE
                id=? AND band_id=? AND event_id=?""",(file_id,band_id,event_id)).fetchone()
            if not row:raise HTTPException(404,"File not found")
            return Response(bytes(row["content"]),media_type="application/pdf",
                headers={"Content-Disposition":'attachment; filename="'+row["filename"]+'"',
                "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"})
    return router
