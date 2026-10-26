"""Bounded CSV itinerary import: source evidence, validated draft, explicit atomic apply."""
import csv
import io
import hashlib
from io import StringIO
import json
from fastapi import APIRouter,HTTPException,Request,Response
from pydantic import Field,ValidationError,field_validator
from .collaboration import Strict,actor
from .operations_audit import require_manager,record_change,check_revision,current_revision
from .tour_routes import StopInput

router=APIRouter()
COLUMNS={'date','city','region','venue','status','arrival_time','departure_time','lodging','travel_notes'}
class ImportInput(Strict):
    tour_id:int
    filename:str=Field(min_length=1,max_length=150)
    csv_text:str=Field(min_length=1,max_length=250000)
    @field_validator('csv_text')
    @classmethod
    def bounded_utf8(cls,value):
        try:encoded=value.encode('utf-8')
        except UnicodeEncodeError:raise ValueError('CSV must contain valid UTF-8 text') from None
        if len(encoded)>250000:raise ValueError('CSV exceeds 250 KB')
        return value
class MapColumns(Strict):
    """Transform existing source to a canonical, separately reviewable CSV."""
    mapping:dict[str,str]=Field(min_length=2,max_length=9)

def canonical_csv(source,mapping):
    if len(set(mapping.values()))!=len(mapping) or not {'date','city'}<=set(mapping.values()) or not set(mapping.values())<=COLUMNS:
        raise HTTPException(422,'Unique target columns including date and city are required')
    try:
        reader=csv.DictReader(StringIO(source.lstrip('\\ufeff')),strict=True)
        headers=reader.fieldnames
        if not headers or len(headers)!=len(set(headers)) or not set(mapping)<=set(headers):
            raise HTTPException(422,'Mapped source columns must exist and be unique')
        buf=io.StringIO()
        columns=[col for col in sorted(COLUMNS) if col in mapping.values()]
        writer=csv.DictWriter(buf,fieldnames=columns,lineterminator='\\n')
        writer.writeheader()
        for index,row in enumerate(reader,1):
            if index>200:raise HTTPException(422,'Import at most 200 rows at a time')
            if None in row or any(v is None for v in row.values()):
                raise HTTPException(422,f'Source row {index} has a column mismatch')
            writer.writerow({destination:row[source] for source,destination in mapping.items()})
        return buf.getvalue()
    except csv.Error:raise HTTPException(422,'Source CSV has invalid quoting or separators') from None

class MapSource(ImportInput):
    mapping:dict[str,str]=Field(min_length=2,max_length=9)

class ApplyImport(Strict):
    revision:int=Field(ge=0)
    row_ids:list[int]=Field(min_length=1,max_length=200)
    confirm:bool

def setup(con):
    con.execute('''CREATE TABLE IF NOT EXISTS itinerary_imports(
        id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),tour_id INTEGER NOT NULL REFERENCES tours(id),
        filename TEXT NOT NULL,source_text TEXT NOT NULL,source_sha256 TEXT NOT NULL,rows_json TEXT NOT NULL,
        created_by INTEGER NOT NULL REFERENCES users(id),UNIQUE(band_id,tour_id,source_sha256))''')

def stop_identity(data):return (str(data.get('date') or data.get('stop_date')),data['city'].strip().casefold(),data.get('venue','').strip().casefold())

def parse_csv(source):
    try:
        reader=csv.DictReader(StringIO(source.lstrip('\ufeff')),strict=True)
        headers=reader.fieldnames
        if not headers or len(headers)!=len(set(headers)) or not {'date','city'}<=set(headers) or not set(headers)<=COLUMNS:
            raise HTTPException(422,'CSV needs unique date and city columns; supported columns: '+', '.join(sorted(COLUMNS)))
        rows=[];seen=set()
        for index,row in enumerate(reader,1):
            if index>200:raise HTTPException(422,'Import at most 200 rows at a time')
            entry={'row_id':index,'source_line':reader.line_num,'status':'draft','stop_id':None,'data':None,'error':None}
            if None in row or any(value is None for value in row.values()):entry['error']='Column count does not match the header'
            else:
                try:
                    values={key:value.strip() for key,value in row.items()}
                    values['status']=values.get('status') or 'planned'
                    data=StopInput(**values).model_dump(mode='json',exclude={'revision','change_reason'})
                    key=stop_identity(data)
                    if key in seen:entry['error']='Duplicate date, city and venue within this file'
                    else:seen.add(key);entry['data']=data
                except ValidationError as exc:entry['error']='; '.join('.'.join(map(str,error['loc']))+': '+error['msg'] for error in exc.errors())
            rows.append(entry)
        if not rows:raise HTTPException(422,'CSV has no itinerary rows')
        return rows
    except csv.Error:raise HTTPException(422,'CSV could not be parsed; check quoting and column separators') from None

