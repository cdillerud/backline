"""Private named calendars and authenticated iCalendar downloads.

No bearer-in-URL feeds, anonymous events or public calendar sharing.
"""
import datetime
import json
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from .show_schedule import TIME_PATTERN, valid_timezone
from zoneinfo import ZoneInfo

router=APIRouter()
class Calendar(BaseModel):
    name:str=Field(min_length=1,max_length=100,pattern=r'.*\S.*')
    color:str=Field(default='#b9fb74',pattern=r'^#[0-9a-fA-F]{6}$')
class Assignment(BaseModel):
    calendar_id:int

def setup(con):
    con.executescript('''CREATE TABLE IF NOT EXISTS band_calendars(
        id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),name TEXT NOT NULL,color TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS event_calendars(
        event_id INTEGER PRIMARY KEY REFERENCES events(id),band_id INTEGER NOT NULL REFERENCES bands(id),
        calendar_id INTEGER NOT NULL REFERENCES band_calendars(id));''')

def ical_escape(value):
    return str(value or '').replace('\\','\\\\').replace('\r\n','\n').replace('\r','\n').replace('\n',r'\n').replace(';',r'\;').replace(',',r'\,')

def fold_line(line):
    """Fold UTF-8 by octets; continuation space counts toward the 75-byte limit."""
    chunks=[];part='';size=0
    for char in line:
        width=len(char.encode('utf-8'))
        if size+width>75:
            chunks.append(part);part=' ';size=1
        part+=char;size+=width
    return '\r\n'.join(chunks+[part])

def render_ical(name,events):
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Backline//Private Calendar//EN','CALSCALE:GREGORIAN',
           'X-WR-CALNAME:'+ical_escape(name)]
    for event in events:
        advance=event['advance']
        lines.extend(['BEGIN:VEVENT',f"UID:backline-{event['band_id']}-{event['id']}@backline.local",
                      'DTSTAMP:'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
                      'SUMMARY:'+ical_escape(event['title']),'LOCATION:'+ical_escape(event['venue'])])
        clock=advance.get('show_time') or event['time']
        zone=advance.get('timezone','')
        if TIME_PATTERN.fullmatch(clock) and valid_timezone(zone):
            day=datetime.date.fromisoformat(event['date'])+datetime.timedelta(days=advance.get('day_offsets',{}).get('show_time',0))
            when=datetime.datetime.combine(day,datetime.time.fromisoformat(clock),tzinfo=ZoneInfo(zone))
            lines.append('DTSTART:'+when.astimezone(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
        else:
            date=datetime.date.fromisoformat(event['date'])
            lines.extend(['DTSTART;VALUE=DATE:'+date.strftime('%Y%m%d'),
                          'DTEND;VALUE=DATE:'+(date+datetime.timedelta(days=1)).strftime('%Y%m%d')])
        descriptions=[event['kind'],event['notes'],'Calendar: '+event['calendar_name']]
        for key,label in (('timezone','Venue time zone'),('load_in','Load-in'),('doors','Doors'),('show_time','Show'),('curfew','Curfew')):
            if advance.get(key):descriptions.append(label+': '+advance[key]+(f" (day +{advance.get('day_offsets',{}).get(key)})" if advance.get('day_offsets',{}).get(key) else ''))
        if clock and not valid_timezone(zone):descriptions.append('Time '+clock+' requires a confirmed venue time zone; exported as an all-day event.')
        lines.append('DESCRIPTION:'+ical_escape('\n'.join(descriptions)))
        if event['status'].lower() in ('canceled','cancelled'):lines.append('STATUS:CANCELLED')
        lines.append('END:VEVENT')
    lines.append('END:VCALENDAR')
    return '\r\n'.join(fold_line(line) for line in lines)+'\r\n'

def attach(db):
    def band(con,band_id):
        row=con.execute('SELECT name FROM bands WHERE id=?',(band_id,)).fetchone()
        if not row:raise HTTPException(404,'Band not found')
        return row['name']
    @router.get('/api/bands/{band_id}/calendars')
    def list_calendars(band_id:int):
        with db() as con:
            band(con,band_id)
            return [dict(r) for r in con.execute('SELECT * FROM band_calendars WHERE band_id=? ORDER BY name,id',(band_id,))]
    @router.post('/api/bands/{band_id}/calendars',status_code=201)
    def add_calendar(band_id:int,data:Calendar):
        with db() as con:
            band(con,band_id)
            row=con.execute('INSERT INTO band_calendars(band_id,name,color) VALUES(?,?,?)',(band_id,data.name.strip(),data.color))
            return {'id':row.lastrowid}
    @router.put('/api/bands/{band_id}/events/{event_id}/calendar')
    def assign(band_id:int,event_id:int,data:Assignment):
        with db() as con:
            if not con.execute('SELECT 1 FROM events WHERE band_id=? AND id=?',(band_id,event_id)).fetchone():raise HTTPException(404,'Event not found')
            if not con.execute('SELECT 1 FROM band_calendars WHERE band_id=? AND id=?',(band_id,data.calendar_id)).fetchone():raise HTTPException(404,'Calendar not found')
            con.execute('''INSERT INTO event_calendars(event_id,band_id,calendar_id) VALUES(?,?,?)
                ON CONFLICT(event_id) DO UPDATE SET calendar_id=excluded.calendar_id''',(event_id,band_id,data.calendar_id))
        return {'assigned':True}
    @router.get('/api/bands/{band_id}/calendar/events')
    def calendar_events(band_id:int):
        with db() as con:
            band(con,band_id)
            rows=con.execute('''SELECT e.*,c.id AS calendar_id,c.name AS calendar_name,c.color AS calendar_color,a.body_json
                FROM events e LEFT JOIN event_calendars ec ON ec.event_id=e.id AND ec.band_id=e.band_id
                LEFT JOIN band_calendars c ON c.id=ec.calendar_id AND c.band_id=e.band_id
                LEFT JOIN venue_advances a ON a.event_id=e.id AND a.band_id=e.band_id
                WHERE e.band_id=? ORDER BY e.date,e.time,e.id''',(band_id,)).fetchall()
            result=[]
            for row in rows:
                item=dict(row);item['advance']=json.loads(item.pop('body_json') or '{}')
                item['calendar_name']=item['calendar_name'] or item['kind']
                item['calendar_color']=item['calendar_color'] or ('#b9fb74' if item['kind']=='Gig' else '#93c5fd')
                result.append(item)
            return result
    @router.get('/api/bands/{band_id}/calendar.ics')
    def export_calendar(band_id:int):
        with db() as con:name=band(con,band_id)
        return Response(render_ical(name,calendar_events(band_id)),media_type='text/calendar',
                        headers={'Content-Disposition':f'attachment; filename="backline-calendar-{band_id}.ics"','Cache-Control':'no-store'})
    return router
