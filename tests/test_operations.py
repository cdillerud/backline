"""Synthetic RoadOps-inspired workflow acceptance and privacy regressions."""
import datetime
from io import BytesIO
from pypdf import PdfReader
from test_collaboration import accounts


def test_advance_history_revision_and_urgent_acknowledgement(accounts):
    app,c,band,_,base,users,h,gig,_,_=accounts
    with app.db() as con:con.execute('UPDATE events SET date=? WHERE id=?',(datetime.datetime.now(datetime.timezone.utc).date().isoformat(),gig))
    path=base+f'/gigs/{gig}/advance'
    body={'timezone':'UTC','load_in':'15:00','show_time':'20:00'}
    assert c.put(path,headers=h['owner'],json=body).status_code==200
    before=c.get(path,headers=h['owner']).json()
    assert before['revision']==1
    assert c.put(path,headers=h['owner'],json={**before,'show_time':'21:00','change_reason':'Venue requested a later set'}).status_code==200
    assert c.put(path,headers=h['owner'],json={**before,'show_time':'22:00'}).status_code==409
    after=c.get(path,headers=h['owner']).json()
    assert after['show_time']=='21:00' and after['revision']==2
    assert c.put(path,headers=h['owner'],json=after).status_code==200
    history=c.get(base+'/operations/history',headers=h['member']).json()
    assert len(history)==2 and history[0]['actor_name']=='Owner'
    assert history[0]['before']['show_time']=='20:00'
    assert history[0]['after']['show_time']=='21:00'
    assert history[0]['reason']=='Venue requested a later set'
    alerts=c.get(base+'/operations/alerts',headers=h['member']).json()
    assert len(alerts)==1 and alerts[0]['acknowledged_at'] is None
    alert_id=alerts[0]['id']
    assert c.post(f'/api/me/operations-alerts/{alert_id}/acknowledge',headers=h['outsider']).status_code==404
    assert c.post(f'/api/me/operations-alerts/{alert_id}/acknowledge',headers=h['member']).status_code==200
    stamp=c.get(base+'/operations/alerts',headers=h['member']).json()[0]['acknowledged_at']
    c.post(f'/api/me/operations-alerts/{alert_id}/acknowledge',headers=h['member'])
    assert c.get(base+'/operations/alerts',headers=h['member']).json()[0]['acknowledged_at']==stamp
    manager=c.get(base+'/operations/alerts',headers=h['owner']).json()[0]
    assert manager['acknowledged_count']==1 and manager['required_count']==5
    assert 'recipients' not in c.get(base+'/operations/alerts',headers=h['member']).json()[0]
    assert any(n['category']=='operations' for n in c.get('/api/me/notifications',headers=h['member']).json())


