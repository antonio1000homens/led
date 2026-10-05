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
**23.5 mm flat upper wall** parallel to the lifted LED panel. Ventilation uses **horizontal slots on the upper return ramp and lower
transition shoulder**. The long rear wall remains solid for the accessory-boss
mounting grid. The backplane reuses all three
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
solid rear boss-mount wall
   |
horizontal vents on lower transition + upper return ramp
   |
23.5 mm flat upper wall flush with lifted panel
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
| `parts/03_universal_equipment_backplane_PRINT_1.scad` | Top-down removable enclosure backplane, oriented with its 256 mm length vertical for printing; the STL is clean and uses slicer-generated support under the insertion tongue |
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
- moving panel/template lower edge and hinge centreline: **40 mm above the stationary floor**
  (**20 mm higher** than the previous installation)
- hinge axis: **y=40 mm, z=16 mm**
- closed moving-template back to barrel clearance: **7 mm**
- moving panel/template knuckles: **34–60, 92–118, 166–194 mm**
- stationary equipment knuckles: **62–90, 136–164, 196–220 mm**
- moving template uses the existing **local hinge roots only**, with no
  full-width lower lip; the moving/front-panel geometry is intentionally
  unchanged and remains outside this reinforcement change
- stationary hinge roots use **rearward-sloping webs that terminate at the hinge shelf**
- each stationary root has a **3 mm local pad** joining its barrel to the web
- a **2 mm full-width stationary lower hinge guard** sits behind the barrel with
  **0.8 mm radial clearance**
- service/mechanical opening range: **0–90°**

The panel/template rotates forward/down. The equipment base, removable backplane
and electronics stay stationary. The raised hinge also allows the stationary
base floor to extend **20 mm farther toward the front** without entering the
0–90° moving-panel sweep. The extension remains a flat structural floor; the
previous shallow front reinforcement ramp has been removed. The moving
template/front-panel geometry is unchanged; its print wrapper removes the
40 mm installation offset.

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
0.6 mm nominal clearance around the 3 mm backplane edge. Each side guide is
**40 mm high × 5 mm wide** and grows directly from the base. The lower 40 mm of
the backplane is stepped inward by 5 mm per side plus 0.6 mm running clearance;
above the guide towers it returns to the normal full width.

**Base/backplane compatibility:** the 40 mm guide height and 40 mm narrowed
backplane foot are a matched interface. A backplane built to this geometry will
not fully seat in the earlier 50 mm-guide base: its full-width shoulder contacts
the final ~10 mm of the old towers before the lower edge reaches the 2 mm rear
seat, leaving the assembly standing roughly 10 mm high. When adopting this
revision, print/use the matching `02_hinged_equipment_base_PRINT_1` and
`03_universal_equipment_backplane_PRINT_1` together.

The guide towers are deliberately thickened toward the **inside** of the
enclosure. Their self-mating pin/socket junctions are carried on that interior
structure, so module-to-module and end-panel connections are hidden from the
outside. The rear exterior plane remains clean.

Each guide root is now additionally reinforced in two directions without
changing the backplane slot:

- the existing **16 mm-high junction support** continues forward until it
  overlaps the stationary hinge plate/guard, making one continuous side load
  path;
- each guide also has a **26 mm-footprint triangular floor gusset**, spanning
  the full 5 mm guide width and rising to 75% of the 40 mm guide height. The
  wedges sit ahead of the insertion slot and overlap the guide's front lip;
- both 1.2 mm capture lips of each 40 mm side guide now continue **inward toward
  the centre as backup backplane support**, stopping at the outer edge of the
  first continuous-rib socket (around X=51.4 mm on the left and X=204.6 mm on
  the right). The resulting first rib gaps remain open with the existing
  0.6 mm rib clearance, so a damaged end tongue does not leave the backplane
  supported only at the extreme enclosure edge;
- the rear of the guide gains a **10 mm-deep triangular buttress at the base**,
  tapering back to the normal guide rear face at the top of the 40 mm rail;
