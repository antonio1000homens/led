"""Deterministic data for Wokwi and host-side tests."""


SERVICES = [
    {"time": "12:04", "destination": "Waterloo", "platform": "1", "status": "On time", "cancelled": False, "delay_reason": ""},
    {"time": "12:16", "destination": "Shepperton", "platform": "2", "status": "12:18", "cancelled": False, "delay_reason": ""},
    {"time": "12:27", "destination": "Waterloo", "platform": "1", "status": "Cancelled", "cancelled": True, "delay_reason": "Signal failure"},
]

