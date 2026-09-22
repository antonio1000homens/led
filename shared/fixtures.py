"""Deterministic data for Wokwi and host-side tests."""


def service(time, destination, platform, status="On time", cancelled=False, delay_reason="", stops=()):
    return {
        "time": time,
        "destination": destination,
        "platform": platform,
        "status": status,
        "cancelled": cancelled,
        "delay_reason": delay_reason,
        "stops": list(stops),
    }


def stop(station, time, status="On time"):
    return {"station": station, "crs": "", "time": time, "status": status, "cancelled": status == "Cancelled"}


SERVICES = [
    service("12:04", "Waterloo", "1", stops=(stop("Clapham Junction", "12:12"), stop("Wimbledon", "12:19"), stop("Surbiton", "12:31"))),
    service("12:16", "Shepperton", "2", "12:18", stops=(stop("Wimbledon", "12:25"), stop("Kingston", "12:37"), stop("Shepperton", "12:52"))),
    service("12:27", "Waterloo", "1", "Cancelled", True, "Signal failure", stops=(stop("Clapham Junction", "12:35"), stop("Wimbledon", "12:42"))),
]

PAGES = [
    SERVICES,
    [
        service("12:34", "Woking", "3", stops=(stop("Wimbledon", "12:41"), stop("Surbiton", "12:54"), stop("Woking", "13:11"))),
        service("12:42", "Waterloo", "1", "12:45", stops=(stop("Raynes Park", "12:49"), stop("Wimbledon", "12:56"))),
        service("12:55", "Hampton Court", "2", "Delayed", False, "Late running", stops=(stop("Wimbledon", "13:02"), stop("Kingston", "13:14"), stop("Hampton Court", "13:24"))),
    ],
    [
        service("13:06", "Guildford", "4", stops=(stop("Wimbledon", "13:13"), stop("Surbiton", "13:26"), stop("Guildford", "13:49"))),
        service("13:18", "Waterloo", "1", "Cancelled", True, "Points failure", stops=(stop("Clapham Junction", "13:26"), stop("Wimbledon", "13:33"))),
        service("13:27", "Shepperton", "2", "13:29", stops=(stop("Wimbledon", "13:36"), stop("Kingston", "13:48"), stop("Shepperton", "14:03"))),
    ],
]


# Credential-free visual fixture matching the normalized Todoist event shape.
# Six rows deliberately exercise both three-row agenda pages.
CALENDAR_EVENTS = [
    {"start": "2026-09-13T18:30:00+01:00", "all_day": False, "date_text": "13/09", "time_text": "18:30", "title": "Scout meeting and programme planning"},
    {"start": "2026-09-14", "all_day": True, "date_text": "14/09", "time_text": "ALL", "title": "School inset day"},
    {"start": "2026-09-14T09:00:00+01:00", "all_day": False, "date_text": "14/09", "time_text": "09:00", "title": "Team stand-up"},
    {"start": "2026-09-15T11:30:00+01:00", "all_day": False, "date_text": "15/09", "time_text": "11:30", "title": "Dentist appointment"},
    {"start": "2026-09-16T17:15:00+01:00", "all_day": False, "date_text": "16/09", "time_text": "17:15", "title": "Pick up shopping"},
    {"start": "2026-09-19T10:00:00+01:00", "all_day": False, "date_text": "19/09", "time_text": "10:00", "title": "District activity day"},
]


def animated_services(seconds, interval):
    return PAGES[int(seconds // interval) % len(PAGES)]
