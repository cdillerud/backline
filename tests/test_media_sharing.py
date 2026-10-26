"""Anonymous-read allowlists, uploads and capability revocation using fake accounts."""
import base64
from io import BytesIO
import json
import logging
import wave
import pytest
from PIL import Image
from test_collaboration import accounts

def photo_payload():
    out=BytesIO();image=Image.new('RGB',(80,60),'green');exif=Image.Exif();exif[270]='PRIVATE GPS AND DESCRIPTION';image.save(out,format='JPEG',exif=exif)
    return {'kind':'photo','filename':'synthetic.jpg','data_base64':base64.b64encode(out.getvalue()).decode()}

def test_private_photo_metadata_quota_and_album_visibility(accounts,monkeypatch):
    app,c,b,other,base,_,h,_,member,_=accounts
    payload=photo_payload()
    assert c.post(base+'/media',headers=h['member'],json=payload).status_code==403
    made=c.post(base+'/media',headers=h['owner'],json=payload)
    assert made.status_code==201,made.text
    ident=made.json()['id']
    assert len(ident)==32
    image=c.get(base+'/media/'+ident,headers=h['member'])
    assert image.headers['x-content-type-options']=='nosniff'
    assert not Image.open(BytesIO(image.content)).getexif()
    assert c.get(base+'/media/'+ident).status_code==401
    assert c.get(f'/api/bands/{other}/media/'+ident,headers=h['outsider']).status_code==404
    assert c.put(base+f'/members/{member}/photo',headers=h['owner'],json={'media_id':ident}).status_code==200
    assert c.get(base+'/member-photos',headers=h['member']).json()[0]['media_id']==ident
    bad={**payload,'data_base64':base64.b64encode(b'<svg onload="alert(1)"></svg>').decode()}
    assert c.post(base+'/media',headers=h['owner'],json=bad).status_code==422
    from src import media_pages
    monkeypatch.setattr(media_pages,'MEDIA_QUOTA',1)
    assert c.post(base+'/media',headers=h['owner'],json=payload).status_code==413
    album=c.post(base+'/albums',headers=h['owner'],json={'name':'Private rehearsal'}).json()['id']
    assert c.get(base+'/albums',headers=h['member']).json()[0]['public']==0
    assert c.post(base+f'/albums/{album}/photos',headers=h['owner'],json={'media_id':ident}).status_code==200

