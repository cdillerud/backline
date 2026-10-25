"""Booking CRM: venue pipeline and append-only contact activity history."""
import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router=APIRouter()
STAGES={'Researching','To Contact','Contacted','Follow Up','Negotiating','Hold','Confirmed','Declined','Closed'}
ACTIVITIES={'Email sent','Email received','Phone call','Text','Meeting','Note','Offer','Follow-up completed'}
def setup(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS booking_leads (
      id INTEGER PRIMARY KEY,
      band_id INTEGER NOT NULL REFERENCES bands(id),
      venue TEXT NOT NULL,
      contact_name TEXT NOT NULL DEFAULT '',
      contact_email TEXT NOT NULL DEFAULT '',
      contact_phone TEXT NOT NULL DEFAULT '',
      city TEXT NOT NULL DEFAULT '',
      stage TEXT NOT NULL DEFAULT 'To Contact',
      next_followup TEXT,
      target_date TEXT,
      notes TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_booking_band_followup ON booking_leads(band_id,next_followup);
    CREATE TABLE IF NOT EXISTS booking_activity (
      id INTEGER PRIMARY KEY,
      band_id INTEGER NOT NULL REFERENCES bands(id),
      lead_id INTEGER NOT NULL REFERENCES booking_leads(id),
      kind TEXT NOT NULL,
      detail TEXT NOT NULL,
      happened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_booking_activity_lead ON booking_activity(lead_id,happened_at,id);
    """)

class LeadInput(BaseModel):
    venue: str=Field(min_length=1,max_length=150)
    contact_name: str=Field(default='',max_length=120)
    contact_email: str=Field(default='',max_length=200)
    contact_phone: str=Field(default='',max_length=40)
    city: str=Field(default='',max_length=120)
    target_date: datetime.date|None=None
    next_followup: datetime.date|None=None
    notes: str=Field(default='',max_length=3000)
class StageInput(BaseModel):
    stage: str
    detail: str=Field(min_length=1,max_length=2000)
    next_followup: datetime.date|None=None
class ActivityInput(BaseModel):
    kind: str
    detail: str=Field(min_length=1,max_length=4000)
    happened_at: datetime.datetime|None=None
    next_followup: datetime.date|None=None

def attach(db):
    def valid_band(con,bid):
        if not con.execute('SELECT 1 FROM bands WHERE id=?',(bid,)).fetchone():
            raise HTTPException(404,'Band not found')
    def lead(con,bid,lid):
        row=con.execute('SELECT * FROM booking_leads WHERE id=? AND band_id=?',(lid,bid)).fetchone()
        if not row: raise HTTPException(404,'Booking prospect not found')
        return row
    @router.get('/api/bands/{band_id}/bookings')
    def bookings(band_id:int):
        with db() as con:
            valid_band(con,band_id)
            return [dict(r) for r in con.execute('''SELECT b.*,
                (SELECT MAX(happened_at) FROM booking_activity a WHERE a.lead_id=b.id) last_contact
                FROM booking_leads b WHERE band_id=?
                ORDER BY CASE WHEN stage IN ('Closed','Declined','Confirmed') THEN 1 ELSE 0 END,
                COALESCE(next_followup,'9999-12-31'),id DESC''',(band_id,))]
    @router.post('/api/bands/{band_id}/bookings',status_code=201)
    def create_booking(band_id:int,data:LeadInput):
        with db() as con:
            valid_band(con,band_id)
            cur=con.execute('''INSERT INTO booking_leads
                (band_id,venue,contact_name,contact_email,contact_phone,city,target_date,next_followup,notes)
                VALUES(?,?,?,?,?,?,?,?,?)''',(band_id,data.venue.strip(),data.contact_name,
                data.contact_email,data.contact_phone,data.city,
                str(data.target_date) if data.target_date else None,
                str(data.next_followup) if data.next_followup else None,data.notes))
            con.execute('INSERT INTO booking_activity(band_id,lead_id,kind,detail) VALUES(?,?,?,?)',
                        (band_id,cur.lastrowid,'Created','Booking prospect created'))
            return {'id':cur.lastrowid}
    @router.get('/api/bands/{band_id}/bookings/{booking_id}/activity')
    def history(band_id:int,booking_id:int):
        with db() as con:
            lead(con,band_id,booking_id)
            return [dict(r) for r in con.execute('''SELECT * FROM booking_activity
                WHERE band_id=? AND lead_id=? ORDER BY happened_at DESC,id DESC''',(band_id,booking_id))]
    @router.post('/api/bands/{band_id}/bookings/{booking_id}/activity',status_code=201)
    def record_activity(band_id:int,booking_id:int,data:ActivityInput):
        if data.kind not in ACTIVITIES: raise HTTPException(422,'Invalid activity type')
        with db() as con:
            lead(con,band_id,booking_id)
            # Append-only: earlier activity is never overwritten or deleted.
            cur=con.execute('''INSERT INTO booking_activity(band_id,lead_id,kind,detail,happened_at)
                VALUES(?,?,?,?,?)''',(band_id,booking_id,data.kind,data.detail,
                data.happened_at.isoformat() if data.happened_at else datetime.datetime.now(datetime.timezone.utc).isoformat()))
            if data.next_followup is not None:
                con.execute('UPDATE booking_leads SET next_followup=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',
                            (str(data.next_followup),booking_id))
            return {'id':cur.lastrowid}
    @router.post('/api/bands/{band_id}/bookings/{booking_id}/stage',status_code=201)
    def change_stage(band_id:int,booking_id:int,data:StageInput):
        if data.stage not in STAGES:raise HTTPException(422,'Invalid booking stage')
        with db() as con:
            current=lead(con,band_id,booking_id)
            if current['stage']==data.stage:raise HTTPException(409,'Stage unchanged')
            con.execute('''UPDATE booking_leads SET stage=?,next_followup=?,updated_at=CURRENT_TIMESTAMP
                WHERE id=?''',(data.stage,str(data.next_followup) if data.next_followup else None,booking_id))
            cur=con.execute('''INSERT INTO booking_activity(band_id,lead_id,kind,detail)
                VALUES(?,?,?,?)''',(band_id,booking_id,'Stage changed',
                f"{current['stage']} → {data.stage}: {data.detail}"))
            return {'id':cur.lastrowid,'stage':data.stage}
    return router
