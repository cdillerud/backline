"""Persistent preflight AI request reservation using atomic SQLite writes.

Quota counts attempts including provider failures. UTC-day global and per-band caps.
It is an operational call limit, not a guaranteed monetary spending cap.
"""
import datetime
import os
import sqlite3
from fastapi import HTTPException

def setup(con):
    con.execute("""CREATE TABLE IF NOT EXISTS ai_daily_requests (
        day TEXT NOT NULL,
        scope TEXT NOT NULL,
        used INTEGER NOT NULL CHECK(used>=0),
        PRIMARY KEY(day,scope)
    )""")

def _limit(name, default, maximum):
    try:
        limit=int(os.getenv(name,str(default)))
    except (ValueError,TypeError):
        raise HTTPException(503,"AI request quota configuration invalid")
    if not 1<=limit<=maximum:
        raise HTTPException(503,"AI request quota configuration invalid")
    return limit

def reserve(con,band_id,day=None):
    """Reserve one billable attempt before network I/O; caller commits immediately.

    SQLite's write transaction serializes concurrent reservations. Any rollback
    must fail closed: the provider must not be called unless commit succeeded.
    """
    if os.getenv("BACKLINE_AI_COPY_ENABLED")!="1":
        return {"reserved":False}
    day=day or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    limits=(("all",_limit("BACKLINE_AI_DAILY_GLOBAL_LIMIT",20,100)),
            (f"band:{int(band_id)}",_limit("BACKLINE_AI_DAILY_BAND_LIMIT",5,50)))
    for scope,limit in limits:
        result=con.execute("""INSERT INTO ai_daily_requests(day,scope,used)
             VALUES(?,?,1)
             ON CONFLICT(day,scope) DO UPDATE SET used=used+1
             WHERE used<?""",(day,scope,limit))
        if result.rowcount!=1:
            raise HTTPException(429,"AI generation daily request limit reached")
    return {"reserved":True,"day":day}
