"""Structured, band-scoped technical stage plots and numbered audio input lists."""
import json
import io
import csv
from xml.sax.saxutils import escape
from fastapi import APIRouter,HTTPException,Response
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
    @router.get('/api/bands/{band_id}/gigs/{event_id}/stage.svg')
    def export_stage_svg(band_id:int,event_id:int):
        with db() as con:
            check(con,band_id,event_id)
            row=con.execute("SELECT body_json FROM show_stage_plots WHERE event_id=? AND band_id=?",
                (event_id,band_id)).fetchone()
            stage=json.loads(row["body_json"]) if row else {"items":[]}
        circles=[]
        for item in stage.get("items",[]):
            x=30+item["x"]*8.4
            y=30+item["y"]*4.4
            label=escape(item["label"])
            circles.append(f'<circle cx="{x}" cy="{y}" r="17" fill="#dae8f5" stroke="#375b77"/><text x="{x}" y="{y+30}" font-size="13" text-anchor="middle">{label}</text>')
        content='<svg xmlns="http://www.w3.org/2000/svg" width="900" height="520" viewBox="0 0 900 520"><rect x="10" y="10" width="880" height="500" rx="12" fill="#fff" stroke="#445"/><text x="450" y="23" text-anchor="middle" font-size="14">UPSTAGE</text>'+''.join(circles)+'<text x="450" y="505" text-anchor="middle" font-size="14">AUDIENCE / DOWNSTAGE</text></svg>'
        return Response(content,media_type="image/svg+xml",headers={"Content-Disposition":'attachment; filename="stage-plot.svg"',"Cache-Control":"no-store"})
    @router.get('/api/bands/{band_id}/gigs/{event_id}/inputs.csv')
    def export_input_list(band_id:int,event_id:int):
        with db() as con:
            check(con,band_id,event_id)
            row=con.execute("SELECT body_json FROM show_stage_plots WHERE event_id=? AND band_id=?",
                (event_id,band_id)).fetchone()
            stage=json.loads(row["body_json"]) if row else {"inputs":[]}
        buf=io.StringIO()
        writer=csv.writer(buf)
        writer.writerow(["Channel","Source","Microphone/DI","Stand","Notes"])
        for item in sorted(stage.get("inputs",[]),key=lambda a:a["channel"]):
            def safe(value):
                value=str(value or "")
                return "'"+value if value.lstrip().startswith(("=","+","-","@")) else value
            writer.writerow([item["channel"],safe(item["source"]),safe(item.get("microphone")),
                safe(item.get("stand")),safe(item.get("notes"))])
        return Response(buf.getvalue(),media_type="text/csv",headers={"Content-Disposition":'attachment; filename="input-list.csv"',"Cache-Control":"no-store"})
    return router
