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

### Open cable sides

The middle enclosure does **not** have solid left or right walls.

Above the 5 mm floor base, both side planes are open so HUB75 ribbons and power cables can pass directly from one panel cavity into the next.

The sloping rear plate provides the main enclosure structure. The final two outer/end enclosures can later add one solid outside wall each; that is intentionally out of scope for this prototype.

### Taper

Requested equipment depth is implemented behind the LED plane as:

- **40 mm at the bottom**
- **10 mm at the top**

The rear plate therefore slopes continuously toward the LED as it rises.

The lower depth gives space for wiring/power hardware while the top stays much slimmer.

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
- the 40→10 mm rear taper rises gradually and is self-supporting;
- the hinge roots rise directly from the base;
- there is no horizontal floating shelf;
- both left/right cable sides remain open.

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
5. Place them one panel pitch apart and check that cable bundles can pass freely across the open side seam.
6. Fit the moving template(s) and insert the 6 mm rod.
7. Verify the enclosure/base remains stationary while the LED/template opens forward/down.
8. Check the 20 mm closed floor clearance with the real LED-panel thickness.
9. Check stability with the moving panel fully open.
10. Only then add outer-end walls, PSU/controller mounts, top retention/latch features and final cable guides.

PETG is preferred for repeated hinge testing; PLA is acceptable for a dimensional-only prototype.
