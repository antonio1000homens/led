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

The tray moves along X. The latch is mounted outside the +Y dock wall and its
30 mm cantilever arm also runs along X, but flexes **sideways in Y**.

During insertion:

1. the tray slides toward +X;
2. its edge rides over the hook's ramp;
3. the printed cantilever bends outward in +Y;
4. the tray reaches the separate hard +X stop;
5. the hook aligns with the tray side notch and springs inward;
6. the hook prevents withdrawal.

To remove the tray, pull the external thumb tab outward in +Y and slide the
tray back toward -X.

The latch is deliberately a separate part. PETG is preferred for repeated
flexing. PLA can be used for a quick fit/geometry prototype.

Initial latch geometry:

- arm length: **30 mm**
- arm width: **8 mm**
- arm thickness: **1.6 mm**
- hook reach from external latch base: **6.5 mm**, giving about **1.8 mm** effective engagement into the tray notch
- tray notch depth: **2.6 mm**

The hard stop takes insertion load; the latch only resists withdrawal.

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

The PSU envelope is approximately **110 x 80 x 37 mm**.

The removable tray has two airflow/support bars and two raised PSU mounting
bosses. The boss tops are raised by the same **2 mm** as the bars so all four
support points form one plane.

The PSU hole coordinates are still placeholders:

```scad
psu_rear_mount_points = [
    [-42, -27],
    [ 42,  27]
];
```

Measure the real PSU before treating those two fixing points as final.

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
Plate preset rejects PETG before slicing. The latch is exported in its assembled
orientation but translated down to Z=0 so the arm prints with its flex direction
in the XY layer plane.
