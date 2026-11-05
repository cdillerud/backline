"""One schedule projection for venue advancement, show-day UI and PDF exports."""
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re

MILESTONES = (("load_in", "Load-in"), ("soundcheck", "Soundcheck"),
              ("doors", "Doors"), ("show_time", "Show time"), ("curfew", "Curfew"))
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def valid_timezone(value):
    try:
        ZoneInfo(value)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


def show_timeline(advance):
    """Tolerate legacy drafts while surfacing missing/invalid operational details."""
    entries, warnings = [], []
    if not valid_timezone(advance.get("timezone", "")):
        warnings.append("Venue time zone needs confirmation.")
    previous = -1
    for key, label in MILESTONES:
        value = advance.get(key, "")
        if not value:
            if key != "curfew":
                warnings.append(f"{label} time is missing.")
            continue
        if not TIME_PATTERN.fullmatch(value):
            warnings.append(f"{label} must use 24-hour HH:MM time.")
            continue
        day = advance.get("day_offsets", {}).get(key, 0)
        minute = day * 1440 + int(value[:2]) * 60 + int(value[3:])
        if minute < previous:
            warnings.append(f"{label} is before the preceding show milestone; check day offsets.")
        previous = minute
        entries.append({"title": label, "time": value, "day_offset": day,
                        "owner": advance.get("production_contact", ""), "location": "",
                        "notes": advance.get("parking", "") if key == "load_in" else "",
                        "source": "venue", "sort_minute": minute})
    for item in advance.get("schedule", []):
        entries.append({**item, "source": "custom",
                        "sort_minute": item["day_offset"] * 1440 + int(item["time"][:2]) * 60 + int(item["time"][3:])})
    if advance.get("status") != "confirmed":
        warnings.append("Venue advancement is not confirmed; this schedule is provisional.")
    return {"timezone": advance.get("timezone", ""), "status": advance.get("status", "draft"),
            "entries": sorted(entries, key=lambda entry: entry["sort_minute"]), "warnings": warnings}
