import os, tempfile
from pathlib import Path
from fastapi.testclient import TestClient

def test_core_workflows():
    with tempfile.TemporaryDirectory() as d:
        os.environ['BACKLINE_DB']=str(Path(d)/'test.db')
        import importlib
        import src.app as module
        importlib.reload(module)
        client=TestClient(module.app)
        assert client.get('/api/health').json()['status']=='ok'
        band=client.post('/api/bands',json={'name':'The Testing Band'}).json()['id']
        b=f'/api/bands/{band}'
        ids=[]
        for name in ['One','Two','Three']:
            r=client.post(b+'/members',json={'name':name});assert r.status_code==201;ids.append(r.json()['id'])
        gig=client.post(b+'/events',json={'kind':'Gig','title':'Saturday set','date':'2026-11-07','fee':'900'}).json()['id']
        song=client.post(b+'/songs',json={'title':'A song'}).json()['id']
        assert client.post(b+'/setlists',json={'title':'Set 1','event_id':gig,'song_ids':[song]}).status_code==201
        for kind,amount in [('income','100.01'),('expense','10.00')]:
            response=client.post(b+'/transactions',json={'kind':kind,'amount':amount,'date':'2026-11-07','event_id':gig,'description':kind});assert response.status_code==201
        settlement=client.post(b+f'/events/{gig}/settle',json={'member_ids':ids,'reserve_percent':10})
        assert settlement.status_code==201,settlement.text
        val=settlement.json();assert val['net_cents']==9001;assert val['reserve_cents']==900;assert val['distributable_cents']==8101
        ss=client.get(b+'/settlements').json()[0]['shares'];assert sum(x['amount_cents'] for x in ss)==8101
        assert max(x['amount_cents'] for x in ss)-min(x['amount_cents'] for x in ss)<=1
        assert client.post(b+f'/events/{gig}/settle',json={'member_ids':ids}).status_code==409
        assert client.post(b+'/transactions',json={'kind':'payout','amount':'27','description':'test','date':'2026-11-07'}).status_code==422
        assert client.post(b+'/transactions',json={'kind':'income','amount':'-2','description':'test','date':'2026-11-07'}).status_code==422
        t=client.get(b+'/transactions').json()[0]
        assert client.post(b+f'/transactions/{t["id"]}/reverse').status_code==201
        assert client.post(b+f'/transactions/{t["id"]}/reverse').status_code==409
        other=client.post('/api/bands',json={'name':'Other'}).json()['id']
        assert client.get(f'/api/bands/{other}/members').json()==[]
        assert client.post(f'/api/bands/{other}/setlists',json={'title':'Fake','song_ids':[song]}).status_code==422
        assert client.post(f'/api/bands/{other}/transactions',json={'kind':'expense','description':'wrong gig','date':'2026-11-07','amount':'10','event_id':gig}).status_code==422
