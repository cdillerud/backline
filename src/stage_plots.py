"""Structured, band-scoped technical stage plots and numbered audio input lists."""
import json
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
router=APIRouter()
class StageItem(BaseModel):
    label:str=Field(min_length=1,max_length=100)
    kind:str=Field(pattern="^(vocal|guitar|bass|drums|keys|monitor|amp|other)$")
    x:int=Field(ge=0,le=100)
    y:int=Field(ge=0,le=100)
class AudioInput(BaseModel):
    channel:int=Field(ge=1,le=128)
    source:str=Field(min_length=1,max_length=120)
    microphone:str=Field(default="",max_length=120)
    stand:str=Field(default="",max_length=60)
    notes:str=Field(default="",max_length=300)
class StageData(BaseModel):
    notes:str=Field(default="",max_length=3000)
    items:list[StageItem]=Field(default_factory=list,max_length=80)
    inputs:list[AudioInput]=Field(default_factory=list,max_length=128)
def setup(con):
    con.execute("""CREATE TABLE IF NOT EXISTS show_stage_plots(
        event_id INTEGER PRIMARY KEY REFERENCES events(id),
        band_id INTEGER NOT NULL REFERENCES bands(id),
        body_json TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
def attach(db):
    def check(con,band,event):
        if not con.execute("SELECT 1 FROM events WHERE id=? AND band_id=? AND kind='Gig'",(event,band)).fetchone():
            raise HTTPException(404,"Gig not found")
    @router.get('/api/bands/{band_id}/gigs/{event_id}/stage')
    def get_stage(band_id:int,event_id:int):
        with db() as con:
            check(con,band_id,event_id)
            row=con.execute("SELECT body_json FROM show_stage_plots WHERE event_id=? AND band_id=?",
                (event_id,band_id)).fetchone()
            return json.loads(row["body_json"]) if row else {"notes":"","items":[],"inputs":[]}
    @router.put('/api/bands/{band_id}/gigs/{event_id}/stage')
    def save_stage(band_id:int,event_id:int,data:StageData):
        channels=[i.channel for i in data.inputs]
        if len(channels)!=len(set(channels)):
            raise HTTPException(422,"Audio input channels must be unique")
        with db() as con:
            check(con,band_id,event_id)
            con.execute("""INSERT INTO show_stage_plots(event_id,band_id,body_json)
              VALUES(?,?,?) ON CONFLICT(event_id) DO UPDATE SET
              body_json=excluded.body_json,updated_at=CURRENT_TIMESTAMP""",
              (event_id,band_id,data.model_dump_json()))
            return {"saved":True,"input_count":len(channels),"item_count":len(data.items)}
    return router
