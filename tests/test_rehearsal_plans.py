"""Rehearsal objectives, private notes and manager authorization."""
from test_collaboration import accounts

def test_rehearsal_plans_are_band_scoped_and_manager_editable(accounts):
    app,c,band,other,base,users,h,gig,_,_=accounts
    event=c.post(base+'/events',json={'kind':'Rehearsal','title':'Synthetic practice',
        'date':'2026-12-08','time':'18:00','venue':'Test studio'}).json()['id']
    url=base+f'/rehearsals/{event}/plan'
    empty=c.get(url,headers=h['owner'])
    assert empty.status_code==200,empty.text
    assert empty.json()['revision']==0
    data={'objectives':'Tighten last chorus','notes':'Work from measure 19'}
    created=c.put(url,headers=h['owner'],json=data)
    assert created.status_code==200,created.text
    assert created.json()['revision']==1
    member=c.get(url,headers=h['member'])
    assert member.status_code==200 and member.json()['objectives']==data['objectives']
    assert c.put(url,headers=h['member'],json={'objectives':'Not allowed','notes':''}).status_code==403
    assert c.get(base+f'/rehearsals/{gig}/plan',headers=h['owner']).status_code==404
    assert c.get(f'/api/bands/{other}/rehearsals/{event}/plan',headers=h['owner']).status_code in (403,404)
    changed=c.put(url,headers=h['owner'],json={'objectives':'Run entire set','notes':''})
    assert changed.status_code==200 and changed.json()['revision']==2
    assert c.get(url,headers=h['owner']).json()['objectives']=='Run entire set'
