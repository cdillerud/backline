"""Synthetic sample content for a dedicated disposable Backline visual preview only."""
import json
def ensure_demo_tasks(con, band):
    """Add missing synthetic checklist examples without resetting existing decisions."""
    from datetime import date, timedelta
    first_gig=con.execute("SELECT id FROM events WHERE band_id=? AND kind='Gig' ORDER BY date LIMIT 1",(band,)).fetchone()
    if not first_gig:return
    existing={json.loads(row[0]).get("title") for row in con.execute(
        "SELECT body_json FROM workspace_tasks WHERE band_id=?",(band,))}
    for title,days,event_id,assignee in [
        ("Confirm showcase stage plot (demo)",5,first_gig[0],"Alex Example"),
        ("Finalize rehearsal set transitions (demo)",3,None,"Sam Example"),
    ]:
        if title in existing:continue
        member=con.execute("SELECT id FROM members WHERE band_id=? AND name=?",
            (band,assignee)).fetchone()
        payload={"title":title,"notes":"Synthetic preparation checklist",
            "assignee_id":member[0] if member else None,
            "due_date":(date.today()+timedelta(days=days)).isoformat(),
            "event_id":event_id,"song_id":None,"setlist_id":None,"completed":False}
        con.execute("INSERT INTO workspace_tasks(band_id,body_json) VALUES(?,?)",
            (band,json.dumps(payload)))

def seed(con):
    marker=con.execute("SELECT 1 FROM bands WHERE name='The Drunk Uncles (Demo)'").fetchone()
    if marker:return
    band=con.execute("INSERT INTO bands(name,genre,description) VALUES(?,?,?)",
        ("The Drunk Uncles (Demo)","Americana / rock","A sample workspace with entirely fictional show information.")).lastrowid
    for name,instrument in [('Alex Example','Guitar / vocal'),('Sam Example','Bass'),('Pat Example','Drums'),('Morgan Example','Keys')]:
        con.execute("INSERT INTO members(band_id,name,instrument) VALUES(?,?,?)",(band,name,instrument))
    for title,key,bpm,duration in [('Example Opener','Am',120,180),('Example Ballad','C',72,240),('Example Closer','G',140,210)]:
        con.execute("INSERT INTO songs(band_id,title,artist,song_key,bpm,duration_seconds) VALUES(?,?,?,?,?,?)",
                    (band,title,'Synthetic Demo',key,bpm,duration))
    from datetime import date,timedelta
    first=(date.today()+timedelta(days=21)).isoformat()
    second=(date.today()+timedelta(days=22)).isoformat()
    gig1=con.execute("""INSERT INTO events(band_id,kind,title,venue,date,time,status,fee_cents)
        VALUES(?,'Gig',?,?,?,'20:00','Confirmed',90000)""",
        (band,'Regional showcase (demo)','Sample Music Hall',first)).lastrowid
    gig2=con.execute("""INSERT INTO events(band_id,kind,title,venue,date,time,status,fee_cents)
        VALUES(?,'Gig',?,?,?,'21:00','Planned',60000)""",
        (band,'Weekend club date (demo)','Fictional Club',second)).lastrowid
    rehearsal=(date.today()+timedelta(days=7)).isoformat()
    con.execute("""INSERT INTO events(band_id,kind,title,venue,date,time,status,notes)
        VALUES(?,'Rehearsal',?,?,?,?,'Confirmed',?)""",
        (band,'Full-band rehearsal (demo)','Example Practice Room',rehearsal,'19:00',
         'Synthetic rehearsal: run the opening set and confirm transitions.'))
    setlist=con.execute("INSERT INTO setlists(band_id,title,event_id) VALUES(?,?,?)",
        (band,'Regional showcase — demo set',gig1)).lastrowid
    for position,song in enumerate(con.execute("SELECT id FROM songs WHERE band_id=? ORDER BY id",(band,)).fetchall(),1):
        con.execute("INSERT INTO setlist_songs(setlist_id,song_id,position) VALUES(?,?,?)",(setlist,song[0],position))
    ensure_demo_tasks(con,band)
    tour=con.execute("INSERT INTO tours(band_id,name,notes) VALUES(?,?,?)",
        (band,'Upper Midwest Weekend — DEMO','Illustrative only. Not real bookings.')).lastrowid
    for event,day,city,region,venue,status in (
        (gig1,first,'Minneapolis','MN','Sample Music Hall','confirmed'),
        (gig2,second,'Madison','WI','Fictional Club','planned')):
        con.execute("""INSERT INTO tour_stops(tour_id,band_id,event_id,stop_date,city,region,
            venue,status,travel_notes) VALUES(?,?,?,?,?,?,?,?,?)""",
            (tour,band,event,day,city,region,venue,status,'Verify travel time before booking.'))
    stage={"notes":"Fictional demo stage plot","items":[
        {"label":"Drums","kind":"drums","x":50,"y":18},
        {"label":"Bass","kind":"bass","x":24,"y":48},
        {"label":"Guitar","kind":"guitar","x":76,"y":48},
        {"label":"Lead vocal","kind":"vocal","x":50,"y":80},
        {"label":"Monitor L","kind":"monitor","x":26,"y":87},
        {"label":"Monitor R","kind":"monitor","x":74,"y":87}],
        "inputs":[{"channel":i,"source":src,"microphone":mic,"stand":"","notes":""}
           for i,src,mic in [(1,"Kick","D112"),(2,"Snare","SM57"),(3,"Bass","DI"),(4,"Guitar","SM57"),(5,"Vocal","SM58")]]}
    con.execute("INSERT INTO show_stage_plots(event_id,band_id,body_json) VALUES(?,?,?)",
        (gig1,band,json.dumps(stage)))
    from .show_ops import DEFAULTS
    for kind,details in DEFAULTS.items():
        con.execute("""INSERT INTO show_packets(band_id,event_id,kind,title,sections_json)
            VALUES(?,?,?,?,?)""",
            (band,gig1,kind,details["title"],json.dumps(details["sections"])))

