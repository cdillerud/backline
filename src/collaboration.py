"""Authenticated band collaboration and personal notifications.

Identity always comes from the session. Email is queued only; a transport must be
explicitly supplied to the testable dispatcher. No live sender is configured.
"""
import datetime
import json
import time
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .show_schedule import valid_timezone

router=APIRouter()
CATEGORIES=('task','rsvp','mention')
class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')
class RSVP(Strict):
    response:str=Field(pattern='^(yes|no|maybe|unknown)$')
    note:str=Field(default='',max_length=1000)
class Thread(Strict):
    title:str=Field(min_length=1,max_length=160,pattern=r'.*\S.*')
    scope:str=Field(default='band',pattern='^(band|song|setlist)$')
    scope_id:int|None=None
class Post(Strict):
    body:str=Field(min_length=1,max_length=5000,pattern=r'[\s\S]*\S[\s\S]*')
    mention_user_ids:list[int]=Field(default_factory=list,max_length=50)
class RosterLink(Strict):
    user_id:int
class Preferences(Strict):
    task:str=Field(default='immediate',pattern='^(immediate|daily|none)$')
    rsvp:str=Field(default='immediate',pattern='^(immediate|daily|none)$')
    mention:str=Field(default='immediate',pattern='^(immediate|daily|none)$')
    timezone:str=Field(default='America/Chicago',max_length=100)
    @field_validator('timezone')
    @classmethod
    def valid_zone(cls,value):
        if not valid_timezone(value):raise ValueError('Valid IANA time zone required')
        return value

def setup(con):
    con.executescript('''
      CREATE TABLE IF NOT EXISTS roster_accounts(
        band_id INTEGER NOT NULL REFERENCES bands(id),member_id INTEGER NOT NULL REFERENCES members(id),
        user_id INTEGER NOT NULL REFERENCES users(id),PRIMARY KEY(band_id,member_id),UNIQUE(band_id,user_id));
      CREATE TABLE IF NOT EXISTS event_rsvps(
        band_id INTEGER NOT NULL REFERENCES bands(id),event_id INTEGER NOT NULL REFERENCES events(id),
        user_id INTEGER NOT NULL REFERENCES users(id),response TEXT NOT NULL,note TEXT NOT NULL,
        updated_at INTEGER NOT NULL,PRIMARY KEY(event_id,user_id));
      CREATE TABLE IF NOT EXISTS discussion_threads(
        id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),title TEXT NOT NULL,
        scope TEXT NOT NULL,scope_id INTEGER,created_by INTEGER NOT NULL REFERENCES users(id));
      CREATE TABLE IF NOT EXISTS discussion_posts(
        id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),thread_id INTEGER NOT NULL REFERENCES discussion_threads(id),
        user_id INTEGER NOT NULL REFERENCES users(id),body TEXT NOT NULL,mentions_json TEXT NOT NULL,
        created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS typing_presence(
        thread_id INTEGER NOT NULL REFERENCES discussion_threads(id),band_id INTEGER NOT NULL REFERENCES bands(id),
        user_id INTEGER NOT NULL REFERENCES users(id),expires_at INTEGER NOT NULL,PRIMARY KEY(thread_id,user_id));
      CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),user_id INTEGER NOT NULL REFERENCES users(id),
        category TEXT NOT NULL,title TEXT NOT NULL,reference TEXT NOT NULL,created_at INTEGER NOT NULL,read_at INTEGER);
      CREATE TABLE IF NOT EXISTS notification_preferences(
        user_id INTEGER PRIMARY KEY REFERENCES users(id),body_json TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS email_outbox(
        notification_id INTEGER PRIMARY KEY REFERENCES notifications(id),available_at INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',delivery_key TEXT);
      CREATE TABLE IF NOT EXISTS task_reminder_runs(
        task_id INTEGER NOT NULL REFERENCES workspace_tasks(id),user_id INTEGER NOT NULL REFERENCES users(id),local_date TEXT NOT NULL,PRIMARY KEY(task_id,user_id,local_date));
      CREATE TABLE IF NOT EXISTS collaboration_audit(
        id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),actor_id INTEGER NOT NULL REFERENCES users(id),
        action TEXT NOT NULL,reference TEXT NOT NULL,created_at INTEGER NOT NULL);
    ''')