def attach(db):
    def get(con,band_id,import_id):
        row=con.execute('SELECT * FROM itinerary_imports WHERE id=? AND band_id=?',(import_id,band_id)).fetchone()
        if not row:raise HTTPException(404,'Import draft not found')
        return row
    def output(con,row):
        result={key:row[key] for key in ('id','tour_id','filename','source_sha256','created_by')}
        rows=json.loads(row['rows_json'])
        existing={stop_identity(dict(stop)) for stop in con.execute('SELECT stop_date,city,venue FROM tour_stops WHERE band_id=? AND tour_id=?',(row['band_id'],row['tour_id']))}
        for entry in rows:
            entry['duplicate_existing']=bool(entry['data'] and entry['status']=='draft' and stop_identity(entry['data']) in existing)
        return result|{'rows':rows,'revision':current_revision(con,row['band_id'],'import',row['id'])}
    @router.post('/api/bands/{band_id}/itinerary-imports/map-source')
    def map_source(band_id:int,data:MapSource,request:Request):
        with db() as con:
            require_manager(con,band_id,actor(request))
            if not con.execute('SELECT 1 FROM tours WHERE id=? AND band_id=?',(data.tour_id,band_id)).fetchone():
                raise HTTPException(404,'Tour not found')
        converted=canonical_csv(data.csv_text,data.mapping)
        rows=parse_csv(converted)
        return {'canonical_csv':converted,'rows':rows,
                'source_sha256':hashlib.sha256(data.csv_text.encode('utf-8')).hexdigest(),
                'original_unchanged':True,'requires_new_review':True}

    @router.post('/api/bands/{band_id}/itinerary-imports',status_code=201)
    def create(band_id:int,data:ImportInput,request:Request):
        uid=actor(request);rows=parse_csv(data.csv_text);digest=hashlib.sha256(data.csv_text.encode('utf-8')).hexdigest()
        with db() as con:
            con.execute('BEGIN IMMEDIATE');require_manager(con,band_id,uid)
            if not con.execute('SELECT 1 FROM tours WHERE id=? AND band_id=?',(data.tour_id,band_id)).fetchone():raise HTTPException(404,'Tour not found')
            existing=con.execute('SELECT * FROM itinerary_imports WHERE band_id=? AND tour_id=? AND source_sha256=?',(band_id,data.tour_id,digest)).fetchone()
            if existing:return output(con,existing)|{'reused':True}
            row=con.execute('INSERT INTO itinerary_imports(band_id,tour_id,filename,source_text,source_sha256,rows_json,created_by) VALUES(?,?,?,?,?,?,?)',
                (band_id,data.tour_id,data.filename,data.csv_text,digest,json.dumps(rows),uid))
            record_change(con,band_id,'import',row.lastrowid,None,{'filename':data.filename,'sha256':digest,'row_count':len(rows)},uid,reason='Created review-only CSV draft')
            return output(con,get(con,band_id,row.lastrowid))|{'reused':False}
    @router.get('/api/bands/{band_id}/itinerary-imports')
    def imports(band_id:int,request:Request):
        with db() as con:
            require_manager(con,band_id,actor(request))
            return [output(con,row) for row in con.execute('SELECT * FROM itinerary_imports WHERE band_id=? ORDER BY id DESC LIMIT 50',(band_id,))]
    @router.get('/api/bands/{band_id}/itinerary-imports/{import_id}')
    def draft(band_id:int,import_id:int,request:Request):
        with db() as con:require_manager(con,band_id,actor(request));return output(con,get(con,band_id,import_id))
    @router.get('/api/bands/{band_id}/itinerary-imports/{import_id}/source')
    def source(band_id:int,import_id:int,request:Request):
        with db() as con:
            require_manager(con,band_id,actor(request));row=get(con,band_id,import_id)
            return {'filename':row['filename'],'source_sha256':row['source_sha256'],'source_text':row['source_text']}
    @router.post('/api/bands/{band_id}/itinerary-imports/{import_id}/map-preview')
    def map_preview(band_id:int,import_id:int,data:MapColumns,request:Request):
        with db() as con:
            require_manager(con,band_id,actor(request))
            original=get(con,band_id,import_id)
            transformed=canonical_csv(original['source_text'],data.mapping)
        rows=parse_csv(transformed)
        return {'canonical_csv':transformed,'rows':rows,'valid_count':sum(bool(r['data']) for r in rows),
                'source_sha256':original['source_sha256'],'original_unchanged':True,
                'requires_new_review':True}

    @router.get('/api/bands/{band_id}/itinerary-imports/{import_id}/review.csv')
    def review_report(band_id:int,import_id:int,request:Request):
        """Manager-only spreadsheet-safe issues report; never applies source data."""
        with db() as con:
            require_manager(con,band_id,actor(request))
            draft=output(con,get(con,band_id,import_id))
        buf=io.StringIO()
        writer=csv.writer(buf)
        writer.writerow(['Row','Source line','Status','Issue','Duplicate existing','Date','City','Venue'])
        def safe(value):
            value=str(value if value is not None else '')
            return "'" + value if value.lstrip().startswith(('=','+','-','@')) else value
        for row in draft['rows']:
            data=row.get('data') or {}
            writer.writerow([row['row_id'],row['source_line'],row['status'],
                safe(row.get('error') or ''), 'Yes' if row.get('duplicate_existing') else 'No',
                safe(data.get('date','')),safe(data.get('city','')),safe(data.get('venue',''))])
        return Response(buf.getvalue(),media_type='text/csv; charset=utf-8',
            headers={'Content-Disposition':f'attachment; filename="itinerary-review-{import_id}.csv"',
                     'Cache-Control':'private, no-store', 'X-Content-Type-Options':'nosniff'})
    @router.post('/api/bands/{band_id}/itinerary-imports/{import_id}/apply')
    def apply(band_id:int,import_id:int,data:ApplyImport,request:Request):
        uid=actor(request)
        if not data.confirm:raise HTTPException(422,'Explicit review confirmation required')
        if len(set(data.row_ids))!=len(data.row_ids):raise HTTPException(422,'Select each row once')
        with db() as con:
            con.execute('BEGIN IMMEDIATE');require_manager(con,band_id,uid);info=get(con,band_id,import_id)
            check_revision(con,band_id,'import',import_id,data.revision)
            rows=json.loads(info['rows_json']);selected=[row for row in rows if row['row_id'] in data.row_ids]
            if len(selected)!=len(data.row_ids):raise HTTPException(422,'Selected row not in this draft')
            if any(row['status']!='draft' or row['error'] or not row['data'] for row in selected):raise HTTPException(409,'Only valid, unapplied draft rows can be imported')
            existing={stop_identity(dict(stop)) for stop in con.execute('SELECT stop_date,city,venue FROM tour_stops WHERE band_id=? AND tour_id=?',(band_id,info['tour_id']))}
            if any(stop_identity(row['data']) in existing for row in selected):raise HTTPException(409,'A selected stop already exists; deselect it and review the draft again')
            before_states=[{key:r[key] for key in ('row_id','status','stop_id')} for r in rows]
            created=[]
            for row in selected:
                item=row['data']
                inserted=con.execute('''INSERT INTO tour_stops(tour_id,band_id,stop_date,city,region,venue,status,arrival_time,departure_time,lodging,travel_notes)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(info['tour_id'],band_id,item['date'],item['city'],item['region'],item['venue'],item['status'],item['arrival_time'],item['departure_time'],item['lodging'],item['travel_notes']))
                row['stop_id']=inserted.lastrowid;row['status']='applied';created.append(inserted.lastrowid)
                record_change(con,band_id,'tour_stop',inserted.lastrowid,None,item,uid,reason=f"Reviewed import {import_id}, row {row['row_id']}, SHA256 {info['source_sha256']}")
            con.execute('UPDATE itinerary_imports SET rows_json=? WHERE id=?',(json.dumps(rows),import_id))
            record_change(con,band_id,'import',import_id,{'row_states':before_states},{'row_states':[{key:r[key] for key in ('row_id','status','stop_id')} for r in rows],'created_stop_ids':created,'source_sha256':info['source_sha256']},uid,reason='Explicitly applied selected reviewed rows')
            return {'created_stop_ids':created,'draft':output(con,get(con,band_id,import_id))}
    return router
