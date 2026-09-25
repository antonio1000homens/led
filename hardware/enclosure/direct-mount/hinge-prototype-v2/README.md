# Support-free 6 mm hinge prototype v2

This is a deliberately simplified mechanical prototype for the LED direct-mount enclosure.

It exists alongside `hinge-version/`; it does **not** replace the verified production backplane or the earlier full equipment-enclosure experiment.

## Mechanical concept

The **equipment enclosure is stationary**.

The **LED panel + verified mounting template is the moving leaf** and opens forward/down like an oven door around a 6 mm horizontal rod.

The stationary enclosure reaches the floor and provides the support footprint. In the closed position the LED/template is intentionally lifted above the floor rather than being used as the stand.

Prototype defaults:

- LED/template bottom edge: **15 mm above ground**
- hinge barrel OD: **14 mm**
- hinge axis: **22 mm above ground**
- hinge axis depth: **z=9 mm behind the LED/template front plane**
- floor-base forward extension: **25 mm in front of the LED plane**
- floor-base thickness: **5 mm**
- enclosure depth behind the LED/template: **24 mm**

## Why this differs from the previous attempt

The earlier v2 prototype treated the template as the stationary half and added a full-width lower tongue/lip beneath it.

That was the wrong motion for the intended product: the lip could obstruct the opening sweep.

This revision therefore:

- removes the full-width template tongue entirely;
- keeps only **local hinge-root reinforcement** behind the existing lower template band;
- makes the enclosure/base the stationary structure;
- rotates the panel/template forward and down;
- adds the requested **2–3 cm floor base** to the enclosure instead;
- holds the panel/template approximately **1.5 cm above the floor** when closed.

## Verified panel geometry

The moving leaf still calls `mount_pattern_template()` directly from `../direct_mount_enclosure.scad`.

That means the physical panel interface remains the currently verified one:

- six panel mounting centres unchanged;
- four moulded-locator clearances unchanged;
- no re-measurement or copied hole coordinates inside this prototype.

Only the hinge reinforcement is added behind the lower band.

## Files

- `01_moving_panel_template_HINGE_TEST.scad` — verified LED mounting template with local moving hinge knuckles.
- `02_stationary_enclosure_HINGE_TEST.scad` — stationary shallow enclosure, fixed knuckles and floor base.
- `00_CLOSED_ASSEMBLY.scad` — vertical/closed assembly preview.
- `00_OPEN_ASSEMBLY.scad` — 90° forward/down opening preview.
- `hinge_prototype_v2.scad` — source geometry.
- `stl/01_moving_panel_template_HINGE_TEST.stl` — generated printable moving leaf.
- `stl/02_stationary_enclosure_HINGE_TEST.stl` — generated printable stationary enclosure/base.

The SCAD files are the source of truth. The STL files are intentionally checked in for direct printing and are regenerated/compared by `Enclosure / Validate`; a PR fails if an STL is stale relative to its SCAD entrypoint.

## Hinge

- physical rod: **6.0 mm**
- printed bore: **7.2 mm**
- printed barrel OD: **14 mm**
- nominal axial knuckle clearance: **1.0 mm**
- closed hinge axis: **y=22 mm, z=9 mm**

The moving and stationary knuckles alternate along X and continue to avoid the lower panel screw/locator columns. The wider central service gap around the lower-centre panel screw is retained.

## Stationary base

The enclosure base is the floor contact.

It extends from the back of the enclosure to **25 mm in front of the LED/template plane**. The base is currently a simple full-width 5 mm slab because this prototype is intended to validate balance, opening clearance and slicer behaviour before styling/material reduction.

With the display closed:

- the enclosure/base sits on the ground;
- the LED/template lower edge is 15 mm above ground;
- the hinge barrel also remains above ground;
- the moving panel does not need a lower support lip.

At 90° open, the panel/template swings forward/down above the base rather than trying to rotate around a projecting template tongue.

## Printing

### Moving panel/template

Print `01_moving_panel_template_HINGE_TEST.scad` exactly as generated.

The verified template remains flat on the build plate. Only local knuckle roots rise behind the existing lower band.

Expected prototype print envelope is approximately:

- **256 × 128 × 16 mm**

There is no full-width lower tongue.

### Stationary enclosure/base

Print `02_stationary_enclosure_HINGE_TEST.scad` exactly as generated.

The wrapper places the large rear plate on the build plate. The 25 mm forward floor extension therefore grows as a vertical, bed-connected slab instead of appearing later as a floating horizontal cantilever.

Expected prototype print envelope is approximately:

- **255 × 142.5 × 51.8 mm**

This is still much lower-risk than standing the 255 mm enclosure vertically.

Supports should not be required by the intended geometry.

## Test sequence

1. Slice both generated STLs in Bambu Studio.
2. Confirm neither reports a floating region / floating cantilever.
3. Print the moving template and confirm the unchanged six mounting holes and locator clearances still fit the real LED panel.
4. Print the stationary enclosure/base.
5. Interleave both hinge halves and insert the real 6 mm rod.
6. Close the display and confirm the enclosure/base carries the assembly while the LED/template remains roughly 15 mm above the floor.
7. Open the LED/template forward/down to 90° and confirm there is no interference from the base, enclosure lower wall or hinge roots.
8. Check that the 25 mm forward base gives enough stability.
9. If required, tune `ground_clearance` between roughly 10–20 mm and `base_front_extension` between 20–30 mm after the physical test.
10. Only after this motion is proven should PSU/controller mounts, cable openings, ventilation and a top latch be added.

PETG is preferred for repeated hinge testing. PLA is acceptable for a dimensional-only print.
