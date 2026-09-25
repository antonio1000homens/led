#!/usr/bin/env python3
"""Publish one short-lived reminder event for MatrixPortal MQTT testing.

Reads MQTT settings from the board's uncommitted settings_local.py. Requires
paho-mqtt in the Python environment used to run this script.
"""

import argparse
import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event
from uuid import uuid4
import json
import sys


DEFAULT_SETTINGS = Path("/Volumes/CIRCUITPY/settings_local.py")


def load_mqtt_settings(path):
    values = {}
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id.startswith("MQTT_"):
            try:
                values[target.id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
    required = ("MQTT_ENABLED", "MQTT_ENABLE_EXPERIMENTAL", "MQTT_BROKER", "MQTT_PORT", "MQTT_TOPIC")
    missing = [key for key in required if key not in values]
    if missing:
        raise ValueError("Missing MQTT settings: " + ", ".join(missing))
    if not values["MQTT_ENABLED"] or not values["MQTT_ENABLE_EXPERIMENTAL"]:
        raise ValueError("MQTT is disabled in board-local settings")
    if not values["MQTT_BROKER"]:
        raise ValueError("MQTT_BROKER is empty")
    return values


def utc_iso(value):
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS)
    parser.add_argument("--label", default="Manual MQTT test")
    args = parser.parse_args()

    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        print("paho-mqtt is required; install it in the Python environment used to run this script", file=sys.stderr)
        return 2

    try:
        settings = load_mqtt_settings(args.settings)
    except (OSError, SyntaxError, ValueError) as error:
        print("Cannot load board MQTT settings:", error, file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc)
    event_id = "manual-" + uuid4().hex
    payload = {
        "id": event_id,
        "type": "reminder",
        "event": "due",
        "label": args.label,
        "due_at": utc_iso(now),
        "published_at": utc_iso(now),
        "expires_at": utc_iso(now + timedelta(minutes=5)),
        "source": "manual-test",
    }

    connected = Event()
    connection_result = {}

    def on_connect(client, userdata, flags, reason_code, properties):
        connection_result["ok"] = not reason_code.is_failure
        connection_result["reason"] = str(reason_code)
        connected.set()

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="led-manual-test-" + uuid4().hex[:10],
    )
    client.username_pw_set(settings.get("MQTT_USERNAME") or None, settings.get("MQTT_PASSWORD") or None)
    client.on_connect = on_connect

    try:
        client.connect(settings["MQTT_BROKER"], settings["MQTT_PORT"], keepalive=30)
        client.loop_start()
        if not connected.wait(10):
            raise TimeoutError("Timed out waiting for broker CONNACK")
        if not connection_result.get("ok"):
            raise ConnectionError("Broker rejected MQTT connection: " + connection_result.get("reason", "unknown reason"))

        info = client.publish(
            settings["MQTT_TOPIC"],
            json.dumps(payload, separators=(",", ":")),
            qos=1,
            retain=False,
        )
        info.wait_for_publish(timeout=10)
        if not info.is_published():
            raise TimeoutError("Timed out waiting for MQTT PUBACK")
    except Exception as error:
        print("MQTT test publish failed:", type(error).__name__ + ":", error, file=sys.stderr)
        return 1
    finally:
        try:
            client.disconnect()
            client.loop_stop()
        except Exception:
            pass

    print("Published QoS 1 test event; PUBACK received")
    print("topic:", settings["MQTT_TOPIC"])
    print("id:", event_id)
    print("label:", args.label)
    print("expires:", payload["expires_at"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
