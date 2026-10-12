#!/usr/bin/env python3
"""Summarize MatrixPortal rail serial captures by departures screen cycle."""

import argparse
import re


_FIELD = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([^ ]+)")
_ERROR_MARKERS = ("MemoryError", "Traceback", "RAIL PREBUILD FAILED", "RAIL GC FAILED")
_RESET_MARKERS = ("soft reboot", "hard reset", "hard reboot", "ESP-ROM:esp32s3")


def _fields(line):
    return dict(_FIELD.findall(line))


def _number(value):
    if value in (None, "None", "n/a"):
        return None
    value = value.rstrip("s")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def summarize(lines, label="capture"):
    """Return one metric dictionary per complete rail screen in the log."""
    cycles = []
    pending_prebuild = {}
    pending_train_heap = None
    pending_entry_gc = None
    current = None
    for line in lines:
        fields = _fields(line)
        if line.startswith("RAIL PREBUILD OK "):
            pending_prebuild[fields.get("screen_id", "departures")] = fields
        elif line.startswith("SCREEN START "):
            if fields.get("kind") == "steam_train_intro":
                pending_train_heap = None
            if fields.get("kind") == "rail_combined":
                current = {
                    "label": label,
                    "screen_id": fields.get("id", "unknown"),
                    "status": "running",
                    "services": None,
                    "static_row_renderer": None,
                    "train_prepared_min_free": None,
                    "build_heap_drop": None,
                    "retained_bytes": None,
                    "build_seconds": None,
                    "prebuild_seconds": None,
                    "ready_to_present_ms": None,
                    "gc_count": 0,
                    "gc_seconds": 0.0,
                    "gap_over_200ms": 0,
                    "max_gap_ms": 0.0,
                    "min_free": None,
                    "errors": 0,
                }
                prepared = pending_prebuild.pop(current["screen_id"], None)
                if prepared:
                    current["prebuild_seconds"] = _number(prepared.get("duration"))
                    current["retained_bytes"] = _number(prepared.get("retained_heap_drop"))
                    current["train_prepared_min_free"] = pending_train_heap
                    current["gc_count"] += 1
                    current["gc_seconds"] += _number(prepared.get("gc_duration")) or 0.0
                if pending_entry_gc is not None:
                    current["gc_count"] += 1
                    current["gc_seconds"] += pending_entry_gc
                    pending_entry_gc = None
            elif current is not None and fields.get("kind") not in ("rail_combined",):
                # An overlay or another screen interrupted this departures cycle.
                current["errors"] += 1
        elif current is not None and line.startswith("RAIL BUILD START "):
            current["services"] = _number(fields.get("services"))
            current["static_row_renderer"] = fields.get("static_row_renderer")
        elif current is not None and line.startswith("RAIL BUILD OK "):
            current["build_heap_drop"] = _number(fields.get("heap_drop"))
            current["build_seconds"] = _number(fields.get("duration"))
        elif current is not None and line.startswith("RAIL POST BUILD GC "):
            current["gc_count"] += 1
            current["gc_seconds"] += _number(fields.get("duration")) or 0.0
            current["retained_bytes"] = _number(fields.get("retained_heap_drop"))
        elif current is not None and line.startswith("RAIL FIRST REFRESH OK "):
            current["ready_to_present_ms"] = _number(fields.get("scene_ready_to_present_ms"))
        elif current is not None and line.startswith("RAIL GC ENTER "):
            if fields.get("entry_collect") == "True":
                current["gc_count"] += 1
                current["gc_seconds"] += _number(fields.get("duration")) or 0.0
        elif current is None and line.startswith("RAIL GC ENTER "):
            if fields.get("entry_collect") == "True":
                pending_entry_gc = _number(fields.get("duration")) or 0.0
        elif current is not None and line.startswith("RAIL GC END "):
            current["gc_count"] += 1
            current["gc_seconds"] += _number(fields.get("duration")) or 0.0
        elif current is not None and line.startswith("RAIL GC EXIT "):
            current["gc_count"] += 1
            current["gc_seconds"] += _number(fields.get("duration")) or 0.0
        elif line.startswith("SCREEN END "):
            ended_kind = fields.get("kind")
            if ended_kind == "steam_train_intro":
                pending_train_heap = _number(fields.get("low_water"))
            if current is not None and fields.get("id") == current["screen_id"]:
                current["min_free"] = _number(fields.get("low_water"))
                current["status"] = "complete"
                cycles.append(current)
                current = None
        if current is not None:
            if any(marker in line for marker in _RESET_MARKERS):
                current["status"] = "reset"
                current["errors"] += 1
                cycles.append(current)
                current = None
                continue
            if line.startswith("RAIL FRAME GAP "):
                gap = _number(fields.get("gap_ms"))
                if gap is not None:
                    current["max_gap_ms"] = max(current["max_gap_ms"], gap)
                    if gap > 200:
                        current["gap_over_200ms"] += 1
            if any(marker in line for marker in _ERROR_MARKERS):
                current["errors"] += 1
    if current is not None:
        current["status"] = "incomplete_capture"
        cycles.append(current)
    return cycles


def _cell(value, decimals=0):
    if value is None:
        return "n/a"
    if decimals:
        return ("{:." + str(decimals) + "f}").format(value)
    return str(int(value))


def render_table(cycles):
    header = (
        "| Run | Screen | Status | Services | Row renderer | Train + prepared min free | Build heap drop | "
        "Retained bytes | Build s | Prebuild s | Ready to present ms | GC count/time s | "
        ">200 ms gaps | Max gap ms | Min free | Errors |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    )
    rows = list(header)
    for item in cycles:
        rows.append(
            "| {label} | {screen_id} | {status} | {services} | {static_row_renderer} | {train_prepared_min_free} | "
            "{build_heap_drop} | {retained_bytes} | {build_seconds} | {prebuild_seconds} | "
            "{ready_to_present_ms} | {gc_count}/{gc_seconds} | {gap_over_200ms} | "
            "{max_gap_ms} | {min_free} | {errors} |".format(
                label=item["label"],
                screen_id=item["screen_id"],
                status=item["status"],
                services=_cell(item["services"]),
                static_row_renderer=item["static_row_renderer"] or "n/a",
                train_prepared_min_free=_cell(item["train_prepared_min_free"]),
                build_heap_drop=_cell(item["build_heap_drop"]),
                retained_bytes=_cell(item["retained_bytes"]),
                build_seconds=_cell(item["build_seconds"], 3),
                prebuild_seconds=_cell(item["prebuild_seconds"], 3),
                ready_to_present_ms=_cell(item["ready_to_present_ms"]),
                gc_count=_cell(item["gc_count"]),
                gc_seconds=_cell(item["gc_seconds"], 3),
                gap_over_200ms=_cell(item["gap_over_200ms"]),
                max_gap_ms=_cell(item["max_gap_ms"]),
                min_free=_cell(item["min_free"]),
                errors=_cell(item["errors"]),
            )
        )
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("serial_log", help="saved CircuitPython serial capture")
    parser.add_argument("--label", default="capture", help="A/B run label")
    args = parser.parse_args()
    with open(args.serial_log, encoding="utf-8", errors="replace") as capture:
        cycles = summarize(capture, args.label)
    print(render_table(cycles))


if __name__ == "__main__":
    main()