def test_guest_requests_approval_limits_cutoff_and_private_pdf(accounts):
    _,c,_,_,base,users,h,gig,_,_=accounts
    path=base+f'/gigs/{gig}'
    policy={'guest_limit':2,'pass_types':['Guest','VIP']}
    assert c.put(path+'/guest-policy',headers=h['owner'],json=policy).status_code==200
    assert c.post(path+'/guest-requests',headers=h['member'],json={'name':'Spoof','requested_by':users['owner']}).status_code==422
    made=c.post(path+'/guest-requests',headers=h['member'],json={'name':'Fictional Guest','quantity':2,'pass_type':'VIP','note':'PRIVATE REQUEST NOTE'})
    assert made.status_code==201,made.text
    ident=made.json()['id']
    assert c.post(path+'/guest-requests',headers=h['member'],json={'name':'fictional guest','pass_type':'VIP'}).status_code==409
    assert c.get(path+'/guests',headers=h['member']).status_code==403
    assert c.get(path+'/guests.pdf',headers=h['viewer']).status_code==403
    assert c.post(path+'/guest-requests',headers=h['viewer'],json={'name':'Denied'}).status_code==403
    assert c.post(path+f'/guest-requests/{ident}/cancel',headers=h['manager']).status_code==404
    assert c.put(path+f'/guests/{ident}/decision',headers=h['member'],json={'status':'approved','revision':1}).status_code==403
    assert c.put(path+f'/guests/{ident}/decision',headers=h['owner'],json={'status':'approved','revision':1,'reason':'Promoter approved'}).status_code==200
    assert c.put(path+f'/guests/{ident}/decision',headers=h['owner'],json={'status':'declined','revision':1}).status_code==409
    second=c.post(path+'/guest-requests',headers=h['owner'],json={'name':'Not Approved'}).json()['id']
    assert c.put(path+f'/guests/{second}/decision',headers=h['owner'],json={'status':'approved','revision':1}).status_code==409
    assert c.get(path+'/guests',headers=h['owner']).json()['approved_count']==2
    pdf=c.get(path+'/guests.pdf',headers=h['owner'])
    text=' '.join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)
    assert 'Fictional Guest' in text and 'VIP' in text and 'Approved headcount: 2' in text
    assert 'PRIVATE REQUEST NOTE' not in text and 'Not Approved' not in text
    assert c.get(base+'/operations/history?resource=guest',headers=h['member']).status_code==403
    assert all(r['resource']!='guest' for r in c.get(base+'/operations/history',headers=h['member']).json())
    rules=c.get(path+'/guest-policy',headers=h['owner']).json()
    assert c.put(path+'/guest-policy',headers=h['owner'],json={**rules,'cutoff_at':'2020-01-01T00:00:00+00:00'}).status_code==200
    assert c.post(path+'/guest-requests',headers=h['member'],json={'name':'Too late'}).status_code==409
    assert c.post(path+f'/guest-requests/{ident}/cancel',headers=h['member']).status_code==200
    pdf=c.get(path+'/guests.pdf',headers=h['owner'])
    assert 'Fictional Guest' not in ' '.join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)


def test_lodging_rooming_occupancy_privacy_and_pdf(accounts):
    _,c,_,other,base,users,h,gig,_,_=accounts
    start=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(days=2)
    body={'hotel':'Synthetic Touring Hotel','address':'123 Example Street','check_in':start.isoformat(),'check_out':(start+datetime.timedelta(days=1)).isoformat(),
          'event_id':gig,'confirmation_reference':'PRIVATE CONFIRMATION','internal_notes':'PRIVATE MANAGER NOTE','traveler_notes':'Use the main entrance'}
    made=c.post(base+'/lodging',headers=h['owner'],json=body)
    assert made.status_code==201,made.text
    stay=made.json()['id']
    room={'label':'101','room_type':'twin','capacity':2,'user_ids':[users['owner'],users['member']]}
    created=c.post(base+f'/lodging/{stay}/rooms',headers=h['owner'],json=room)
    assert created.status_code==201,created.text
    room_id=created.json()['id']
    assert c.post(base+f'/lodging/{stay}/rooms',headers=h['owner'],json={**room,'label':'102'}).status_code==409
    assert c.post(base+f'/lodging/{stay}/rooms',headers=h['owner'],json={**room,'user_ids':[users['outsider']]}).status_code==422
    assert c.post(base+f'/lodging/{stay}/rooms',headers=h['owner'],json={**room,'capacity':1}).status_code==422
    assert c.post(base+f'/lodging/{stay}/rooms',headers=h['owner'],json={'label':'PRIVATE OTHER ROOM','user_ids':[users['viewer']]}).status_code==201
    response=c.get(base+'/lodging',headers=h['member'])
    assert response.status_code==200
    assert 'PRIVATE' not in response.text and 'Owner' not in response.text
    assert response.json()['items'][0]['rooms'][0]['label']=='101'
    assert c.get(base+'/lodging',headers=h['treasurer']).json()['items']==[]
    assert c.get(base+f'/lodging/{stay}/rooming.pdf',headers=h['member']).status_code==403
    second=c.post(base+'/lodging',headers=h['owner'],json={**body,'hotel':'Overlapping Hotel'}).json()['id']
    assert c.post(base+f'/lodging/{second}/rooms',headers=h['owner'],json={'label':'A','user_ids':[users['member']]}).status_code==409
    assert c.put(base+f'/lodging/{stay}',headers=h['owner'],json={**body,'revision':0}).status_code==409
    assert c.put(base+f'/lodging/{stay}/rooms/{room_id}',headers=h['member'],json={**room,'revision':1}).status_code==403
    pdf=c.get(base+f'/lodging/{stay}/rooming.pdf',headers=h['owner'])
    text=' '.join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)
    assert 'Synthetic Touring Hotel' in text and 'Owner' in text and 'Member' in text
    assert 'PRIVATE CONFIRMATION' not in text and 'PRIVATE MANAGER NOTE' not in text
    assert c.get(f'/api/bands/{other}/lodging',headers=h['owner']).status_code==403


