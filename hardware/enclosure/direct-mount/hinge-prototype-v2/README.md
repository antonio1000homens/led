# Support-free 6 mm hinge prototype v2

This prototype now covers the complete four-panel stationary enclosure set: one controller end, two identical middle enclosures and one power-cable end.

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
- hinge axis depth: **16 mm behind the LED/template front plane**
- closed plate-to-barrel clearance: **7 mm**
- floor-base forward extension: **25 mm**
- floor-base thickness: **5 mm**

The moving template has no full-width lower lip. Only local hinge roots are added behind its existing lower band.

The hinge axis is deliberately set farther behind the moving plate than in the earlier prototype. The 2 mm plate back now has **7 mm clearance to the front of the 14 mm hinge barrel**. The stationary knuckle is now supported locally from the full-width lower hinge guard rather than by a large diagonal web running back to the rear floor edge. A compact tapered rib rises from the guard into the barrel's bottom tangent, keeping the first barrel layers printable while leaving the moving plate's forward/downward rotation corridor clear.

Every stationary enclosure now also includes a **2 mm full-width lower hinge guard**. The guard rises from the 5 mm floor/base to the hinge centreline and sits immediately behind the 14 mm hinge-barrel envelope, leaving **0.8 mm clearance** to the moving hinge. It closes the exposed low opening behind the LED/template when the panel is shut, while the open left/right side planes above it remain available for hinge sweep and inter-panel cabling.

## Enclosure variants

The four-panel display now uses three stationary enclosure prints:

- **left/controller end** — one outer closure wall, integrated MatrixPortal S3 standoffs and an exposed service opening for the USB/buttons edge;
- **middle** — completely open left/right side planes above the floor base for hinge sweep and inter-panel cabling; print this part **twice**;
- **right/power end** — one solid outer closure wall plus a round rear cable-entry hole for a snap grommet.

All three share the same hinge, rear profile, upper ventilation and top landing geometry.

### Middle enclosure

### Open cable sides and ventilation

The middle enclosure has **no fixed left/right side walls above the 5 mm floor base**.

That open-side geometry is required for two reasons:

- the LED/template must be able to swivel through its hinge arc without colliding with stationary side walls;
- HUB75 ribbons and power cables need to pass directly between neighbouring panel cavities.

The rear plate provides the main enclosure structure.

A thin stationary **hinge guard plate spans the complete module width** across the lower front opening. It starts with a 0.5 mm overlap into the floor/base for print continuity, rises to the hinge centreline and sits 0.8 mm behind the barrel's rear-most surface. Short bridge pads exist only at the stationary knuckle segments, so the guard is structurally tied to each stationary hinge while the alternating moving-knuckle spans remain unobstructed.

The guard is shared by the controller end, both middle enclosures and the power end. It does **not** recreate the removed side walls: the left/right side planes remain open above the floor base for panel motion and cable routing.

The **entire lower 60 mm orthogonal section is now solid** with no ventilation openings.

Ventilation exists only in the upper tapered section, using a fine slotted grille:

- **3 mm-wide vertical openings**
- **8 mm pitch**
- therefore **5 mm solid ribs** between slots
- vent field starts 10 mm above the taper transition

This gives a mesh-like appearance and airflow without the fragile small intersections of a true printed mesh. It should also be easier for Bambu Studio to slice consistently.

### Left/controller end

The left end wall is placed primarily **outside the LED/template footprint** so it closes the display without blocking the moving panel's swing.

The MatrixPortal S3 is mounted parallel to the LED plane inside the lower 60 mm orthogonal cavity. Its PCB position is based on the existing validated MatrixPortal dimensions and M2.5 mounting-hole offsets from `direct_mount_enclosure.scad`.

Rather than individual button holes, the outer wall has one generous service opening exposing the complete short MatrixPortal edge. This gives direct access to USB-C and the hardware controls while allowing tolerance for the real PCB/connectors.

Four integrated **8 mm standoffs with 2.8 mm M2.5 clearance holes** support the controller from the flat lower rear wall.

### Right/power end

The right enclosure gets a solid outer closure wall, also positioned primarily outside the LED/template footprint.

A rear cable-entry hole is cut through the orthogonal lower rear wall:

- prototype hole diameter: **14 mm**
- location: low on the rear of the right-end enclosure
- intended use: pass the incoming power cable through a snap grommet

