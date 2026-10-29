"""Bounded private media and explicitly published, allowlisted band pages."""
import base64
import binascii
import datetime
import hashlib
import html
from io import BytesIO
import json
import os
import re
import secrets
import warnings
import wave
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import Field
from PIL import Image, ImageOps, UnidentifiedImageError
from .collaboration import Strict, actor

router=APIRouter()
MAX_PHOTO=5*1024*1024
MAX_AUDIO=25*1024*1024
MEDIA_QUOTA=100*1024*1024
class Upload(Strict):
    kind:str=Field(pattern='^(photo|recording)$')
    filename:str=Field(min_length=1,max_length=150)
    data_base64:str=Field(min_length=4,max_length=35000000)
class Album(Strict):
    name:str=Field(min_length=1,max_length=140,pattern=r'.*\S.*')
    public:bool=False
class PhotoLink(Strict):
    media_id:str=Field(pattern='^[a-f0-9]{32}$')
class AlbumPhotoLink(PhotoLink):
    confirm_public:bool=False
class Profile(Strict):
    slug:str=Field(min_length=3,max_length=60,pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    bio:str=Field(default='',max_length=2000)
    banner_media_id:str|None=None
    album_ids:list[int]=Field(default_factory=list,max_length=30)
    event_ids:list[int]=Field(default_factory=list,max_length=100)
class ConfirmPublish(Strict):
    confirm:bool

def setup(con):
    con.executescript('''
      CREATE TABLE IF NOT EXISTS band_media(
        id TEXT PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),kind TEXT NOT NULL,filename TEXT NOT NULL,
        content_type TEXT NOT NULL,content BLOB NOT NULL,width INTEGER,height INTEGER,sha256 TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS photo_albums(
        id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),name TEXT NOT NULL,public INTEGER NOT NULL DEFAULT 0);
      CREATE TABLE IF NOT EXISTS album_photos(
        album_id INTEGER NOT NULL REFERENCES photo_albums(id),media_id TEXT NOT NULL REFERENCES band_media(id),PRIMARY KEY(album_id,media_id));
      CREATE TABLE IF NOT EXISTS song_recordings(
        song_id INTEGER PRIMARY KEY REFERENCES songs(id),band_id INTEGER NOT NULL REFERENCES bands(id),media_id TEXT NOT NULL REFERENCES band_media(id));
      CREATE TABLE IF NOT EXISTS member_photos(
        member_id INTEGER PRIMARY KEY REFERENCES members(id),band_id INTEGER NOT NULL REFERENCES bands(id),media_id TEXT NOT NULL REFERENCES band_media(id));
      CREATE TABLE IF NOT EXISTS band_public_profiles(
        band_id INTEGER PRIMARY KEY REFERENCES bands(id),slug TEXT NOT NULL UNIQUE,draft_json TEXT NOT NULL,published_json TEXT);
      CREATE TABLE IF NOT EXISTS publishing_audit(
        id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),actor_id INTEGER NOT NULL REFERENCES users(id),
        action TEXT NOT NULL,details_json TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    ''')

def clean_upload(data):
    try:raw=base64.b64decode(data.data_base64,validate=True)
    except (ValueError,binascii.Error):raise HTTPException(422,'Invalid file encoding') from None
    if data.kind=='photo':
        if not 16<=len(raw)<=MAX_PHOTO:raise HTTPException(422,'Photo must be at most 5 MB')
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error',Image.DecompressionBombWarning)
                with Image.open(BytesIO(raw)) as source:
                    if source.format not in ('JPEG','PNG'):raise ValueError('JPEG or PNG required')
                    if source.width*source.height>12_000_000:raise ValueError('Photo exceeds 12 megapixels')
                    source.load();image=ImageOps.exif_transpose(source).convert('RGB')
                    image.thumbnail((2400,2400))
                    # Fresh pixel buffer prevents metadata, scripts and EXIF surviving.
                    clean=Image.new('RGB',image.size);clean.paste(image)
                    output=BytesIO();clean.save(output,format='JPEG',quality=88)
                    return output.getvalue(),'image/jpeg',clean.width,clean.height
        except (ValueError,OSError,UnidentifiedImageError,Image.DecompressionBombWarning,Image.DecompressionBombError):
            raise HTTPException(422,'Invalid image; use JPEG/PNG within the pixel limit') from None
    if not 44<=len(raw)<=MAX_AUDIO:raise HTTPException(422,'Recording must be a PCM WAV file at most 25 MB')
    try:
        with wave.open(BytesIO(raw),'rb') as source:
            channels,width,rate,frames=source.getnchannels(),source.getsampwidth(),source.getframerate(),source.getnframes()
            if channels not in (1,2) or width not in (1,2,3,4) or not 8000<=rate<=96000 or frames/rate>1200:raise ValueError('Unsupported WAV')
            if frames*channels*width>MAX_AUDIO:raise ValueError('Oversized decoded WAV')
            audio=source.readframes(frames)
            if len(audio)!=frames*channels*width:raise ValueError('Truncated WAV')
        output=BytesIO()
        with wave.open(output,'wb') as dest:
            dest.setnchannels(channels);dest.setsampwidth(width);dest.setframerate(rate);dest.writeframes(audio)
        return output.getvalue(),'audio/wav',None,None
    except (ValueError,OSError,EOFError,wave.Error):raise HTTPException(422,'Invalid PCM WAV recording') from None

def media(con,band_id,media_id,kind=None):
    row=con.execute('SELECT * FROM band_media WHERE band_id=? AND id=?',(band_id,media_id)).fetchone()
    if not row or kind and row['kind']!=kind:raise HTTPException(404,'Media not found')
    return row

def public_snapshot(con,band_id,config,strict=True):
    band=con.execute('SELECT name FROM bands WHERE id=?',(band_id,)).fetchone()
    result={'name':band['name'],'slug':config['slug'],'bio':config.get('bio',''),'banner_media_id':None,'gigs':[],'albums':[]}
    if config.get('banner_media_id'):
        try:media(con,band_id,config['banner_media_id'],'photo');result['banner_media_id']=config['banner_media_id']
        except HTTPException:
            if strict:raise
    for event_id in dict.fromkeys(config.get('event_ids',[])):
        row=con.execute("SELECT title,date,venue,status FROM events WHERE band_id=? AND id=? AND kind='Gig'",(band_id,event_id)).fetchone()
        if not row:
            if strict:raise HTTPException(422,'Selected gig must belong to this band')
            continue
        if row['date']>=datetime.date.today().isoformat() and row['status'].lower() not in ('canceled','cancelled'):
            result['gigs'].append({'title':row['title'],'date':row['date'],'venue':row['venue']})
    result['gigs'].sort(key=lambda gig:(gig['date'],gig['title']))
    for album_id in dict.fromkeys(config.get('album_ids',[])):
        row=con.execute('SELECT id,name,public FROM photo_albums WHERE band_id=? AND id=?',(band_id,album_id)).fetchone()
        if not row or not row['public']:
            if strict:raise HTTPException(422,'Selected albums must belong to this band and be explicitly marked public')
            continue
        photos=[r['media_id'] for r in con.execute('''SELECT a.media_id FROM album_photos a JOIN band_media m ON m.id=a.media_id
            WHERE a.album_id=? AND m.band_id=? AND m.kind='photo' ORDER BY a.media_id''',(album_id,band_id))]
        result['albums'].append({'name':row['name'],'photos':photos})
    return result

def public_allowed(config,media_id):
    return media_id==config.get('banner_media_id') or any(media_id in album['photos'] for album in config['albums'])

def file_response(row):
    return Response(bytes(row['content']),media_type=row['content_type'],headers={
        'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; sandbox",
        'Content-Disposition':'inline; filename="photo.jpg"' if row['kind']=='photo' else 'attachment; filename="reference.wav"'})

def attach(db):
    def album(con,band_id,album_id):
        row=con.execute('SELECT * FROM photo_albums WHERE band_id=? AND id=?',(band_id,album_id)).fetchone()
        if not row:raise HTTPException(404,'Album not found')
        return row
    def audit(con,band_id,user_id,action,details):
        con.execute('INSERT INTO publishing_audit(band_id,actor_id,action,details_json) VALUES(?,?,?,?)',(band_id,user_id,action,json.dumps(details)))
    @router.get('/api/bands/{band_id}/media')
    def media_list(band_id:int):
        with db() as con:return [dict(r) for r in con.execute('SELECT id,kind,filename,width,height,length(content) AS size_bytes FROM band_media WHERE band_id=? ORDER BY rowid DESC LIMIT 200',(band_id,))]
    @router.post('/api/bands/{band_id}/media',status_code=201)
    def upload(band_id:int,data:Upload,request:Request):
        user_id=actor(request);content,content_type,width,height=clean_upload(data);media_id=secrets.token_hex(16)
        with db() as con:
            # Acquire the write transaction before quota check so concurrent uploads serialize.
            con.execute('BEGIN IMMEDIATE')
            if not con.execute('SELECT 1 FROM bands WHERE id=?',(band_id,)).fetchone():raise HTTPException(404,'Band not found')
            used=con.execute('SELECT coalesce(sum(length(content)),0) FROM band_media WHERE band_id=?',(band_id,)).fetchone()[0]
            if used+len(content)>MEDIA_QUOTA:raise HTTPException(413,'Band media quota is 100 MB')
            con.execute('INSERT INTO band_media(id,band_id,kind,filename,content_type,content,width,height,sha256) VALUES(?,?,?,?,?,?,?,?,?)',
                        (media_id,band_id,data.kind,data.filename,content_type,content,width,height,hashlib.sha256(content).hexdigest()))
            audit(con,band_id,user_id,'upload',{'media_id':media_id,'kind':data.kind})
        return {'id':media_id,'size_bytes':len(content)}
    @router.get('/api/bands/{band_id}/media/{media_id}')
    def read_media(band_id:int,media_id:str):
        with db() as con:return file_response(media(con,band_id,media_id))
    @router.get('/api/bands/{band_id}/albums')
    def albums(band_id:int):
        with db() as con:
            result=[]
            for row in con.execute('SELECT * FROM photo_albums WHERE band_id=? ORDER BY id DESC',(band_id,)):
                photos=[r['media_id'] for r in con.execute('SELECT media_id FROM album_photos WHERE album_id=? ORDER BY media_id',(row['id'],))]
                result.append(dict(row)|{'photos':photos})
            return result
    @router.post('/api/bands/{band_id}/albums',status_code=201)
    def make_album(band_id:int,data:Album,request:Request):
        user_id=actor(request)
        with db() as con:
            row=con.execute('INSERT INTO photo_albums(band_id,name,public) VALUES(?,?,?)',(band_id,data.name,data.public))
            audit(con,band_id,user_id,'create_album',{'album_id':row.lastrowid,'public':data.public})
            return {'id':row.lastrowid}
    @router.put('/api/bands/{band_id}/albums/{album_id}')
    def edit_album(band_id:int,album_id:int,data:Album,request:Request):
        user_id=actor(request)
        with db() as con:
            album(con,band_id,album_id)
            con.execute('UPDATE photo_albums SET name=?,public=? WHERE band_id=? AND id=?',(data.name,data.public,band_id,album_id))
            audit(con,band_id,user_id,'album_visibility',{'album_id':album_id,'public':data.public})
        return {'saved':True}
    @router.post('/api/bands/{band_id}/albums/{album_id}/photos')
    def add_photo(band_id:int,album_id:int,data:AlbumPhotoLink,request:Request):
        actor(request)
        with db() as con:
            info=album(con,band_id,album_id);media(con,band_id,data.media_id,'photo')
            profile=con.execute('SELECT published_json FROM band_public_profiles WHERE band_id=?',(band_id,)).fetchone()
            public=bool(info['public'] and profile and profile['published_json'] and album_id in json.loads(profile['published_json']).get('album_ids',[]))
            if public and not data.confirm_public:raise HTTPException(409,'This album is published; explicitly confirm making the new photo public')
            con.execute('INSERT OR IGNORE INTO album_photos(album_id,media_id) VALUES(?,?)',(album_id,data.media_id))
        return {'linked':True}
    @router.put('/api/bands/{band_id}/songs/{song_id}/recording')
    def attach_recording(band_id:int,song_id:int,data:PhotoLink,request:Request):
        actor(request)
        with db() as con:
            if not con.execute('SELECT 1 FROM songs WHERE id=? AND band_id=?',(song_id,band_id)).fetchone():raise HTTPException(404,'Song not found')
            media(con,band_id,data.media_id,'recording')
            con.execute('''INSERT INTO song_recordings(song_id,band_id,media_id) VALUES(?,?,?)
                ON CONFLICT(song_id) DO UPDATE SET media_id=excluded.media_id''',(song_id,band_id,data.media_id))
        return {'linked':True}
    @router.get('/api/bands/{band_id}/recordings')
    def recordings(band_id:int):
        with db() as con:return [dict(r) for r in con.execute('SELECT song_id,media_id FROM song_recordings WHERE band_id=?',(band_id,))]
    @router.put('/api/bands/{band_id}/members/{member_id}/photo')
    def attach_member_photo(band_id:int,member_id:int,data:PhotoLink,request:Request):
        actor(request)
        with db() as con:
            if not con.execute('SELECT 1 FROM members WHERE id=? AND band_id=?',(member_id,band_id)).fetchone():raise HTTPException(404,'Member not found')
            media(con,band_id,data.media_id,'photo')
            con.execute('''INSERT INTO member_photos(member_id,band_id,media_id) VALUES(?,?,?)
                ON CONFLICT(member_id) DO UPDATE SET media_id=excluded.media_id''',(member_id,band_id,data.media_id))
        return {'linked':True}
    @router.get('/api/bands/{band_id}/member-photos')
    def member_photos(band_id:int):
        with db() as con:return [dict(r) for r in con.execute('SELECT member_id,media_id FROM member_photos WHERE band_id=?',(band_id,))]
    @router.get('/api/bands/{band_id}/public-profile')
    def read_profile(band_id:int):
        with db() as con:
            row=con.execute('SELECT * FROM band_public_profiles WHERE band_id=?',(band_id,)).fetchone()
            return {'draft':json.loads(row['draft_json']) if row else None,'published':bool(row and row['published_json']),
                    'publishing_enabled':os.getenv('BACKLINE_PUBLIC_SHARING_ENABLED')=='1'}
    @router.put('/api/bands/{band_id}/public-profile')
    def save_profile(band_id:int,data:Profile,request:Request):
        user_id=actor(request)
        with db() as con:
            previous=con.execute('SELECT slug FROM band_public_profiles WHERE band_id=?',(band_id,)).fetchone()
            if previous and previous['slug']!=data.slug:raise HTTPException(409,'Public slug is fixed; revoke and contact an administrator to change it')
            public_snapshot(con,band_id,data.model_dump())
            other=con.execute('SELECT band_id FROM band_public_profiles WHERE slug=?',(data.slug,)).fetchone()
            if other and other['band_id']!=band_id:raise HTTPException(409,'Public address is already in use')
            con.execute('''INSERT INTO band_public_profiles(band_id,slug,draft_json) VALUES(?,?,?)
                ON CONFLICT(band_id) DO UPDATE SET draft_json=excluded.draft_json''',(band_id,data.slug,data.model_dump_json()))
            audit(con,band_id,user_id,'save_draft',{'slug':data.slug})
        return {'saved':True}
    @router.get('/api/bands/{band_id}/public-profile/preview')
    def preview(band_id:int):
        with db() as con:
            row=con.execute('SELECT draft_json FROM band_public_profiles WHERE band_id=?',(band_id,)).fetchone()
            if not row:raise HTTPException(404,'Save a profile draft first')
            return public_snapshot(con,band_id,json.loads(row['draft_json']))
    @router.post('/api/bands/{band_id}/public-profile/publish')
    def publish(band_id:int,data:ConfirmPublish,request:Request):
        user_id=actor(request)
        if os.getenv('BACKLINE_PUBLIC_SHARING_ENABLED')!='1':raise HTTPException(409,'Public publishing is disabled for this environment')
        if not data.confirm:raise HTTPException(422,'Explicit publication confirmation required')
        with db() as con:
            row=con.execute('SELECT draft_json FROM band_public_profiles WHERE band_id=?',(band_id,)).fetchone()
            if not row:raise HTTPException(404,'Save and preview a profile draft first')
            config=json.loads(row['draft_json']);public_snapshot(con,band_id,config)
            con.execute('UPDATE band_public_profiles SET published_json=draft_json WHERE band_id=?',(band_id,))
            audit(con,band_id,user_id,'publish',config)
        return {'published':True,'url':'/public/bands/'+config['slug']}
    @router.post('/api/bands/{band_id}/public-profile/revoke')
    def revoke(band_id:int,request:Request):
        user_id=actor(request)
        with db() as con:
            con.execute('UPDATE band_public_profiles SET published_json=NULL WHERE band_id=?',(band_id,))
            audit(con,band_id,user_id,'revoke',{})
        return {'revoked':True}
    def live(con,slug):
        if os.getenv('BACKLINE_PUBLIC_SHARING_ENABLED')!='1':raise HTTPException(404,'Public page not found')
        row=con.execute('SELECT band_id,published_json FROM band_public_profiles WHERE slug=? AND published_json IS NOT NULL',(slug,)).fetchone()
        if not row:raise HTTPException(404,'Public page not found')
        return row['band_id'],public_snapshot(con,row['band_id'],json.loads(row['published_json']),False)
    @router.get('/public/bands/{slug}/data')
    def public_data(slug:str):
        with db() as con:return Response(json.dumps(live(con,slug)[1]),media_type='application/json',headers={'Cache-Control':'no-store'})
    @router.get('/public/bands/{slug}/media/{media_id}')
    def public_photo(slug:str,media_id:str):
        with db() as con:
            band_id,snapshot=live(con,slug)
            if not public_allowed(snapshot,media_id):raise HTTPException(404,'Public image not found')
            return file_response(media(con,band_id,media_id,'photo'))
    @router.get('/public/bands/{slug}')
    def public_page(slug:str):
        with db() as con:_,snapshot=live(con,slug)
        e=html.escape
        image=lambda ident:'<img loading="lazy" alt="Band photo" src="/public/bands/'+e(slug)+'/media/'+e(ident)+'">'
        body='<h1>'+e(snapshot['name'])+'</h1>'+(image(snapshot['banner_media_id']) if snapshot['banner_media_id'] else '')+'<p class="bio">'+e(snapshot['bio'])+'</p><h2>Upcoming shows</h2>'
        body+=''.join('<article><strong>'+e(g['title'])+'</strong><p>'+e(g['date'])+' · '+e(g['venue'])+'</p></article>' for g in snapshot['gigs']) or '<p>No public shows announced.</p>'
        for item in snapshot['albums']:body+='<h2>'+e(item['name'])+'</h2><div class="photos">'+''.join(image(ident) for ident in item['photos'])+'</div>'
        content='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(snapshot['name'])+'</title><style>body{font:18px/1.6 system-ui;max-width:960px;margin:auto;padding:30px;background:#101720;color:#edf3f7}h1{font-size:42px}img{max-width:100%;border-radius:14px}.photos{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}article{padding:15px;border:1px solid #49617a;border-radius:12px;margin:14px 0}.bio{white-space:pre-wrap}</style><body>'+body+'</body></html>'
        return Response(content,media_type='text/html',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
            'Content-Security-Policy':"default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"})
    return router
