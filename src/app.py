"""Backline local-first band management MVP.
Run: uvicorn src.app:app --reload (from project root).
"""
from __future__ import annotations
import os, sqlite3, json, datetime
from contextlib import contextmanager
from pathlib import Path
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('BACKLINE_DB', ROOT.parent / 'backline.db'))
app = FastAPI(title='Backline API', version='0.1.0')
app.mount('/static', StaticFiles(directory=str(ROOT/'static')), name='static')
from .security import install_preview_auth
install_preview_auth(app)

@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=10)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        yield con
        con.commit()
    except:
        con.rollback(); raise
    finally: con.close()

def init_db():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS bands (id INTEGER PRIMARY KEY, name TEXT NOT NULL, genre TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS members (id INTEGER PRIMARY KEY, band_id INTEGER NOT NULL REFERENCES bands(id), name TEXT NOT NULL, instrument TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '', role TEXT NOT NULL DEFAULT 'Member', active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, band_id INTEGER NOT NULL REFERENCES bands(id), kind TEXT NOT NULL CHECK(kind IN ('Gig','Rehearsal')), title TEXT NOT NULL, venue TEXT NOT NULL DEFAULT '', date TEXT NOT NULL, time TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'Planned', notes TEXT NOT NULL DEFAULT '', fee_cents INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS songs (id INTEGER PRIMARY KEY, band_id INTEGER NOT NULL REFERENCES bands(id), title TEXT NOT NULL, artist TEXT NOT NULL DEFAULT '', song_key TEXT NOT NULL DEFAULT '', bpm INTEGER, duration_seconds INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'Learning', notes TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS setlists (id INTEGER PRIMARY KEY, band_id INTEGER NOT NULL REFERENCES bands(id), title TEXT NOT NULL, event_id INTEGER REFERENCES events(id), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS setlist_songs (id INTEGER PRIMARY KEY, setlist_id INTEGER NOT NULL REFERENCES setlists(id) ON DELETE CASCADE, song_id INTEGER NOT NULL REFERENCES songs(id), position INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, band_id INTEGER NOT NULL REFERENCES bands(id), event_id INTEGER REFERENCES events(id), member_id INTEGER REFERENCES members(id), kind TEXT NOT NULL CHECK(kind IN ('income','expense','payout','contribution')), amount_cents INTEGER NOT NULL CHECK(amount_cents>0), category TEXT NOT NULL DEFAULT '', description TEXT NOT NULL, date TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, reversal_of INTEGER REFERENCES transactions(id), UNIQUE(reversal_of));
        CREATE TABLE IF NOT EXISTS settlements (id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL UNIQUE REFERENCES events(id), reserve_basis_points INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS settlement_shares (id INTEGER PRIMARY KEY, settlement_id INTEGER NOT NULL REFERENCES settlements(id), member_id INTEGER NOT NULL REFERENCES members(id), amount_cents INTEGER NOT NULL CHECK(amount_cents>=0), UNIQUE(settlement_id,member_id));
        ''')
        if not c.execute('SELECT 1 FROM bands LIMIT 1').fetchone():
            c.execute('INSERT INTO bands(name,genre,description) VALUES(?,?,?)',('My Band','Rock / Americana','Your band workspace'))

def fetchall(query, args=()):
    with db() as c: return [dict(r) for r in c.execute(query,args).fetchall()]

def fetchone(query,args=()):
    with db() as c:
        x=c.execute(query,args).fetchone();return dict(x) if x else None

def cents(value):
    try:
        d=Decimal(str(value)); a=int((d*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
        if not d.is_finite() or a<0 or a>100000000000: raise ValueError()
        return a
    except (InvalidOperation, ValueError, OverflowError): raise HTTPException(422,'Invalid nonnegative money amount')

def band_exists(band_id):
    if not fetchone('SELECT id FROM bands WHERE id=?',(band_id,)): raise HTTPException(404,'Band not found')

def valid_member(c,band_id,member_id):
    if member_id is not None and not c.execute('SELECT 1 FROM members WHERE band_id=? AND id=?',(band_id,member_id)).fetchone(): raise HTTPException(422,'Member does not belong to band')

def valid_event(c,band_id,event_id):
    if event_id is not None and not c.execute('SELECT 1 FROM events WHERE band_id=? AND id=?',(band_id,event_id)).fetchone(): raise HTTPException(422,'Event does not belong to band')

class BandInput(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    genre: str = Field(default='',max_length=120)
    description: str = Field(default='',max_length=500)
class MemberInput(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    instrument: str = Field(default='',max_length=100)
    email: str = Field(default='',max_length=200)
    role: str = Field(default='Member',max_length=40)
class EventInput(BaseModel):
    kind: str
    title: str = Field(min_length=1,max_length=150)
    venue: str = Field(default='',max_length=150)
    date: datetime.date
    time: str = ''
    status: str = 'Planned'
    notes: str = ''
    fee: str|int|float = '0'
class SongInput(BaseModel):
    title: str = Field(min_length=1,max_length=180)
    artist: str = ''
    song_key: str = ''
    bpm: int|None = Field(default=None,ge=1,le=400)
    duration_seconds: int = Field(default=0,ge=0,le=36000)
    status: str = 'Learning'
    notes: str = ''
class TransactionInput(BaseModel):
    kind: str
    amount: str|int|float
    description: str = Field(min_length=1,max_length=300)
    category: str = ''
    date: datetime.date
    event_id: int|None = None
    member_id: int|None = None
class SetlistInput(BaseModel):
    title: str = Field(min_length=1,max_length=160)
    event_id: int|None = None
    song_ids: list[int] = Field(default_factory=list,max_length=200)
class SettlementInput(BaseModel):
    member_ids: list[int] = Field(min_length=1)
    reserve_percent: int = Field(default=0,ge=0,le=100)

@app.get('/')
def home(): return FileResponse(ROOT/'static'/'index.html')
@app.get('/api/health')
def health(): return {'status':'ok','version':'0.1.0'}
@app.get('/api/bands')
def bands(): return fetchall('SELECT * FROM bands ORDER BY id')
@app.post('/api/bands',status_code=201)
def add_band(data:BandInput):
    with db() as c:
        cur=c.execute('INSERT INTO bands(name,genre,description) VALUES(?,?,?)',(data.name.strip(),data.genre,data.description));return {'id':cur.lastrowid}
@app.patch('/api/bands/{band_id}')
def update_band(band_id:int,data:BandInput):
    band_exists(band_id)
    with db() as c: c.execute('UPDATE bands SET name=?,genre=?,description=? WHERE id=?',(data.name.strip(),data.genre,data.description,band_id))
    return {'ok':True}
@app.get('/api/bands/{band_id}/members')
def members(band_id:int):
    band_exists(band_id);return fetchall('SELECT * FROM members WHERE band_id=? ORDER BY active DESC,name',(band_id,))
@app.post('/api/bands/{band_id}/members',status_code=201)
def add_member(band_id:int,data:MemberInput):
    band_exists(band_id)
    with db() as c:
        cur=c.execute('INSERT INTO members(band_id,name,instrument,email,role) VALUES(?,?,?,?,?)',(band_id,data.name.strip(),data.instrument,data.email,data.role));return {'id':cur.lastrowid}
@app.get('/api/bands/{band_id}/events')
def events(band_id:int):
    band_exists(band_id);return fetchall('SELECT * FROM events WHERE band_id=? ORDER BY date,time,id',(band_id,))
@app.post('/api/bands/{band_id}/events',status_code=201)
def add_event(band_id:int,data:EventInput):
    band_exists(band_id)
    if data.kind not in ('Gig','Rehearsal'):raise HTTPException(422,'Invalid event kind')
    with db() as c:
        cur=c.execute('INSERT INTO events(band_id,kind,title,venue,date,time,status,notes,fee_cents) VALUES(?,?,?,?,?,?,?,?,?)',(band_id,data.kind,data.title,data.venue,str(data.date),data.time,data.status,data.notes,cents(data.fee)));return {'id':cur.lastrowid}
@app.get('/api/bands/{band_id}/songs')
def songs(band_id:int):
    band_exists(band_id);return fetchall('SELECT * FROM songs WHERE band_id=? ORDER BY title',(band_id,))
@app.post('/api/bands/{band_id}/songs',status_code=201)
def add_song(band_id:int,data:SongInput):
    band_exists(band_id)
    with db() as c:
        cur=c.execute('INSERT INTO songs(band_id,title,artist,song_key,bpm,duration_seconds,status,notes) VALUES(?,?,?,?,?,?,?,?)',(band_id,data.title.strip(),data.artist,data.song_key,data.bpm,data.duration_seconds,data.status,data.notes));return {'id':cur.lastrowid}
@app.get('/api/bands/{band_id}/setlists')
def setlists(band_id:int):
    band_exists(band_id)
    result=fetchall('SELECT * FROM setlists WHERE band_id=? ORDER BY id DESC',(band_id,))
    for r in result:r['songs']=fetchall('SELECT s.*,ss.position FROM setlist_songs ss JOIN songs s ON s.id=ss.song_id WHERE ss.setlist_id=? ORDER BY ss.position',(r['id'],))
    return result
@app.post('/api/bands/{band_id}/setlists',status_code=201)
def add_setlist(band_id:int,data:SetlistInput):
    band_exists(band_id)
    with db() as c:
        valid_event(c,band_id,data.event_id)
        for song_id in data.song_ids:
            if not c.execute('SELECT 1 FROM songs WHERE id=? AND band_id=?',(song_id,band_id)).fetchone():raise HTTPException(422,'Song does not belong to band')
        cur=c.execute('INSERT INTO setlists(band_id,title,event_id) VALUES(?,?,?)',(band_id,data.title,data.event_id))
        for pos,song_id in enumerate(data.song_ids,1):c.execute('INSERT INTO setlist_songs(setlist_id,song_id,position) VALUES(?,?,?)',(cur.lastrowid,song_id,pos))
        return {'id':cur.lastrowid}
@app.get('/api/bands/{band_id}/transactions')
def transactions(band_id:int):
    band_exists(band_id)
    return fetchall('''SELECT t.*,e.title event_title,m.name member_name FROM transactions t LEFT JOIN events e ON t.event_id=e.id LEFT JOIN members m ON t.member_id=m.id WHERE t.band_id=? ORDER BY date DESC,id DESC''',(band_id,))
@app.post('/api/bands/{band_id}/transactions',status_code=201)
def add_transaction(band_id:int,data:TransactionInput):
    band_exists(band_id)
    if data.kind not in ('income','expense','payout','contribution'):raise HTTPException(422,'Invalid transaction type')
    amount=cents(data.amount)
    if not amount:raise HTTPException(422,'Amount must be positive')
    if data.kind=='payout' and data.member_id is None:raise HTTPException(422,'Payout requires member')
    with db() as c:
        valid_member(c,band_id,data.member_id);valid_event(c,band_id,data.event_id)
        if data.kind == 'payout' and data.event_id is not None:
            share = c.execute("""SELECT ss.amount_cents
                FROM settlement_shares ss
                JOIN settlements se ON se.id=ss.settlement_id
                WHERE se.event_id=? AND ss.member_id=?""",
                (data.event_id, data.member_id)).fetchone()
            if share is not None:
                paid = c.execute("""SELECT COALESCE(SUM(t.amount_cents),0)
                    FROM transactions t
                    WHERE t.event_id=? AND t.member_id=?
                    AND t.kind='payout' AND t.reversal_of IS NULL
                    AND NOT EXISTS (SELECT 1 FROM transactions rev WHERE rev.reversal_of=t.id)""",
                    (data.event_id, data.member_id)).fetchone()[0]
                if paid + amount > share['amount_cents']:
                    raise HTTPException(422,'Payout exceeds member settlement share')
        cur=c.execute('INSERT INTO transactions(band_id,event_id,member_id,kind,amount_cents,category,description,date) VALUES(?,?,?,?,?,?,?,?)',(band_id,data.event_id,data.member_id,data.kind,amount,data.category,data.description,str(data.date)))
        return {'id':cur.lastrowid}
@app.post('/api/bands/{band_id}/transactions/{transaction_id}/reverse',status_code=201)
def reverse_transaction(band_id:int,transaction_id:int):
    """Reversals are a new immutable compensating entry, never deletion."""
    with db() as c:
        t=c.execute('SELECT * FROM transactions WHERE id=? AND band_id=?',(transaction_id,band_id)).fetchone()
        if not t:raise HTTPException(404,'Transaction not found')
        if t['reversal_of'] is not None:raise HTTPException(409,'Cannot reverse a reversal')
        if c.execute('SELECT id FROM transactions WHERE reversal_of=?',(transaction_id,)).fetchone():raise HTTPException(409,'Already reversed')
        inverse={'income':'expense','expense':'income','payout':'contribution','contribution':'payout'}[t['kind']]
        c.execute('INSERT INTO transactions(band_id,event_id,member_id,kind,amount_cents,category,description,date,reversal_of) VALUES(?,?,?,?,?,?,?,?,?)',(band_id,t['event_id'],t['member_id'],inverse,t['amount_cents'],'Correction',f"Reversal of #{transaction_id}: {t['description']}",str(datetime.date.today()),transaction_id))
    return {'ok':True}
@app.get('/api/bands/{band_id}/finance')
def finance(band_id:int):
    band_exists(band_id)
    rows=fetchall('SELECT kind,COALESCE(SUM(amount_cents),0) total FROM transactions WHERE band_id=? GROUP BY kind',(band_id,))
    sums={r['kind']:r['total'] for r in rows}
    inflow=sums.get('income',0)+sums.get('contribution',0)
    outflow=sums.get('expense',0)+sums.get('payout',0)
    return {'income_cents':sums.get('income',0),'contributions_cents':sums.get('contribution',0),'expenses_cents':sums.get('expense',0),'payouts_cents':sums.get('payout',0),'balance_cents':inflow-outflow,'net_operating_cents':sums.get('income',0)-sums.get('expense',0)}
@app.get('/api/bands/{band_id}/settlements')
def settlements(band_id:int):
    band_exists(band_id)
    rows=fetchall('SELECT s.*,e.title event_title,e.date event_date FROM settlements s JOIN events e ON s.event_id=e.id WHERE e.band_id=? ORDER BY s.id DESC',(band_id,))
    for r in rows:
        r['shares']=fetchall('''SELECT ss.*,m.name member_name,(SELECT COALESCE(SUM(t.amount_cents),0) FROM transactions t WHERE t.member_id=ss.member_id AND t.event_id=s.event_id AND t.kind='payout' AND t.reversal_of IS NULL AND NOT EXISTS (SELECT 1 FROM transactions rev WHERE rev.reversal_of=t.id)) paid_cents FROM settlement_shares ss JOIN members m ON m.id=ss.member_id JOIN settlements s ON s.id=ss.settlement_id WHERE ss.settlement_id=?''',(r['id'],))
    return rows
@app.post('/api/bands/{band_id}/events/{event_id}/settle',status_code=201)
def settle(band_id:int,event_id:int,data:SettlementInput):
    """Settlement snapshots net gig cash once, splits cents deterministically."""
    if len(set(data.member_ids))!=len(data.member_ids):raise HTTPException(422,'Duplicate band members')
    with db() as c:
        e=c.execute("SELECT * FROM events WHERE id=? AND band_id=? AND kind='Gig'",(event_id,band_id)).fetchone()
        if not e:raise HTTPException(404,'Gig not found')
        if c.execute('SELECT id FROM settlements WHERE event_id=?',(event_id,)).fetchone():raise HTTPException(409,'Gig already settled')
        for mid in data.member_ids:valid_member(c,band_id,mid)
        amounts=c.execute("SELECT kind,COALESCE(SUM(amount_cents),0) AS n FROM transactions WHERE event_id=? AND kind IN ('income','expense') GROUP BY kind",(event_id,)).fetchall()
        agg={r['kind']:r['n'] for r in amounts}
        net=agg.get('income',0)-agg.get('expense',0)
        if net<0:raise HTTPException(422,'Gig has a loss: no payout to allocate')
        retained=net*data.reserve_percent//100
        available=net-retained
        ids=sorted(data.member_ids)
        base,remainder=divmod(available,len(ids))
        record=c.execute('INSERT INTO settlements(event_id,reserve_basis_points) VALUES(?,?)',(event_id,data.reserve_percent*100));sid=record.lastrowid
        for i,mid in enumerate(ids):c.execute('INSERT INTO settlement_shares(settlement_id,member_id,amount_cents) VALUES(?,?,?)',(sid,mid,base+(1 if i<remainder else 0)))
        return {'id':sid,'net_cents':net,'reserve_cents':retained,'distributable_cents':available}
@app.get('/api/bands/{band_id}/dashboard')
def dashboard(band_id:int):
    band_exists(band_id)
    today=datetime.date.today().isoformat()
    with db() as c:
        upcoming=[dict(r) for r in c.execute('SELECT * FROM events WHERE band_id=? AND date>=? ORDER BY date,time LIMIT 6',(band_id,today))]
        counts={'members':c.execute('SELECT COUNT(*) FROM members WHERE band_id=? AND active=1',(band_id,)).fetchone()[0], 'songs':c.execute('SELECT COUNT(*) FROM songs WHERE band_id=?',(band_id,)).fetchone()[0], 'gigs':c.execute("SELECT COUNT(*) FROM events WHERE band_id=? AND kind='Gig' AND date>=?",(band_id,today)).fetchone()[0]}
    return {'upcoming':upcoming,'counts':counts,'finance':finance(band_id)}

init_db()
