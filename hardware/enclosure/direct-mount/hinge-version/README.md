# 6 mm rail hinge prototype

This directory is an **experimental alternative** to the production direct-mount backplane/lid arrangement.

It does not replace the validated production files under `../parts/` and `../stl/`.

## Concept

The fixed half is derived from the corrected `08_mount_pattern_template_PRINT_1` geometry, so it uses the exact current panel mounting and locator coordinates from `../direct_mount_enclosure.scad`.

The moving half is a deeper equipment enclosure/tray. A continuous **6 mm metal rail** passes through alternating printed hinge knuckles on both halves and becomes the hinge pin.

With four modules side-by-side, the intention is that a single 1000 mm × 6 mm rail can pass through the bottom knuckles across the display.

When the moving enclosure is opened downward:

- the back of the LED panel remains on the fixed-template side;
- the PSU, controller and wiring can stay attached to the moving equipment tray;
- the equipment tray rotates around the same 6 mm rail.

## Printable files

- `08_mount_pattern_template_HINGE_PRINT_1.scad`
- `stl/08_mount_pattern_template_HINGE_PRINT_1.stl`
  - corrected 256 × 128 mm template geometry;
  - six panel boss holes remain x = 7.9 / 128 / 248.1 mm and y = 7.9 / 120.1 mm;
  - four moulded-locator clearances remain unchanged;
  - alternating fixed hinge knuckles are integrated below the bottom edge.

- `11_hinged_equipment_enclosure_PRINT_1.scad`
- `stl/11_hinged_equipment_enclosure_PRINT_1.stl`
  - complementary hinge knuckles;
  - 30 mm internal tray depth between the front lip and equipment mounting plate;
  - full-size slotted equipment mounting plate for PSU/controller/cable ties;
  - full-width rear foot beam and diagonal ribs at the lower edge to increase desk footprint.

## Hinge dimensions

- physical hinge rail: **6.0 mm diameter**
- printed hinge bore: **7.2 mm**
- printed hinge barrel outside diameter: **13 mm**
- hinge axis: **y = -5.8 mm, z = 8 mm** relative to the panel coordinate system

The 7.2 mm bore deliberately preserves the same 0.6 mm radial clearance currently used for the 6 mm reinforcement bars.

The knuckles alternate:

### Fixed template

- x = 16–48 mm
- x = 96–128 mm
- x = 176–208 mm

### Moving enclosure

- x = 50–94 mm
- x = 130–174 mm
- x = 210–240 mm

This leaves approximately 2 mm axial clearance between neighbouring printed knuckles.

## Moving equipment enclosure

The moving tray is intentionally generic for this first hinge test rather than matching one exact PSU.

Closed-position envelope:

- moving tray footprint: **255 × 126 mm** (y=1.5…127.5 mm), intentionally raised 1 mm to clear the fixed hinge barrels
- tray front lip: **z = 12 mm**
- inside face of rear mounting plate: **z = 42 mm**
- rear plate thickness: **3 mm**
- usable cavity depth: approximately **30 mm**
- rear foot extends to **z = 60 mm**

The equipment plate includes repeated **16 × 4.2 mm slots** suitable for:

- M3 hardware with washers/nuts;
- printed standoffs;
- cable ties;
- cable-management clips.

Two larger slots near the top are intended for wiring/ribbon passthrough.

The lower rear foot beam and four diagonal ribs make the enclosure substantially deeper at the bottom than at the main mounting plate. In the closed/upright position this acts as a rear desk foot. The moving tray body starts at y=1.5 mm, leaving about 0.8 mm nominal clearance above the fixed hinge-barrel envelope.

## Assembly preview

Open:

`00_hinge_version_ASSEMBLY.scad`

The preview shows the moving enclosure opened approximately 72 degrees around the hinge rail.

`hinged_equipment_enclosure_at_angle(0)` is closed.

A positive angle rotates the equipment enclosure downward.

## Material

For the hinge prototype:

- **PETG is preferred** for the printed hinge knuckles because it is less brittle under repeated opening/closing.
- PLA is fine for a dimensional test, but repeated hinge loading may eventually crack a barrel or its root.

The 6 mm hinge rail should remain metal.

## Physical validation before printing four modules

Print **one fixed hinge template and one moving enclosure first** and check:

1. The corrected six boss holes and four locator clearances still fit the real panel.
2. A real 6 mm rail passes through all alternating 7.2 mm knuckles without forcing.
3. The knuckles rotate freely without excessive vertical play.
4. The lower hinge spine is stiff enough when the tray is loaded.
5. The tray clears the actual rear LED components when closed.
6. The 30 mm cavity is sufficient for the chosen PSU/controller.
7. The rear foot gives the intended desk stability.
8. Cables have enough service loop to open the tray without pulling connectors.

## Not yet finalised

This first prototype deliberately does **not** bake in a final top latch. Once the hinge spacing, closed tray depth and equipment clearances are physically confirmed, the next revision can add the preferred top closure:

- printed PETG snap latch;
- captive M3 thumbscrew/latch;
- or a small magnetic latch.

The hinge axis and corrected panel-template coordinates should remain unchanged when adding that latch.