def actor(request):
    user=getattr(request.state,'user',None)
    if not user:raise HTTPException(401,'Individual account sign-in required for collaboration')
    return user['id']

def preferences(con,user_id):
    row=con.execute('SELECT body_json FROM notification_preferences WHERE user_id=?',(user_id,)).fetchone()
    return json.loads(row['body_json']) if row else Preferences().model_dump()

def delivery_time(prefs,category,now):
    if prefs[category]=='none':return None
    if prefs[category]=='immediate':return now
    local=datetime.datetime.fromtimestamp(now,ZoneInfo(prefs['timezone']))
    next_digest=local.replace(hour=9,minute=0,second=0,microsecond=0)
    if next_digest<=local:next_digest+=datetime.timedelta(days=1)
    return int(next_digest.timestamp())

def enqueue_task_reminders(con,user_id,now=None):
    now=int(time.time()) if now is None else now
    prefs=preferences(con,user_id)
    local_date=datetime.datetime.fromtimestamp(now,ZoneInfo(prefs['timezone'])).date()
    tomorrow=(local_date+datetime.timedelta(days=1)).isoformat()
    rows=con.execute("""SELECT t.id,t.band_id,t.body_json,r.member_id FROM workspace_tasks t
        JOIN roster_accounts r ON r.band_id=t.band_id AND r.user_id=?
        JOIN band_users b ON b.band_id=t.band_id AND b.user_id=r.user_id""",(user_id,)).fetchall()
    for row in rows:
        data=json.loads(row['body_json'])
        if data.get('completed') or data.get('assignee_id')!=row['member_id'] or data.get('due_date')!=tomorrow:continue
        inserted=con.execute('INSERT OR IGNORE INTO task_reminder_runs(task_id,user_id,local_date) VALUES(?,?,?)',(row['id'],user_id,str(local_date)))
        if inserted.rowcount:notify(con,row['band_id'],user_id,'task','Due tomorrow: '+data['title'],'task:'+str(row['id']),now)

def notify(con,band_id,user_id,category,title,reference,now=None):
    now=int(time.time()) if now is None else now
    if not con.execute('SELECT 1 FROM band_users WHERE band_id=? AND user_id=?',(band_id,user_id)).fetchone():return
    row=con.execute('INSERT INTO notifications(band_id,user_id,category,title,reference,created_at) VALUES(?,?,?,?,?,?)',
                    (band_id,user_id,category,title[:300],reference,now))
    prefs=preferences(con,user_id)
    if prefs[category]=='none':return row.lastrowid
    available=delivery_time(prefs,category,now)
    con.execute('INSERT INTO email_outbox(notification_id,available_at) VALUES(?,?)',(row.lastrowid,available))
    return row.lastrowid

def notify_task(con,band_id,task_id,data,previous=None):
    if data.assignee_id is None or previous and previous.get('assignee_id')==data.assignee_id:return
    row=con.execute('SELECT user_id FROM roster_accounts WHERE band_id=? AND member_id=?',(band_id,data.assignee_id)).fetchone()
    if row:notify(con,band_id,row['user_id'],'task','Task assigned: '+data.title,'task:'+str(task_id))

def dispatch_outbox(con,transport,now=None):
    """Explicit transport only. Supply a fake in tests; no background sender exists.

    Stable delivery keys support provider-side idempotency on a retry after a
    process crash. A real provider must honor these keys before live activation.
    """
    import hashlib
    now=int(time.time()) if now is None else now
    rows=con.execute('''SELECT n.*,u.email,o.available_at FROM email_outbox o JOIN notifications n ON n.id=o.notification_id
        JOIN users u ON u.id=n.user_id JOIN band_users b ON b.band_id=n.band_id AND b.user_id=n.user_id
        WHERE o.status='pending' AND o.available_at<=? ORDER BY n.id''',(now,)).fetchall()
    groups={}
    for row in rows:
        mode=preferences(con,row['user_id'])[row['category']]
        if mode=='none':
            con.execute("UPDATE email_outbox SET status='suppressed' WHERE notification_id=?",(row['id'],));continue
        key=(row['user_id'],row['available_at'] if mode=='daily' else row['id'],mode)
        groups.setdefault(key,[]).append(dict(row))
    delivered=0
    for items in groups.values():
        ids=[item['id'] for item in items]
        key='backline-'+hashlib.sha256(','.join(map(str,ids)).encode()).hexdigest()
        transport(email=items[0]['email'],items=items,idempotency_key=key)
        for notification_id in ids:con.execute("UPDATE email_outbox SET status='sent',delivery_key=? WHERE notification_id=?",(key,notification_id))
        delivered+=1
    return delivered

