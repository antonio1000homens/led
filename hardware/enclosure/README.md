# LED enclosure CAD

The project is committed to the **modular hinged direct-mount enclosure** tracked by issue #133. This is the single supported enclosure architecture.

The hinge mechanism follows the validated geometry restored in PR #119:
the **equipment enclosure/base is stationary**, while the **LED panel and its
mounting template form the moving leaf** and open forward/down through a full
0–90° service arc.

The newer modular equipment system remains in place behind that hinge: a
stationary universal base contains a recessed rear locating groove, and the
universal backplane/enclosure drops vertically into that groove from above.
The backplane now carries a **54 mm clear-depth universal equipment zone**.
Only the lower U-channel insertion section is smaller; immediately above the
guides the shell uses one identical full-width Y/Z profile for the complete
256 mm length. That makes the long X dimension suitable as the print-vertical
axis. The deep section returns toward the panel near the top and finishes with a
**10 mm flat upper wall** parallel to the LED panel. Ventilation uses long
**horizontal slots** through the deep rear wall. The backplane reuses all three
existing top-row panel screw positions as aligned closure fasteners, so no
rotating tab or local top cutout is required.

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
lower 40 mm-depth U-channel insertion section
   |
full-width 54 mm enclosure profile with constant X cross-section
   |
horizontal rear-wall ventilation
   |
short return ramp
   |
10 mm flat upper wall flush with panel
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
| `parts/03_universal_equipment_backplane_PRINT_1.scad` | Top-down removable enclosure backplane, oriented with its 256 mm length vertical for printing, with a breakaway insertion-tongue support |
| `parts/04_left_equipment_side_PRINT_1.scad` | Detachable left end wall matching the lower insertion section, constant full-depth zone and upper return |
| `parts/05_right_equipment_side_PRINT_1.scad` | Detachable right end wall matching the lower insertion section, constant full-depth zone and upper return |

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
outer side now carries a hinge-style rod support with the same **14 mm OD** and
**7.2 mm clearance bore** as the main hinge barrels. The outer section remains
capped at the rail endpoint so the rod cannot escape axially; from that endpoint
the support becomes a hollow sleeve around the rod and continues to the nearest
hinge barrel (**X=34 mm** on the left and **X=220 mm** on the right). This removes
the previous exposed solid-plug appearance while keeping the rod retained.

## Top-down removable backplane

The base/backplane interface uses a **recessed groove at the rear edge of the
base** plus two structural side guides. The centre groove is 2 mm deep with
0.4 mm nominal clearance around the 3 mm backplane edge. Each side guide is
**50 mm high × 5 mm wide** and grows directly from the base. The lower 50 mm of
the backplane is stepped inward by 5 mm per side plus 0.4 mm running clearance;
above the guide towers it returns to the normal full width.

The guide towers are deliberately thickened toward the **inside** of the
enclosure. Their self-mating pin/socket junctions are carried on that interior
structure, so module-to-module and end-panel connections are hidden from the
outside. The rear exterior plane remains clean.

The removable backplane/enclosure installs from directly above:

1. lower the narrowed 50 mm backplane foot between the two 5 mm side guides;
2. continue downward into the rear groove until the backplane reaches the
   positive 2 mm-deep seat;
3. the full-width shoulder above the guides then sits over the tower tops;
4. fit the detachable outer side/end piece where required.

The universal backplane keeps the existing lower guide interface but is now
designed around side-on vertical printing:

- lower guide/insertion zone retains the original **40 mm** depth and narrowed
  width required by the U-channel capture;
- immediately above the 50 mm guide section, the shell switches to the
  **full service width** and keeps the same Y/Z profile across the complete
  256 mm X length;
- main equipment zone: **54 mm clear depth**;
- full-depth vertical region: **84 mm high**, preserving 4 mm total clearance
  around the PSU's 80 mm dimension;
- return ramp: **4 mm high**, repeated identically across X;
- final upper wall: **10 mm high**, flat and parallel to the LED panel;
- stationary enclosure top: **148 mm**, matching the front-panel height;
- ventilation: long **horizontal 3 mm slots** on a 9 mm pitch through the
  full-depth rear wall;
- lower insertion wall, return ramp and final 10 mm top wall remain solid;
- rear cable/ribbon slots remain absent;
- three closure-hole X positions: **7.9 / 128.0 / 248.1 mm**;
- closure-hole installed Y: **140.1 mm**;
- closure-hole diameter: **4.5 mm**, identical to the panel mounting holes.

These three holes are derived directly from the existing measured top-row panel
mounting coordinates, so the enclosure and panel stay aligned from one source
of truth. Longer screws pass through the stationary backplane into the existing
panel mounting locations and act as removable closure fasteners. The three
closure screws must be removed or loosened before opening the hinged panel.

The upper module/end-plate alignment **solid** remains entirely below the 75 mm
ramp start. Its vertical release slot is a void that extends 15 mm into the ramp,
allowing the removable backplane to lift past an end plate without bringing any
solid connector geometry into the clamp clearance zone.

