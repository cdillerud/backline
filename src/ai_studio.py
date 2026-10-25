"""AI Gig Studio foundation: source-backed market findings and approval-only drafts.

No autonomous external publishing. No arbitrary URL fetching (SSRF risk).
Market findings must have explicit source URLs supplied from a trusted event-data adapter.
"""
import datetime
import time
from .market_provider import discover
from .campaign_strategy import drafts as build_drafts
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl

router=APIRouter()
class Finding(BaseModel):
    title:str=Field(min_length=1,max_length=200)
    source_url:HttpUrl
    event_date:datetime.date
    venue:str=Field(default='',max_length=160)
    category:str=Field(default='Concert',max_length=60)
    relevance:str=Field(default='',max_length=600)
class Draft(BaseModel):
    channel:str=Field(pattern='^(Facebook|Instagram|Email|Press|Other)$')
    angle:str=Field(min_length=1,max_length=120)
    body:str=Field(min_length=1,max_length=4000)
class Approval(BaseModel):
    note:str=Field(default='',max_length=500)

def setup(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS gig_market_findings (
      id INTEGER PRIMARY KEY, band_id INTEGER NOT NULL REFERENCES bands(id),
      event_id INTEGER NOT NULL REFERENCES events(id), title TEXT NOT NULL,
      source_url TEXT NOT NULL, event_date TEXT NOT NULL,
      venue TEXT NOT NULL DEFAULT '', category TEXT NOT NULL,
      relevance TEXT NOT NULL DEFAULT '',
      captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS gig_market_scans (
      band_id INTEGER NOT NULL REFERENCES bands(id),
      event_id INTEGER NOT NULL REFERENCES events(id),
      city TEXT NOT NULL,
      event_date TEXT NOT NULL,
      scanned_at INTEGER NOT NULL,
      PRIMARY KEY(band_id,event_id,city,event_date)
    );
    CREATE TABLE IF NOT EXISTS gig_campaign_drafts (
      id INTEGER PRIMARY KEY, band_id INTEGER NOT NULL REFERENCES bands(id),
      event_id INTEGER NOT NULL REFERENCES events(id), channel TEXT NOT NULL,
      angle TEXT NOT NULL, body TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','approved')),
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS gig_campaign_reviews (
      id INTEGER PRIMARY KEY, draft_id INTEGER NOT NULL REFERENCES gig_campaign_drafts(id),
      action TEXT NOT NULL, note TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
def attach(db):
    def gig(con,band,event):
        if not con.execute("SELECT id FROM events WHERE band_id=? AND id=? AND kind='Gig'",(band,event)).fetchone():
            raise HTTPException(404,'Gig not found in band')
    @router.post('/api/bands/{band_id}/gigs/{event_id}/market/discover')
    def discover_market(band_id:int,event_id:int,city:str):
        with db() as c:
            gig(c,band_id,event_id)
            target=c.execute('SELECT date FROM events WHERE id=?',(event_id,)).fetchone()['date']
            city=city.strip().lower()
            if not city or len(city)>100:
                raise HTTPException(422,'Valid city required')
            recent=c.execute("""SELECT scanned_at FROM gig_market_scans
                WHERE band_id=? AND event_id=? AND city=? AND event_date=?""",
                (band_id,event_id,city,target)).fetchone()
            if recent and time.time()-recent['scanned_at']<21600:
                return {'status':'cached','added':0}
        found=discover(city,target)
        added=0
        with db() as c:
            gig(c,band_id,event_id)
            for item in found:
                exists=c.execute("""SELECT 1 FROM gig_market_findings
                    WHERE band_id=? AND event_id=? AND source_url=?""",
                    (band_id,event_id,item['source_url'])).fetchone()
                if exists:continue
                c.execute("""INSERT INTO gig_market_findings
                  (band_id,event_id,title,source_url,event_date,venue,category,relevance)
                  VALUES(?,?,?,?,?,?,?,?)""",(band_id,event_id,item['title'],
                    item['source_url'],item['event_date'],item['venue'],
                    item['category'],'Ticketmaster Discovery'))
                added+=1
            c.execute("""INSERT INTO gig_market_scans(band_id,event_id,city,event_date,scanned_at)
                VALUES(?,?,?,?,?) ON CONFLICT(band_id,event_id,city,event_date)
                DO UPDATE SET scanned_at=excluded.scanned_at""",
                (band_id,event_id,city,target,int(time.time())))
        return {'status':'complete','found':len(found),'added':added}
    @router.get('/api/bands/{band_id}/gigs/{event_id}/market')
    def market(band_id:int,event_id:int):
        with db() as c:
            gig(c,band_id,event_id)
            return [dict(x) for x in c.execute("""SELECT * FROM gig_market_findings
              WHERE band_id=? AND event_id=? ORDER BY event_date,id""",(band_id,event_id))]
    @router.post('/api/bands/{band_id}/gigs/{event_id}/market',status_code=201)
    def add_market(band_id:int,event_id:int,data:Finding):
        with db() as c:
            gig(c,band_id,event_id)
            q=c.execute("""INSERT INTO gig_market_findings
              (band_id,event_id,title,source_url,event_date,venue,category,relevance)
              VALUES(?,?,?,?,?,?,?,?)""",(band_id,event_id,data.title,str(data.source_url),
              str(data.event_date),data.venue,data.category,data.relevance))
            return {'id':q.lastrowid}
    @router.post('/api/bands/{band_id}/gigs/{event_id}/campaign/generate')
    def generate_campaign(band_id:int,event_id:int):
        with db() as c:
            gig(c,band_id,event_id)
            event=dict(c.execute('SELECT * FROM events WHERE id=?',(event_id,)).fetchone())
            band=dict(c.execute('SELECT * FROM bands WHERE id=?',(band_id,)).fetchone())
            findings=[dict(row) for row in c.execute("""SELECT * FROM gig_market_findings
                WHERE band_id=? AND event_id=?""",(band_id,event_id))]
            campaign=build_drafts(event,band,findings)
            created=[]
            for item in campaign['drafts']:
                row=c.execute("""INSERT INTO gig_campaign_drafts
                    (band_id,event_id,channel,angle,body) VALUES(?,?,?,?,?)""",
                    (band_id,event_id,item['channel'],item['angle'],item['body']))
                created.append(row.lastrowid)
            return {'draft_ids':created,'strategy':campaign['strategy'],
                    'verification_required':campaign['verification_required'],
                    'generated_by':campaign['generated_by'],'published':False}
    @router.get('/api/bands/{band_id}/gigs/{event_id}/campaign')
    def campaign(band_id:int,event_id:int):
        with db() as c:
            gig(c,band_id,event_id)
            return [dict(x) for x in c.execute("""SELECT * FROM gig_campaign_drafts
              WHERE band_id=? AND event_id=? ORDER BY id DESC""",(band_id,event_id))]
    @router.post('/api/bands/{band_id}/gigs/{event_id}/campaign',status_code=201)
    def create_draft(band_id:int,event_id:int,data:Draft):
        with db() as c:
            gig(c,band_id,event_id)
            q=c.execute("""INSERT INTO gig_campaign_drafts(band_id,event_id,channel,angle,body)
                VALUES(?,?,?,?,?)""",(band_id,event_id,data.channel,data.angle,data.body))
            return {'id':q.lastrowid,'status':'draft'}
    @router.post('/api/bands/{band_id}/gigs/{event_id}/campaign/{draft_id}/approve')
    def approve(band_id:int,event_id:int,draft_id:int,data:Approval):
        with db() as c:
            gig(c,band_id,event_id)
            current=c.execute("""SELECT status FROM gig_campaign_drafts
                WHERE id=? AND event_id=? AND band_id=?""",(draft_id,event_id,band_id)).fetchone()
            if not current:raise HTTPException(404,'Draft not found')
            if current['status']=='approved':raise HTTPException(409,'Already approved')
            c.execute("UPDATE gig_campaign_drafts SET status='approved' WHERE id=?",(draft_id,))
            c.execute("INSERT INTO gig_campaign_reviews(draft_id,action,note) VALUES(?,?,?)",
                (draft_id,'approved',data.note))
            return {'status':'approved','published':False}
    return router
