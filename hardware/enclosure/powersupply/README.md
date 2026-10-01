# Power-supply mounting experiments

Experimental fully printed mounting concepts for [issue #166](https://github.com/antonio1000homens/led/issues/166).

These files deliberately live outside the canonical enclosure `parts/` and `stl/`
sets. They are prototypes for physical fit testing and **must not** be treated as
production geometry until the real PSU mounting-hole coordinates have been
measured.

## Known geometry

The canonical universal backplane provides M3 accessory bosses at:

- X: `32 / 80 / 128 / 176 / 224 mm`
- Y: `60 / 124 mm`

The prototypes use the centred four-boss rectangle:

- X: `80 / 176 mm`
- Y: `60 / 124 mm`
- relative spacing: **96 × 64 mm**

The enclosure documentation currently records the PSU envelope as approximately
**110 × 80 × 37 mm**.

`psu_mount_common.scad` therefore uses that envelope and the real enclosure boss
spacing, but the two PSU rear/bottom mounting-hole coordinates are still
explicitly marked as placeholders.

## Options

| File | Concept | Depends on measured PSU holes? | Main purpose |
| --- | --- | --- | --- |
| `01_adapter_plate.scad` | Simple plate + support rails + corner guides | Yes, for final screw locations | Lowest-complexity baseline |
| `02_slide_cradle.scad` | Horizontal slide-in cradle + one lock screw | No | Test service access and envelope capture |
| `03_service_tray.scad` | Two-piece dock + removable PSU tray | Optional | Test removing PSU/wiring as a module |
| `04_hybrid_mount.scad` | Plate + locating pins + corner guides + lock screw | Yes, for locating pins | Preferred issue #166 direction |
| `00_compare_options.scad` | Four-up geometry view | N/A | Visual comparison only |

All options are printed plastic plus ordinary fasteners. There is **no metal
adapter plate and no loose spacer/standoff scheme**.

## Before a production print

Measure the real PSU and update `psu_mount_common.scad`:

```scad
psu_w = 110;
psu_h = 80;
psu_d = 37;

psu_rear_mount_points = [
    [x1, y1],
    [x2, y2]
];
```

Use the PSU centre as `[0, 0]`. Positive X is toward the right of the backplane;
positive Y is toward the top of the enclosure.

Also verify:

1. the PSU can be inserted with the enclosure side/terminal wiring present;
2. the 82 mm prototype adapter height fits the real 84 mm deep equipment zone;
3. terminal screws remain accessible;
4. no printed feature blocks PSU case ventilation;
5. locating pins actually match the PSU xole/slot shape;
6. screw heads cannot touch the PSU PCB or mains wiring;
7. the mount stays captive when the enclosure is opened or moved.

## Rendering

From this directory:

```bash
openscad -o /tmp/psu-adapter.stl 01_adapter_plate.scad
openscad -o /tmp/psu-cradle.stl 02_slide_cradle.scad
openscad -o /tmp/psu-service-tray.stl 03_service_tray.scad
openscad -o /tmp/psu-hybrid.stl 04_hybrid_mount.scad
```

For the service tray, switch:

```scad
layout = "assembled";
```

to inspect the dock/tray relationship instead of generating the separated print
layout.

The final chosen mount should then be promoted into the normal enclosure
generation/validation flow and sliced with the configured H2D PETG profile.
