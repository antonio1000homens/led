# Modular 6 mm rail hinge enclosure

This directory contains the modular hinged enclosure introduced by issue #133.

It reuses the corrected LED-panel mounting geometry from
`../direct_mount_enclosure.scad`, but the moving enclosure is no longer one
large print. The moving assembly is split into independently printable,
interchangeable parts:

```text
fixed LED-panel template
        |
        | 6 mm metal hinge rail
        v
universal hinge/base
        |
        | lateral slide
        v
universal equipment backplane
        |
        +-- detachable left side
        +-- detachable right side
        +-- PSU adapter (future/separate)
        +-- MatrixPortal adapter (future/separate)
        +-- other accessory adapters
```

The **base and backplane are identical for every panel position**. Position- or
equipment-specific behaviour belongs on detachable sides or accessory adapters,
not in the main enclosure geometry.

## Source of truth

The editable parametric source is:

```text
hinge_version.scad
```

Do not manually edit STL meshes.

The fixed panel-side hinge still derives its six panel mounting points and
moulded-locator clearances from the validated direct-mount source.

## Printable entrypoints

| File | Purpose |
| --- | --- |
| `08_mount_pattern_template_HINGE_PRINT_1.scad` | Fixed LED-panel template and fixed hinge knuckles |
| `11_hinged_equipment_base_PRINT_1.scad` | Universal moving hinge/base with slide rail |
| `12_universal_equipment_backplane_PRINT_1.scad` | Universal slide-in equipment plate |
| `13_left_equipment_side_PRINT_1.scad` | Detachable left end/retainer |
| `14_right_equipment_side_PRINT_1.scad` | Detachable right end/retainer |

`11_hinged_equipment_enclosure_PRINT_1.scad` is retained only as a deprecated
compatibility entrypoint. It no longer represents a complete monolithic
equipment enclosure.

The modular STLs are generated from these wrappers on demand by OpenSCAD,
repository CI, or Windsor Slicer. This avoids keeping stale experimental binary
STLs as a second source of truth.

## Hinge geometry

The proven concealed hinge dimensions are preserved:

- physical hinge rail: **6.0 mm diameter**
- printed rail bore: **7.2 mm**
- printed barrel outside diameter: **13 mm**
- hinge axis: **y = 11.5 mm, z = 10.5 mm**
- fixed knuckles:
  - x = 36–60 mm
  - x = 92–118 mm
  - x = 166–194 mm
- moving/base knuckles:
  - x = 62–90 mm
  - x = 136–164 mm
  - x = 196–220 mm

The centre panel screw continues to have the wider service gap around
x = 118–136 mm.

### Support-free sweep relief

The moving base still has the internal relief needed for the concealed hinge to
rotate. The original rectangular relief stopped abruptly at the pivot line and
Bambu Studio identified the returning wall as a floating cantilever.

The current relief:

1. keeps the required full opening below the hinge pivot;
2. then closes gradually over **9.5 mm** of installed Y;
3. makes the front wall grow back progressively instead of appearing on one
   unsupported print layer.

This change preserves the 6 mm hinge geometry while allowing the standalone base
to pass real Bambu Studio validation without supports.

## Section 1: universal hinge/base

The base contains only the mechanical functions that every module needs:

- moving hinge knuckles and 7.2 mm rail passage;
- fixed-knuckle clearance pockets;
- concealed hinge sweep clearance;
- a broad bottom/desk-foot strip;
- the support-free backplane slide rail;
- left/right self-mating alignment connectors.

It deliberately does **not** contain:

- the full equipment plate;
- permanent side walls;
- PSU-specific mounting holes;
- MatrixPortal-specific mounting holes;
- a left/middle/right panel identity.

This means the base can be printed by itself for a cheap hinge/rotation test.

## Section 2: universal slide-in backplane

The backplane inserts laterally into the base. Either end can be left open while
installing it; the corresponding detachable side piece then closes that end and
acts as the positive slide-out retainer.

### Rail profile

The rail is a **one-sided captive dovetail/open-wall rail**, not a rectangular
roofed T-slot.

The base rail is constructed from bed-connected walls:

- front rail wall begins at **z = 32 mm**;
- rear rail wall begins at **z = 46 mm**;
- front retaining lip shifts rearward progressively between
  **y = 22.5 mm and y = 31 mm**;
- narrow neck reaches approximately **y = 33 mm**.

The backplane has the complementary enlarged lower head and narrow stem.

Nominal FDM clearance is **0.4 mm per exposed mating face**.

The important design property is that no flat ceiling is created above a
captive rail cavity. The retaining lip grows progressively in the base print
orientation, so the rail remains captive without recreating the
floating-region problem.

### Retention

The backplane is not glued to the base.

Normal retention comes from:

1. the captive rail profile, which prevents the plate pulling directly away
   from the base; and
2. the detachable end/side pieces, which close the lateral slide path.

## Universal accessory mount pattern

Every backplane carries the same generic M3-ready boss grid.

Current boss centres:

- X = **32 / 80 / 128 / 176 / 224 mm**
- Y = **48 / 80 / 112 mm**

Boss geometry:

- boss outside diameter: **8 mm**
- boss height behind plate: **5 mm**
- through-hole diameter: **3.4 mm**

This is intentionally not a MatrixPortal or PSU footprint. Component-specific
hardware should use a small adapter/carrier fixed to whichever subset of these
universal points is appropriate.

