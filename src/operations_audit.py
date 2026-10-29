"""Transactional operational history, versions and explicit crew acknowledgements."""
import datetime
import json
import time
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, Request
from .collaboration import actor, notify
from .show_schedule import valid_timezone, TIME_PATTERN

router=APIRouter()
PRIVATE_RESOURCES={'guest','guest_policy','lodging','room','import'}
TIMING_FIELDS={'load_in','soundcheck','doors','show_time','curfew','timezone','day_offsets','schedule','parking','venue_address','contact_phone','production_contact'}

def setup(con):
    con.executescript('''
      CREATE TABLE IF NOT EXISTS operations_versions(
        band_id INTEGER NOT NULL REFERENCES bands(id),resource TEXT NOT NULL,record_id TEXT NOT NULL,
        revision INTEGER NOT NULL,PRIMARY KEY(band_id,resource,record_id));
      CREATE TABLE IF NOT EXISTS operations_history(
        id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),event_id INTEGER REFERENCES events(id),
        resource TEXT NOT NULL,record_id TEXT NOT NULL,actor_id INTEGER REFERENCES users(id),reason TEXT NOT NULL,
        before_json TEXT,after_json TEXT NOT NULL,revision INTEGER NOT NULL,created_at INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS operations_alerts(
        id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),event_id INTEGER NOT NULL REFERENCES events(id),
        history_id INTEGER NOT NULL UNIQUE REFERENCES operations_history(id),title TEXT NOT NULL,created_at INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS operations_alert_recipients(
        alert_id INTEGER NOT NULL REFERENCES operations_alerts(id),user_id INTEGER NOT NULL REFERENCES users(id),
        acknowledged_at INTEGER,PRIMARY KEY(alert_id,user_id));
    ''')

def user_id(request):
    user=getattr(request.state,'user',None)
    return user['id'] if user else None

def is_manager(con,band_id,user_id):
    row=con.execute('SELECT role FROM band_users WHERE band_id=? AND user_id=?',(band_id,user_id)).fetchone()
    return bool(row and row['role'] in ('owner','manager'))

def require_manager(con,band_id,user_id):
    if not is_manager(con,band_id,user_id):raise HTTPException(403,'Band manager access required')

def current_revision(con,band_id,resource,record_id):
    row=con.execute('SELECT revision FROM operations_versions WHERE band_id=? AND resource=? AND record_id=?',(band_id,resource,str(record_id))).fetchone()
    return row['revision'] if row else 0

def check_revision(con,band_id,resource,record_id,expected):
    revision=current_revision(con,band_id,resource,record_id)
    if expected is not None and expected!=revision:raise HTTPException(409,'This record changed. Reload and review before saving.')
    return revision

def record_change(con,band_id,resource,record_id,before,after,actor_id=None,event_id=None,reason=''):
    if before==after:return None
    revision=current_revision(con,band_id,resource,record_id)+1
    con.execute('''INSERT INTO operations_versions(band_id,resource,record_id,revision) VALUES(?,?,?,?)
        ON CONFLICT(band_id,resource,record_id) DO UPDATE SET revision=excluded.revision''',(band_id,resource,str(record_id),revision))
    row=con.execute('''INSERT INTO operations_history(band_id,event_id,resource,record_id,actor_id,reason,before_json,after_json,revision,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?)''',(band_id,event_id,resource,str(record_id),actor_id,reason,
        json.dumps(before,sort_keys=True) if before is not None else None,json.dumps(after,sort_keys=True),revision,int(time.time())))
    return row.lastrowid

def urgent_advance_change(con,band_id,event_id,history_id,before,after,now=None):
    if not history_id or before is None or not any(before.get(key)!=after.get(key) for key in TIMING_FIELDS):return
    now=int(time.time()) if now is None else now
    event=con.execute("SELECT date,title FROM events WHERE band_id=? AND id=? AND kind='Gig'",(band_id,event_id)).fetchone()
    if not event:return
    zone=after.get('timezone') or before.get('timezone') or ''
    if not valid_timezone(zone):return # Do not guess venue time zones.
    local=datetime.datetime.fromtimestamp(now,ZoneInfo(zone))
    day=datetime.date.fromisoformat(event['date'])
    clock=after.get('show_time') or before.get('show_time') or ''
    urgent=day==local.date()
    if TIME_PATTERN.fullmatch(clock):
        start=datetime.datetime.combine(day+datetime.timedelta(days=after.get('day_offsets',{}).get('show_time',0)),datetime.time.fromisoformat(clock),tzinfo=ZoneInfo(zone))
        urgent=urgent or 0<=start.timestamp()-now<=86400
        curfew=after.get('curfew') or before.get('curfew') or ''
        if TIME_PATTERN.fullmatch(curfew):
            end=datetime.datetime.combine(day+datetime.timedelta(days=after.get('day_offsets',{}).get('curfew',0)),datetime.time.fromisoformat(curfew),tzinfo=ZoneInfo(zone))
            urgent=urgent or start.timestamp()<=now<=end.timestamp()
    if not urgent:return
    row=con.execute('INSERT INTO operations_alerts(band_id,event_id,history_id,title,created_at) VALUES(?,?,?,?,?)',
                    (band_id,event_id,history_id,'Show-day details changed: '+event['title'],now))
    for recipient in con.execute('SELECT user_id FROM band_users WHERE band_id=?',(band_id,)).fetchall():
        con.execute('INSERT INTO operations_alert_recipients(alert_id,user_id) VALUES(?,?)',(row.lastrowid,recipient['user_id']))
        notify(con,band_id,recipient['user_id'],'operations','Urgent: '+event['title']+' details changed','operations-alert:'+str(row.lastrowid),now)

