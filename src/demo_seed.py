"""Synthetic sample content for a dedicated disposable Backline visual preview only."""
import json
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
    if con.execute("SELECT 1 FROM bands LIMIT 1").fetchone() or con.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        raise RuntimeError("Authenticated demo initialization requires an entirely empty database")
    seed(con)
    band=con.execute("SELECT id FROM bands WHERE name='The Drunk Uncles (Demo)'").fetchone()
    if not band:
        raise RuntimeError("Synthetic demo band missing")
    from .accounts import hash_password
    uid=con.execute("INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)",
        ("demo-owner@example.test","Demo Band Manager",hash_password(password))).lastrowid
    con.execute("INSERT INTO band_users(band_id,user_id,role) VALUES(?,?,'owner')",(band[0],uid))
