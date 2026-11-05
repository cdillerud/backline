"""Private rehearsal plans attached to existing band events."""
from fastapi import APIRouter,HTTPException,Request
from pydantic import Field
from .collaboration import Strict,actor
from .operations_audit import require_manager

router=APIRouter()

class RehearsalPlan(Strict):
    objectives:str=Field(default='',max_length=4000)
    notes:str=Field(default='',max_length=8000)

def setup(con):
    con.execute("""CREATE TABLE IF NOT EXISTS rehearsal_plans(
        event_id INTEGER PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
        objectives TEXT NOT NULL DEFAULT '',
        notes TEXT NOT NULL DEFAULT '',
        revision INTEGER NOT NULL DEFAULT 1)""")

def attach(db):
    @router.get('/api/bands/{band_id}/rehearsals/{event_id}/plan')
    def get_plan(band_id:int,event_id:int,request:Request):
        with db() as con:
            uid=actor(request)
            if not con.execute('SELECT 1 FROM band_users WHERE band_id=? AND user_id=?',(band_id,uid)).fetchone():
                raise HTTPException(403,'Band membership required')
            row=con.execute("SELECT id FROM events WHERE id=? AND band_id=? AND kind='Rehearsal'",(event_id,band_id)).fetchone()
            if not row:raise HTTPException(404,'Rehearsal not found')
            existing=con.execute('SELECT objectives,notes,revision FROM rehearsal_plans WHERE event_id=?',(event_id,)).fetchone()
            return dict(existing) if existing else {'objectives':'','notes':'','revision':0}
    @router.put('/api/bands/{band_id}/rehearsals/{event_id}/plan')
    def save_plan(band_id:int,event_id:int,data:RehearsalPlan,request:Request):
        with db() as con:
            require_manager(con,band_id,actor(request))
            if not con.execute("SELECT 1 FROM events WHERE id=? AND band_id=? AND kind='Rehearsal'",(event_id,band_id)).fetchone():
                raise HTTPException(404,'Rehearsal not found')
            con.execute("""INSERT INTO rehearsal_plans(event_id,objectives,notes,revision) VALUES(?,?,?,1)
                ON CONFLICT(event_id) DO UPDATE SET objectives=excluded.objectives,notes=excluded.notes,revision=rehearsal_plans.revision+1""",
                (event_id,data.objectives,data.notes))
            row=con.execute('SELECT objectives,notes,revision FROM rehearsal_plans WHERE event_id=?',(event_id,)).fetchone()
            return dict(row)
    return router
