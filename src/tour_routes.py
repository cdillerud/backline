"""Band-scoped tour routing and itinerary foundation.

Stops are chronological; geographical routing times require a licensed maps
provider and are intentionally not guessed here.
"""
import datetime
import json
from .show_schedule import TIME_PATTERN, show_timeline
from fastapi import APIRouter,HTTPException,Request
from .operations_audit import record_change,current_revision,check_revision,user_id
from pydantic import BaseModel,Field,field_validator
router=APIRouter()
class TourInput(BaseModel):
    name:str=Field(min_length=1,max_length=140)
    notes:str=Field(default='',max_length=2000)
class StopInput(BaseModel):
    revision:int|None=Field(default=None,ge=0)
    change_reason:str=Field(default="",max_length=500)
    date:datetime.date
    city:str=Field(min_length=1,max_length=120)
    region:str=Field(default='',max_length=80)
    venue:str=Field(default='',max_length=160)
    event_id:int|None=None
    status:str=Field(default='planned',pattern='^(planned|hold|confirmed|cancelled|travel)$')
    arrival_time:str=Field(default='',max_length=20)
    departure_time:str=Field(default='',max_length=20)
    lodging:str=Field(default='',max_length=250)
    travel_notes:str=Field(default='',max_length=2000)
    @field_validator("city")
    @classmethod
    def city_not_blank(cls,value):
        if not value.strip():raise ValueError("City is required")
        return value.strip()

    @field_validator("arrival_time","departure_time")
    @classmethod
    def clock_time(cls,value):
        if value and not TIME_PATTERN.fullmatch(value):raise ValueError("Use 24-hour HH:MM time")
        return value

def setup(con):
    con.executescript("""CREATE TABLE IF NOT EXISTS tours(
      id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),
      name TEXT NOT NULL,notes TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS tour_stops(
      id INTEGER PRIMARY KEY,tour_id INTEGER NOT NULL REFERENCES tours(id),
      band_id INTEGER NOT NULL REFERENCES bands(id),
      event_id INTEGER REFERENCES events(id),
      stop_date TEXT NOT NULL,city TEXT NOT NULL,region TEXT NOT NULL DEFAULT '',
      venue TEXT NOT NULL DEFAULT '',status TEXT NOT NULL,
      arrival_time TEXT NOT NULL DEFAULT '',departure_time TEXT NOT NULL DEFAULT '',
      lodging TEXT NOT NULL DEFAULT '',travel_notes TEXT NOT NULL DEFAULT '',
      UNIQUE(tour_id,event_id));""")
