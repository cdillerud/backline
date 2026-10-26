"""Explicit, revocable venue sharing and minimized calendar capabilities."""
import hashlib
import json
import logging
import os
import re
import secrets
import time
from fastapi import APIRouter,HTTPException,Request,Response
from pydantic import Field
from .collaboration import Strict,actor
from .calendars import render_ical

router=APIRouter()
VENUE_FIELDS={'name','address','contacts','load_in_notes','curfew_notes','tags','favourite'}
class VenueShare(Strict):
    destination_band_id:int
    fields:list[str]=Field(min_length=1,max_length=7)
    confirm:bool=False
class SharedVenueLink(Strict):
    share_id:int
class FeedConfirm(Strict):
    confirm:bool

class RedactCalendarTokens(logging.Filter):
    def filter(self,record):
        if isinstance(record.args,tuple):
            record.args=tuple(re.sub(r'/calendar-feeds/[^\s?]+','/calendar-feeds/[REDACTED].ics',value) if isinstance(value,str) else value for value in record.args)
        return True

if not any(isinstance(f,RedactCalendarTokens) for f in logging.getLogger('uvicorn.access').filters):
    logging.getLogger('uvicorn.access').addFilter(RedactCalendarTokens())

def setup(con):
    con.executescript('''
      CREATE TABLE IF NOT EXISTS venue_shares(
        id INTEGER PRIMARY KEY,source_band_id INTEGER NOT NULL REFERENCES bands(id),destination_band_id INTEGER NOT NULL REFERENCES bands(id),
        venue_id INTEGER NOT NULL REFERENCES workspace_venues(id),fields_json TEXT NOT NULL,created_by INTEGER NOT NULL REFERENCES users(id),
        created_at INTEGER NOT NULL,revoked_at INTEGER);
      CREATE TABLE IF NOT EXISTS event_shared_venues(
        event_id INTEGER PRIMARY KEY REFERENCES events(id),band_id INTEGER NOT NULL REFERENCES bands(id),share_id INTEGER NOT NULL REFERENCES venue_shares(id));
      CREATE TABLE IF NOT EXISTS calendar_subscriptions(
        id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),calendar_id INTEGER NOT NULL REFERENCES band_calendars(id),
        token_hash TEXT NOT NULL UNIQUE,created_by INTEGER NOT NULL REFERENCES users(id),created_at INTEGER NOT NULL,revoked_at INTEGER);
    ''')

def project_share(con,row):
    venue=con.execute('SELECT body_json FROM workspace_venues WHERE id=? AND band_id=?',(row['venue_id'],row['source_band_id'])).fetchone()
    if not venue:return None
    body=json.loads(venue['body_json']);fields=json.loads(row['fields_json'])
    return {key:body[key] for key in fields if key in body}|{'share_id':row['id'],'shared':True}

def resolve_shared_venue(con,band_id,event_id):
    row=con.execute('''SELECT s.* FROM event_shared_venues e JOIN venue_shares s ON s.id=e.share_id
        WHERE e.band_id=? AND e.event_id=? AND s.destination_band_id=e.band_id AND s.revoked_at IS NULL''',(band_id,event_id)).fetchone()
    return project_share(con,row) if row else None