def test_reviewed_csv_import_is_draft_only_atomic_and_deduplicated(accounts):
    _,c,_,other,base,_,h,_,_,_=accounts
    tour=c.post(base+'/tours',headers=h['owner'],json={'name':'Synthetic CSV Tour'}).json()['id']
    source='date,city,venue,arrival_time\n2026-12-01,Minneapolis,Fictional Hall,16:00\nnot-a-date,Madison,Fictional Club,16:00\n2026-12-02,Chicago,Synthetic Room,17:00\n'
    path=base+'/itinerary-imports'
    made=c.post(path,headers=h['owner'],json={'tour_id':tour,'filename':'tour.csv','csv_text':source})
    assert made.status_code==201,made.text
    draft=made.json();ident=draft['id']
    assert len(draft['source_sha256'])==64 and draft['rows'][1]['error']
    assert c.get(base+f'/tours/{tour}/route',headers=h['owner']).json()['stops']==[]
    assert c.post(path,headers=h['owner'],json={'tour_id':tour,'filename':'again.csv','csv_text':source}).json()['id']==ident
    assert c.post(path+f'/{ident}/apply',headers=h['owner'],json={'revision':1,'row_ids':[1,2],'confirm':True}).status_code==409
    assert c.get(base+f'/tours/{tour}/route',headers=h['owner']).json()['stops']==[]
    assert c.post(path+f'/{ident}/apply',headers=h['owner'],json={'revision':1,'row_ids':[1,3],'confirm':False}).status_code==422
    applied=c.post(path+f'/{ident}/apply',headers=h['owner'],json={'revision':1,'row_ids':[1,3],'confirm':True})
    assert applied.status_code==200,applied.text
    assert len(applied.json()['created_stop_ids'])==2
    assert c.post(path+f'/{ident}/apply',headers=h['owner'],json={'revision':1,'row_ids':[1],'confirm':True}).status_code==409
    assert len(c.get(base+f'/tours/{tour}/route',headers=h['owner']).json()['stops'])==2
    assert c.get(path,headers=h['member']).status_code==403
    assert c.post(path,headers=h['member'],json={'tour_id':tour,'filename':'bad.csv','csv_text':source}).status_code==403
    assert c.post(f'/api/bands/{other}/itinerary-imports',headers=h['outsider'],json={'tour_id':tour,'filename':'bad.csv','csv_text':source}).status_code==404
    # Different source text cannot bypass duplicate stop detection after preview.
    duplicate=c.post(path,headers=h['owner'],json={'tour_id':tour,'filename':'duplicate.csv','csv_text':source+'\n'}).json()
    assert duplicate['rows'][0]['duplicate_existing']
    assert c.post(path+f'/{duplicate["id"]}/apply',headers=h['owner'],json={'revision':1,'row_ids':[1],'confirm':True}).status_code==409

