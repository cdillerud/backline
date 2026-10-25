"""Evidence-aware, deterministic campaign strategy and draft generation.

Suggestions are interpretations, not verified claims about audiences or turnout.
No remote model calls, no paid API use, and no automatic publishing.
"""
import datetime

def strategy(gig, findings):
    day=datetime.date.fromisoformat(gig["date"])
    same_day=[x for x in findings if x["event_date"]==day.isoformat()]
    references=[{"title":x["title"],"url":x["source_url"]} for x in same_day[:5]]
    angles=[{"title":"Lead with the band and venue",
             "rationale":"Specific show information is more reliable than assumed audience behavior.",
             "evidence":[],"confidence":"high"}]
    if same_day:
        angles.append({"title":"Stand out in a busy local calendar",
            "rationale":"Nearby events are listed for the same date, but audience overlap is unverified.",
            "evidence":references,"confidence":"medium"})
    else:
        angles.append({"title":"Make this gig the plan",
            "rationale":"No same-day events have been recorded; this does not mean there are none.",
            "evidence":[],"confidence":"low"})
    return {"angles":angles,"findings_considered":len(findings),
            "caveat":"Marketing hypotheses only. Event listings do not prove attendance or audience overlap."}

def drafts(gig,band,findings):
    band_name=band["name"].strip()
    venue=gig["venue"].strip()
    date=datetime.date.fromisoformat(gig["date"]).strftime("%A, %B %d")
    location=f" at {venue}" if venue else ""
    title=f"{band_name} live{location} — {date}"
    basic=f"{band_name} plays live{location} on {date}. Come see us."
    evidence=strategy(gig,findings)
    result=[
        {"channel":"Facebook","angle":"Show announcement","body":basic},
        {"channel":"Instagram","angle":"Short show reminder","body":f"{title}. See you there."},
        {"channel":"Email","angle":"Gig invitation","body":f"Subject: {title}\n\n{basic}"}]
    return {"drafts":result,"strategy":evidence,
            "verification_required":["Show time","Door time","Admission or ticket information","Venue address"],
            "generated_by":"deterministic_template","published":False}