def seed_accounts(con, password):
    """Create a synthetic band owner only in an empty, explicitly opted-in demo DB.

    Never grant access to an existing band, user, or session.
    Password must be provided through deployment secrets, not source control.
    """
    if len(password) < 12:
        raise ValueError("Synthetic demo password must contain at least 12 characters")
    bands=con.execute("SELECT id,name FROM bands").fetchall()
    users=con.execute("SELECT id,email FROM users").fetchall()
    if bands or users:
        # Idempotent restart is allowed only for our one dedicated demo account and band.
        if (len(bands)==1 and bands[0]["name"]=="The Drunk Uncles (Demo)" and
            len(users)==1 and users[0]["email"]=="demo-owner@example.test" and
            con.execute("SELECT role FROM band_users WHERE band_id=? AND user_id=?",
                (bands[0]["id"],users[0]["id"])).fetchone()["role"]=="owner"):
            ensure_demo_tasks(con,bands[0]["id"])
            return
        raise RuntimeError("Authenticated demo initialization refuses existing non-demo data")
    seed(con)
    band=con.execute("SELECT id FROM bands WHERE name='The Drunk Uncles (Demo)'").fetchone()
    if not band:
        raise RuntimeError("Synthetic demo band missing")
    from .accounts import hash_password
    uid=con.execute("INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)",
        ("demo-owner@example.test","Demo Band Manager",hash_password(password))).lastrowid
    con.execute("INSERT INTO band_users(band_id,user_id,role) VALUES(?,?,'owner')",(band[0],uid))
    # Private collaboration examples are accessible only to the synthetic owner.
    import time
    now=int(time.time())
    event=con.execute("SELECT id FROM events WHERE band_id=? ORDER BY date LIMIT 1",(band[0],)).fetchone()
    member=con.execute("SELECT id FROM members WHERE band_id=? ORDER BY id LIMIT 1",(band[0],)).fetchone()
    if member:
        con.execute("INSERT INTO roster_accounts(band_id,member_id,user_id) VALUES(?,?,?)",
            (band[0],member[0],uid))
    if event:
        con.execute("INSERT INTO event_rsvps(band_id,event_id,user_id,response,note,updated_at) VALUES(?,?,?,?,?,?)",
            (band[0],event[0],uid,'yes','Demo RSVP — synthetic data',now))
    thread=con.execute("INSERT INTO discussion_threads(band_id,title,scope,scope_id,created_by) VALUES(?,?,?,?,?)",
        (band[0],'Weekend show preparation (demo)','band',None,uid)).lastrowid
    con.execute("INSERT INTO discussion_posts(band_id,thread_id,user_id,body,mentions_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
        (band[0],thread,uid,'Demo: confirm stage plot and arrival time before the weekend.','[]',now,now))
