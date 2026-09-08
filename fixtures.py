"""Deterministic data for Wokwi and host-side tests."""


SERVICES = [
    {"time": "12:04", "destination": "Waterloo", "platform": "1", "status": "On time", "cancelled": False, "delay_reason": ""},
    {"time": "12:16", "destination": "Shepperton", "platform": "2", "status": "12:18", "cancelled": False, "delay_reason": ""},
    {"time": "12:27", "destination": "Waterloo", "platform": "1", "status": "Cancelled", "cancelled": True, "delay_reason": "Signal failure"},
]

PAGES = [
    SERVICES,
    [
        {"time": "12:34", "destination": "Woking", "platform": "3", "status": "On time", "cancelled": False, "delay_reason": ""},
        {"time": "12:42", "destination": "Waterloo", "platform": "1", "status": "12:45", "cancelled": False, "delay_reason": ""},
        {"time": "12:55", "destination": "Hampton Court", "platform": "2", "status": "Delayed", "cancelled": False, "delay_reason": "Late running"},
    ],
    [
        {"time": "13:06", "destination": "Guildford", "platform": "4", "status": "On time", "cancelled": False, "delay_reason": ""},
        {"time": "13:18", "destination": "Waterloo", "platform": "1", "status": "Cancelled", "cancelled": True, "delay_reason": "Points failure"},
        {"time": "13:27", "destination": "Shepperton", "platform": "2", "status": "13:29", "cancelled": False, "delay_reason": ""},
    ],
]


def animated_services(seconds, interval):
    return PAGES[int(seconds // interval) % len(PAGES)]
