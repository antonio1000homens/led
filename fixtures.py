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


# This is deliberately a credential-free visual fixture. A future calendar
# adapter must normalize its provider data to this shape before it reaches a
# display layout.
CALENDAR_EVENTS = [
    {"start": "18:30", "title": "Scout meeting and programme planning", "location": "Scout HQ"},
    {"start": "Tomorrow 09:00", "title": "Team stand-up", "location": "Online"},
    {"start": "Sat 10:00", "title": "District activity day", "location": "Kingston"},
]


def animated_services(seconds, interval):
    return PAGES[int(seconds // interval) % len(PAGES)]