def attach(db):
    def admin(con,band_id,user_id):
        row=con.execute("SELECT role FROM band_users WHERE band_id=? AND user_id=?",(band_id,user_id)).fetchone()
        if not row or row['role'] not in ('owner','manager'):raise HTTPException(403,'Manager access required in both bands')
    def preview_share(con,band_id,venue_id,data,user_id):
        admin(con,band_id,user_id);admin(con,data.destination_band_id,user_id)
        if band_id==data.destination_band_id:raise HTTPException(422,'Choose another band')
        fields=set(data.fields)
        if not fields<=VENUE_FIELDS or 'name' not in fields:raise HTTPException(422,'Select supported fields including venue name')
        row=con.execute('SELECT body_json FROM workspace_venues WHERE id=? AND band_id=?',(venue_id,band_id)).fetchone()
        if not row:raise HTTPException(404,'Venue not found')
        body=json.loads(row['body_json'])
        name=con.execute('SELECT name FROM bands WHERE id=?',(data.destination_band_id,)).fetchone()['name']
        return {'destination':name,'fields':sorted(fields),'venue':{key:body[key] for key in sorted(fields)}}
    @router.post('/api/bands/{band_id}/venues/{venue_id}/share-preview')
    def share_preview(band_id:int,venue_id:int,data:VenueShare,request:Request):
        with db() as con:return preview_share(con,band_id,venue_id,data,actor(request))
    @router.post('/api/bands/{band_id}/venues/{venue_id}/shares',status_code=201)
    def share(band_id:int,venue_id:int,data:VenueShare,request:Request):
        user_id=actor(request)
        if not data.confirm:raise HTTPException(422,'Preview the selected fields and explicitly confirm sharing')
        with db() as con:
            preview=preview_share(con,band_id,venue_id,data,user_id)
            row=con.execute('''INSERT INTO venue_shares(source_band_id,destination_band_id,venue_id,fields_json,created_by,created_at)
                VALUES(?,?,?,?,?,?)''',(band_id,data.destination_band_id,venue_id,json.dumps(preview['fields']),user_id,int(time.time())))
            con.execute('INSERT INTO collaboration_audit(band_id,actor_id,action,reference,created_at) VALUES(?,?,?,?,?)',
                        (band_id,user_id,'share_venue',str(row.lastrowid),int(time.time())))
            return {'id':row.lastrowid}
    @router.get('/api/bands/{band_id}/venues/{venue_id}/shares')
    def shares(band_id:int,venue_id:int,request:Request):
        with db() as con:
            admin(con,band_id,actor(request))
            return [dict(r) for r in con.execute('SELECT id,destination_band_id,fields_json,created_at,revoked_at FROM venue_shares WHERE source_band_id=? AND venue_id=? ORDER BY id DESC',(band_id,venue_id))]
    @router.post('/api/bands/{band_id}/venues/{venue_id}/shares/{share_id}/revoke')
    def revoke_share(band_id:int,venue_id:int,share_id:int,request:Request):
        user_id=actor(request)
        with db() as con:
            admin(con,band_id,user_id)
            result=con.execute('UPDATE venue_shares SET revoked_at=? WHERE id=? AND source_band_id=? AND venue_id=?',(int(time.time()),share_id,band_id,venue_id))
            if result.rowcount!=1:raise HTTPException(404,'Share not found')
            con.execute('INSERT INTO collaboration_audit(band_id,actor_id,action,reference,created_at) VALUES(?,?,?,?,?)',
                        (band_id,user_id,'revoke_venue_share',str(share_id),int(time.time())))
        return {'revoked':True}
    @router.get('/api/bands/{band_id}/shared-venues')
    def shared_venues(band_id:int):
        with db() as con:
            return [body for row in con.execute('SELECT * FROM venue_shares WHERE destination_band_id=? AND revoked_at IS NULL ORDER BY id',(band_id,)) if (body:=project_share(con,row))]
    @router.put('/api/bands/{band_id}/events/{event_id}/shared-venue')
    def link_shared(band_id:int,event_id:int,data:SharedVenueLink):
        with db() as con:
            if not con.execute("SELECT 1 FROM events WHERE id=? AND band_id=? AND kind='Gig'",(event_id,band_id)).fetchone():raise HTTPException(404,'Gig not found')
            if not con.execute('SELECT 1 FROM venue_shares WHERE id=? AND destination_band_id=? AND revoked_at IS NULL',(data.share_id,band_id)).fetchone():raise HTTPException(404,'Active share not found')
            con.execute('''INSERT INTO event_shared_venues(event_id,band_id,share_id) VALUES(?,?,?)
                ON CONFLICT(event_id) DO UPDATE SET share_id=excluded.share_id''',(event_id,band_id,data.share_id))
            con.execute('DELETE FROM event_venues WHERE band_id=? AND event_id=?',(band_id,event_id))
        return {'linked':True}
    @router.post('/api/bands/{band_id}/calendars/{calendar_id}/subscriptions',status_code=201)
    def subscribe(band_id:int,calendar_id:int,data:FeedConfirm,request:Request):
        user_id=actor(request)
        if os.getenv('BACKLINE_PUBLIC_SHARING_ENABLED')!='1':raise HTTPException(409,'Calendar subscriptions are disabled for this environment')
        if not data.confirm:raise HTTPException(422,'Confirm that anyone with this URL can read the selected calendar')
        token=secrets.token_hex(32)
        with db() as con:
            admin(con,band_id,user_id)
            if not con.execute('SELECT 1 FROM band_calendars WHERE id=? AND band_id=?',(calendar_id,band_id)).fetchone():raise HTTPException(404,'Calendar not found')
            row=con.execute('INSERT INTO calendar_subscriptions(band_id,calendar_id,token_hash,created_by,created_at) VALUES(?,?,?,?,?)',
                            (band_id,calendar_id,hashlib.sha256(token.encode()).hexdigest(),user_id,int(time.time())))
            return {'id':row.lastrowid,'url':'/calendar-feeds/'+token+'.ics','warning':'Secret URL: calendar providers may retain copies after revocation.'}
    @router.get('/api/bands/{band_id}/calendars/{calendar_id}/subscriptions')
    def subscription_list(band_id:int,calendar_id:int,request:Request):
        with db() as con:
            admin(con,band_id,actor(request))
            return [dict(r) for r in con.execute('SELECT id,created_at,revoked_at FROM calendar_subscriptions WHERE band_id=? AND calendar_id=? ORDER BY id DESC',(band_id,calendar_id))]
    @router.post('/api/bands/{band_id}/calendars/{calendar_id}/subscriptions/{subscription_id}/revoke')
    def unsubscribe(band_id:int,calendar_id:int,subscription_id:int,request:Request):
        with db() as con:
            admin(con,band_id,actor(request))
            row=con.execute('UPDATE calendar_subscriptions SET revoked_at=? WHERE id=? AND band_id=? AND calendar_id=?',(int(time.time()),subscription_id,band_id,calendar_id))
            if row.rowcount!=1:raise HTTPException(404,'Subscription not found')
        return {'revoked':True}
    @router.get('/calendar-feeds/{token}.ics')
    def feed(token:str):
        if os.getenv('BACKLINE_PUBLIC_SHARING_ENABLED')!='1' or not re.fullmatch('[a-f0-9]{64}',token):raise HTTPException(404,'Calendar feed not found')
        with db() as con:
            row=con.execute('''SELECT s.*,c.name FROM calendar_subscriptions s JOIN band_calendars c ON c.id=s.calendar_id AND c.band_id=s.band_id
                JOIN band_users b ON b.band_id=s.band_id AND b.user_id=s.created_by AND b.role IN ('owner','manager')
                WHERE s.token_hash=? AND s.revoked_at IS NULL''',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            if not row:raise HTTPException(404,'Calendar feed not found')
            events=[]
            for event in con.execute('''SELECT e.*,a.body_json FROM events e JOIN event_calendars ec ON ec.event_id=e.id AND ec.band_id=e.band_id
                LEFT JOIN venue_advances a ON a.event_id=e.id AND a.band_id=e.band_id
                WHERE e.band_id=? AND ec.calendar_id=? ORDER BY e.date,e.id''',(row['band_id'],row['calendar_id'])):
                advance=json.loads(event['body_json'] or '{}')
                events.append({'id':event['id'],'band_id':event['band_id'],'title':event['title'],'date':event['date'],'time':event['time'],
                    'venue':event['venue'],'status':event['status'],'kind':event['kind'],'notes':'','calendar_name':row['name'],
                    'advance':{'show_time':advance.get('show_time',''),'timezone':advance.get('timezone',''),
                               'day_offsets':{'show_time':advance.get('day_offsets',{}).get('show_time',0)}}})
            return Response(render_ical(row['name'],events),media_type='text/calendar',headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'})
    return router