- a low **full-width rear shelf** extends the stationary base to the same rear
  plane as those buttresses; the left and right **1.2 mm-thick upright
  guardrails now continue from each side guide to the nearest outer rib**
  (about 58.5 mm each), with a small overlap into the X=64 / 192 mm rib tabs;
  the centre span stays open apart from the existing X=128 mm tab;
- the **3 mm backplane slot and 0.6 mm running clearance remain unchanged**.

The removable backplane/enclosure installs from directly above:

1. lower the shortened 40 mm backplane foot between the two 5 mm side guides;
2. continue downward into the rear groove until the backplane reaches the
   positive 2 mm-deep seat;
3. the 2 mm rear groove seats the sliding tongue independently. Each of the
   three **continuous 24 mm ribs now extends 1 mm below the nominal Y=0.5 mm
   floor reference**. This compensates for the observed ~1 mm physical assembly
   lift without changing the stationary base. The stationary guardrail enters a channel carved through the
   front of the rib: 0.6 mm tongue clearance, 1.2 mm guardrail thickness and
   0.6 mm clearance to the solid rear rib wall. The low rear shelf is pocketed
   through the complete rear shelf/base-seat band beneath the rib footprint,
   while the #170 outer rails/tabs are deliberately retained inside those
   sockets. All three rib feet expose bilateral lower/front entry relief so a
   stationary tab cannot catch on a closed half of a rib during top-down
   insertion. The centre tab uses two
   short low root spurs across the centre-rib socket so it remains manifold with
   the surrounding shelf without closing the full centre span;
4. the full-width shoulder above the guides then sits over the tower tops while
   the low rear shelf and rib rear faces terminate on the same flush plane;
5. fit the detachable outer side/end piece where required.

The universal backplane keeps the existing lower guide interface but is now
designed around side-on vertical printing:

- lower guide/insertion zone retains the original **40 mm** depth and narrowed
  width required by the U-channel capture;
- immediately above the 40 mm guide section, the shell switches to the
  **full service width** and keeps the same Y/Z profile across the complete
  256 mm X length;
- the fragile tongue-to-deep-shell junction is reinforced by **three continuous
  rear ribs**, centred at X = **64 / 128 / 192 mm**. Each keeps the existing
  **24 mm print-Z taper** but now runs as one solid object from the reinforced
  shoulder to **Y=-0.5 mm**, providing 1 mm of rib-only seating compensation
  below the nominal Y=0.5 mm base reference. The existing **18 mm-wide guardrail
  channel** is subtracted through the lower/front portion of that solid rib,
  preserving the 0.6 mm tongue clearance, 1.2 mm guardrail and 0.6 mm rear
  clearance. Because the whole rib retains the existing gradual X/print-Z taper,
  Windsor/Bambu Studio does not detect a floating region;
- main equipment zone: **54 mm clear depth**;
- structural full-depth rear-wall region: **92 mm high** from the 40 mm guide
  top to the return ramp;
- the reinforced lower shoulder occupies the first **8 mm**, leaving **84 mm
  of genuinely usable full-depth height above it**: 80 mm PSU height + 4 mm
  total vertical clearance;
- return ramp: **12 mm high**, repeated identically across X and carrying the restored top ventilation;
- final upper wall: **23.5 mm high**, flat and parallel to the lifted LED panel;
  the raised enclosure provides enough extra height to restore the 12 mm return
  ramp while retaining the full PSU envelope;
- stationary enclosure top: **168 mm**, matching the lifted front-panel height;
- ventilation: **three rows** of seven **24 mm × 1 mm rounded horizontal slots**
  on the reinforced lower transition plus **four rows** of seven matching slots
  across the restored **12 mm upper return ramp**;
- the full-depth rear wall stays solid for the M3 boss grid;
- lower insertion wall and final 23.5 mm top wall remain solid;
- rear cable/ribbon slots remain absent;
- three closure-hole X positions: **7.9 / 128.0 / 248.1 mm**;
- closure-hole installed Y: **160.1 mm**;
- closure-hole diameter: **4.5 mm**, identical to the panel mounting holes.