def test_lodging_date_changes_reject_overlap_without_partial_edits(accounts):
    _,c,_,_,base,users,h,_,_,_=accounts
    start=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(days=2)
    body={'hotel':'Hotel One','check_in':start.isoformat(),'check_out':(start+datetime.timedelta(days=1)).isoformat()}
    first=c.post(base+'/lodging',headers=h['owner'],json=body).json()['id']
    second=c.post(base+'/lodging',headers=h['owner'],json={**body,'hotel':'Hotel Two','check_in':(start+datetime.timedelta(days=2)).isoformat(),'check_out':(start+datetime.timedelta(days=3)).isoformat()}).json()['id']
    for stay in [first,second]:
        assert c.post(base+f'/lodging/{stay}/rooms',headers=h['owner'],json={'label':'101','user_ids':[users['member']]}).status_code==201
    assert c.put(base+f'/lodging/{first}',headers=h['owner'],json={**body,'revision':1,'check_out':(start+datetime.timedelta(days=3)).isoformat()}).status_code==409
    result=c.get(base+'/lodging',headers=h['owner']).json()['items']
    assert datetime.datetime.fromisoformat(result[0]['check_out'])==datetime.datetime.fromisoformat(body['check_out']) and result[0]['revision']==1
    assert c.put(base+f'/lodging/{first}',headers=h['owner'],json={**body,'revision':1,'cancelled':True}).status_code==200
    pdf=c.get(base+f'/lodging/{first}/rooming.pdf',headers=h['owner'])
    assert 'CANCELLED - do not use' in ' '.join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)


def test_guest_resubmission_returns_to_pending_and_preserves_audit(accounts):
    _,c,_,_,base,_,h,gig,_,_=accounts
    path=base+f'/gigs/{gig}'
    ident=c.post(path+'/guest-requests',headers=h['member'],json={'name':'Returning Guest'}).json()['id']
    c.put(path+f'/guests/{ident}/decision',headers=h['owner'],json={'status':'approved','revision':1})
    c.post(path+f'/guest-requests/{ident}/cancel',headers=h['member'])
    again=c.post(path+'/guest-requests',headers=h['member'],json={'name':'Returning Guest','quantity':2})
    assert again.status_code==201 and again.json()['id']==ident and again.json()['resubmitted']
    row=c.get(path+'/guests',headers=h['owner']).json()['items'][0]
    assert row['status']=='pending' and row['quantity']==2 and row['revision']==4
    assert c.get(path+'/guests',headers=h['owner']).json()['approved_count']==0


def test_import_source_and_validation_are_manager_scoped(accounts):
    _,c,_,_,base,_,h,_,_,_=accounts
    tour=c.post(base+'/tours',headers=h['owner'],json={'name':'Source Evidence'}).json()['id']
    path=base+'/itinerary-imports'
    payload={'tour_id':tour,'filename':'evidence.csv','csv_text':'date,city,venue,travel_notes\n2026-12-01,Test City,Test Hall,PRIVATE SOURCE NOTE\n'}
    made=c.post(path,headers=h['owner'],json=payload).json()
    source=c.get(path+f'/{made["id"]}/source',headers=h['owner']).json()
    assert source['source_text']==payload['csv_text'] and source['source_sha256']==made['source_sha256']
    assert c.get(path+f'/{made["id"]}/source',headers=h['member']).status_code==403
    report=c.get(path+f'/{made["id"]}/review.csv',headers=h['owner'])
    assert report.status_code==200 and 'text/csv' in report.headers['content-type']
    assert 'no-store' in report.headers['cache-control']
    assert 'Source line' in report.text and 'PRIVATE SOURCE NOTE' not in report.text
    assert c.get(path+f'/{made["id"]}/review.csv',headers=h['member']).status_code==403
    assert c.get(f'/api/bands/999999/itinerary-imports/{made["id"]}/review.csv',headers=h['outsider']).status_code in (403,404)

    for csv_text in ['date,city,unknown\n2026-12-01,Test,x\n','date,date,city\n2026-12-01,2026-12-01,Test\n','date,city\n']:
        assert c.post(path,headers=h['owner'],json={**payload,'csv_text':csv_text}).status_code==422
    assert c.post(path,headers=h['owner'],json={**payload,'csv_text':'date,city\n'+'2026-12-01,City\n'*201}).status_code==422