def test_recording_validation_and_song_attachment(accounts):
    _,c,_,other,base,_,h,_,_,_=accounts
    song=c.post(base+'/songs',headers=h['owner'],json={'title':'Reference song'}).json()['id']
    output=BytesIO()
    with wave.open(output,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(8000);wav.writeframes(b'\0\0'*800)
    payload={'kind':'recording','filename':'reference.wav','data_base64':base64.b64encode(output.getvalue()).decode()}
    made=c.post(base+'/media',headers=h['owner'],json=payload)
    assert made.status_code==201,made.text
    ident=made.json()['id']
    assert c.put(base+f'/songs/{song}/recording',headers=h['owner'],json={'media_id':ident}).status_code==200
    assert c.get(base+'/recordings',headers=h['member']).json()[0]['media_id']==ident
    assert c.post(base+'/media',headers=h['owner'],json={**payload,'data_base64':base64.b64encode(output.getvalue()[:-25]).decode()}).status_code==422
    assert c.get(f'/api/bands/{other}/media/{ident}',headers=h['outsider']).status_code==404

def test_public_page_is_allowlisted_explicit_and_revocable(accounts,monkeypatch):
    app,c,b,other,base,users,h,gig,_,_=accounts
    monkeypatch.setenv('BACKLINE_PUBLIC_SHARING_ENABLED','1')
    ident=c.post(base+'/media',headers=h['owner'],json=photo_payload()).json()['id']
    album=c.post(base+'/albums',headers=h['owner'],json={'name':'Approved gallery'}).json()['id']
    c.post(base+f'/albums/{album}/photos',headers=h['owner'],json={'media_id':ident})
    config={'slug':'synthetic-band','bio':'Public bio <script>alert(1)</script>','banner_media_id':None,'album_ids':[album],'event_ids':[gig]}
    assert c.put(base+'/public-profile',headers=h['owner'],json=config).status_code==422
    assert c.put(base+f'/albums/{album}',headers=h['owner'],json={'name':'Approved gallery','public':True}).status_code==200
    assert c.put(base+'/public-profile',headers=h['owner'],json=config).status_code==200
    assert c.get('/public/bands/synthetic-band/data').status_code==404
    assert c.post(base+'/public-profile/publish',headers=h['member'],json={'confirm':True}).status_code==403
    assert c.post(base+'/public-profile/publish',headers=h['owner'],json={'confirm':False}).status_code==422
    with app.db() as con:con.execute("UPDATE events SET notes='PRIVATE ACCESS CODE 1234' WHERE id=?",(gig,))
    c.put(base+f'/gigs/{gig}/advance',headers=h['owner'],json={'parking':'SECRET LOADING DOOR','venue_contact':'PRIVATE PHONE'})
    assert c.post(base+'/public-profile/publish',headers=h['owner'],json={'confirm':True}).status_code==200
    data=c.get('/public/bands/synthetic-band/data')
    assert data.status_code==200,data.text
    assert set(data.json())=={'name','slug','bio','banner_media_id','gigs','albums'}
    assert all(secret not in data.text for secret in ['PRIVATE ACCESS','SECRET LOADING','PRIVATE PHONE','assignee_id','user_id','contact_email'])
    rendered=c.get('/public/bands/synthetic-band')
    assert '<script>' not in rendered.text and '&lt;script&gt;' in rendered.text
    assert 'frame-ancestors' in rendered.headers['content-security-policy']
    assert c.get('/public/bands/synthetic-band/media/'+ident).status_code==200
    c.put(base+f'/albums/{album}',headers=h['owner'],json={'name':'Private now','public':False})
    assert c.get('/public/bands/synthetic-band/media/'+ident).status_code==404
    c.post(base+'/public-profile/revoke',headers=h['owner'])
    assert c.get('/public/bands/synthetic-band').status_code==404
    monkeypatch.setenv('BACKLINE_PUBLIC_SHARING_ENABLED','0')
    assert c.post(base+'/public-profile/publish',headers=h['owner'],json={'confirm':True}).status_code==409
    assert c.get('/api/bands').status_code==401

def test_explicit_venue_share_and_live_revocation(accounts):
    app,c,b,other,base,users,h,gig,_,_=accounts
    with app.db() as con:con.execute("INSERT INTO band_users VALUES(?,?,'manager')",(other,users['owner']))
    venue=c.post(base+'/venues',headers=h['owner'],json={'name':'Shared Hall','address':'Public venue address',
        'contacts':[{'name':'Private engineer','phone':'SECRET'}],'load_in_notes':'PRIVATE SIDE DOOR'}).json()['id']
    body={'destination_band_id':other,'fields':['name','address']}
    preview=c.post(base+f'/venues/{venue}/share-preview',headers=h['owner'],json=body)
    assert preview.status_code==200 and set(preview.json()['venue'])=={'name','address'}
    assert c.post(base+f'/venues/{venue}/shares',headers=h['owner'],json=body).status_code==422
    share=c.post(base+f'/venues/{venue}/shares',headers=h['owner'],json={**body,'confirm':True}).json()['id']
    destination=f'/api/bands/{other}'
    shared=c.get(destination+'/shared-venues',headers=h['outsider']).json()[0]
    assert 'contacts' not in shared and 'load_in_notes' not in shared
    othergig=c.post(destination+'/events',headers=h['outsider'],json={'kind':'Gig','title':'Destination gig','date':'2026-11-16'}).json()['id']
    assert c.put(destination+f'/events/{othergig}/shared-venue',headers=h['outsider'],json={'share_id':share}).status_code==200
    assert c.get(destination+f'/events/{othergig}/venue',headers=h['outsider']).json()['name']=='Shared Hall'
    assert c.get(base+'/venues',headers=h['outsider']).status_code==403
    assert c.post(base+f'/venues/{venue}/shares/{share}/revoke',headers=h['owner']).status_code==200
    assert c.get(destination+'/shared-venues',headers=h['outsider']).json()==[]
    assert c.get(destination+f'/events/{othergig}/venue',headers=h['outsider']).json() is None
    assert c.get(destination+f'/gigs/{othergig}/packet.pdf',headers=h['outsider']).status_code==200

def test_calendar_capabilities_minimize_data_and_revoke(accounts,monkeypatch):
    app,c,b,other,base,users,h,gig,_,_=accounts
    monkeypatch.setenv('BACKLINE_PUBLIC_SHARING_ENABLED','1')
    calendar=c.post(base+'/calendars',headers=h['owner'],json={'name':'Selected public dates'}).json()['id']
    c.put(base+f'/events/{gig}/calendar',headers=h['owner'],json={'calendar_id':calendar})
    with app.db() as con:con.execute("UPDATE events SET notes='PRIVATE GIG NOTES' WHERE id=?",(gig,))
    c.put(base+f'/gigs/{gig}/advance',headers=h['owner'],json={'load_in':'17:00','contact_phone':'PRIVATE PHONE','timezone':'America/Chicago','show_time':'20:00'})
    path=base+f'/calendars/{calendar}/subscriptions'
    assert c.post(path,headers=h['member'],json={'confirm':True}).status_code==403
    assert c.post(path,headers=h['owner'],json={'confirm':False}).status_code==422
    made=c.post(path,headers=h['owner'],json={'confirm':True}).json()
    url=made['url'];token=url.split('/')[-1][:-4]
    with app.db() as con:
        row=con.execute('SELECT token_hash FROM calendar_subscriptions WHERE id=?',(made['id'],)).fetchone()
        assert row['token_hash']!=token and token not in row['token_hash']
    feed=c.get(url)
    assert feed.status_code==200 and 'Synthetic Show' in feed.text
    assert 'PRIVATE' not in feed.text and 'Load-in' not in feed.text
    from src.sharing import RedactCalendarTokens
    record=logging.LogRecord('uvicorn.access',20,'',1,'%s %s',('GET',url),None)
    RedactCalendarTokens().filter(record)
    assert token not in str(record.args)
    assert c.post(path+f'/{made["id"]}/revoke',headers=h['owner']).status_code==200
    assert c.get(url).status_code==404

def test_published_albums_require_explicit_confirmation_for_new_images(accounts,monkeypatch):
    _,c,_,_,base,_,h,_,_,_=accounts
    monkeypatch.setenv('BACKLINE_PUBLIC_SHARING_ENABLED','1')
    ident=c.post(base+'/media',headers=h['owner'],json=photo_payload()).json()['id']
    album=c.post(base+'/albums',headers=h['owner'],json={'name':'Public photos','public':True}).json()['id']
    c.put(base+'/public-profile',headers=h['owner'],json={'slug':'public-synthetic','album_ids':[album]})
    c.post(base+'/public-profile/publish',headers=h['owner'],json={'confirm':True})
    path=base+f'/albums/{album}/photos'
    assert c.post(path,headers=h['owner'],json={'media_id':ident}).status_code==409
    assert c.get('/public/bands/public-synthetic/media/'+ident).status_code==404
    assert c.post(path,headers=h['owner'],json={'media_id':ident,'confirm_public':True}).status_code==200
    assert c.get('/public/bands/public-synthetic/media/'+ident).status_code==200

def test_image_pixel_limit_and_invalid_encoding(accounts):
    _,c,_,_,base,_,h,_,_,_=accounts
    out=BytesIO();Image.new('L',(4000,3100)).save(out,format='PNG')
    assert c.post(base+'/media',headers=h['owner'],json={'kind':'photo','filename':'large.png','data_base64':base64.b64encode(out.getvalue()).decode()}).status_code==422
    assert c.post(base+'/media',headers=h['owner'],json={'kind':'photo','filename':'bad.png','data_base64':'@@@@'}).status_code==422
