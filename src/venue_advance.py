"""Band- and gig-scoped venue advancement confirmations."""
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router=APIRouter()
class Advance(BaseModel):
    venue_contact:str=Field(default="",max_length=150)
    production_contact:str=Field(default="",max_length=150)
    contact_email:str=Field(default="",max_length=200)
    contact_phone:str=Field(default="",max_length=80)
    load_in:str=Field(default="",max_length=30)
    soundcheck:str=Field(default="",max_length=30)
    doors:str=Field(default="",max_length=30)
    show_time:str=Field(default="",max_length=30)
    curfew:str=Field(default="",max_length=30)
    parking:str=Field(default="",max_length=1000)
    open_questions:str=Field(default="",max_length=3000)
    status:str=Field(default="draft",pattern="^(draft|awaiting_venue|confirmed)$")

def setup(con):
    con.execute("""CREATE TABLE IF NOT EXISTS venue_advances(
      event_id INTEGER PRIMARY KEY REFERENCES events(id),
      band_id INTEGER NOT NULL REFERENCES bands(id),
      body_json TEXT NOT NULL,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

def attach(db):
    def check(con,band_id,event_id):
        if not con.execute("SELECT 1 FROM events WHERE id=? AND band_id=? AND kind='Gig'",
                           (event_id,band_id)).fetchone():
            raise HTTPException(404,"Gig not found")
    @router.get("/api/bands/{band_id}/gigs/{event_id}/advance")
    def read_advance(band_id:int,event_id:int):
        with db() as con:
            check(con,band_id,event_id)
            row=con.execute("SELECT body_json FROM venue_advances WHERE band_id=? AND event_id=?",
                            (band_id,event_id)).fetchone()
            return json.loads(row["body_json"]) if row else Advance().model_dump()
    @router.put("/api/bands/{band_id}/gigs/{event_id}/advance")
    def save_advance(band_id:int,event_id:int,data:Advance):
        if data.status=="confirmed" and (not data.venue_contact.strip() or not data.load_in.strip()
            or not data.soundcheck.strip() or not data.doors.strip() or not data.show_time.strip()
            or data.open_questions.strip()):
            raise HTTPException(422,"Confirm venue contact and show times, and resolve open questions first")
        with db() as con:
            check(con,band_id,event_id)
            con.execute("""INSERT INTO venue_advances(event_id,band_id,body_json)
                VALUES(?,?,?) ON CONFLICT(event_id) DO UPDATE SET body_json=excluded.body_json,
                updated_at=CURRENT_TIMESTAMP""",(event_id,band_id,data.model_dump_json()))
            return {"saved":True,"status":data.status}
    return router
