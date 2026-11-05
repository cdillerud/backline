"""Scoped show guests and structured lodging; private operational PDFs stay manager-only."""
import datetime
import json
from fastapi import APIRouter,HTTPException,Request,Response
from pydantic import Field,field_validator,model_validator
from .collaboration import Strict,actor,notify
from .operations_audit import require_manager,is_manager,record_change,current_revision,check_revision
from .show_pdf import create_operations_pdf

router=APIRouter()
class GuestPolicy(Strict):
    revision:int=Field(default=0,ge=0)
    cutoff_at:datetime.datetime|None=None
    guest_limit:int=Field(default=100,ge=0,le=5000)
    pass_types:list[str]=Field(default_factory=lambda:['Guest'],min_length=1,max_length=20)
    change_reason:str=Field(default='',max_length=500)
    @field_validator('cutoff_at')
    @classmethod
    def aware(cls,value):
        if value is not None and value.utcoffset() is None:raise ValueError('Cutoff requires a time zone offset')
        return value
    @field_validator('pass_types')
    @classmethod
    def passes(cls,value):
        if any(not item.strip() or len(item)>60 for item in value):raise ValueError('Pass types must have 1 to 60 characters')
        return list(dict.fromkeys(item.strip() for item in value))
class GuestInput(Strict):
    name:str=Field(min_length=1,max_length=160,pattern=r'.*\S.*')
    quantity:int=Field(default=1,ge=1,le=10)
    pass_type:str=Field(default='Guest',min_length=1,max_length=60)
    note:str=Field(default='',max_length=1000)
class GuestDecision(Strict):
    revision:int=Field(ge=0)
    status:str=Field(pattern='^(approved|declined|pending)$')
    reason:str=Field(default='',max_length=500)
class StayInput(Strict):
    revision:int=Field(default=0,ge=0)
    hotel:str=Field(min_length=1,max_length=180,pattern=r'.*\S.*')
    address:str=Field(default='',max_length=500)
    phone:str=Field(default='',max_length=80)
    check_in:datetime.datetime
    check_out:datetime.datetime
    event_id:int|None=None
    tour_id:int|None=None
    confirmation_reference:str=Field(default='',max_length=150)
    internal_notes:str=Field(default='',max_length=2000)
    traveler_notes:str=Field(default='',max_length=2000)
    cancelled:bool=False
    change_reason:str=Field(default='',max_length=500)
    @model_validator(mode='after')
    def dates(self):
        if self.check_in.utcoffset() is None or self.check_out.utcoffset() is None:raise ValueError('Hotel times require time zone offsets')
        if self.check_out<=self.check_in:raise ValueError('Check-out must follow check-in')
        if self.check_out.timestamp()-self.check_in.timestamp()>60*86400:raise ValueError('A stay cannot exceed 60 days')
        return self
class RoomInput(Strict):
    revision:int=Field(default=0,ge=0)
    label:str=Field(min_length=1,max_length=80,pattern=r'.*\S.*')
    room_type:str=Field(default='single',pattern='^(single|double|twin|suite|other)$')
    capacity:int=Field(default=1,ge=1,le=10)
    user_ids:list[int]=Field(default_factory=list,max_length=10)
    traveler_notes:str=Field(default='',max_length=1000)
    change_reason:str=Field(default='',max_length=500)
    @model_validator(mode='after')
    def capacity_check(self):
        if len(self.user_ids)!=len(set(self.user_ids)):raise ValueError('Room occupants must be unique')
        if len(self.user_ids)>self.capacity:raise ValueError('Room capacity exceeded')
        self.user_ids=sorted(self.user_ids)
        return self

