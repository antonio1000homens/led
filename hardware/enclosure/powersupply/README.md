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

## Enclosure attachment

The dock uses six enclosure bosses:

- absolute X: **80 / 176 mm**
- absolute Y: **62.5 / 86.5 / 110.5 mm**
- local dock X: **-48 / +48 mm**
- local dock Y: **-24 / 0 / +24 mm**

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

The removable tray is now **84 mm** wide. With the Ø8 mm raised mounting bosses,
the boss edges reach Y=+/-41 mm, leaving **1 mm** of tray material outside each
boss. The dock is **89 mm** wide so the capture-channel walls remain fused to
the dock base. This still fits inside the enclosure backplane's 92 mm full-depth
mounting zone.

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