The same backplane can therefore move between panel positions or change purpose
without being reprinted.

## Backplane ventilation and cable passages

The universal backplane includes:

- rounded upper ventilation slots:
  - 24 × 5 mm
  - X = 56 / 128 / 200 mm
  - Y = 64 / 96 mm
- rounded lower cable/ribbon passages:
  - 20 × 6 mm
  - X = 64 / 176 mm
  - Y = 36 mm

These openings avoid the universal boss grid and the slide rail.

## Side-to-side alignment

Both the base and backplane use a self-mating pin/socket scheme so identical
modules can sit next to each other.

Connector dimensions:

- locating pin diameter: **4.0 mm**
- socket diameter: **4.7 mm**
- nominal pin length: **4 mm**
- nominal socket depth: **4 mm**

Each edge has one pin role and one socket role. The pattern is reversed on the
opposite edge, so:

```text
right edge of module A <-> left edge of identical module B
```

No separate male/female main enclosure is required.

The pins are alignment/retention features only; they are not intended to carry
the full structural load.

### Base connectors

The base's two connector features are both kept inside the first **4 mm floor
band** so the horizontal pins are connected to the print from their first
layers.

They are separated in rear depth rather than vertical height:

- A feature around z = **24 mm**
- B feature around z = **52 mm**

This placement was selected after Windsor Slicer correctly identified the
earlier higher horizontal peg as a floating cantilever.

### Backplane connectors

Backplane side connectors are located around:

- A: y = **56 mm**
- B: y = **104 mm**
- z ≈ **44 mm**

Local pads reinforce the plate around these features.

## Separate side pieces

The left and right enclosure sides are separate printable parts. They:

- close the equipment cavity;
- mate with both the base connector pair and the backplane connector pair;
- act as end-stops for the lateral backplane rail;
- can be replaced independently.

Only the side pieces may need position-specific variants in future.

Examples of future side variants that can reuse the exact same base/backplane:

- plain outside end;
- U-shaped cable-pass-through side;
- MatrixPortal button/USB service side;
- power-cable/grommet side.

## Assembly previews

Open:

```text
00_hinge_version_ASSEMBLY.scad
```

for the moving modular assembly opened approximately 72 degrees.

Open:

```text
00_hinge_version_CLOSED_ASSEMBLY.scad
```

for the closed-position inspection.

The preview renders the pieces separately so the base, backplane and sides can
be visually distinguished.

## Windsor Slicer models

`.windsor-slicer.yaml` exposes:

```text
modular-hinge-base
universal-equipment-backplane
left-equipment-side
right-equipment-side
```

The required validation profile is:

```text
Bambu Studio: v02.08.02.61
Machine:      Bambu Lab H2D 0.4 nozzle
Process:      0.20mm Standard @BBL H2D
Filament:     Bambu PLA Basic @BBL H2D
```

During issue #133 implementation, all four parts were generated from one
immutable repository revision and returned:

```text
ready_for_print = true
categories      = []
fatal_categories = []
```

No printer job is started by this validation.

## Repository geometry validation

The normal enclosure validator now runs:

```bash
python hardware/enclosure/direct-mount/scripts/validate_enclosure.py
```

and includes
`scripts/validate_hinge_version_stls.py`.

The modular validator:

- renders all four modular printable entrypoints;
- checks non-empty, watertight, positive-volume meshes;
- requires one connected printable shell per part;
- runs the same coarse floating-layer/island proxy used by hinge-v2;
- checks that installed base and backplane do not intersect;
- checks base/fixed-template hinge sweep at representative service angles;
- renders both open and closed assembly previews.

Bambu Studio/Windsor Slicer remains the final authority for slicer-specific
floating-region and support diagnostics.

## Recommended print/test order

Do not print four complete enclosures first.

1. **Base only**
   - print one `11_hinged_equipment_base_PRINT_1`;
   - insert the real 6 mm metal rail;
   - mate it with one fixed hinge template;
   - verify free rotation and panel-screw access.

2. **Backplane only**
   - print one universal backplane;
   - inspect the dovetail tongue and universal boss grid.

3. **Rail fit**
   - slide the backplane laterally into the base;
   - confirm the fit is firm but hand-serviceable;
   - confirm it traverses the complete rail without binding or excessive play.

4. **Side interfaces**
   - print the two side pieces;
   - confirm pin/socket engagement with both base and backplane;
   - confirm the installed sides prevent the backplane sliding out.

5. **Neighbour test**
   - use two base/backplane sets to confirm identical right/left module
     interfaces mate without a special middle enclosure.

6. Only after the above succeeds should the remaining full-size parts be
   printed.

## Material

- **PETG is preferred** for the hinge/base and repeated side connector use.
- PLA is suitable for early dimensional coupons/prototypes.
- The 6 mm hinge rail remains metal.

## Physical validation still required

Automated geometry and Bambu validation do not prove FDM tolerances on the
physical printer.

Before accepting four-module production use, physically confirm:

- real 6 mm rail fit and rotation;
- 0.4 mm rail clearance on the actual printer/filament;
- pin/socket insertion and retention;
- two identical neighbouring modules align correctly;
- side pieces retain the slide-in backplane;
- M3 hardware/adapters fit the universal boss pattern;
- LED-panel cables remain clear through the full service angle;
- the complete loaded backplane does not cause excessive base/hinge flex.