The **14 mm value is only a prototype default**. Before the final print, set `power_grommet_hole_d` to the panel cut-out diameter specified by the actual grommet.

Both outer walls include a **7.2 mm hinge-rod pass-through** aligned to the continuous 6 mm hinge rail.

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

- **256 × 128 × 23 mm**

### Stationary enclosure/base variants

- `02_middle_stationary_enclosure_HINGE_TEST.scad`
- `03_left_controller_end_enclosure_HINGE_TEST.scad`
- `04_right_power_end_enclosure_HINGE_TEST.scad`

All stationary variants print **upright on their actual floor base**.

That orientation is intentional:

- the 5 mm base is a broad Z=0 contact patch;
- the lower 60 mm rear wall rises vertically at the full 40 mm depth and is completely solid;
- the 40→10 mm taper begins only above that point and remains self-supporting;
- only the upper tapered wall is ventilated, using fine 3 mm slits with 5 mm ribs;
- the top roof ramps forward to meet the LED-template rear plane;
- the stationary hinge roots use compact guard-to-barrel support ribs rather than large rearward floor braces, leaving the moving plate's sweep path clear;
- the 2 mm full-width hinge guard grows continuously from the same base and remains behind the hinge sweep;
- there is no horizontal floating lower shelf or unsupported top cantilever;
- both left/right side planes remain open above the floor base so the moving LED/template can swing freely and cables can cross between modules.

Expected envelope is approximately:

- middle: **255 × 68 × 148 mm**
- left/controller end: **~258 × 68 × 148 mm**
- right/power end: **~258 × 68 × 148 mm**

The end variants are slightly wider because the outer closure wall sits primarily outside the 256 mm LED/template footprint.

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
- `00_FOUR_PANEL_CLOSED_ASSEMBLY.scad` — controller end + two middle + power end, closed
- `00_FOUR_PANEL_OPEN_ASSEMBLY.scad` — all four moving LED/templates opened

The four-panel preview uses one continuous 6 mm rod across the complete enclosure set and shows a reference MatrixPortal PCB at the controller end.

## Printable/generated files

- `01_moving_panel_template_HINGE_TEST.scad`
- `02_middle_stationary_enclosure_HINGE_TEST.scad`
- `stl/01_moving_panel_template_HINGE_TEST.stl`
- `stl/02_middle_stationary_enclosure_HINGE_TEST.stl`
- `03_left_controller_end_enclosure_HINGE_TEST.scad`
- `stl/03_left_controller_end_enclosure_HINGE_TEST.stl`
- `04_right_power_end_enclosure_HINGE_TEST.scad`
- `stl/04_right_power_end_enclosure_HINGE_TEST.stl`

The SCAD files are the source of truth. The STL files are checked in for direct Bambu Studio use and are regenerated/compared by `Enclosure / Validate`; a PR fails if any STL is stale relative to its SCAD entrypoint.

The validator checks all four printable variants, their intended print envelopes, the floating-layer proxy for stationary enclosures, and all six assembly previews.

## Physical test sequence

1. Slice both generated STLs in Bambu Studio.
2. Confirm neither reports floating regions / floating cantilevers.
3. Print the moving template and reconfirm its fit on a real LED panel.
4. Print one controller end, **two middle enclosures**, and one power end.
5. Assemble them on the nominal 256 mm panel pitch and insert the continuous 6 mm hinge rod.
6. Verify all four LED/templates sweep freely and the outer walls remain clear of the moving panels.
7. Check that cable bundles pass freely through the open middle seams.
8. Fit the MatrixPortal to the controller-end standoffs and verify USB/button access through the service opening.
9. Test-fit the chosen power-cable grommet in the rear hole before routing the cable.
10. Verify the enclosure/base remains stationary while the LED/templates open forward/down.
11. With each LED/template closed, confirm the full-width lower hinge guard blocks direct access into the cavity behind the panel.
12. Open and close each panel through the full **0–90° service arc** and confirm the moving plate does not contact the stationary hinge barrel, rear support web or guard.
13. Confirm the closed moving plate has the intended **7 mm gap to the front of the stationary hinge barrel** and the guard remains at least 0.8 mm behind the barrel envelope.
14. Check the 20 mm closed floor clearance with the real LED-panel thickness.
15. Check stability with all moving panels open.

PETG is preferred for repeated hinge testing; PLA is acceptable for a dimensional-only prototype.
