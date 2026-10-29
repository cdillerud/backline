"""Opt-in Ticketmaster Discovery adapter for gig market research.

Fixed HTTPS provider host, server-side key, bounded response and network timeout.
Provider events are evidence, never user instructions. No AI calls or publishing.
"""
import datetime
import json
import os
import urllib.parse
import urllib.request
from fastapi import HTTPException

HOST="https://app.ticketmaster.com/discovery/v2/events.json"

def normalized(payload):
    events=payload.get("_embedded",{}).get("events",[])
    result=[]
    for event in events[:30]:
        dates=event.get("dates",{}).get("start",{})
        day=dates.get("localDate","")
        link=event.get("url","")
        name=event.get("name","")
        venue=next(iter(event.get("_embedded",{}).get("venues",[])),{}).get("name","")
        if not (name and day and link.startswith("https://")):
            continue
        try: datetime.date.fromisoformat(day)
        except ValueError: continue
        classification=next(iter(event.get("classifications",[])),{})
        category=classification.get("segment",{}).get("name","Event")
        result.append({"title":name[:200],"source_url":link,
                       "event_date":day,"venue":venue[:160],
                       "category":category[:60],"relevance":""})
    return result

def discover(city,day,fetch=None):
    if os.getenv("BACKLINE_MARKET_DISCOVERY_ENABLED")!="1":
        raise HTTPException(503,"Market discovery not enabled")
    key=os.getenv("TICKETMASTER_API_KEY","")
    if not key:
        raise HTTPException(503,"Ticketmaster key not configured")
    if not city or len(city)>100:
        raise HTTPException(422,"A city is required")
    date=datetime.date.fromisoformat(day)
    query=urllib.parse.urlencode({"apikey":key,"city":city,"countryCode":"US",
        "startDateTime":str(date)+"T00:00:00Z",
        "endDateTime":str(date+datetime.timedelta(days=1))+"T00:00:00Z",
        "size":30,"sort":"date,asc"})
    request=urllib.request.Request(HOST+"?"+query,headers={"Accept":"application/json"})
    if fetch is None:
        def fetch(req):
            with urllib.request.urlopen(req,timeout=8) as response:
                return response.read(500001)
    try:
        body=fetch(request)
        if len(body)>500000:
            raise ValueError("Provider response too large")
        return normalized(json.loads(body))
    except (ValueError,KeyError,TypeError,TimeoutError,OSError) as err:
        # Do not expose provider query URLs containing API keys.
        raise HTTPException(502,"Event provider unavailable or returned invalid data") from None