def setup(con):
    con.executescript('''
      CREATE TABLE IF NOT EXISTS show_guest_policies(event_id INTEGER PRIMARY KEY REFERENCES events(id),band_id INTEGER NOT NULL REFERENCES bands(id),body_json TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS show_guests(id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),event_id INTEGER NOT NULL REFERENCES events(id),
        requested_by INTEGER NOT NULL REFERENCES users(id),name TEXT NOT NULL,quantity INTEGER NOT NULL,pass_type TEXT NOT NULL,note TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',decision_reason TEXT NOT NULL DEFAULT '',request_key TEXT NOT NULL,UNIQUE(event_id,requested_by,request_key));
      CREATE TABLE IF NOT EXISTS lodging_stays(id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),body_json TEXT NOT NULL,start_at INTEGER NOT NULL,end_at INTEGER NOT NULL,cancelled INTEGER NOT NULL DEFAULT 0);
      CREATE TABLE IF NOT EXISTS lodging_rooms(id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),stay_id INTEGER NOT NULL REFERENCES lodging_stays(id),body_json TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS lodging_room_people(room_id INTEGER NOT NULL REFERENCES lodging_rooms(id),stay_id INTEGER NOT NULL REFERENCES lodging_stays(id),
        user_id INTEGER NOT NULL REFERENCES users(id),PRIMARY KEY(room_id,user_id),UNIQUE(stay_id,user_id));
    ''')

