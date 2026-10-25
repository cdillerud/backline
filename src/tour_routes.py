"""Band-scoped tour routing and itinerary foundation.

Stops are chronological; geographical routing times require a licensed maps
provider and are intentionally not guessed here.
"""
import datetime
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
router=APIRouter()
class TourInput(BaseModel):
    name:str=Field(min_length=1,max_length=140)
    notes:str=Field(default='',max_length=2000)
class StopInput(BaseModel):
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
    def add_stop(band_id:int,tour_id:int,data:StopInput):
        with db() as con:
            tour(con,band_id,tour_id)
            if data.event_id is not None:
                event=con.execute("""SELECT date,venue FROM events
                    WHERE id=? AND band_id=? AND kind='Gig'""",(data.event_id,band_id)).fetchone()
                if not event:raise HTTPException(422,"Linked gig not found in band")
                if event["date"]!=str(data.date):raise HTTPException(422,"Stop date must match linked gig")
            values=(tour_id,band_id,data.event_id,str(data.date),data.city.strip(),data.region.strip(),
                    data.venue.strip(),data.status,data.arrival_time,data.departure_time,
                    data.lodging,data.travel_notes)
            try:row=con.execute("""INSERT INTO tour_stops(tour_id,band_id,event_id,stop_date,
                city,region,venue,status,arrival_time,departure_time,lodging,travel_notes)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",values)
            except Exception as exc:
                if "UNIQUE constraint" in str(exc):raise HTTPException(409,"Gig already linked to tour") from None
                raise
            return {"id":row.lastrowid}
    @router.get('/api/bands/{band_id}/tours/{tour_id}/route')
    def route(band_id:int,tour_id:int):
        with db() as con:
            info=dict(tour(con,band_id,tour_id))
            stops=[dict(r) for r in con.execute("""SELECT * FROM tour_stops
                WHERE band_id=? AND tour_id=? ORDER BY stop_date,id""",(band_id,tour_id))]
        warnings=[]
        previous=None
        for stop in stops:
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
