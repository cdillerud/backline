"""Private workspace venues, task checklists and musical repertoire editing.

All routes retain the existing band account middleware and role permissions.
No public sharing, cross-band contact sharing or outbound messages are enabled.
"""
import datetime
import json
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, field_validator
from .show_pdf import create_setlist_pdf
from .collaboration import notify_task
from .sharing import resolve_shared_venue

router=APIRouter()

class Contact(BaseModel):
    name:str=Field(min_length=1,max_length=120)
    role:str=Field(default='',max_length=100)
    email:str=Field(default='',max_length=200)
    phone:str=Field(default='',max_length=80)

class Venue(BaseModel):
    name:str=Field(min_length=1,max_length=150)
    address:str=Field(default='',max_length=500)
    contacts:list[Contact]=Field(default_factory=list,max_length=30)
    load_in_notes:str=Field(default='',max_length=2000)
    curfew_notes:str=Field(default='',max_length=1000)
    tags:list[str]=Field(default_factory=list,max_length=30)
    favourite:bool=False

    @field_validator('name')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():raise ValueError('Venue name is required')
        return value.strip()

    @field_validator('tags')
    @classmethod
    def tag_lengths(cls,value):
        if any(not tag.strip() or len(tag)>60 for tag in value):raise ValueError('Tags must be 1 to 60 characters')
        return list(dict.fromkeys(tag.strip() for tag in value))

class Task(BaseModel):
    title:str=Field(min_length=1,max_length=200)
    notes:str=Field(default='',max_length=3000)
    assignee_id:int|None=None
    due_date:datetime.date|None=None
    event_id:int|None=None
    song_id:int|None=None
    setlist_id:int|None=None
    completed:bool=False

    @field_validator('title')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():raise ValueError('Task title is required')
        return value.strip()

class Repertoire(BaseModel):
    title:str=Field(min_length=1,max_length=180)
    artist:str=Field(default='',max_length=200)
    song_key:str=Field(default='',max_length=30)
    bpm:int|None=Field(default=None,ge=1,le=400)
    duration_seconds:int=Field(default=0,ge=0,le=36000)
    status:str=Field(default='Learning',max_length=60)
    notes:str=Field(default='',max_length=5000)
    tags:list[str]=Field(default_factory=list,max_length=30)
    reference_url:str=Field(default='',max_length=1500)

    @field_validator('reference_url')
    @classmethod
    def safe_reference(cls,value):
        from urllib.parse import urlsplit
        if value:
            parsed=urlsplit(value)
            if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError('Reference recording must use an HTTPS URL without credentials')
        return value

    @field_validator('title')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():raise ValueError('Song title is required')
        return value.strip()

    @field_validator('tags')
    @classmethod
    def tag_lengths(cls,value):return Venue.tag_lengths(value)

class SetlistEdit(BaseModel):
    title:str=Field(min_length=1,max_length=160)
    event_id:int|None=None
    song_ids:list[int]=Field(default_factory=list,max_length=200)

class VenueLink(BaseModel):
    venue_id:int


def setup(con):
    con.executescript('''
      CREATE TABLE IF NOT EXISTS workspace_venues(
        id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),body_json TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS event_venues(
        event_id INTEGER PRIMARY KEY REFERENCES events(id),band_id INTEGER NOT NULL REFERENCES bands(id),
        venue_id INTEGER NOT NULL REFERENCES workspace_venues(id));
      CREATE TABLE IF NOT EXISTS workspace_tasks(
        id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),body_json TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS song_details(
        song_id INTEGER PRIMARY KEY REFERENCES songs(id),band_id INTEGER NOT NULL REFERENCES bands(id),
        tags_json TEXT NOT NULL DEFAULT '[]',reference_url TEXT NOT NULL DEFAULT '');
    ''')


