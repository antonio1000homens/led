# 6 mm rail hinge prototype

This directory is an **experimental alternative** to the production direct-mount backplane/lid arrangement.

It does not replace the validated production files under `../parts/` and `../stl/`.

## Concept

The fixed half is derived from the corrected `08_mount_pattern_template_PRINT_1` geometry, so it uses the exact current panel mounting and locator coordinates from `../direct_mount_enclosure.scad`.

The moving half is a deeper equipment enclosure/tray. A continuous **6 mm metal rail** passes through alternating printed hinge knuckles on both halves and becomes the hinge pin.

With four modules side-by-side, the intention is that a single 1000 mm × 6 mm rail can pass through the internal lower knuckles across the display. The hinge axis stays inside the 256 × 128 mm panel footprint, so the hinge does not add height below the enclosure.

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
  - alternating fixed hinge knuckles sit on local reinforcement pads inside the lower template band;
  - a small internal PETG snap latch is integrated into the upper template band.

- `11_hinged_equipment_enclosure_PRINT_1.scad`
- `stl/11_hinged_equipment_enclosure_PRINT_1.stl`
  - complementary hinge knuckles;
  - 30 mm internal tray depth between the front lip and equipment mounting plate;
  - full-size slotted equipment mounting plate for PSU/controller/cable ties;
  - full-width lower wiring zone, then an 8 mm-per-side taper toward the top;
  - mirrored U-shaped cable notches, open toward the LED panel, for use as a middle enclosure;
  - full-width rear foot beam and diagonal ribs at the lower edge to increase desk footprint;
  - an internal catch pocket for the template-mounted snap latch.

## Hinge dimensions

- physical hinge rail: **6.0 mm diameter**
- printed hinge bore: **7.2 mm**
- printed hinge barrel outside diameter: **13 mm**
- hinge axis: **y = 16 mm, z = 8 mm** relative to the panel coordinate system
- complete 13 mm hinge-barrel envelope: **y = 9.5…22.5 mm**, fully inside the 0…128 mm panel footprint

The 7.2 mm bore deliberately preserves the same 0.6 mm radial clearance currently used for the 6 mm reinforcement bars.

The knuckles alternate:

### Fixed template

- x = 20–48 mm
- x = 90–118 mm
- x = 160–188 mm

These positions deliberately avoid the panel screw columns at x = 7.9 / 128 / 248.1 mm.

### Moving enclosure

- x = 50–88 mm
- x = 120–158 mm
- x = 190–228 mm

This leaves approximately 2 mm axial clearance between neighbouring printed knuckles.

## Moving equipment enclosure

The moving tray is intentionally generic for this first hinge test rather than matching one exact PSU.

Closed-position envelope:

- lower moving-tray footprint: **255 mm wide × 126 mm high** (y=1.5…127.5 mm)
- hinge axis at **y=16 mm**, contained inside this footprint
- lower **52 mm** wiring zone remains full-width
- above that zone, each side tapers inward by **8 mm**, giving a **239 mm** top width
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

The two larger wiring/ribbon slots in the rear equipment plate are now kept in the **lower wiring zone** instead of near the top.

Because this specific tray is intended to be a **middle enclosure**, both lower side walls contain matching **U-shaped cable notches**. Each notch is open toward the LED-panel/front side rather than forming a closed hole. Panel-to-panel power and HUB75/data cables can therefore remain connected to the fixed LED panels while the moving tray swings down and away from them.

The prototype notch is **30 mm high × 22 mm deep** with **4 mm rounded rear corners**. It begins immediately above the lower perimeter wall, preserving the hinge/base structure underneath. The upper enclosure simultaneously tapers inward by **8 mm per side** above the 52 mm lower wiring zone, increasing the gap between neighbouring enclosures where no cable width is needed.

The taper and notch dimensions are parameters in `hinge_version.scad` (`lower_wiring_zone_h`, `upper_side_inset`, `side_cable_notch_y`, `side_cable_notch_depth`, and `side_cable_notch_corner_r`) so they can be adjusted after a physical cable-fit test.

The lower rear foot beam and four diagonal ribs make the enclosure substantially deeper at the bottom than at the main mounting plate. In the closed/upright position this acts as a rear desk foot. The 6 mm rail hinge now sits inside the lower enclosure perimeter instead of extending below it.

## Internal snap latch

The fixed template now includes a small prototype snap latch at **x = 96 mm**, positioned away from the panel screw columns. The latch consists of:

- a short riser from the template;
- a **12 mm wide PETG cantilever tongue**;
- a rounded detent at the free end.

The moving enclosure has a matching shallow internal catch pocket behind its front lip. As the enclosure closes, the rounded detent flexes the tongue slightly toward the LED panel, then snaps behind the lip into the pocket.

The latch is entirely inside the enclosure envelope and does not add height or an external protrusion. PETG is recommended for this feature because the tongue is intended to flex repeatedly.

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
4. The local hinge-root pads are stiff enough when the tray is loaded.
5. The internal hinge rotates without fouling the LED panel or lower enclosure wall.
6. The internal snap latch engages and releases without excessive force or permanent deformation.
7. The tray clears the actual rear LED components when closed.
8. The 30 mm cavity is sufficient for the chosen PSU/controller.
9. The rear foot gives the intended desk stability.
10. Power and HUB75/data cables sit comfortably in both 30 × 22 mm U-notches without being pinched.
11. Open the tray while panel-to-panel cables remain connected and verify that the U-notches disengage cleanly without pulling the cables.
12. Verify the 8 mm-per-side upper taper leaves useful clearance between neighbouring enclosures without interfering with the equipment mounted inside.

## Not yet finalised

The internal printed snap latch is now included as a **prototype**. Its engagement depth and release force should be confirmed on the first physical print before printing all four modules. If the printed latch proves too stiff or too loose, the latch dimensions can be tuned without moving the hinge axis or changing the corrected panel-template coordinates.