def attach(db):
    def gig(con,band_id,event_id):
        row=con.execute("SELECT title,date FROM events WHERE band_id=? AND id=? AND kind='Gig'",(band_id,event_id)).fetchone()
        if not row:raise HTTPException(404,'Gig not found')
        return row
    def policy(con,band_id,event_id):
        row=con.execute('SELECT body_json FROM show_guest_policies WHERE band_id=? AND event_id=?',(band_id,event_id)).fetchone()
        data=json.loads(row['body_json']) if row else GuestPolicy().model_dump(mode='json',exclude={'revision','change_reason'})
        return data|{'revision':current_revision(con,band_id,'guest_policy',event_id)}
    def guest(con,band_id,event_id,guest_id):
        row=con.execute('SELECT * FROM show_guests WHERE band_id=? AND event_id=? AND id=?',(band_id,event_id,guest_id)).fetchone()
        if not row:raise HTTPException(404,'Guest request not found')
        return dict(row)
    def guest_body(row):return {key:row[key] for key in ('name','quantity','pass_type','note','status','decision_reason','requested_by')}
    @router.get('/api/bands/{band_id}/gigs/{event_id}/guest-policy')
    def read_policy(band_id:int,event_id:int,request:Request):
        actor(request)
        with db() as con:gig(con,band_id,event_id);return policy(con,band_id,event_id)
    @router.put('/api/bands/{band_id}/gigs/{event_id}/guest-policy')
    def save_policy(band_id:int,event_id:int,data:GuestPolicy,request:Request):
        uid=actor(request)
        with db() as con:
            con.execute('BEGIN IMMEDIATE');require_manager(con,band_id,uid);gig(con,band_id,event_id)
            check_revision(con,band_id,'guest_policy',event_id,data.revision)
            before=policy(con,band_id,event_id);before.pop('revision')
            approved=con.execute("SELECT coalesce(sum(quantity),0) FROM show_guests WHERE band_id=? AND event_id=? AND status='approved'",(band_id,event_id)).fetchone()[0]
            if data.guest_limit<approved:raise HTTPException(409,'Guest limit cannot be below the approved headcount')
            after=data.model_dump(mode='json',exclude={'revision','change_reason'})
            record_change(con,band_id,'guest_policy',event_id,before,after,uid,event_id,data.change_reason)
            con.execute('''INSERT INTO show_guest_policies(event_id,band_id,body_json) VALUES(?,?,?)
                ON CONFLICT(event_id) DO UPDATE SET body_json=excluded.body_json''',(event_id,band_id,json.dumps(after)))
        return {'saved':True}
    @router.get('/api/bands/{band_id}/gigs/{event_id}/guest-requests')
    def own_requests(band_id:int,event_id:int,request:Request):
        uid=actor(request)
        with db() as con:
            gig(con,band_id,event_id)
            return [dict(row)|{'revision':current_revision(con,band_id,'guest',row['id'])} for row in con.execute('SELECT * FROM show_guests WHERE band_id=? AND event_id=? AND requested_by=? ORDER BY id DESC',(band_id,event_id,uid))]
    @router.post('/api/bands/{band_id}/gigs/{event_id}/guest-requests',status_code=201)
    def request_guest(band_id:int,event_id:int,data:GuestInput,request:Request):
        uid=actor(request)
        with db() as con:
            con.execute('BEGIN IMMEDIATE');gig(con,band_id,event_id);rules=policy(con,band_id,event_id)
            if rules['cutoff_at'] and datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime.fromisoformat(rules['cutoff_at']):raise HTTPException(409,'Guest request cutoff has passed')
            if data.pass_type not in rules['pass_types']:raise HTTPException(422,'Choose an allowed pass type')
            key=json.dumps([data.name.strip().casefold(),data.pass_type.casefold()])
            existing=con.execute('SELECT * FROM show_guests WHERE event_id=? AND requested_by=? AND request_key=?',(event_id,uid,key)).fetchone()
            if existing and existing['status']!='cancelled':raise HTTPException(409,'A request for this guest and pass type already exists')
            before=guest_body(existing) if existing else None
            if existing:
                ident=existing['id']
                con.execute("UPDATE show_guests SET name=?,quantity=?,note=?,status='pending',decision_reason='' WHERE id=?",(data.name.strip(),data.quantity,data.note,ident))
            else:
                if con.execute('SELECT count(*) FROM show_guests WHERE event_id=? AND requested_by=?',(event_id,uid)).fetchone()[0]>=100:raise HTTPException(429,'At most 100 guest requests per person per show')
                if con.execute('SELECT count(*) FROM show_guests WHERE event_id=?',(event_id,)).fetchone()[0]>=5000:raise HTTPException(429,'This show has reached its guest-request limit')
                ident=con.execute('INSERT INTO show_guests(band_id,event_id,requested_by,name,quantity,pass_type,note,request_key) VALUES(?,?,?,?,?,?,?,?)',
                    (band_id,event_id,uid,data.name.strip(),data.quantity,data.pass_type,data.note,key)).lastrowid
            after={'name':data.name.strip(),'quantity':data.quantity,'pass_type':data.pass_type,'note':data.note,'status':'pending','decision_reason':'','requested_by':uid}
            record_change(con,band_id,'guest',ident,before,after,uid,event_id,'Guest request resubmitted' if existing else 'Guest request submitted')
            for manager in con.execute("SELECT user_id FROM band_users WHERE band_id=? AND role IN ('owner','manager')",(band_id,)).fetchall():
                notify(con,band_id,manager['user_id'],'operations','Guest request needs review','guest:'+str(ident))
            return {'id':ident,'status':'pending','resubmitted':bool(existing)}
    @router.post('/api/bands/{band_id}/gigs/{event_id}/guest-requests/{guest_id}/cancel')
    def cancel_guest(band_id:int,event_id:int,guest_id:int,request:Request):
        uid=actor(request)
        with db() as con:
            con.execute('BEGIN IMMEDIATE');before=guest(con,band_id,event_id,guest_id)
            if before['requested_by']!=uid:raise HTTPException(404,'Guest request not found')
            if before['status']=='cancelled':return {'cancelled':True}
            after=guest_body(before)|{'status':'cancelled'}
            record_change(con,band_id,'guest',guest_id,guest_body(before),after,uid,event_id,'Requester cancelled')
            con.execute("UPDATE show_guests SET status='cancelled' WHERE id=?",(guest_id,))
            for manager in con.execute("SELECT user_id FROM band_users WHERE band_id=? AND role IN ('owner','manager')",(band_id,)).fetchall():
                notify(con,band_id,manager['user_id'],'operations','Guest request cancelled; review box-office list','guest:'+str(guest_id))
        return {'cancelled':True}
    @router.get('/api/bands/{band_id}/gigs/{event_id}/guests')
    def guest_list(band_id:int,event_id:int,request:Request):
        uid=actor(request)
        with db() as con:
            require_manager(con,band_id,uid);gig(con,band_id,event_id)
            rows=[dict(row)|{'revision':current_revision(con,band_id,'guest',row['id'])} for row in con.execute('''SELECT g.*,coalesce(m.name,u.display_name) AS requester_name FROM show_guests g JOIN users u ON u.id=g.requested_by
                LEFT JOIN roster_accounts a ON a.band_id=g.band_id AND a.user_id=u.id LEFT JOIN members m ON m.id=a.member_id AND m.band_id=g.band_id
                WHERE g.band_id=? AND g.event_id=? ORDER BY g.name,g.id''',(band_id,event_id))]
            return {'items':rows,'approved_count':sum(row['quantity'] for row in rows if row['status']=='approved')}
    @router.put('/api/bands/{band_id}/gigs/{event_id}/guests/{guest_id}/decision')
    def decide_guest(band_id:int,event_id:int,guest_id:int,data:GuestDecision,request:Request):
        uid=actor(request)
        with db() as con:
            con.execute('BEGIN IMMEDIATE');require_manager(con,band_id,uid);before=guest(con,band_id,event_id,guest_id)
            check_revision(con,band_id,'guest',guest_id,data.revision)
            if before['status']=='cancelled':raise HTTPException(409,'Cancelled requests cannot be approved')
            if data.status=='approved':
                total=con.execute("SELECT coalesce(sum(quantity),0) FROM show_guests WHERE band_id=? AND event_id=? AND status='approved' AND id!=?",(band_id,event_id,guest_id)).fetchone()[0]
                if total+before['quantity']>policy(con,band_id,event_id)['guest_limit']:raise HTTPException(409,'Approved headcount would exceed the guest limit')
            after=guest_body(before)|{'status':data.status,'decision_reason':data.reason}
            changed=record_change(con,band_id,'guest',guest_id,guest_body(before),after,uid,event_id,data.reason)
            con.execute('UPDATE show_guests SET status=?,decision_reason=? WHERE id=?',(data.status,data.reason,guest_id))
            if changed:notify(con,band_id,before['requested_by'],'operations','Guest request '+data.status,'guest:'+str(guest_id))
        return {'saved':True}
    @router.get('/api/bands/{band_id}/gigs/{event_id}/guests.pdf')
    def guests_pdf(band_id:int,event_id:int,request:Request):
        uid=actor(request)
        with db() as con:
            require_manager(con,band_id,uid);event=gig(con,band_id,event_id)
            rows=con.execute("SELECT name,quantity,pass_type FROM show_guests WHERE band_id=? AND event_id=? AND status='approved' ORDER BY name,id",(band_id,event_id)).fetchall()
            payload=create_operations_pdf('Box-office guest list',event['title']+' | '+event['date']+' | Approved guests only',
                ['Guest','Count','Pass type'],[[r['name'],r['quantity'],r['pass_type']] for r in rows],f"Approved headcount: {sum(r['quantity'] for r in rows)}")
        return Response(payload,media_type='application/pdf',headers={'Cache-Control':'no-store','Content-Disposition':f'attachment; filename="backline-guests-{event_id}.pdf"'})
    def stay(con,band_id,stay_id):
        row=con.execute('SELECT * FROM lodging_stays WHERE band_id=? AND id=?',(band_id,stay_id)).fetchone()
        if not row:raise HTTPException(404,'Stay not found')
        return row
    def validate_links(con,band_id,data):
        for key,table in (('event_id','events'),('tour_id','tours')):
            value=getattr(data,key)
            if value is not None and not con.execute(f'SELECT 1 FROM {table} WHERE band_id=? AND id=?',(band_id,value)).fetchone():raise HTTPException(422,'Linked record must belong to this band')
    def check_occupants(con,band_id,stay_id,room_id,users,start,end,cancelled):
        for uid in users:
            if not con.execute('SELECT 1 FROM band_users WHERE band_id=? AND user_id=?',(band_id,uid)).fetchone():raise HTTPException(422,'Room occupants must belong to this band')
            other=con.execute('SELECT room_id FROM lodging_room_people WHERE stay_id=? AND user_id=? AND room_id!=?',(stay_id,uid,room_id or -1)).fetchone()
            if other:raise HTTPException(409,'A traveler is already assigned to another room in this stay')
            if not cancelled and con.execute('''SELECT 1 FROM lodging_room_people p JOIN lodging_stays s ON s.id=p.stay_id
                WHERE s.band_id=? AND p.user_id=? AND s.id!=? AND s.cancelled=0 AND s.start_at<? AND s.end_at>?''',(band_id,uid,stay_id,end,start)).fetchone():
                raise HTTPException(409,'A traveler already has an overlapping hotel assignment')
    @router.get('/api/bands/{band_id}/lodging')
    def lodging(band_id:int,request:Request):
        uid=actor(request)
        with db() as con:
            manager=is_manager(con,band_id,uid);result=[]
            for row in con.execute('SELECT * FROM lodging_stays WHERE band_id=? ORDER BY start_at,id',(band_id,)):
                rooms=[]
                for room in con.execute('SELECT * FROM lodging_rooms WHERE stay_id=? AND band_id=? ORDER BY id',(row['id'],band_id)):
                    people=[dict(p) for p in con.execute('''SELECT u.id,coalesce(m.name,u.display_name) AS display_name FROM lodging_room_people p JOIN users u ON u.id=p.user_id
                        JOIN band_users b ON b.band_id=? AND b.user_id=p.user_id LEFT JOIN roster_accounts a ON a.band_id=b.band_id AND a.user_id=u.id
                        LEFT JOIN members m ON m.id=a.member_id AND m.band_id=b.band_id WHERE p.room_id=? ORDER BY u.display_name''',(band_id,room['id']))]
                    if manager or any(p['id']==uid for p in people):
                        body=json.loads(room['body_json'])
                        # Ordinary travelers receive their room only, without other occupants' identities.
                        if not manager:body.pop('user_ids',None)
                        rooms.append(body|{'id':room['id'],'people':people if manager else [],'revision':current_revision(con,band_id,'room',room['id'])})
                if manager or rooms:
                    body=json.loads(row['body_json'])
                    if not manager:
                        for key in ('confirmation_reference','internal_notes','tour_id','event_id'):body.pop(key,None)
                    result.append(body|{'id':row['id'],'rooms':rooms,'revision':current_revision(con,band_id,'lodging',row['id'])})
            return {'items':result,'can_manage':manager}
    @router.post('/api/bands/{band_id}/lodging',status_code=201)
    def add_stay(band_id:int,data:StayInput,request:Request):
        uid=actor(request);after=data.model_dump(mode='json',exclude={'revision','change_reason'})
        with db() as con:
            require_manager(con,band_id,uid);validate_links(con,band_id,data)
            row=con.execute('INSERT INTO lodging_stays(band_id,body_json,start_at,end_at,cancelled) VALUES(?,?,?,?,?)',(band_id,json.dumps(after),int(data.check_in.timestamp()),int(data.check_out.timestamp()),data.cancelled))
            record_change(con,band_id,'lodging',row.lastrowid,None,after,uid,data.event_id,data.change_reason)
            return {'id':row.lastrowid}
    @router.put('/api/bands/{band_id}/lodging/{stay_id}')
    def edit_stay(band_id:int,stay_id:int,data:StayInput,request:Request):
        uid=actor(request);after=data.model_dump(mode='json',exclude={'revision','change_reason'})
        with db() as con:
            con.execute('BEGIN IMMEDIATE');require_manager(con,band_id,uid);before=stay(con,band_id,stay_id)
            check_revision(con,band_id,'lodging',stay_id,data.revision);validate_links(con,band_id,data)
            for room in con.execute('SELECT id FROM lodging_rooms WHERE stay_id=? AND band_id=?',(stay_id,band_id)).fetchall():
                users=[r['user_id'] for r in con.execute('SELECT user_id FROM lodging_room_people WHERE room_id=?',(room['id'],))]
                check_occupants(con,band_id,stay_id,room['id'],users,int(data.check_in.timestamp()),int(data.check_out.timestamp()),data.cancelled)
            record_change(con,band_id,'lodging',stay_id,json.loads(before['body_json']),after,uid,data.event_id,data.change_reason)
            con.execute('UPDATE lodging_stays SET body_json=?,start_at=?,end_at=?,cancelled=? WHERE id=?',(json.dumps(after),int(data.check_in.timestamp()),int(data.check_out.timestamp()),data.cancelled,stay_id))
        return {'saved':True}
    def save_room(con,band_id,stay_id,room_id,data,uid):
        require_manager(con,band_id,uid);info=stay(con,band_id,stay_id)
        previous=con.execute('SELECT * FROM lodging_rooms WHERE band_id=? AND stay_id=? AND id=?',(band_id,stay_id,room_id)).fetchone() if room_id else None
        if room_id and not previous:raise HTTPException(404,'Room not found')
        if room_id:check_revision(con,band_id,'room',room_id,data.revision)
        check_occupants(con,band_id,stay_id,room_id,data.user_ids,info['start_at'],info['end_at'],info['cancelled'])
        after=data.model_dump(exclude={'revision','change_reason'})
        if room_id:
            con.execute('UPDATE lodging_rooms SET body_json=? WHERE id=?',(json.dumps(after),room_id))
            con.execute('DELETE FROM lodging_room_people WHERE room_id=?',(room_id,))
        else:room_id=con.execute('INSERT INTO lodging_rooms(band_id,stay_id,body_json) VALUES(?,?,?)',(band_id,stay_id,json.dumps(after))).lastrowid
        con.executemany('INSERT INTO lodging_room_people(room_id,stay_id,user_id) VALUES(?,?,?)',[(room_id,stay_id,user) for user in data.user_ids])
        record_change(con,band_id,'room',room_id,json.loads(previous['body_json']) if previous else None,after,uid,json.loads(info['body_json']).get('event_id'),data.change_reason)
        return {'id':room_id}
    @router.post('/api/bands/{band_id}/lodging/{stay_id}/rooms',status_code=201)
    def add_room(band_id:int,stay_id:int,data:RoomInput,request:Request):
        with db() as con:con.execute('BEGIN IMMEDIATE');return save_room(con,band_id,stay_id,None,data,actor(request))
    @router.put('/api/bands/{band_id}/lodging/{stay_id}/rooms/{room_id}')
    def edit_room(band_id:int,stay_id:int,room_id:int,data:RoomInput,request:Request):
        with db() as con:con.execute('BEGIN IMMEDIATE');return save_room(con,band_id,stay_id,room_id,data,actor(request))
    @router.get('/api/bands/{band_id}/lodging/{stay_id}/rooming.pdf')
    def rooming_pdf(band_id:int,stay_id:int,request:Request):
        with db() as con:
            require_manager(con,band_id,actor(request));info=json.loads(stay(con,band_id,stay_id)['body_json']);rows=[]
            for room in con.execute('SELECT * FROM lodging_rooms WHERE band_id=? AND stay_id=? ORDER BY id',(band_id,stay_id)):
                body=json.loads(room['body_json'])
                names=[r['display_name'] for r in con.execute('''SELECT coalesce(m.name,u.display_name) AS display_name FROM lodging_room_people p JOIN users u ON u.id=p.user_id
                    JOIN band_users b ON b.band_id=? AND b.user_id=u.id LEFT JOIN roster_accounts a ON a.band_id=b.band_id AND a.user_id=u.id
                    LEFT JOIN members m ON m.id=a.member_id AND m.band_id=b.band_id WHERE p.room_id=? ORDER BY u.display_name''',(band_id,room['id']))]
                if names:
                    rows.extend([[body['label'],body['room_type'],name,1] for name in names])
                else:rows.append([body['label'],body['room_type'],'Unassigned',0])
            payload=create_operations_pdf('Private hotel rooming list',('CANCELLED - do not use | ' if info.get('cancelled') else 'ACTIVE | ')+info['hotel']+' | '+info['check_in']+' to '+info['check_out'],['Room','Type','Travelers','Count'],rows,info['address'])
        return Response(payload,media_type='application/pdf',headers={'Cache-Control':'no-store','Content-Disposition':f'attachment; filename="backline-rooming-{stay_id}.pdf"'})
    return router
