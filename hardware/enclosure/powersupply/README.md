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
modelled as threaded holes.

A **heat-set insert is not a bolt**. It is a small purchased brass sleeve with
an M3 internal thread. The insert is heated (normally with a soldering iron or
heat-set-insert tip) and pressed into a correctly sized plastic boss. After it
cools, an ordinary M3 machine screw threads into the brass insert.

The attachment stack is therefore:

```text
M3 screw
   |
service-tray dock
   |
brass M3 heat-set insert
   |
printed enclosure boss
```

`06_boss_heatset_insert_test.scad` is **not** the insert. It is a small
printable coupon that reproduces one current enclosure boss so the real brass
insert can be tested without damaging the enclosure.

The current boss is only 7 mm OD with a 3.4 mm blind hole, so insert fit must be
proven on the coupon before fitting inserts to the real backplane. If the chosen
M3 insert needs a larger boss or different pilot diameter, the canonical
backplane boss geometry should be changed deliberately rather than forcing the
insert into the existing part.

## PSU geometry

The enclosure documentation records the PSU envelope as approximately
**110 x 80 x 37 mm**. Those dimensions are used only to size the mount geometry;
there is no longer a transparent simulated PSU body in any SCAD preview.

The two PSU rear/bottom mounting-hole positions are still placeholders:

```scad
psu_rear_mount_points = [
    [-42, -27],
    [ 42,  27]
];
```

Replace them with measurements from the real PSU before relying on the locating
pins or PSU pilot holes.

## Options

The direct-slide cradle and hybrid concepts have been removed because the PSU
itself has no rail features and the selected direction is the removable service
tray.

| File | Concept | Purpose |
| --- | --- | --- |
| `03_service_tray.scad` | Fixed dock + removable PSU tray | **Selected design direction** |
| `05_backplane_fit_preview.scad` | Adapter against current six-boss backplane interface | Verify enclosure-side boss alignment |
| `06_boss_heatset_insert_test.scad` | Exact single-boss coupon | Test a real brass M3 heat-set insert safely |
| `07_service_tray_snap_latch.scad` | Service tray + replaceable cantilever latch | **Alternative tool-free service lock for visual/physical testing** |
| `00_compare_options.scad` | Screw-lock tray + snap-latch tray | Visual comparison |

## Completeness audit

The enclosure-side attachment has now been reviewed for the remaining service-tray designs.

| Option | Enclosure attachment | PSU retention | Current status |
| --- | --- | --- | --- |
| 3 - Service tray | Fixed dock has six retained screw lands; removable tray is captured in dock channels | Two raised PSU screw bosses level with support bars; tray retained by removable side-entry M3 lock screw | **Selected direction; final PSU hole coordinates still need measurement** |

The service-tray dock retains two full-height fixing spines around X=+/-48, so
all six M3 enclosure fixing holes remain visible and connected to the dock
perimeter.

The two PSU mounting points on the removable tray are now **raised by the same
2 mm as the airflow/support bars**. Their top faces and the bars therefore form
one common support plane; tightening the PSU screws will no longer pull the PSU
down below the rails.

Option 03 keeps the removable side-entry M3 lock as the baseline.

Option 07 is a new **tool-free snap-latch alternative**. It keeps the same
dock/tray geometry and hard +X insertion stop, but adds a separate replaceable
cantilever latch outside the +Y channel wall. The latch arm runs parallel to
tray travel. Its hook reaches through a small wall window into a side notch in
the tray.

During insertion the tray edge rides up the hook ramp and flexes the latch
outward. When the tray reaches the hard +X stop, the notch aligns with the hook
and the latch snaps inward automatically. Pull the external thumb tab outward
to release the hook, then slide the tray back out.

The latch is a separate part so it can be replaced without reprinting the dock.
PETG is recommended for repeated use; PLA is useful for a quick dimensional
prototype but is expected to fatigue sooner. The first prototype uses a
1.6 mm-thick, 8 mm-wide, 30 mm-long cantilever arm with about 2 mm of effective
notch engagement.

The current side-lock boss uses a 2.8 mm tapping pilot for prototype testing.
If repeated servicing shows that plastic threads wear too quickly, that external
boss can be dimensioned for a brass M3 heat-set insert once the actual insert
dimensions are known.

The direct-slide cradle and hybrid have been removed from the branch.

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
openscad -o /tmp/psu-service-tray.stl 03_service_tray.scad
openscad -o /tmp/psu-fit-preview.stl 05_backplane_fit_preview.scad
openscad -o /tmp/psu-boss-test.stl 06_boss_heatset_insert_test.scad
openscad -o /tmp/psu-snap-tray.stl 07_service_tray_snap_latch.scad
```

For the service tray, set `layout = "assembled"` in
`03_service_tray.scad` to inspect the dock and tray together instead of the
separated print layout.

The final selected mount can then be promoted into the normal enclosure
generation/validation flow and sliced with the configured H2D PETG profile.