The full-depth section carries the accessory mounting grid. Horizontal
ventilation slots are cut through its rear wall, while the lower insertion
section, return ramp and final 10 mm flat upper wall remain solid. Rear cable/ribbon through-slots remain intentionally absent.

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
- Y = **60 / 124 mm** (two rows, 10 mm inside the lower/upper edges of the 84 mm full-depth wall)
- boss OD = **7 mm**
- boss height = **4 mm**
- blind M3 clearance hole = **3.4 mm**, stopping before the external rear skin

PSU, MatrixPortal and future electronics should use detachable adapter plates.

For the measured ~110 × 80 × 37 mm PSU, the full-width ~255 × 84 × 54 mm
equipment region leaves ample horizontal room, 2 mm above/below the 80 mm
dimension when centred, and 17 mm of depth clearance. The rear shell profile is
continuous across X above the lower guide/insertion section. Where a 4 mm boss overlaps
the PSU footprint, 50 mm of usable depth remains, still 13 mm beyond the PSU.

## Side alignment

The base guide towers expose complementary pin/socket features on their left
and right edges so identical neighbouring modules self-align. These junctions
sit on the **inside/cavity-facing portion of the 50 mm guide towers**. End-panel
mating sockets are blind from the inside, leaving the outside side faces solid.

- pin diameter: **4.0 mm**
- socket diameter: **4.7 mm**
- nominal printed pin length: **3 mm**; joined-module engagement is approximately **2 mm** after the 1 mm module-edge gap

These features provide alignment/retention, not the primary structural load.

## Assembly previews

Single-module service views:

- `schematics/00_hinged_enclosure_ASSEMBLY.scad` — one module open to 90°
- `schematics/00_hinged_enclosure_CLOSED_ASSEMBLY.scad` — one module closed

Complete four-module display views:

- `schematics/00_complete_enclosure_OPEN_ASSEMBLY.scad` — all four modules open to 90°
- `schematics/00_complete_enclosure_CLOSED_ASSEMBLY.scad` — all four modules closed

The complete views use the current self-mating modular geometry: internal seams do
not carry detachable side retainers; only the two outside edges use end pieces.

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
the 54 mm universal deep zone, the **constant X profile and horizontal vents**,
the final 10 mm flat top wall, the three-screw top closure, capped hollow rail sleeves, lower usable
equipment volume, and neighboring-module clearance.

During design/iteration, Windsor Slicer can be invoked explicitly using the repository-root
`.windsor-slicer.yaml` and the real Bambu Studio H2D profile. GitHub Actions does **not** run Bambu Studio or generate `.3mf` files.

## Physical acceptance order

1. Print one moving panel hinge template and one stationary equipment base.
2. Confirm the three top closure screws align and secure the closed panel; then
   remove/loosen them and confirm the real 6 mm rail lets the **panel/template**
   rotate freely from 0–90° while the equipment base stays fixed.
3. Confirm the stationary lower guard and rearward hinge support webs never touch the moving panel.
4. Print one universal backplane and verify the narrowed lower 50 mm slides
   between both 5 mm guide towers with 0.4 mm running clearance, then seats
   2 mm into the rear groove and removes upward.
5. Verify the backplane returns to full width above the guide towers and the
   towers prevent lateral movement.
6. Verify the main equipment zone provides 54 mm clear depth across the usable
   width, the horizontal rear-wall vents are clean, and the final 10 mm wall is
   flat/parallel to the panel with all three top-row closure holes aligned.
   Confirm there are still no rear cable/ribbon slots.
7. Print both side pieces and verify the hidden pin/socket engagement, solid
   exterior faces, profile alignment, and that each capped rod retainer remains
   hollow around the 6 mm rod up to the nearest hinge barrel.
8. Verify two identical stationary equipment assemblies align side-by-side
   using the hidden guide-tower junctions.
9. Fit representative M3 hardware/adapters to the **inside** lower boss grid
   and confirm the outside rear skin remains unbroken.
10. Only then print the remaining modules.

PETG remains preferred for repeated hinge testing.

### Backplane print stability

The backplane now prints **side-on with the 256 mm X dimension vertical**. Above
the guide section the shell has the same Y/Z profile on every structural layer,
so the 54 mm deep wall, short return ramp and top wall build without the old
under-ramp support forest.

The lower insertion tongue is intentionally narrower than the main shell so it
can slide into the base U-channels. With the left end on the bed, that tongue
starts about **1.6 mm above the bed**. The manufacturing wrapper therefore adds
one **1.0 mm-thick breakaway strip** under the tongue, extending through the
guide-height section and overlapping the tongue by **0.4 mm**. It is the only
print-only support geometry.

The support exists only in `03_universal_equipment_backplane_PRINT_1.stl`;
`universal_equipment_backplane()` remains support-free for installed assembly
and interference checks. After printing, snap/cut the low strip away from the
insertion tongue and clean the contact line.

For the H2D production candidate use **Bambu PETG Basic @BBL H2D 0.4 nozzle**,
**0.20mm Standard @BBL H2D**, and the **Textured PEI Plate**.