def attach(db):
    def record(con,table,band_id,record_id):
        row=con.execute(f'SELECT * FROM {table} WHERE id=? AND band_id=?',(record_id,band_id)).fetchone()
        if not row:raise HTTPException(404,'Band record not found')
        return row
    def thread(con,band_id,thread_id):return record(con,'discussion_threads',band_id,thread_id)
    def mentions(con,band_id,ids):
        for user_id in set(ids):
            if not con.execute('SELECT 1 FROM band_users WHERE band_id=? AND user_id=?',(band_id,user_id)).fetchone():raise HTTPException(422,'Mention must belong to this band')
    def rate(con,user_id):
        now=int(time.time())
        count=con.execute('SELECT count(*) FROM discussion_posts WHERE user_id=? AND created_at>?',(user_id,now-60)).fetchone()[0]
        if count>=20:raise HTTPException(429,'Please wait before posting more replies')
    @router.get('/api/bands/{band_id}/collaboration')
    def summary(band_id:int,request:Request):
        user_id=actor(request)
        with db() as con:
            membership=con.execute('SELECT role FROM band_users WHERE band_id=? AND user_id=?',(band_id,user_id)).fetchone()
            if not membership:raise HTTPException(403,'Band access denied')
            members=[dict(r) for r in con.execute('''SELECT u.id,coalesce(m.name,u.display_name) AS display_name,b.role,r.member_id,m.instrument
                FROM band_users b JOIN users u ON u.id=b.user_id LEFT JOIN roster_accounts r ON r.band_id=b.band_id AND r.user_id=b.user_id
                LEFT JOIN members m ON m.id=r.member_id AND m.band_id=b.band_id WHERE b.band_id=? ORDER BY u.display_name''',(band_id,))]
            return {'user_id':user_id,'role':membership['role'],'members':members,'email_delivery':'disabled'}
    @router.put('/api/bands/{band_id}/members/{member_id}/account')
    def link_roster(band_id:int,member_id:int,data:RosterLink,request:Request):
        user_id=actor(request)
        with db() as con:
            record(con,'members',band_id,member_id)
            if not con.execute('SELECT 1 FROM band_users WHERE band_id=? AND user_id=?',(band_id,data.user_id)).fetchone():raise HTTPException(422,'Account must belong to this band')
            existing=con.execute('SELECT member_id FROM roster_accounts WHERE band_id=? AND user_id=?',(band_id,data.user_id)).fetchone()
            if existing and existing['member_id']!=member_id:raise HTTPException(409,'Account already linked to another roster member')
            con.execute('''INSERT INTO roster_accounts(band_id,member_id,user_id) VALUES(?,?,?)
                ON CONFLICT(band_id,member_id) DO UPDATE SET user_id=excluded.user_id''',(band_id,member_id,data.user_id))
            con.execute('INSERT INTO collaboration_audit(band_id,actor_id,action,reference,created_at) VALUES(?,?,?,?,?)',
                        (band_id,user_id,'link_roster',str(member_id),int(time.time())))
        return {'linked':True}
    @router.get('/api/bands/{band_id}/events/{event_id}/rsvps')
    def rsvps(band_id:int,event_id:int,request:Request):
        actor(request)
        with db() as con:
            record(con,'events',band_id,event_id)
            return [dict(r) for r in con.execute('''SELECT u.id AS user_id,coalesce(m.name,u.display_name) AS display_name,
                m.instrument,a.member_id AS member_id,coalesce(r.response,'unknown') AS response,coalesce(r.note,'') AS note,r.updated_at
                FROM band_users b JOIN users u ON u.id=b.user_id
                LEFT JOIN roster_accounts a ON a.band_id=b.band_id AND a.user_id=b.user_id
                LEFT JOIN members m ON m.id=a.member_id AND m.band_id=b.band_id
                LEFT JOIN event_rsvps r ON r.user_id=b.user_id AND r.band_id=b.band_id AND r.event_id=?
                WHERE b.band_id=? ORDER BY display_name''',(event_id,band_id))]
    @router.put('/api/bands/{band_id}/events/{event_id}/rsvp')
    def save_rsvp(band_id:int,event_id:int,data:RSVP,request:Request):
        user_id=actor(request)
        with db() as con:
            record(con,'events',band_id,event_id)
            con.execute('''INSERT INTO event_rsvps(band_id,event_id,user_id,response,note,updated_at) VALUES(?,?,?,?,?,?)
                ON CONFLICT(event_id,user_id) DO UPDATE SET response=excluded.response,note=excluded.note,updated_at=excluded.updated_at''',
                        (band_id,event_id,user_id,data.response,data.note,int(time.time())))
        return {'saved':True}
    @router.post('/api/bands/{band_id}/events/{event_id}/rsvp-requests')
    def request_rsvps(band_id:int,event_id:int,request:Request):
        actor(request)
        with db() as con:
            event=record(con,'events',band_id,event_id)
            for row in con.execute("SELECT user_id FROM band_users WHERE band_id=? AND role IN ('owner','manager','member')",(band_id,)):
                notify(con,band_id,row['user_id'],'rsvp','RSVP requested: '+event['title'],'event:'+str(event_id))
        return {'requested':True,'email_delivery':'disabled'}
    @router.get('/api/bands/{band_id}/discussions')
    def threads(band_id:int,request:Request):
        actor(request)
        with db() as con:return [dict(r) for r in con.execute('SELECT * FROM discussion_threads WHERE band_id=? ORDER BY id DESC',(band_id,))]
    @router.post('/api/bands/{band_id}/discussions',status_code=201)
    def create_thread(band_id:int,data:Thread,request:Request):
        user_id=actor(request)
        with db() as con:
            if data.scope=='band' and data.scope_id is not None:raise HTTPException(422,'Band thread cannot have an item ID')
            if data.scope!='band':
                if data.scope_id is None:raise HTTPException(422,'Linked item required')
                record(con,'songs' if data.scope=='song' else 'setlists',band_id,data.scope_id)
            row=con.execute('INSERT INTO discussion_threads(band_id,title,scope,scope_id,created_by) VALUES(?,?,?,?,?)',(band_id,data.title,data.scope,data.scope_id,user_id))
            return {'id':row.lastrowid}
    @router.get('/api/bands/{band_id}/discussions/{thread_id}/posts')
    def posts(band_id:int,thread_id:int,request:Request,after:int=0):
        actor(request)
        with db() as con:
            thread(con,band_id,thread_id)
            return [dict(r)|{'mention_user_ids':json.loads(r['mentions_json'])} for r in con.execute('''SELECT p.*,a.member_id AS member_id,coalesce(m.name,u.display_name) AS display_name FROM discussion_posts p
                JOIN users u ON u.id=p.user_id LEFT JOIN roster_accounts a ON a.band_id=p.band_id AND a.user_id=p.user_id
                LEFT JOIN members m ON m.id=a.member_id AND m.band_id=p.band_id
                WHERE p.band_id=? AND p.thread_id=? AND p.id>? ORDER BY p.id LIMIT 500''',(band_id,thread_id,after))]
    @router.post('/api/bands/{band_id}/discussions/{thread_id}/posts',status_code=201)
    def add_post(band_id:int,thread_id:int,data:Post,request:Request):
        user_id=actor(request);now=int(time.time())
        with db() as con:
            info=thread(con,band_id,thread_id);rate(con,user_id);mentions(con,band_id,data.mention_user_ids)
            row=con.execute('INSERT INTO discussion_posts(band_id,thread_id,user_id,body,mentions_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                            (band_id,thread_id,user_id,data.body,json.dumps(sorted(set(data.mention_user_ids))),now,now))
            for mentioned in set(data.mention_user_ids)-{user_id}:notify(con,band_id,mentioned,'mention','Mention in '+info['title'],'thread:'+str(thread_id))
            return {'id':row.lastrowid}
    @router.put('/api/bands/{band_id}/discussions/{thread_id}/posts/{post_id}')
    def edit_post(band_id:int,thread_id:int,post_id:int,data:Post,request:Request):
        user_id=actor(request)
        with db() as con:
            thread(con,band_id,thread_id);row=record(con,'discussion_posts',band_id,post_id)
            if row['thread_id']!=thread_id or row['user_id']!=user_id:raise HTTPException(403,'Only the author can edit this reply')
            mentions(con,band_id,data.mention_user_ids)
            old=set(json.loads(row['mentions_json']))
            con.execute('UPDATE discussion_posts SET body=?,mentions_json=?,updated_at=? WHERE id=?',
                        (data.body,json.dumps(sorted(set(data.mention_user_ids))),int(time.time()),post_id))
            for mentioned in set(data.mention_user_ids)-old-{user_id}:notify(con,band_id,mentioned,'mention','Mention in discussion','thread:'+str(thread_id))
        return {'updated':True}
    @router.post('/api/bands/{band_id}/discussions/{thread_id}/typing')
    def typing(band_id:int,thread_id:int,request:Request):
        user_id=actor(request)
        with db() as con:
            thread(con,band_id,thread_id)
            con.execute('''INSERT INTO typing_presence(thread_id,band_id,user_id,expires_at) VALUES(?,?,?,?)
                ON CONFLICT(thread_id,user_id) DO UPDATE SET expires_at=excluded.expires_at''',(thread_id,band_id,user_id,int(time.time())+10))
        return {'expires_in':10}
    @router.get('/api/bands/{band_id}/discussions/{thread_id}/typing')
    def typing_users(band_id:int,thread_id:int,request:Request):
        user_id=actor(request)
        with db() as con:
            thread(con,band_id,thread_id)
            return [dict(r) for r in con.execute('''SELECT u.id,coalesce(m.name,u.display_name) AS display_name FROM typing_presence p JOIN users u ON u.id=p.user_id
                LEFT JOIN roster_accounts a ON a.band_id=p.band_id AND a.user_id=p.user_id
                LEFT JOIN members m ON m.id=a.member_id AND m.band_id=p.band_id
                JOIN band_users b ON b.user_id=p.user_id AND b.band_id=p.band_id
                WHERE p.thread_id=? AND p.band_id=? AND p.expires_at>? AND p.user_id!=?''',(thread_id,band_id,int(time.time()),user_id))]
    @router.get('/api/me/notifications')
    def notification_list(request:Request):
        user_id=actor(request)
        with db() as con:
            enqueue_task_reminders(con,user_id)
            return [dict(r) for r in con.execute('''SELECT n.* FROM notifications n JOIN band_users b ON b.band_id=n.band_id AND b.user_id=n.user_id
            WHERE n.user_id=? ORDER BY n.id DESC LIMIT 200''',(user_id,))]
    @router.post('/api/me/notifications/{notification_id}/read')
    def mark_read(notification_id:int,request:Request):
        user_id=actor(request)
        with db() as con:
            row=con.execute('''UPDATE notifications SET read_at=? WHERE id=? AND user_id=? AND EXISTS
                (SELECT 1 FROM band_users b WHERE b.band_id=notifications.band_id AND b.user_id=?)''',(int(time.time()),notification_id,user_id,user_id))
            if row.rowcount!=1:raise HTTPException(404,'Notification not found')
        return {'read':True}
    @router.get('/api/me/notification-preferences')
    def read_preferences(request:Request):
        with db() as con:return preferences(con,actor(request))|{'email_delivery':'disabled'}
    @router.put('/api/me/notification-preferences')
    def save_preferences(data:Preferences,request:Request):
        user_id=actor(request)
        with db() as con:
            con.execute('''INSERT INTO notification_preferences(user_id,body_json) VALUES(?,?)
                ON CONFLICT(user_id) DO UPDATE SET body_json=excluded.body_json''',(user_id,data.model_dump_json()))
            now=int(time.time())
            for row in con.execute('''SELECT n.id,n.category FROM notifications n JOIN email_outbox o ON o.notification_id=n.id
                WHERE n.user_id=? AND o.status='pending' ''',(user_id,)).fetchall():
                available=delivery_time(data.model_dump(),row['category'],now)
                if available is None:con.execute("UPDATE email_outbox SET status='suppressed' WHERE notification_id=?",(row['id'],))
                else:con.execute('UPDATE email_outbox SET available_at=? WHERE notification_id=?',(available,row['id']))
        return {'saved':True,'email_delivery':'disabled'}
    return router