def attach(db):
    def band(con,band_id):
        if not con.execute('SELECT 1 FROM bands WHERE id=?',(band_id,)).fetchone():raise HTTPException(404,'Band not found')
    def record(con,table,band_id,record_id):
        row=con.execute(f'SELECT * FROM {table} WHERE id=? AND band_id=?',(record_id,band_id)).fetchone()
        if not row:raise HTTPException(404,'Workspace record not found')
        return row
    def task_links(con,band_id,data):
        for field,table in (('assignee_id','members'),('event_id','events'),('song_id','songs'),('setlist_id','setlists')):
            value=getattr(data,field)
            if value is not None:record(con,table,band_id,value)
    @router.get('/api/bands/{band_id}/venues')
    def venues(band_id:int):
        with db() as con:
            band(con,band_id)
            return [json.loads(row['body_json'])|{'id':row['id']} for row in con.execute(
                'SELECT * FROM workspace_venues WHERE band_id=? ORDER BY id',(band_id,))]
    @router.post('/api/bands/{band_id}/venues',status_code=201)
    def add_venue(band_id:int,data:Venue):
        with db() as con:
            band(con,band_id)
            row=con.execute('INSERT INTO workspace_venues(band_id,body_json) VALUES(?,?)',(band_id,data.model_dump_json()))
            return {'id':row.lastrowid}
    @router.put('/api/bands/{band_id}/venues/{venue_id}')
    def edit_venue(band_id:int,venue_id:int,data:Venue):
        with db() as con:
            record(con,'workspace_venues',band_id,venue_id)
            con.execute('UPDATE workspace_venues SET body_json=? WHERE id=? AND band_id=?',(data.model_dump_json(),venue_id,band_id))
        return {'updated':True}
    @router.put('/api/bands/{band_id}/events/{event_id}/venue')
    def link_venue(band_id:int,event_id:int,data:VenueLink):
        with db() as con:
            event=record(con,'events',band_id,event_id)
            if event['kind']!='Gig':raise HTTPException(422,'Venue links require a gig')
            record(con,'workspace_venues',band_id,data.venue_id)
            con.execute('''INSERT INTO event_venues(event_id,band_id,venue_id) VALUES(?,?,?)
                ON CONFLICT(event_id) DO UPDATE SET venue_id=excluded.venue_id''',(event_id,band_id,data.venue_id))
            con.execute('DELETE FROM event_shared_venues WHERE band_id=? AND event_id=?',(band_id,event_id))
        return {'linked':True}
    @router.get('/api/bands/{band_id}/events/{event_id}/venue')
    def event_venue(band_id:int,event_id:int):
        with db() as con:
            record(con,'events',band_id,event_id)
            row=con.execute('''SELECT v.* FROM event_venues e JOIN workspace_venues v ON v.id=e.venue_id AND v.band_id=e.band_id
                WHERE e.band_id=? AND e.event_id=?''',(band_id,event_id)).fetchone()
            return json.loads(row['body_json'])|{'id':row['id']} if row else resolve_shared_venue(con,band_id,event_id)
    @router.get('/api/bands/{band_id}/tasks')
    def tasks(band_id:int):
        with db() as con:
            band(con,band_id)
            results=[json.loads(row['body_json'])|{'id':row['id']} for row in con.execute('SELECT * FROM workspace_tasks WHERE band_id=?',(band_id,))]
        today=datetime.date.today()
        for item in results:
            due=datetime.date.fromisoformat(item['due_date']) if item.get('due_date') else None
            item['reminder']='completed' if item['completed'] else 'overdue' if due and due<today else 'due_today' if due==today else 'due_tomorrow' if due==today+datetime.timedelta(days=1) else ''
        return sorted(results,key=lambda t:(t['completed'],t.get('due_date') or '9999-12-31',t['id']))
    @router.post('/api/bands/{band_id}/tasks',status_code=201)
    def add_task(band_id:int,data:Task):
        with db() as con:
            band(con,band_id);task_links(con,band_id,data)
            row=con.execute('INSERT INTO workspace_tasks(band_id,body_json) VALUES(?,?)',(band_id,data.model_dump_json()))
            notify_task(con,band_id,row.lastrowid,data)
            return {'id':row.lastrowid}
    @router.put('/api/bands/{band_id}/tasks/{task_id}')
    def edit_task(band_id:int,task_id:int,data:Task):
        with db() as con:
            previous=json.loads(record(con,'workspace_tasks',band_id,task_id)['body_json']);task_links(con,band_id,data)
            notify_task(con,band_id,task_id,data,previous)
            con.execute('UPDATE workspace_tasks SET body_json=? WHERE id=? AND band_id=?',(data.model_dump_json(),task_id,band_id))
        return {'updated':True}
    @router.get('/api/bands/{band_id}/song-details')
    def song_details(band_id:int):
        with db() as con:
            band(con,band_id)
            return [{'song_id':r['song_id'],'tags':json.loads(r['tags_json']),'reference_url':r['reference_url']} for r in con.execute('SELECT * FROM song_details WHERE band_id=?',(band_id,))]
    @router.put('/api/bands/{band_id}/songs/{song_id}')
    def edit_song(band_id:int,song_id:int,data:Repertoire):
        with db() as con:
            record(con,'songs',band_id,song_id)
            con.execute('''UPDATE songs SET title=?,artist=?,song_key=?,bpm=?,duration_seconds=?,status=?,notes=?
                WHERE id=? AND band_id=?''',(data.title,data.artist,data.song_key,data.bpm,data.duration_seconds,data.status,data.notes,song_id,band_id))
            con.execute('''INSERT INTO song_details(song_id,band_id,tags_json,reference_url) VALUES(?,?,?,?)
                ON CONFLICT(song_id) DO UPDATE SET tags_json=excluded.tags_json,reference_url=excluded.reference_url''',
                (song_id,band_id,json.dumps(data.tags),data.reference_url))
        return {'updated':True}
    @router.put('/api/bands/{band_id}/setlists/{setlist_id}')
    def edit_setlist(band_id:int,setlist_id:int,data:SetlistEdit):
        if not data.title.strip():raise HTTPException(422,'Setlist title is required')
        with db() as con:
            record(con,'setlists',band_id,setlist_id)
            if data.event_id is not None:record(con,'events',band_id,data.event_id)
            for song_id in data.song_ids:record(con,'songs',band_id,song_id)
            con.execute('UPDATE setlists SET title=?,event_id=? WHERE id=? AND band_id=?',(data.title.strip(),data.event_id,setlist_id,band_id))
            con.execute('DELETE FROM setlist_songs WHERE setlist_id=?',(setlist_id,))
            con.executemany('INSERT INTO setlist_songs(setlist_id,song_id,position) VALUES(?,?,?)',
                            [(setlist_id,song_id,index) for index,song_id in enumerate(data.song_ids,1)])
        return {'updated':True}
    @router.get('/api/bands/{band_id}/setlists/{setlist_id}/pdf')
    def setlist_pdf(band_id:int,setlist_id:int):
        with db() as con:
            info=dict(record(con,'setlists',band_id,setlist_id))
            name=con.execute('SELECT name FROM bands WHERE id=?',(band_id,)).fetchone()['name']
            songs=[dict(row) for row in con.execute('''SELECT s.* FROM setlist_songs ss JOIN songs s ON s.id=ss.song_id
                WHERE ss.setlist_id=? AND s.band_id=? ORDER BY ss.position,ss.id''',(setlist_id,band_id))]
        return Response(create_setlist_pdf(name,info,songs),media_type='application/pdf',
                        headers={'Content-Disposition':f'attachment; filename="backline-setlist-{setlist_id}.pdf"','Cache-Control':'no-store'})
    return router