def attach(db):
    def tour(con,band_id,tour_id):
        row=con.execute("SELECT * FROM tours WHERE id=? AND band_id=?",(tour_id,band_id)).fetchone()
        if not row:raise HTTPException(404,"Tour not found")
        return row
    def validate_link(con,band_id,data):
        if data.event_id is not None:
            event=con.execute("SELECT date FROM events WHERE id=? AND band_id=? AND kind='Gig'",
                              (data.event_id,band_id)).fetchone()
            if not event:raise HTTPException(422,"Linked gig not found in band")
            if event["date"]!=str(data.date):raise HTTPException(422,"Stop date must match linked gig")
    @router.post('/api/bands/{band_id}/tours',status_code=201)
    def create_tour(band_id:int,data:TourInput):
        with db() as con:
            if not con.execute("SELECT 1 FROM bands WHERE id=?",(band_id,)).fetchone():
                raise HTTPException(404,"Band not found")
            row=con.execute("INSERT INTO tours(band_id,name,notes) VALUES(?,?,?)",
                            (band_id,data.name.strip(),data.notes))
            return {"id":row.lastrowid}
    @router.get('/api/bands/{band_id}/tours')
    def list_tours(band_id:int):
        with db() as con:
            if not con.execute("SELECT 1 FROM bands WHERE id=?",(band_id,)).fetchone():
                raise HTTPException(404,"Band not found")
            return [dict(row) for row in con.execute("SELECT * FROM tours WHERE band_id=? ORDER BY id DESC",(band_id,))]
    @router.post('/api/bands/{band_id}/tours/{tour_id}/stops',status_code=201)
    def add_stop(band_id:int,tour_id:int,data:StopInput,request:Request):
        with db() as con:
            tour(con,band_id,tour_id)
            validate_link(con,band_id,data)
            values=(tour_id,band_id,data.event_id,str(data.date),data.city.strip(),data.region.strip(),
                    data.venue.strip(),data.status,data.arrival_time,data.departure_time,
                    data.lodging,data.travel_notes)
            try:row=con.execute("""INSERT INTO tour_stops(tour_id,band_id,event_id,stop_date,
                city,region,venue,status,arrival_time,departure_time,lodging,travel_notes)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",values)
            except Exception as exc:
                if "UNIQUE constraint" in str(exc):raise HTTPException(409,"Gig already linked to tour") from None
                raise
            record_change(con,band_id,'tour_stop',row.lastrowid,None,data.model_dump(mode='json',exclude={'revision','change_reason'}),user_id(request),data.event_id,data.change_reason)
            return {"id":row.lastrowid}
    @router.put('/api/bands/{band_id}/tours/{tour_id}/stops/{stop_id}')
    def edit_stop(band_id:int,tour_id:int,stop_id:int,data:StopInput,request:Request):
        with db() as con:
            con.execute('BEGIN IMMEDIATE')
            tour(con,band_id,tour_id)
            check_revision(con,band_id,'tour_stop',stop_id,data.revision)
            previous=con.execute('SELECT * FROM tour_stops WHERE id=? AND tour_id=? AND band_id=?',(stop_id,tour_id,band_id)).fetchone()
            if not con.execute("SELECT 1 FROM tour_stops WHERE id=? AND tour_id=? AND band_id=?",
                               (stop_id,tour_id,band_id)).fetchone():raise HTTPException(404,"Stop not found")
            validate_link(con,band_id,data)
            before={key:previous[key] for key in ('city','region','venue','event_id','status','arrival_time','departure_time','lodging','travel_notes')}
            before['date']=previous['stop_date']
            record_change(con,band_id,'tour_stop',stop_id,before,data.model_dump(mode='json',exclude={'revision','change_reason'}),user_id(request),data.event_id,data.change_reason)
            try:
                con.execute("""UPDATE tour_stops SET event_id=?,stop_date=?,city=?,region=?,venue=?,status=?,
                    arrival_time=?,departure_time=?,lodging=?,travel_notes=? WHERE id=? AND tour_id=? AND band_id=?""",
                    (data.event_id,str(data.date),data.city,data.region.strip(),data.venue.strip(),data.status,
                     data.arrival_time,data.departure_time,data.lodging,data.travel_notes,stop_id,tour_id,band_id))
            except Exception as exc:
                if "UNIQUE constraint" in str(exc):raise HTTPException(409,"Gig already linked to tour") from None
                raise
        return {"updated":True}
    @router.get('/api/bands/{band_id}/tours/{tour_id}/route')
    def route(band_id:int,tour_id:int):
        with db() as con:
            con.execute('BEGIN')
            info=dict(tour(con,band_id,tour_id))
            stops=[dict(r) for r in con.execute("""SELECT * FROM tour_stops
                WHERE band_id=? AND tour_id=? ORDER BY stop_date,id""",(band_id,tour_id))]
            for stop in stops:
                stop["revision"]=current_revision(con,band_id,"tour_stop",stop["id"])
                stop["advance"]=None
                if stop["event_id"] is not None:
                    row=con.execute("""SELECT e.date,e.venue,e.title,a.body_json FROM events e
                        LEFT JOIN venue_advances a ON a.event_id=e.id AND a.band_id=e.band_id
                        WHERE e.id=? AND e.band_id=? AND e.kind='Gig'""",(stop["event_id"],band_id)).fetchone()
                    if row:
                        advance=json.loads(row["body_json"]) if row["body_json"] else {}
                        stop["advance"]={"gig_title":row["title"],"gig_date":row["date"],"venue":row["venue"],
                            "venue_contact":advance.get("venue_contact",""),"contact_phone":advance.get("contact_phone",""),
                            "parking":advance.get("parking",""),"timeline":show_timeline(advance)}
        warnings=[]
        previous=None
        for stop in stops:
            if stop["status"]=="cancelled":continue
            if stop["advance"] and stop["advance"]["gig_date"]!=stop["stop_date"]:
                warnings.append({"stop_id":stop["id"],"type":"gig_date_changed","message":"Linked gig date has changed; update this stop before travel"})
            if previous:
                span=(datetime.date.fromisoformat(stop["stop_date"])-
                      datetime.date.fromisoformat(previous["stop_date"])).days
                if span==0 and (stop["city"],stop["region"])!=(previous["city"],previous["region"]):
                    warnings.append({"stop_id":stop["id"],"type":"same_day_different_city",
                                     "message":"Same-day stops in different cities require travel verification"})
                if span==1 and (stop["city"],stop["region"])!=(previous["city"],previous["region"]):
                    warnings.append({"stop_id":stop["id"],"type":"overnight_transfer",
                                     "message":"Next-day travel needs a checked driving time and rest plan"})
            previous=stop
        return {"tour":info,"stops":stops,"warnings":warnings,
                "drive_time_status":"not_calculated",
                "note":"Stop order follows dates; no driving distances or routing optimization inferred"}
    return router