def test_import_mapping_preview_requires_new_review_and_preserves_original(accounts):
    _,c,_,_,base,_,h,_,_,_=accounts
    tour=c.post(base+'/tours',headers=h['owner'],json={'name':'Mapped Tour'}).json()['id']
    path=base+'/itinerary-imports'
    raw='Day,Town,Stage,Private note\\n2026-12-01,Minneapolis,Sample Hall,DO NOT DISTRIBUTE\\n'
    # Raw nonstandard headings are not accepted as a directly applicable import.
    assert c.post(path,headers=h['owner'],json={'tour_id':tour,'filename':'nonstandard.csv','csv_text':raw}).status_code==422
    seed='date,city,venue\\n2026-12-01,Minneapolis,Sample Hall\\n'
    draft=c.post(path,headers=h['owner'],json={'tour_id':tour,'filename':'original.csv','csv_text':seed}).json()
    ident=draft['id']
    endpoint=path+f'/{ident}/map-preview'
    mapping={'date':'date','city':'city','venue':'venue'}
    preview=c.post(endpoint,headers=h['owner'],json={'mapping':mapping})
    assert preview.status_code==200,preview.text
    assert preview.json()['requires_new_review'] is True
    assert preview.json()['source_sha256']==draft['source_sha256']
    assert preview.json()['canonical_csv'].startswith('city,date,venue')
    assert c.get(path+f'/{ident}/source',headers=h['owner']).json()['source_text']==seed
    assert c.get(base+f'/tours/{tour}/route',headers=h['owner']).json()['stops']==[]
    assert c.post(endpoint,headers=h['owner'],json={'mapping':{'date':'date','city':'date'}}).status_code==422
    assert c.post(endpoint,headers=h['member'],json={'mapping':mapping}).status_code==403

def test_urgent_alerts_cover_an_explicit_after_midnight_show_window(accounts):
    app,_,band,_,_,users,_,gig,_,_=accounts
    from src.operations_audit import record_change,urgent_advance_change
    before={'timezone':'UTC','show_time':'23:00','curfew':'02:00','day_offsets':{'curfew':1},'parking':'Old dock'}
    after={**before,'parking':'New dock'}
    now=int(datetime.datetime(2026,12,2,0,30,tzinfo=datetime.timezone.utc).timestamp())
    with app.db() as con:
        con.execute("UPDATE events SET date='2026-12-01' WHERE id=?",(gig,))
        history=record_change(con,band,'advance',gig,before,after,users['owner'],gig,'Loading changed after midnight')
        urgent_advance_change(con,band,gig,history,before,after,now)
        assert con.execute('SELECT count(*) FROM operations_alerts').fetchone()[0]==1

def test_operational_pdf_handles_long_multi_page_rooming_lists():
    from src.show_pdf import create_operations_pdf
    rows=[[str(100+i//2),'twin','Synthetic Traveler '+str(i+1),1] for i in range(40)]
    reader=PdfReader(BytesIO(create_operations_pdf('Private rooming list','Synthetic Hotel',['Room','Type','Traveler','Count'],rows)))
    assert len(reader.pages)>=2
    for index,page in enumerate(reader.pages,1):
        text=page.extract_text()
        assert 'Traveler' in text and 'Room' in text and 'Page '+str(index) in text
    text=' '.join(page.extract_text() for page in reader.pages)
    assert 'Synthetic Traveler 1' in text and 'Synthetic Traveler 40' in text
