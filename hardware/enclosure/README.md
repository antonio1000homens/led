# LED enclosure CAD

The project is committed to the **modular hinged direct-mount enclosure** tracked by issue #133. This is the single supported enclosure architecture.

The hinge mechanism follows the validated geometry restored in PR #119:
the **equipment enclosure/base is stationary**, while the **LED panel and its
mounting template form the moving leaf** and open forward/down through a full
0–90° service arc.

The newer modular equipment system remains in place behind that hinge: a
stationary universal base contains a recessed rear locating groove, and the
universal backplane/enclosure drops vertically into that groove from above.
The lower equipment section stays vertical at the full 40 mm depth to
**75 mm**, ramps more steeply to the shallow rear wall by **120 mm**, then
continues vertically to the full **148 mm panel height**. The backplane now
reuses all three existing top-row panel screw positions as aligned closure
fasteners, so no rotating tab or local top cutout is required.

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
recessed rear top-down groove
   |
vertical lower backplane (40 mm cavity depth)
   |
solid upper ramp (75 -> 120 mm)
   |
28 mm shallow vertical wall to full panel height
   |
three aligned top-row closure screw holes
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
| `parts/02_hinged_equipment_base_PRINT_1.scad` | **Stationary** universal equipment base, hinge knuckles/support webs/guard and recessed rear backplane groove |
| `parts/03_universal_equipment_backplane_PRINT_1.scad` | Top-down removable vertical/tapered enclosure backplane with generic M3 adapter bosses |
| `parts/04_left_equipment_side_PRINT_1.scad` | Detachable left outer wall following the 40 -> 10 mm taper |
| `parts/05_right_equipment_side_PRINT_1.scad` | Detachable right outer wall following the upper taper |

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

The 6 mm hinge rail is defined from **X=10 mm to X=246 mm**. Each detachable
outer side now includes an integrated solid coaxial end stop that reaches the
corresponding rod end. The stops do not extend inward beyond the rail endpoints:
the left stop ends at X=10 mm, leaving 24 mm to the first hinge barrel at X=34,
and the right stop begins at X=246 mm, leaving 26 mm from the final barrel end
at X=220. Fit the rod before installing both end pieces; the end pieces then
prevent axial escape of the rail.

## Top-down tapered backplane

The base/backplane interface uses a **recessed groove at the rear edge of the
base** plus two structural side guides. The centre groove is 2 mm deep with
0.4 mm nominal clearance around the 3 mm backplane edge. Each side guide is
**30 mm high × 5 mm wide** and grows directly from the base. The lower 30 mm of
the backplane is stepped inward by 5 mm per side plus 0.4 mm running clearance;
above the guide towers it returns to the normal full width.

The guide towers are deliberately thickened toward the **inside** of the
enclosure. Their self-mating pin/socket junctions are carried on that interior
structure, so module-to-module and end-panel connections are hidden from the
outside. The rear exterior plane remains clean.

The removable backplane/enclosure installs from directly above:

1. lower the narrowed 30 mm backplane foot between the two 5 mm side guides;
2. continue downward into the rear groove until the backplane reaches the
   positive 2 mm-deep seat;
3. the full-width shoulder above the guides then sits over the tower tops;
4. fit the detachable outer side/end piece where required.

The enclosure keeps the proven lower depth while making the top closure simpler:

- lower section: **40 mm cavity depth**, vertical/orthogonal;
- taper begins: **75 mm above the floor**;
- taper reaches the shallow wall: **120 mm**;
- shallow upper wall: **28 mm high**, vertical and parallel to the LED panel;
- stationary enclosure top: **148 mm**, matching the front-panel height;
- three closure-hole X positions: **7.9 / 128.0 / 248.1 mm**;
- closure-hole installed Y: **140.1 mm**;
- closure-hole diameter: **4.5 mm**, identical to the panel mounting holes;
- rear enclosure ventilation: **none**. The lower vertical wall, sloped ramp
  and upper vertical wall are all solid.

These three holes are derived directly from the existing measured top-row panel
mounting coordinates, so the enclosure and panel stay aligned from one source
of truth. Longer screws pass through the stationary backplane into the existing
panel mounting locations and act as removable closure fasteners. The three
closure screws must be removed or loosened before opening the hinged panel.

The upper module/end-plate alignment **solid** remains entirely below the 75 mm
ramp start. Its vertical release slot is a void that extends 15 mm into the ramp,
allowing the removable backplane to lift past an end plate without bringing any
solid connector geometry into the clamp clearance zone.

The lower vertical section carries the accessory mounting grid. The rear
backplane has **no ventilation slots and no cable/ribbon through-slots**; the
lower vertical wall, ramp and upper vertical wall are all solid apart from the
intentional mounting/alignment holes.

