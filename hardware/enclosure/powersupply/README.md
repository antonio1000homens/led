# Power-supply mounting experiments

Experimental fully printed mounting concepts for issue #166.

These files live outside the canonical enclosure `parts/` and `stl/` sets.
They are prototypes for physical fit testing and must not be treated as
production geometry until the real PSU mounting-hole coordinates and retention
method have been verified.

## Current backplane interface

PR #167 is based on the current enclosure geometry from PR #164.

The universal backplane currently provides five X columns and three Y rows of
7 mm OD x 4 mm high bosses. For the PSU adapter these experiments use the two
central outer columns and all three Y rows:

- absolute X: **80 / 176 mm**
- absolute Y: **62.5 / 86.5 / 110.5 mm**
- local X about adapter centre: **-48 / +48 mm**
- local Y about adapter centre: **-24 / 0 / +24 mm**

That gives a six-boss interface spanning **96 x 48 mm**.

Every adapter base now has six 3.6 mm screw-clearance holes and six shallow
**7.5 mm diameter x 1.2 mm deep** locating pockets on its back face. The 7 mm
backplane bosses enter those pockets, so alignment is provided by the boss
bodies themselves rather than by visually centring loose screw holes.

Open `05_backplane_fit_preview.scad` to see this relationship directly. The
solid object is the printable adapter; the transparent wall and six cylinders
simulate the current backplane and bosses.

## Fastener retention

The current backplane bosses contain **3.4 mm blind holes**. They are not
modelled as threaded holes, so an ordinary M3 machine screw must not be assumed
to grip them securely by itself.

For the PSU experiment, the preferred retention test is:

1. print `06_boss_insert_test.scad`, which reproduces the current boss and
   blind-hole geometry;
2. test the intended M3 heat-set insert and screw on the coupon;
3. only use heat-set inserts in the real backplane bosses if the coupon shows
   adequate wall thickness, insertion depth and pull-out strength;
4. if the insert is too large for the 7 mm boss, do not force it - change the
   canonical boss design in a separate revision instead.

This keeps PR #167 from silently changing the already-validated universal
backplane while still providing an explicit, testable fastening path.

## PSU geometry

The enclosure documentation records the PSU envelope as approximately
**110 x 80 x 37 mm**.

`psu_mount_common.scad` uses that envelope, but these two PSU rear/bottom
mounting-hole positions are still placeholders:

```scad
psu_rear_mount_points = [
    [-42, -27],
    [ 42,  27]
];
```

Replace them with measurements from the real PSU before relying on the locating
pins or PSU pilot holes.

## Options

| File | Concept | Purpose |
| --- | --- | --- |
| `01_adapter_plate.scad` | Simple plate + support rails + corner guides | Lowest-complexity baseline |
| `02_slide_cradle.scad` | Horizontal slide-in cradle + lock screw | Test service access without relying on PSU hole coordinates |
| `03_service_tray.scad` | Two-piece dock + removable PSU tray | Remove PSU/wiring as a module |
| `04_hybrid_mount.scad` | Plate + PSU locating pins + corner guides + lock screw | Preferred issue #166 direction |
| `05_backplane_fit_preview.scad` | Adapter assembled on current six-boss backplane interface | Verify boss alignment visually |
| `06_boss_insert_test.scad` | Exact single-boss coupon | Test M3 insert/retention safely |
| `00_compare_options.scad` | Four-up geometry view | Compare the four mount concepts |

All options are printed plastic plus ordinary fasteners. There is no metal
adapter plate and no loose spacer/standoff scheme.

## Before a production print

Verify:

1. all six locating pockets seat over the real backplane bosses;
2. the adapter sits flat without rocking;
3. the chosen boss retention method survives the test coupon;
4. the PSU can be inserted with terminal wiring present;
5. terminal screws remain accessible;
6. no printed feature blocks PSU ventilation;
7. PSU mounting-hole coordinates match the real unit;
8. screw heads/inserts cannot touch the PSU PCB or mains wiring.

## Rendering

From this directory:

```bash
openscad -o /tmp/psu-adapter.stl 01_adapter_plate.scad
openscad -o /tmp/psu-cradle.stl 02_slide_cradle.scad
openscad -o /tmp/psu-service-tray.stl 03_service_tray.scad
openscad -o /tmp/psu-hybrid.stl 04_hybrid_mount.scad
openscad -o /tmp/psu-fit-preview.stl 05_backplane_fit_preview.scad
openscad -o /tmp/psu-boss-test.stl 06_boss_insert_test.scad
```

For the service tray, set `layout = "assembled"` in
`03_service_tray.scad` to inspect the dock and tray together instead of the
separated print layout.

The final selected mount can then be promoted into the normal enclosure
generation/validation flow and sliced with the configured H2D PETG profile.
