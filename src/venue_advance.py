"""Band- and gig-scoped venue advancement confirmations."""
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from .show_schedule import MILESTONES, TIME_PATTERN, valid_timezone, show_timeline

router=APIRouter()
class ScheduleEntry(BaseModel):
    title:str=Field(min_length=1,max_length=120)
    time:str=Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    day_offset:int=Field(default=0,ge=0,le=2)
    owner:str=Field(default="",max_length=150)
    location:str=Field(default="",max_length=200)
    notes:str=Field(default="",max_length=1000)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls,value):
        if not value.strip():raise ValueError("Schedule title is required")
        return value.strip()

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
    timezone:str=Field(default="",max_length=100)
    day_offsets:dict[str,int]=Field(default_factory=dict,max_length=5)
    schedule:list[ScheduleEntry]=Field(default_factory=list,max_length=50)
    venue_address:str=Field(default="",max_length=500)
    lodging:str=Field(default="",max_length=1000)
    hospitality:str=Field(default="",max_length=1000)
    settlement:str=Field(default="",max_length=1000)

    @field_validator("load_in","soundcheck","doors","show_time","curfew")
    @classmethod
    def clock_time(cls,value):
        if value and not TIME_PATTERN.fullmatch(value):raise ValueError("Use 24-hour HH:MM time")
        return value

    @field_validator("timezone")
    @classmethod
    def venue_timezone(cls,value):
        if value and not valid_timezone(value):raise ValueError("Use a valid IANA time zone, such as America/Chicago")
        return value

    @field_validator("day_offsets")
    @classmethod
    def schedule_days(cls,value):
        if any(key not in dict(MILESTONES) or day not in (0,1,2) for key,day in value.items()):
            raise ValueError("Day offsets must be 0, 1 or 2 for show milestones")
        return value

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
    @router.get("/api/bands/{band_id}/gigs/{event_id}/timeline")
    def timeline(band_id:int,event_id:int):
        return show_timeline(read_advance(band_id,event_id))
    @router.put("/api/bands/{band_id}/gigs/{event_id}/advance")
    def save_advance(band_id:int,event_id:int,data:Advance):
        if data.status=="confirmed" and (not data.venue_contact.strip() or not data.load_in.strip()
            or not data.soundcheck.strip() or not data.doors.strip() or not data.show_time.strip()
            or data.open_questions.strip()):
            raise HTTPException(422,"Confirm venue contact and show times, and resolve open questions first")
        if data.status=="confirmed":
            warnings=show_timeline(data.model_dump())["warnings"]
            if warnings:raise HTTPException(422," ".join(warnings))
        with db() as con:
            check(con,band_id,event_id)
            con.execute("""INSERT INTO venue_advances(event_id,band_id,body_json)
                VALUES(?,?,?) ON CONFLICT(event_id) DO UPDATE SET body_json=excluded.body_json,
                updated_at=CURRENT_TIMESTAMP""",(event_id,band_id,data.model_dump_json()))
            return {"saved":True,"status":data.status}
    return router
