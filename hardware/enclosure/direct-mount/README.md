# Modular hinged direct-mount enclosure

Issue #133 makes this the canonical enclosure architecture.

The hinge mechanism follows the validated geometry restored in PR #119:
the **equipment enclosure/base is stationary**, while the **LED panel and its
mounting template form the moving leaf** and open forward/down through a full
0–90° service arc.

The newer modular equipment system remains in place behind that hinge: a
stationary universal base provides the bottom seat, a universal backplane drops
in vertically from above, and shallow detachable side guides align the edges.

## Architecture

```text
moving LED panel
   |
moving panel mounting template + local hinge roots
   |
6 mm metal hinge rail
   |
stationary equipment-side hinge knuckles
   |
reinforced hinge shelf + rearward support webs
   |
stationary universal equipment base
   |
base floor edge / backplane seat
   |
stationary universal equipment backplane
   |
   +-- detachable left side
   +-- detachable right side
   +-- future PSU adapter
   +-- future MatrixPortal adapter
   +-- future power/cable adapters
```

Every equipment base and every backplane remains interchangeable between all
four panel positions. Position- or component-specific behaviour belongs on
detachable side pieces or accessory adapters.

## Canonical printable parts

| Wrapper | Purpose |
| --- | --- |
| `parts/01_panel_hinge_template_PRINT_1.scad` | **Moving** LED/panel mounting template with local hinge roots |
| `parts/02_hinged_equipment_base_PRINT_1.scad` | **Stationary** universal equipment base, hinge knuckles/support webs/guard and open backplane seat |
| `parts/03_universal_equipment_backplane_PRINT_1.scad` | Stationary top-down removable equipment plate with generic M3 adapter bosses |
| `parts/04_left_equipment_side_PRINT_1.scad` | Detachable left perimeter guide |
| `parts/05_right_equipment_side_PRINT_1.scad` | Detachable right perimeter guide |

Matching canonical STL meshes are versioned under `stl/` and must be regenerated whenever a production SCAD changes.

## Panel mounting geometry

The six physically corrected brass insert centres remain:

- X = **7.9 / 128.0 / 248.1 mm**
- Y = **7.9 / 120.1 mm**

The four moulded-locator clearance centres remain:

- X = **26.704 / 229.296 mm**
- Y = **12.0 / 116.0 mm**
- clearance diameter = **10 mm**

## Restored PR #119 hinge

The canonical hinge now preserves the validated mechanical arrangement rather
than only its clearance numbers:

- metal rail: **6.0 mm**
- printed bore: **7.2 mm**
- barrel OD: **14 mm**
- moving panel/template lower edge: **20 mm above the stationary floor**
- hinge axis: **y=27 mm, z=16 mm**
- closed moving-template back to barrel clearance: **7 mm**
- moving panel/template knuckles: **34–60, 92–118, 166–194 mm**
- stationary equipment knuckles: **62–90, 136–164, 196–220 mm**
- moving template uses **local hinge roots only**, with no full-width lower lip
- stationary hinge roots use **rearward-sloping webs that terminate at the hinge shelf**
- each stationary root has a **3 mm local pad** joining its barrel to the web
- a **2 mm full-width stationary lower hinge guard** sits behind the barrel with
  **0.8 mm radial clearance**
- service/mechanical opening range: **0–90°**

The panel/template rotates forward/down. The equipment base, removable backplane
and electronics stay stationary.

## Top-down backplane

The stationary backplane installs from above and lowers vertically until its
plain lower edge rests on the base floor edge. The base contains no width-spanning
retaining rail, ramp, lip, or captive channel, leaving the lower interior open
for equipment and cabling. The detachable side pieces provide shallow perimeter
guides with 0.4 mm nominal clearance; they are fitted after the backplane and
can be removed to lift it out for service.

In a joined row, install side guides only at the two outside edges; neighboring
base and backplane pin/socket features mate across internal seams at the 256 mm
panel pitch. This avoids overlapping duplicate side walls. Glue is not part of
normal assembly.

## Universal accessory interface

Every backplane carries the same M3-ready boss grid:

- X = **32 / 80 / 128 / 176 / 224 mm**
- Y = **48 / 80 / 112 mm**
- boss OD = **8 mm**
- boss height = **5 mm**
- through-hole = **3.4 mm**

PSU, MatrixPortal and future electronics should use detachable adapter plates.

## Side alignment

The base and backplane expose complementary pin/socket features on their left
and right edges so identical neighbouring modules self-align.

- pin diameter: **4.0 mm**
- socket diameter: **4.7 mm**
- nominal engagement: **4 mm**

These features provide alignment/retention, not the primary structural load.

## Assembly previews

- `schematics/00_hinged_enclosure_ASSEMBLY.scad` — panel open to 90°
- `schematics/00_hinged_enclosure_CLOSED_ASSEMBLY.scad` — panel closed

## STL generation and validation

Regenerate the checked-in manufacturing STLs with:

```bash
python hardware/enclosure/direct-mount/scripts/generate_stls.py
```

Run the mechanical validator with:

```bash
python hardware/enclosure/direct-mount/scripts/validate_enclosure.py
```

CI regenerates all five canonical parts, verifies they match the checked-in
STLs, checks mesh health and floating-layer proxies, verifies base/backplane
fit, then holds the **equipment enclosure stationary** and checks the **moving
panel/template** and 6 mm rod for volumetric interference at 0, 15, 30, 45, 60,
75 and 90°. It also checks the hinge-shelf/rail contracts and neighboring-module
clearance.

During design/iteration, Windsor Slicer can be invoked explicitly using the repository-root
`.windsor-slicer.yaml` and the real Bambu Studio H2D profile. GitHub Actions does **not** run Bambu Studio or generate `.3mf` files.

## Physical acceptance order

1. Print one moving panel hinge template and one stationary equipment base.
2. Confirm the real 6 mm rail fits and the **panel/template** rotates freely from 0–90° while the equipment base stays fixed.
3. Confirm the stationary lower guard and rearward hinge support webs never touch the moving panel.
4. Print one universal backplane and verify top-down insertion, base-edge seating, and upward removal.
5. Print both side pieces and verify pin/socket engagement and perimeter alignment.
6. Verify two identical stationary equipment assemblies align side-by-side.
7. Fit representative M3 hardware/adapters to the boss grid.
8. Only then print the remaining modules.

PETG remains preferred for repeated hinge testing.