These three holes are derived directly from the existing measured top-row panel
mounting coordinates, so the enclosure and panel stay aligned from one source
of truth. Longer screws pass through the stationary backplane into the existing
panel mounting locations and act as removable closure fasteners. The three
closure screws must be removed or loosened before opening the hinged panel.

The upper module/end-plate alignment remains entirely below the 75 mm ramp
start, but now uses only **compact local seam bosses** around the seated tab/slot
instead of the previous long diagonal edge arms. Each boss is 10 mm high and
tapers across the 8 mm edge width from the native 3 mm rear wall to the local
connector thickness, which keeps the side-on print self-supporting. The vertical
release slot still extends 15 mm into the ramp so the removable backplane can
lift past an end plate without bringing solid connector geometry into the clamp
clearance zone.

The full-depth **rear wall** carries the accessory mounting grid and remains
solid around that grid except for the blind boss holes. Ventilation is confined
to the reinforced lower transition shoulder and the restored 12 mm upper return
ramp. The lower insertion section and final 23.5 mm flat upper wall remain solid. Rear cable/ribbon through-slots remain intentionally absent.

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
- Y = **62.5 / 82.5 / 102.5 mm** (three rows; outer rows 22 mm inside the full-depth-region edges, plus a centred row)
- boss OD = **7 mm**
- boss height = **4 mm**
- blind M3 clearance hole = **3.4 mm**, stopping before the external rear skin

PSU, MatrixPortal and future electronics should use detachable adapter plates.

For the measured ~110 × 80 × 37 mm PSU, the full-width ~255 × 84 × 54 mm
equipment region leaves ample horizontal room, 2 mm above/below the 80 mm
dimension when centred, and 17 mm of depth clearance. The rear shell profile is
continuous across X above the lower guide/insertion section. Where a 4 mm boss overlaps
the PSU footprint, 50 mm of usable depth remains, still 13 mm beyond the PSU.

## Full-height detachable end caps and side alignment

The detachable left/right sides are now full-height **end caps** rather than
enclosure-only plates:

- the **lower/base section** follows the current base only from the triangular
  guide reinforcement rearward; the old forward floor extension is deliberately
  omitted, so the visible front edge follows the triangle diagonal;
- the base's existing complementary **4.0 mm pin / 4.7 mm socket** interface is
  reused unchanged by the end cap, so each side locks to the same A/B junctions
  used when two bases mate;
- the **upper/enclosure section** follows the deep region and return ramp, then
  stops at the ramp end; there is **no shallow top leg** up to the LED-board edge
  because the enclosure/backplane itself closes that final gap;
- the retained upper section still adds an inward return that reaches
  **10 mm beyond the actual enclosure edge**;
- the existing 0.4 mm side clearance plus 0.5 mm backplane inset means that
  return is 10.9 mm from the side's inner face to its inner end;
- the return is carved around the live base/backplane geometry and has a
  dedicated keep-out around the upper module-to-module connector and its
  vertical release path, so it cannot consume the connector region.

The external 3 mm end face is continuous only across the retained base/upper
profile: it does not extend forward beyond the base triangle and does not extend
above the enclosure return ramp. The internal 10 mm return is still locally
removed where the current enclosure/module connector needs space.
These features provide end coverage and alignment/retention, not the primary
structural load between modules.

## Left-side C14 mains inlet

The detachable **left** equipment side includes a portrait snap-in opening for
the fused/switched IEC C14 inlet. It is integrated into the new full-height end
cap and its hidden relief cuts through the 10 mm upper return locally, leaving
the intended thin snap land at the exterior face.

- measured body/cutout: **44 mm high × 27 mm wide** in portrait orientation;
- FDM allowance: **0.10 mm per edge** → 44.2 × 27.2 mm printed opening;
- measured body intrusion: **30 mm** behind the inside face;
- conservative rotated flange keep-out: **50 mm high × 30.5 mm wide**;
- current side wall: **3.0 mm**;
- hidden relief leaves a **1.4 mm** snap land while the rest of the side stays
  at the current 3 mm thickness;
- hidden relief margin: **2 mm** around the opening.

