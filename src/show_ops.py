"""Band show-operation templates and gig-specific advances.

Templates are band-scoped. A show packet snapshots its chosen template so that
future template edits do not silently rewrite previously advanced shows.
"""
import json
from fastapi.responses import Response
from .show_pdf import create_show_pdf
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field

router=APIRouter()
KINDS={"technical_rider","hospitality_rider","show_advance","day_of_show","tour_call_sheet","settlement_sheet"}
DEFAULTS={
"technical_rider":{"title":"Technical rider","sections":[{"heading":"Stage plot and input list","body":"List each performer, instrument, microphone, DI, and monitor requirement."},{"heading":"Backline","body":"List amplifiers, drums, keyboards, stands, and equipment provided by each party."},{"heading":"Power and sound","body":"Confirm stage power, PA, console, monitors, and sound engineer."},{"heading":"Contact","body":"Production contact: TBD"}]},
"hospitality_rider":{"title":"Hospitality rider","sections":[{"heading":"Green room","body":"Confirm secure dressing space, access, and guest policy."},{"heading":"Food and drinks","body":"Confirm meal arrangements, water, dietary restrictions, and hospitality budget."},{"heading":"Parking and load-in","body":"Confirm vehicle parking, loading entrance, and access instructions."}]},
"show_advance":{"title":"Show advance","sections":[{"heading":"Production contacts","body":"Promoter, venue, production manager, and day-of-show phone numbers: TBD"},{"heading":"Logistics","body":"Load-in, soundcheck, doors, set time, curfew, parking and settlement: confirm with venue."},{"heading":"Promotion and ticketing","body":"Confirm approved artwork, ticket link, guest list and announcement timing."},{"heading":"Open questions","body":"Record questions and written confirmations here."}]},
"day_of_show":{"title":"Day-of-show schedule","sections":[{"heading":"Arrival and load-in","body":"Time TBD — parking, access, unload and stage setup"},{"heading":"Soundcheck","body":"Time TBD — line check, monitors, and changeovers"},{"heading":"Doors and performance","body":"Doors TBD — set start TBD — end TBD"},{"heading":"Strike and settlement","body":"Time TBD — merchandise, payment, load-out, departure"}]},
"tour_call_sheet":{"title":"Touring call sheet","sections":[{"heading":"Show identification","body":"Date, venue, city, tour manager and production contact: TBD"},{"heading":"Tour party and contacts","body":"Band, crew, drivers, promoter, house engineer, emergency contacts: TBD"},{"heading":"Travel and accommodations","body":"Hotel, check-out, departure, travel time, parking and vehicle details: TBD"},{"heading":"Calls and schedule","body":"Crew call, load-in, soundcheck, meal, doors, show, load-out: TBD"},{"heading":"Access and contingencies","body":"Passes, Wi-Fi, loading entrance, accessibility, local hospital, weather plan: TBD"}]},
"settlement_sheet":{"title":"Show settlement checklist","sections":[{"heading":"Guarantee and deal terms","body":"Confirm agreed guarantee, door percentage, bonuses, deposits and signed contract."},{"heading":"Expenses and deductions","body":"Confirm approved production charges, house fees, taxes, merch split, and receipts."},{"heading":"Payment and sign-off","body":"Verify amount due, payment method, payee, promoter and authorized signatures."}]}
}
class PacketInput(BaseModel):
    kind:str
    title:str=Field(min_length=1,max_length=140)
    sections:list[dict[str,str]]=Field(min_length=1,max_length=25)
class PacketUpdate(BaseModel):
    title:str=Field(min_length=1,max_length=140)
    sections:list[dict[str,str]]=Field(min_length=1,max_length=25)

def validate(kind,sections):
    if kind not in KINDS:raise HTTPException(422,"Unsupported show document type")
    for section in sections:
        if set(section)!={"heading","body"} or not (1<=len(section["heading"].strip())<=100) or len(section["body"])>6000:
            raise HTTPException(422,"Invalid document section")

def setup(con):
    con.executescript("""CREATE TABLE IF NOT EXISTS show_templates(
      id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),
      kind TEXT NOT NULL,title TEXT NOT NULL,sections_json TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS show_packets(
      id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),
      event_id INTEGER NOT NULL REFERENCES events(id),
      kind TEXT NOT NULL,title TEXT NOT NULL,sections_json TEXT NOT NULL,
      template_id INTEGER REFERENCES show_templates(id),
      status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','ready')),
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(event_id,kind));""")

