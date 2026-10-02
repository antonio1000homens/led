# PSU snap-latch service tray

Issue #166 now has one selected PSU mounting design: a **removable service tray
with a replaceable cantilever snap latch**.

The previous adapter, direct-slide, hybrid and side-screw service-tray concepts
have been removed.

## Parts

| File | Purpose |
| --- | --- |
| `01_service_tray_snap_latch.scad` | Source design and assembled visualisation |
| `02_service_tray_snap_dock_PRINT_1.scad` | Printable fixed dock |
| `03_service_tray_snap_tray_PRINT_1.scad` | Printable removable PSU tray |
| `04_service_tray_snap_latch_PRINT_1.scad` | Printable replaceable flexible latch |
| `05_backplane_fit_preview.scad` | Supporting enclosure-boss alignment preview |
| `06_boss_heatset_insert_test.scad` | Supporting M3 heat-set-insert test coupon |
| `psu_mount_common.scad` | Shared dimensions and enclosure interface |

## How the latch works

The latch is now **front-operated** so the assembled PSU mount needs no side
access.

The tray still slides along X. The replaceable 30 mm cantilever sits on the
front/insertion (-X) face of the dock and flexes **vertically in Z**.

During insertion:

1. the tray slides toward +X;
2. its trailing/front lip reaches the hook ramp;
3. the lip pushes the cantilever **downward**;
4. the tray reaches the separate hard +X stop;
5. the hook springs upward into an underside pocket behind the tray's front lip;
6. that front lip prevents the tray withdrawing.

To remove the tray, reach the insertion/front edge, press the thumb tab
**down**, and pull the tray back toward -X. There is no side-release motion and
nothing needs to be reached from either Y side.

The latch remains a separate replaceable part. PETG is preferred for repeated
flexing; PLA is useful for quick dimensional testing.

Initial front-latch geometry:

- cantilever length: **30 mm**
- spring thickness in Z: **1.4 mm**
- spring width in X: **1.6 mm**
- tray retaining lip: **1.5 mm**
- underside catch pocket: **4 mm long x 7 mm wide x 2 mm deep**
- front release tab: **press down to unlatch**

The hard +X stop takes insertion load; the latch only resists withdrawal.

### Latch-to-dock attachment

The **latch does not snap onto the dock**. It is a replaceable part retained by
two horizontal M3 machine screws. The screws pass through the 3.2 mm clearance
holes in the latch base and thread into **brass M3 heat-set inserts** installed
in the front (-X) dock pad.

The dock pad is now sized specifically for this serviceable fixing:

- pad depth in X: **5.4 mm**
- pad width in Y: **16 mm**
- pad height in Z: **7 mm**
- insert pitch: **7 mm**
- insert pilot/bore: **3.4 mm**, matching the existing heat-set test coupon
- insert socket depth: **4.2 mm**
- blind PETG wall behind each socket: **1.2 mm**

Heat-set the two inserts horizontally from the service/front face **before**
fitting the latch. The latch can then be removed without repeatedly cutting M3
threads into PETG. An M3x6 screw is the expected starting length for the 1.8 mm
latch base plus the insert engagement, but verify the usable thread depth of the
actual purchased insert before tightening.

The thicker insert pad grows only toward -X, so it does **not** change the
critical 79 mm Y envelope. The latch hook is lengthened by the same amount that
the base moves outward, keeping the hook/tooth engagement position in the tray
pocket unchanged.

Use `06_boss_heatset_insert_test.scad` to prove the 3.4 mm bore against the
actual inserts before heat-setting the production dock. If the real insert
requires a different pilot diameter, change the latch bore to match the proven
coupon rather than forcing the insert.

## Enclosure attachment

The dock uses six enclosure bosses. Physical fit testing required the outer Y
rows to move **5 mm inward**:

- absolute X: **80 / 176 mm**
- absolute Y: **67.5 / 86.5 / 105.5 mm**
- local dock X: **-48 / +48 mm**
- local dock Y: **-19 / 0 / +19 mm**

Each dock fixing has:

- 7.5 mm locating pocket around the 7 mm enclosure boss;
- 3.6 mm M3 clearance hole;
- 7 mm equipment-side screw-head recess.

The current enclosure boss contains a 3.4 mm blind hole. A heat-set insert is a
purchased brass M3 threaded sleeve, not a bolt. Print
`06_boss_heatset_insert_test.scad` and prove the chosen insert on the coupon
before fitting inserts to the real enclosure.

## PSU support

The measured PSU envelope is **110 x 80 x 37 mm**.

The two mounting-hole centres are diagonally opposed and measured **3 mm from
the adjacent long and short edges**. Relative to the centred PSU this resolves
to:

```scad
psu_rear_mount_points = [
    [-52, -37],
    [ 52,  37]
];
```

Those coordinates imply a diagonal centre-to-centre distance of **127.64 mm**.
The separate hand measurement was approximately **125 mm**; the edge-inset
measurements are used for the CAD because they uniquely locate both holes.

Physical fit testing established an **80 mm maximum usable enclosure opening**.
The previous 84 mm tray / 89 mm dock therefore did not fit.

The corrected design uses:

- removable tray Y envelope: **79 mm**
- fixed dock Y envelope: **79 mm**
- clearance inside an 80 mm opening: **0.5 mm per side**
- PSU width: **80 mm**, overhanging the tray by only **0.5 mm per side**
- two **internal dovetail runners** at Y=+/-25 mm instead of external side
  capture rails

The dovetails positively capture the tray without adding anything outside the
79 mm envelope. Their matching underside grooves stop 8 mm short of the rear
edge so the tray remains a connected, support-friendly print.

The measured PSU screw pilots remain at Y=+/-37 mm. Their 2.8 mm holes still
retain just over **1 mm** of PETG to the 79 mm tray edge. The Ø8 mm raised
support bosses are clipped flush at the tray boundary rather than widening the
part.

The boss tops remain raised by the same **2 mm** as the airflow/support bars so
the PSU sits on one common support plane.

## Render parts locally

```bash
openscad -o /tmp/psu-service-tray-dock.stl 02_service_tray_snap_dock_PRINT_1.scad
openscad -o /tmp/psu-service-tray-tray.stl 03_service_tray_snap_tray_PRINT_1.scad
openscad -o /tmp/psu-service-tray-latch.stl 04_service_tray_snap_latch_PRINT_1.scad
```

The three printable parts are also declared in `.windsor-slicer.yaml` as:

- `psu-service-tray-dock`
- `psu-service-tray-tray`
- `psu-service-tray-latch`

Windsor validation uses:

- machine: `Bambu Lab H2D 0.4 nozzle`
- process: `0.20mm Standard @BBL H2D`
- filament: `Bambu PETG Basic @BBL H2D 0.4 nozzle`
- bed: `Textured PEI Plate`

The Textured PEI bed is specified explicitly because Bambu Studio's default Cool
Plate preset rejects PETG before slicing. The front-operated latch is authored
with its spring arm directly on Z=0, so the separate latch prints flat without
support.