def attach(db):
    @router.get('/api/bands/{band_id}/operations/history')
    def history(band_id:int,request:Request,event_id:int|None=None,resource:str|None=None,record_id:str|None=None,before_id:int|None=None):
        uid=user_id(request)
        with db() as con:
            manager=is_manager(con,band_id,uid)
            if resource in PRIVATE_RESOURCES and not manager:raise HTTPException(403,'This history is restricted to managers')
            sql='''SELECT h.*,u.display_name AS actor_name FROM operations_history h LEFT JOIN users u ON u.id=h.actor_id WHERE h.band_id=?''';values=[band_id]
            for key,value in (('event_id',event_id),('resource',resource),('record_id',record_id)):
                if value is not None:sql+=' AND h.'+key+'=?';values.append(value)
            if before_id is not None:sql+=' AND h.id<?';values.append(before_id)
            if not manager:
                sql+=' AND h.resource NOT IN ('+','.join('?' for _ in PRIVATE_RESOURCES)+')';values+=sorted(PRIVATE_RESOURCES)
            rows=con.execute(sql+' ORDER BY h.id DESC LIMIT 100',values).fetchall()
            result=[]
            for row in rows:
                item=dict(row);item['before']=json.loads(item.pop('before_json') or 'null');item['after']=json.loads(item.pop('after_json'))
                item['actor_name']=item['actor_name'] or 'Private preview'
                result.append(item)
            return result
    @router.get('/api/bands/{band_id}/operations/alerts')
    def alerts(band_id:int,request:Request,event_id:int|None=None):
        uid=actor(request)
        with db() as con:
            sql='''SELECT a.*,r.acknowledged_at FROM operations_alerts a JOIN operations_alert_recipients r ON r.alert_id=a.id AND r.user_id=?
                WHERE a.band_id=?''';values=[uid,band_id]
            if event_id is not None:sql+=' AND a.event_id=?';values.append(event_id)
            rows=con.execute(sql+' ORDER BY (r.acknowledged_at IS NOT NULL),a.id DESC LIMIT 100',values).fetchall()
            result=[]
            for row in rows:
                item=dict(row)
                recipients=[dict(r) for r in con.execute('''SELECT coalesce(m.name,u.display_name) AS display_name,r.acknowledged_at FROM operations_alert_recipients r
                    JOIN users u ON u.id=r.user_id JOIN band_users b ON b.user_id=r.user_id AND b.band_id=?
                    LEFT JOIN roster_accounts a ON a.band_id=b.band_id AND a.user_id=u.id LEFT JOIN members m ON m.id=a.member_id AND m.band_id=b.band_id WHERE r.alert_id=? ORDER BY u.display_name''',(band_id,row['id']))]
                item['required_count']=len(recipients);item['acknowledged_count']=sum(r['acknowledged_at'] is not None for r in recipients)
                if is_manager(con,band_id,uid):item['recipients']=recipients
                result.append(item)
            return result
    @router.post('/api/me/operations-alerts/{alert_id}/acknowledge')
    def acknowledge(alert_id:int,request:Request):
        uid=actor(request)
        with db() as con:
            row=con.execute('''UPDATE operations_alert_recipients SET acknowledged_at=coalesce(acknowledged_at,?)
                WHERE alert_id=? AND user_id=? AND EXISTS(SELECT 1 FROM operations_alerts a JOIN band_users b ON b.band_id=a.band_id
                WHERE a.id=alert_id AND b.user_id=?)''',(int(time.time()),alert_id,uid,uid))
            if row.rowcount!=1:raise HTTPException(404,'Alert not found')
        return {'acknowledged':True}
    return router