def attach(db):
    def band(con,band_id):
        if not con.execute("SELECT 1 FROM bands WHERE id=?",(band_id,)).fetchone():
            raise HTTPException(404,"Band not found")
    def gig(con,band_id,event_id):
        if not con.execute("SELECT 1 FROM events WHERE band_id=? AND id=? AND kind='Gig'",(band_id,event_id)).fetchone():
            raise HTTPException(404,"Gig not found")
    @router.get('/api/show-document-defaults')
    def defaults():return DEFAULTS
    @router.get('/api/bands/{band_id}/show-templates')
    def templates(band_id:int):
        with db() as con:
            band(con,band_id)
            return [dict(row)|{"sections":json.loads(row["sections_json"])} for row in con.execute(
                "SELECT * FROM show_templates WHERE band_id=? ORDER BY kind,id",(band_id,))]
    @router.post('/api/bands/{band_id}/show-templates',status_code=201)
    def make_template(band_id:int,data:PacketInput):
        validate(data.kind,data.sections)
        with db() as con:
            band(con,band_id)
            row=con.execute("INSERT INTO show_templates(band_id,kind,title,sections_json) VALUES(?,?,?,?)",
                 (band_id,data.kind,data.title,json.dumps(data.sections)))
            return {"id":row.lastrowid}
    @router.put('/api/bands/{band_id}/show-templates/{template_id}')
    def edit_template(band_id:int,template_id:int,data:PacketUpdate):
        with db() as con:
            row=con.execute("SELECT kind FROM show_templates WHERE id=? AND band_id=?",(template_id,band_id)).fetchone()
            if not row:raise HTTPException(404,"Template not found")
            validate(row["kind"],data.sections)
            con.execute("UPDATE show_templates SET title=?,sections_json=? WHERE id=?",
                (data.title,json.dumps(data.sections),template_id))
        return {"updated":True}
    @router.get('/api/bands/{band_id}/gigs/{event_id}/packet')
    def packet(band_id:int,event_id:int):
        with db() as con:
            gig(con,band_id,event_id)
            return [dict(row)|{"sections":json.loads(row["sections_json"])} for row in con.execute(
                "SELECT * FROM show_packets WHERE band_id=? AND event_id=? ORDER BY kind",(band_id,event_id))]
    @router.get('/api/bands/{band_id}/gigs/{event_id}/packet.pdf')
    def pdf_packet(band_id:int,event_id:int):
        with db() as con:
            gig(con,band_id,event_id)
            band_record=con.execute("SELECT name FROM bands WHERE id=?",(band_id,)).fetchone()
            event=con.execute("SELECT title,date,venue FROM events WHERE band_id=? AND id=?",(band_id,event_id)).fetchone()
            documents=[dict(row)|{"sections":json.loads(row["sections_json"])} for row in con.execute(
                "SELECT * FROM show_packets WHERE band_id=? AND event_id=? ORDER BY kind",(band_id,event_id))]
        payload=create_show_pdf(band_record,event,documents)
        return Response(content=payload,media_type="application/pdf",
            headers={"Content-Disposition":f'attachment; filename="backline-show-{event_id}.pdf"',
                     "Cache-Control":"no-store"})
    class FromTemplate(BaseModel):
        kind:str
        template_id:int|None=None
    @router.post('/api/bands/{band_id}/gigs/{event_id}/packet',status_code=201)
    def make_packet(band_id:int,event_id:int,data:FromTemplate):
        if data.kind not in KINDS:raise HTTPException(422,"Unsupported show document type")
        with db() as con:
            gig(con,band_id,event_id)
            if data.template_id is not None:
                template=con.execute("SELECT * FROM show_templates WHERE id=? AND band_id=? AND kind=?",
                    (data.template_id,band_id,data.kind)).fetchone()
                if not template:raise HTTPException(404,"Band template not found")
                title,sections=template["title"],template["sections_json"]
            else:
                title,sections=DEFAULTS[data.kind]["title"],json.dumps(DEFAULTS[data.kind]["sections"])
            if con.execute("SELECT 1 FROM show_packets WHERE event_id=? AND kind=?",(event_id,data.kind)).fetchone():
                raise HTTPException(409,"Show document already exists")
            row=con.execute("""INSERT INTO show_packets
                (band_id,event_id,kind,title,sections_json,template_id) VALUES(?,?,?,?,?,?)""",
                (band_id,event_id,data.kind,title,sections,data.template_id))
            return {"id":row.lastrowid,"status":"draft"}
    @router.put('/api/bands/{band_id}/gigs/{event_id}/packet/{packet_id}')
    def update_packet(band_id:int,event_id:int,packet_id:int,data:PacketUpdate):
        with db() as con:
            gig(con,band_id,event_id)
            row=con.execute("SELECT kind FROM show_packets WHERE id=? AND band_id=? AND event_id=?",
               (packet_id,band_id,event_id)).fetchone()
            if not row:raise HTTPException(404,"Show document not found")
            validate(row["kind"],data.sections)
            con.execute("""UPDATE show_packets SET title=?,sections_json=?,status='draft',
                updated_at=CURRENT_TIMESTAMP WHERE id=?""",(data.title,json.dumps(data.sections),packet_id))
            return {"updated":True,"status":"draft"}
    @router.post('/api/bands/{band_id}/gigs/{event_id}/packet/{packet_id}/ready')
    def mark_ready(band_id:int,event_id:int,packet_id:int):
        with db() as con:
            gig(con,band_id,event_id)
            result=con.execute("""UPDATE show_packets SET status='ready',updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND band_id=? AND event_id=?""",(packet_id,band_id,event_id))
            if result.rowcount!=1:raise HTTPException(404,"Show document not found")
            return {"status":"ready","sent":False}
    return router
