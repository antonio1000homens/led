# Flush-base 6 mm hinge prototype v2

This is a deliberately simplified **print-first prototype** for a bottom-hinged service enclosure. It does not replace the production direct-mount enclosure or the older `hinge-version/` experiment.

## What this prototype proves

The fixed half calls the existing production `backplane(false)` directly, so the verified LED-panel mounting holes, locator clearances, reinforcement-bar bores, seam geometry and screw wells remain owned by `../direct_mount_enclosure.scad`.

The prototype adds only the hinge/base mechanics needed for a physical test:

- **6.0 mm metal rod** hinge pin;
- **7.2 mm printed bore**;
- alternating fixed/moving hinge lugs along the 256 mm panel width;
- a fixed **14 mm-high base tongue** behind the production backplane;
- a simple moving service enclosure with matching hinge beams;
- closed and open assembly previews;
- a small rod-fit coupon.

## Why the hinge lugs are rectangular

The previous round-barrel experiments could be mechanically connected but still create slicer warnings because a horizontal round barrel can begin with a very small contact area and then grow outward as a cantilever.

For this prototype the hinge knuckles are **14 × 14 mm rectangular lugs** with a circular 7.2 mm bore. The lugs alternate along X, so they do not need a round outside surface to rotate around one another: only the common 6 mm rod defines the pivot.

This gives the slicer simple vertical/flat geometry while preserving the real hinge motion.

## Flush base / tongue

The hinge axis is:

- `y = 7.5 mm`
- `z ≈ 26.9 mm`

The lower face of each 14 mm hinge lug is exactly `y = 0.5 mm`, matching the lower edge of the verified production backplane.

The fixed backplane grows a **14 mm-high tongue** from `z = 15.5 mm` to the rear of the hinge. The tongue therefore:

1. overlaps the existing 16 mm backplane by 0.5 mm, so it is one structural part;
2. supports the fixed hinge lugs over their full height, rather than letting a lug begin in mid-air;
3. becomes the flat underside/base instead of allowing the hinge to protrude below the enclosure.

Circular sweep pockets are removed only where the moving lugs rotate. Narrow clearances are also removed at the extreme left/right for the moving enclosure side walls. The rest of the tongue remains available as the base.

## Moving enclosure print orientation

`02_moving_enclosure_HINGE_V2.scad` is already exported in the intended slicer orientation: **rear face on the print bed**.

Approximate print bounds are:

- X: **255 mm**
- Y: **127 mm**
- Z: **30.9 mm**

In that orientation:

- the 2.5 mm rear panel starts on the bed;
- the side/top walls grow directly from the rear panel;
- each moving hinge beam grows continuously from the rear panel toward the rod bore;
- there are no elevated downward-facing start surfaces in the prototype geometry.

The fixed backplane prints in its normal production orientation.

## Kinematic clearance

The pivot is intentionally farther behind the 16 mm production backplane than the closed 14 mm lug alone would require. A square lug's corner sweeps at its diagonal radius while rotating, so the pivot spacing is based on that full sweep rather than only the closed-position depth.

The checked geometry has no fixed/moving intersection when closed and no intersection at:

`5°, 15°, 30°, 45°, 60°, 75°, 90°`

using the positive opening direction in `moving_at_angle()`.

## Files

- `hinge_prototype_v2.scad` — shared prototype source.
- `01_fixed_backplane_HINGE_V2.scad` — verified production backplane + fixed tongue/lugs.
- `02_moving_enclosure_HINGE_V2.scad` — moving enclosure, already oriented rear-face-down for printing.
- `03_hinge_fit_coupon_HINGE_V2.scad` — quick 6 mm rod/bore test.
- `00_closed_assembly_HINGE_V2.scad` — closed preview.
- `00_open_assembly_HINGE_V2.scad` — 75° open preview.
- `98_closed_intersection_CHECK.scad` — should render empty.
- `99_collision_sweep_CHECK.scad` — should render empty for the tested opening angles.

## Exporting STL files

From this directory:

```bash
openscad -o fixed_backplane_hinge_v2.stl 01_fixed_backplane_HINGE_V2.scad
openscad -o moving_enclosure_hinge_v2.stl 02_moving_enclosure_HINGE_V2.scad
openscad -o hinge_fit_coupon_v2.stl 03_hinge_fit_coupon_HINGE_V2.scad
```

Open the resulting STL files in Bambu Studio without changing their orientation first. The moving enclosure is already transformed for the intended rear-face-down print.

## Recommended first physical test

Print the small coupon first and confirm the real 6 mm rod slides through the 7.2 mm bore comfortably. Then print one fixed backplane and one moving enclosure and verify:

1. the fixed backplane still fits the real LED panel exactly as the production part does;
2. the rod passes through all alternating lugs without forcing;
3. the two halves close without the hinge protruding below the tongue/base;
4. the enclosure rotates freely through the service angle;
5. Bambu Studio no longer reports a hinge-created floating region/cantilever;
6. the 14 mm tongue is thick enough for the base you want before adding final cable cut-outs, PSU mounts or a latch.

The prototype intentionally defers those secondary features until this hinge/base geometry has been physically validated.
