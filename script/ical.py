#!/usr/bin/env python3
"""
Sync recurring events from an Outlook ICS feed to iCloud, using Timeline but manually filtering
to avoid "AttributeError: 'generator' object has no attribute 'end_before'".

Usage:
  python ical.py        -> Sync
  python ical.py delete -> Delete all events
"""

import sys
import uuid
import datetime
import configparser

import requests
import arrow
import pytz
from ics import Calendar
from ics.timeline import Timeline  # We can still import Timeline for expansion
from caldav import DAVClient
from icalendar import Calendar as ICAL_Calendar, Event as ICAL_Event

# 1) CONFIG
config = configparser.ConfigParser(interpolation=None)
config.read("config.ini")

ICS_URL = config["calendar"]["ICS_URL"]
CALDAV_URL = config["calendar"]["CALDAV_URL"]
USERNAME = config["calendar"]["USERNAME"]
PASSWORD = config["calendar"]["PASSWORD"]
TARGET_CALENDAR_NAME = config["calendar"]["TARGET_CALENDAR_NAME"]

# 2) TIMEZONE fix set to East Cost
EASTERN = pytz.timezone("America/New_York")


def force_to_eastern(dt: datetime.datetime) -> datetime.datetime:
    """
    Discard any tzinfo, then treat as Eastern time.
    """
    dt_naive = dt.replace(tzinfo=None)
    return EASTERN.localize(dt_naive)


# 3) CREATE ICAL EVENT
def create_ical_event(summary, start_eastern, end_eastern, uid=None):
    cal = ICAL_Calendar()
    cal.add("prodid", "-//My Recurring Sync//example.com//")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")

    event = ICAL_Event()
    event.add("summary", summary)

    if uid:
        event.add("uid", uid)
    else:
        event.add("uid", str(uuid.uuid4()))

    now_utc = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    event.add("dtstamp", now_utc)

    # DTSTART in Eastern
    event.add("dtstart", start_eastern)
    event["DTSTART"].params["TZID"] = "America/New_York"

    # DTEND in Eastern
    event.add("dtend", end_eastern)
    event["DTEND"].params["TZID"] = "America/New_York"

    event.add("transp", "TRANSPARENT")
    cal.add_component(event)

    return cal.to_ical().decode("utf-8")


# 4) SYNC FUNCTION (MANUAL FILTERING)


def sync_calendar():
    """
    1) Fetch ICS
    2) Parse with `ics`
    3) Create a Timeline, expand all events
    4) Manually filter by date range
    5) Force times to Eastern
    6) Avoid duplicates
    7) Upload to iCloud
    """

    # 1) Fetch ICS
    print(f"Fetching ICS from: {ICS_URL}")
    resp = requests.get(ICS_URL)
    resp.raise_for_status()
    ics_data = resp.text

    # 2) Parse ICS
    outlook_cal = Calendar(ics_data)

    # 3) Create a Timeline, but don't chain calls
    timeline = Timeline(outlook_cal)

    # Convert the timeline generator to a list of occurrences
    all_occurrences = list(timeline)  # This expands recurrences

    # 4) Define our date range manually
    now = arrow.utcnow()
    start_bound = now.shift(years=-1)
    end_bound = now.shift(years=+2)

    # 5) Connect to iCloud
    print(f"Connecting to iCloud: {CALDAV_URL}")
    client = DAVClient(url=CALDAV_URL, username=USERNAME, password=PASSWORD)
    principal = client.principal()
    calendars = principal.calendars()

    target_calendar = None
    for c in calendars:
        if TARGET_CALENDAR_NAME in c.name:
            target_calendar = c
            break

    if not target_calendar:
        print(f"Error: Calendar '{TARGET_CALENDAR_NAME}' not found.")
        return

    # Build a set of existing occurrences
    existing_occurrences = set()
    for ev in target_calendar.events():
        vevent = ev.vobject_instance.vevent
        summ = vevent.summary.value
        dtstart = getattr(vevent, "dtstart", None)
        dtend = getattr(vevent, "dtend", None)
        if dtstart and dtend:
            s_start = (
                dtstart.value.isoformat()
                if hasattr(dtstart.value, "isoformat")
                else str(dtstart.value)
            )
            s_end = (
                dtend.value.isoformat()
                if hasattr(dtend.value, "isoformat")
                else str(dtend.value)
            )
            existing_occurrences.add((summ, s_start, s_end))

    # 6) Iterate over all occurrences, manually filter
    for occ in all_occurrences:
        # occ.begin/end are Arrow objects
        if occ.begin < start_bound or occ.begin > end_bound:
            # skip out-of-range events
            continue

        summary = occ.name or "No Title"

        # Force times to Eastern
        start_eastern = force_to_eastern(occ.begin.datetime)
        end_eastern = force_to_eastern(occ.end.datetime)

        # Check duplicates
        sstart = start_eastern.isoformat()
        send = end_eastern.isoformat()

        if (summary, sstart, send) in existing_occurrences:
            print(f"Skipping duplicate: {summary} @ {start_eastern}")
            continue

        # Build iCalendar data
        uid = occ.uid
        ical_data = create_ical_event(summary, start_eastern, end_eastern, uid=uid)

        print(
            f"\n=== Adding occurrence ===\nSummary: {summary}\nStart: {start_eastern}\nEnd: {end_eastern}\n"
        )

        # 7) Add to iCloud
        try:
            target_calendar.add_event(ical_data)
            existing_occurrences.add((summary, sstart, send))
            print(f"Added occurrence: {summary}")
        except Exception as e:
            print(f"Error adding '{summary}': {e}")

    print("\nRecurring sync complete (manual filtering)!")


###############################################################################
# 5) DELETE FUNCTION
###############################################################################
def delete_all_events():
    print(f"Connecting to iCloud: {CALDAV_URL}")
    client = DAVClient(url=CALDAV_URL, username=USERNAME, password=PASSWORD)
    principal = client.principal()
    calendars = principal.calendars()

    target_calendar = None
    for c in calendars:
        if TARGET_CALENDAR_NAME in c.name:
            target_calendar = c
            break

    if not target_calendar:
        print(f"Error: Calendar '{TARGET_CALENDAR_NAME}' not found.")
        return

    evs = target_calendar.events()
    print(f"Found {len(evs)} events in '{TARGET_CALENDAR_NAME}'. Deleting all...")

    for ev in evs:
        vevent = ev.vobject_instance.vevent
        summary = vevent.summary.value
        print(f"Deleting: {summary}")
        ev.delete()

    print("All events deleted.")


# 6) MAIN


def main():
    if len(sys.argv) > 1 and sys.argv[1].lower() == "delete":
        print("WARNING: This will delete ALL events in your iCloud calendar!")
        confirm = input("Type 'YES' to confirm: ")
        if confirm == "YES":
            delete_all_events()
        else:
            print("Delete canceled.")
    else:
        sync_calendar()


if __name__ == "__main__":
    main()