Placement is derived from the current `universal_deep_y1`,
`enclosure_front_z` and `universal_deep_rear_z` values. In the current model
the 44 × 27 × 30 mm occupied body envelope sits well above the hinge rod
retainer/sleeve; validation checks both the full body envelope against the rod
sleeve and against the stationary enclosure core. Later base/enclosure changes
therefore fail CI if they consume that clearance.

If the real inlet has a 2 mm or thicker latch shoulder, tune
`c14_snap_panel_t` after the physical fit test rather than enlarging the measured
44 × 27 mm exterior opening.

Physical acceptance: the flange sits flat, the spring lugs clear and catch
behind the inner edge, the inlet cannot pull back out without compressing the
lugs, and the 3 mm side remains intact outside the local hidden relief.

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

CI regenerates all seven canonical parts, verifies they match the checked-in
STLs, checks mesh health and floating-layer proxies, verifies base/backplane
fit and top-down insertion, then holds the **equipment enclosure stationary**
and checks the **moving panel/template** and 6 mm rod for volumetric interference
at 0, 15, 30, 45, 60, 75 and 90°. It also checks the rear-groove location,
the 54 mm universal deep zone, the **constant X profile and horizontal vents**,
the final 23.5 mm flat top wall, the three-screw top closure, capped hollow rail sleeves, lower usable
equipment volume, and neighboring-module clearance.

During design/iteration, Windsor Slicer can be invoked explicitly using the repository-root
`.windsor-slicer.yaml` and the real Bambu Studio H2D profile. GitHub Actions does **not** run Bambu Studio or generate `.3mf` files.

## Physical acceptance order

1. Print one moving panel hinge template and one stationary equipment base.
2. Confirm the three top closure screws align and secure the closed panel; then
   remove/loosen them and confirm the real 6 mm rail lets the **panel/template**
   rotate freely from 0–90° while the equipment base stays fixed.
3. Confirm the stationary lower guard and rearward hinge support webs never touch the moving panel.
4. Print one universal backplane and verify the narrowed lower 40 mm slides
   between both 5 mm guide towers with 0.6 mm running clearance, then seats
   2 mm into the rear groove and removes upward.
5. Verify the backplane returns to full width above the guide towers and the
   towers prevent lateral movement. Inspect all three tapered rear reinforcement
   ribs and confirm the **gap behind the sliding tongue is visibly present**.
   Check that the left/right upright guardrails run continuously from the side
   guides to the first outer rib on each side, and that all three 1.2 mm tabs
   enter their rib channels freely with 0.6 mm clearance to the tongue and
   0.6 mm clearance to the rear rib foot/wall. Confirm the 12 mm-wide rear foot
   continues below each rail to Y=2.5 mm without closing the channel. The centre
   span must remain open and the slide-facing surface must remain flat/unmodified.
6. Verify the main equipment zone provides 54 mm clear depth across the usable
   width and **84 mm clear height above the reinforced shoulder** (80 mm PSU +
   4 mm clearance). Confirm all three narrow rounded vent rows are clean on the
   reinforced lower transition and all four rounded rows are clean across the
   restored 12 mm upper return ramp; the full-depth rear boss wall should remain solid.
   Confirm the final 23.5 mm wall is flat/parallel to the panel with all three
   top-row closure holes aligned and there are still no rear cable/ribbon slots.
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
so the 54 mm deep wall, 12 mm return ramp and top wall build without the old
under-ramp support forest.

The lower insertion tongue is intentionally narrower than the main shell so it
can slide into the base U-channels. With the left end on the bed, that tongue
starts above the bed. The manufacturing STL now leaves this region **clean**:
no sacrificial pedestal is fused into the CAD.

Use the repository-root Windsor Slicer manifest with the
`petg-supported` variant. It selects **Bambu Lab H2D 0.4 nozzle**,
**0.20mm Standard @BBL H2D**, **Bambu PETG Basic @BBL H2D 0.4 nozzle**,
**Textured PEI Plate**, and **tree-auto support**. The separate
`support-free-check` variant deliberately leaves support off so unsupported
regions remain visible during diagnostics.
