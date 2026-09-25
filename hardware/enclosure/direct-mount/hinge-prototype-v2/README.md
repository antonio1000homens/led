# Support-free 6 mm hinge prototype v2

This prototype isolates the mechanics for the hinged LED display before PSU/controller mounts, cable management and the final outer-end closures are added.

## Mechanical concept

The **equipment enclosure stays stationary**.

The **LED panel + verified mounting template is the moving leaf** and opens forward/down around a 6 mm horizontal rod.

The panel mounting geometry still comes directly from `mount_pattern_template()` in `../direct_mount_enclosure.scad`; the six mounting centres and locator clearances are unchanged.

Prototype defaults:

- LED/template lower edge: **20 mm above the floor**
- hinge rod: **6 mm**
- printed hinge bore: **7.2 mm**
- hinge barrel OD: **14 mm**
- hinge axis: **27 mm above the floor**
- floor-base forward extension: **25 mm**
- floor-base thickness: **5 mm**

The moving template has no full-width lower lip. Only local hinge roots are added behind its existing lower band.

## Middle enclosure prototype

This revision deliberately models the **two middle enclosure positions** of the final four-panel display.

The printable middle enclosure is identical for both centre panels, so print the same STL twice.

### Lower side walls, cable corridor and ventilation

Each middle enclosure now has a **3 mm lower side wall/cheek on both sides**.

The side cheeks:

- overlap the 5 mm floor base so they are part of the same printed solid;
- rise only to the **60 mm taper start**;
- span the full 40 mm-deep lower equipment cavity;
- contain a **7.2 mm pass-through bore** concentric with the continuous **6 mm hinge rod**.

Above 60 mm, both side planes remain open so HUB75 ribbons and power cables can pass directly between neighbouring panel cavities without being trapped by a full-height wall.

The rear plate provides the main enclosure structure.

The **entire lower 60 mm orthogonal section is now solid** with no ventilation openings.

Ventilation exists only in the upper tapered section, using a fine slotted grille:

- **3 mm-wide vertical openings**
- **8 mm pitch**
- therefore **5 mm solid ribs** between slots
- vent field starts 10 mm above the taper transition

This gives a mesh-like appearance and airflow without the fragile small intersections of a true printed mesh. It should also be easier for Bambu Studio to slice consistently.

The final two outer/end enclosures can later add one solid outside wall each; that is intentionally out of scope for this prototype.

### Lower orthogonal section + taper

The enclosure profile is now intentionally two-stage:

- from the floor to **60 mm high**: the rear wall stays vertical/orthogonal at the full **40 mm depth**
- above **60 mm**: the rear wall begins tapering
- at the top junction: the enclosure reaches **10 mm depth**

So the taper no longer starts at the base. The first 6 cm remains a conventional rectangular equipment cavity, which is better suited to the PSU/power-distribution area and lower cabling.

At the top, the enclosure now continues forward with a **full-width top link/roof** so the stationary enclosure closes against the rear of the LED-panel template rather than simply ending 10 mm behind it.

The top link stops **0.8 mm behind the template's rear surface** in the closed position. That gives a visible/structural closure while preserving hinge movement and print tolerance.

The top link is now constructed specifically to avoid Bambu Studio's **floating cantilever** detection. Its first printable roof layers overlap the already-printed tapered rear wall; successive layers grow forward until the final layers form the complete top cap at the LED-template junction.

This is intentionally different from the previous front-first hull, whose first roof layer began detached from the rear wall even though the finished roof looked like a printable ramp.

The lower 60 mm therefore provides a full-depth equipment zone while the upper enclosure becomes progressively slimmer.

## Print strategy

### Moving LED/template

`01_moving_panel_template_HINGE_TEST.scad`

Prints flat on the verified template face.

Expected envelope is approximately:

- **256 × 128 × 16 mm**

### Middle stationary enclosure/base

`02_middle_stationary_enclosure_HINGE_TEST.scad`

The enclosure prints **upright on its actual floor base**.

That orientation is intentional:

- the 5 mm base is a broad Z=0 contact patch;
- the lower 60 mm rear wall rises vertically at the full 40 mm depth and is completely solid;
- the 40→10 mm taper begins only above that point and remains self-supporting;
- only the upper tapered wall is ventilated, using fine 3 mm slits with 5 mm ribs;
- the top roof ramps forward to meet the LED-template rear plane;
- the hinge roots rise directly from the base;
- there is no horizontal floating lower shelf or unsupported top cantilever;
- the lower side cheeks support the base/rod region up to 60 mm;
- both left/right sides remain open above 60 mm for the cable corridor.

Expected envelope is approximately:

- **255 × 68 × 148 mm**

The 68 mm footprint is approximately 25 mm forward of the LED plane plus 40 mm rear depth and small offsets.

## Assembly preview orientation

The production geometry uses:

- X = panel width
- Y = panel height
- Z = enclosure depth

OpenSCAD normally treats **Z** as vertical, so raw assembly geometry can look as if the Y axis is inverted or sideways.

Assembly previews now apply a presentation-only **+90° X rotation**, mapping physical +Y to visual/world +Z.

This changes only the assembly view. Printable part coordinates and mounting geometry are unchanged.

## Assembly preview files

- `00_CLOSED_ASSEMBLY.scad` — one middle module closed
- `00_OPEN_ASSEMBLY.scad` — one middle module at 90°
- `00_TWO_MIDDLE_CLOSED_ASSEMBLY.scad` — both centre modules adjacent
- `00_TWO_MIDDLE_OPEN_ASSEMBLY.scad` — both centre modules opened to expose the cable-side geometry

The two-middle preview uses one continuous 6 mm rod across both adjacent hinge sets.

## Printable/generated files

- `01_moving_panel_template_HINGE_TEST.scad`
- `02_middle_stationary_enclosure_HINGE_TEST.scad`
- `stl/01_moving_panel_template_HINGE_TEST.stl`
- `stl/02_middle_stationary_enclosure_HINGE_TEST.stl`

The SCAD files are the source of truth. The STL files are checked in for direct Bambu Studio use.

`Enclosure / Validate` regenerates both STLs, compares their triangle geometry against the checked-in files, checks the intended print envelopes and parses all four assembly previews.

## Physical test sequence

1. Slice both generated STLs in Bambu Studio.
2. Confirm neither reports floating regions / floating cantilevers.
3. Print the moving template and reconfirm its fit on a real LED panel.
4. Print **two copies** of the middle stationary enclosure.
5. Place them one panel pitch apart and confirm the lower side cheeks align without collision.
6. Pass the 6 mm rod through the 7.2 mm side-wall bores and hinge barrels.
7. Check that cable bundles can still pass freely across the open side seam above the 60 mm side walls.
8. Fit the moving template(s) and verify the hinge motion.
9. Verify the enclosure/base remains stationary while the LED/template opens forward/down.
10. Check the 20 mm closed floor clearance with the real LED-panel thickness.
11. Check stability with the moving panel fully open.
12. Only then add the two outer-end enclosure variants, PSU/controller mounts, top retention/latch features and final cable guides.

PETG is preferred for repeated hinge testing; PLA is acceptable for a dimensional-only prototype.