In a joined row, side pieces are installed only at the two outside edges;
neighboring guide-tower pin/socket features mate across internal seams.
HUB75/power cabling must route through these open internal module-to-module
sides rather than through the rear backplane.
Glue is not part of normal assembly.

## Universal accessory interface

Every backplane carries the same M3-ready boss grid on its **inside face**.
The bosses project into the equipment cavity and use blind holes; at least
1.2 mm of solid material remains on the external rear face, so no boss or screw
hole is visible from outside:

- X = **32 / 80 / 128 / 176 / 224 mm**
- Y = **18 / 36 / 54 mm** (kept entirely on the vertical lower section)
- boss OD = **8 mm**
- boss height = **5 mm**
- blind M3 clearance hole = **3.4 mm**, stopping before the external rear skin

PSU, MatrixPortal and future electronics should use detachable adapter plates.

## Side alignment

The base guide towers expose complementary pin/socket features on their left
and right edges so identical neighbouring modules self-align. These junctions
sit on the **inside/cavity-facing portion of the 30 mm guide towers**. End-panel
mating sockets are blind from the inside, leaving the outside side faces solid.

- pin diameter: **4.0 mm**
- socket diameter: **4.7 mm**
- nominal printed pin length: **3 mm**; joined-module engagement is approximately **2 mm** after the 1 mm module-edge gap

These features provide alignment/retention, not the primary structural load.

## Assembly previews

- `schematics/00_hinged_enclosure_ASSEMBLY.scad` — panel open to 90°
- `schematics/00_hinged_enclosure_CLOSED_ASSEMBLY.scad` — panel closed

## STL generation and validation

Regenerate the checked-in manufacturing STLs with:

```bash
python hardware/enclosure/scripts/generate_stls.py
```

Run the mechanical validator with:

```bash
python hardware/enclosure/scripts/validate_enclosure.py
```

CI regenerates all five canonical parts, verifies they match the checked-in
STLs, checks mesh health and floating-layer proxies, verifies base/backplane
fit and top-down insertion, then holds the **equipment enclosure stationary**
and checks the **moving panel/template** and 6 mm rod for volumetric interference
at 0, 15, 30, 45, 60, 75 and 90°. It also checks the rear-groove location,
upper taper, the **fully solid rear enclosure with no ventilation slots**, the
three-screw top closure, integrated rail end stops, lower usable equipment
volume, and neighboring-module clearance.

During design/iteration, Windsor Slicer can be invoked explicitly using the repository-root
`.windsor-slicer.yaml` and the real Bambu Studio H2D profile. GitHub Actions does **not** run Bambu Studio or generate `.3mf` files.

## Physical acceptance order

1. Print one moving panel hinge template and one stationary equipment base.
2. Confirm the three top closure screws align and secure the closed panel; then
   remove/loosen them and confirm the real 6 mm rail lets the **panel/template**
   rotate freely from 0–90° while the equipment base stays fixed.
3. Confirm the stationary lower guard and rearward hinge support webs never touch the moving panel.
4. Print one universal backplane and verify the narrowed lower 30 mm slides
   between both 5 mm guide towers with 0.4 mm running clearance, then seats
   2 mm into the rear groove and removes upward.
5. Verify the backplane returns to full width above the guide towers and the
   towers prevent lateral movement.
6. Verify the 40 mm-deep section remains vertical to 75 mm, the solid ramp
   reaches the shallow wall by 120 mm, and the final 28 mm wall reaches the
   full 148 mm panel height with **no ventilation or rear cable slots** and all
   three top-row closure holes aligned to the panel.
7. Print both side pieces and verify the hidden pin/socket engagement, solid
   exterior faces, taper alignment, and that the integrated end stops terminate
   the 6 mm rod at X=10/246 without touching either hinge barrel.
8. Verify two identical stationary equipment assemblies align side-by-side
   using the hidden guide-tower junctions.
9. Fit representative M3 hardware/adapters to the **inside** lower boss grid
   and confirm the outside rear skin remains unbroken.
10. Only then print the remaining modules.

PETG remains preferred for repeated hinge testing.

### Backplane print stability

The manufacturing wrapper for `03_universal_equipment_backplane_PRINT_1.stl`
includes five **print-only sacrificial anti-tip stabilisers** restored from the
earlier print-stability revision. The installed backplane geometry is unchanged.

Each stabiliser uses a **12 × 38 mm** transverse bed pad, **1.0 mm** thick, with
paired gussets rising **20 mm** on both sides of the upright wall. The gussets
join through **0.8 mm breakaway necks** so they can be flexed/cut away after the
print. Their purpose is to resist nozzle loads in both directions and prevent
the tall backplane detaching or falling during the print.

After printing, remove all five stabilisers and clean the lower locating edge
before fitting the backplane into its base/groove.

For the H2D production candidate use **Bambu PETG Basic @BBL H2D 0.4 nozzle**,
**0.20mm Standard @BBL H2D**, and the **Textured PEI Plate**.
