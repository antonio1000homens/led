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
  - no integrated top latch/cantilever is present, keeping this part support-free when printed flat.

- `11_hinged_equipment_enclosure_PRINT_1.scad`
- `stl/11_hinged_equipment_enclosure_PRINT_1.stl`
  - complementary hinge knuckles;
  - 30 mm internal tray depth between the front lip and equipment mounting plate;
  - full-size slotted equipment mounting plate for PSU/controller/cable ties;
  - full-width lower wiring zone, then an 8 mm-per-side taper toward the top;
  - mirrored U-shaped cable notches, open toward the LED panel, for use as a middle enclosure;
  - continuous full-width sloped rear-foot gusset to increase desk footprint without a floating beam;
  - STL is exported on its side for printing: approximately **57.4 × 127 mm** bed footprint and **255 mm** print height;
  - no matching latch pocket is included in this print-first hinge prototype.

## Hinge dimensions

- physical hinge rail: **6.0 mm diameter**
- printed hinge bore: **7.2 mm**
- printed hinge barrel outside diameter: **13 mm**
- hinge axis: **y = 11.5 mm, z = 10.5 mm** relative to the panel coordinate system
- complete 13 mm hinge-barrel envelope: **y = 5…18 mm**, fully inside the enclosure/base footprint
- the nearest barrel surface is **4.5 mm inboard** from the enclosure's y=0.5 mm lower edge
- barrel Z envelope: **z = 4…17 mm**, entirely behind the 2 mm fixed template

The 7.2 mm bore deliberately preserves the same 0.6 mm radial clearance currently used for the 6 mm reinforcement bars.

The knuckles alternate:

### Fixed template

- x = 36–60 mm
- x = 92–118 mm
- x = 166–194 mm

### Moving enclosure

- x = 62–90 mm
- x = 136–164 mm
- x = 196–220 mm

Both halves now deliberately avoid **all lower critical X columns**:

- panel screws at x = 7.9 / 128 / 248.1 mm;
- moulded locator clearances at x = 26.704 / 229.296 mm.

The centre panel screw gets a deliberately wider **x=118…136 mm service gap** so neither hinge half blocks the screw head or screwdriver access. Normal adjacent knuckle gaps remain approximately 2 mm.

## Moving equipment enclosure

The moving tray is intentionally generic for this first hinge test rather than matching one exact PSU.

Closed-position envelope:

- the LED-facing moving rim starts at the **hinge axis y=11.5 mm** so it can rotate freely;
- a continuous lower apron continues down to the normal **y=0.5 mm** enclosure edge, so the closed base remains flush;
- only the apron’s internal LED-facing/front-lower quadrant is relieved for the hinge sweep; the rail and both knuckle sets stay behind the outer base silhouette;
- top remains at **y=127.5 mm**;
- the front rim closes at **z=2.6 mm**, only **0.6 mm behind the 2 mm fixed template**, so the base/enclosure read as flush when closed;
- the fixed hinge knuckles sit in front-entry pockets inside the moving enclosure rather than projecting outside it;
- lower **46 mm** wiring/equipment zone remains full-width;
- above that zone, each side tapers inward by **8 mm**, giving a **239 mm** top width;
- lower equipment-plate depth: **z=42 mm**;
- upper equipment-plate depth: **z=28 mm**;
- the rear surface slopes continuously between those values, making the top about **14 mm shallower** than the bottom equipment zone;
- rear plate thickness: **3 mm**;
- usable cavity depth is approximately **39.4 mm at the lower zone** and **25.4 mm at the top**, measured from the 2.6 mm closing rim;
- rear foot still extends to **z=60 mm** at the bottom for desk stability.

The standalone moving-enclosure STL is intentionally **not** exported open-face-down. In that orientation the rear equipment plate would begin around 42 mm above the build plate and behave like a large ceiling/bridge. The print STL is rotated onto its left side instead, giving an approximately **57.4 × 127 mm** footprint and **255 mm** height. This keeps the equipment plate vertical while printing. The assembly SCAD files continue to use the normal physical orientation.

The hinge sweep relief also stops at the pivot line instead of cutting through the rear half of the lower wall, so the moving knuckles remain structurally tied into the lower apron. Fixed-knuckle locations still use their dedicated front-entry clearance pockets.

The equipment plate includes repeated **16 × 4.2 mm slots** suitable for:

- M3 hardware with washers/nuts;
- printed standoffs;
- cable ties;
- cable-management clips.

The two larger wiring/ribbon slots in the rear equipment plate are now kept in the **lower wiring zone** instead of near the top.

Dedicated ventilation is only added to the **upper tapered region** of the rear equipment plate. It uses rounded 24 × 5 mm slots on three rows (y=84 / 101 / 118 mm). There are **no dedicated ventilation openings in the lower wiring/base zone**, keeping the bottom stronger and less exposed.

Because this specific tray is intended to be a **middle enclosure**, both lower side walls contain matching **U-shaped cable notches**. Each notch is open toward the LED-panel/front side rather than forming a closed hole. Panel-to-panel power and HUB75/data cables can therefore remain connected to the fixed LED panels while the moving tray swings down and away from them.

The prototype notch is **30 mm high × 22 mm deep** with **4 mm rounded rear corners**. It begins immediately above the lower perimeter wall, preserving the hinge/base structure underneath. The upper enclosure simultaneously tapers inward by **8 mm per side** above the 46 mm lower wiring zone, increasing the gap between neighbouring enclosures where no cable width is needed.

The taper and notch dimensions are parameters in `hinge_version.scad` (`lower_wiring_zone_h`, `upper_side_inset`, `side_cable_notch_y`, `side_cable_notch_depth`, and `side_cable_notch_corner_r`) so they can be adjusted after a physical cable-fit test.

The lower rear foot is now a **continuous full-width sloped gusset** from the lower equipment plate to the 60 mm rear extent. The previous full-width beam began at z=54 mm while only four narrow ribs existed underneath it, which produced another large floating/unsupported start surface in Bambu Studio. The sloped gusset grows progressively instead. Above the lower wiring/equipment zone, both the side outline and the rear depth taper inward to reduce material and rear protrusion.

The 6 mm rail is now a **fully internal concealed hinge**. The barrel sits at y=5…18 mm and z=4…17 mm, entirely inside the moving enclosure/base envelope. The continuous lower apron reaches y=0.5 mm and remains intact behind the pivot, so the closed base stays flush. Only the front side of the pivot is relieved for the opening sweep. Fixed knuckles nest into matching front-entry pockets in the moving enclosure.

## Top closure

The integrated snap latch has been **removed from this prototype** because its cantilever was floating above the print bed when the fixed template was printed flat.

That keeps the fixed hinged template support-free in its intended print orientation.

After the hinge, closed clearance and equipment depth are physically confirmed, the top closure should be added as a **separate printable part** rather than fused into the template. Good candidates are:

- a small PETG clip that snaps over the two closed edges;
- a pivoting printed latch retained by an M3 screw;
- a captive thumbscrew latch;
- or a small magnetic catch.

This lets the template remain flat-printable and means the latch can be reprinted/tuned independently.

## Assembly preview

Open:

`00_hinge_version_ASSEMBLY.scad`

The preview shows the moving enclosure opened approximately 72 degrees around the hinge rail.

`hinged_equipment_enclosure_at_angle(0)` is closed. A separate `00_hinge_version_CLOSED_ASSEMBLY.scad` view is provided specifically to inspect the flush closed position and concealed hinge pockets.

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
5. The concealed edge hinge rotates through the required service angle without the moving shell fouling the fixed template.
6. Confirm the fixed template prints flat without supports or floating cantilevers.
7. The tray clears the actual rear LED components when closed.
8. The chosen PSU fits in the deeper lower zone and the controller fits within the shallower tapered upper zone.
9. The rear foot gives the intended desk stability.
10. Power and HUB75/data cables sit comfortably in both 30 × 22 mm U-notches without being pinched.
11. Open the tray while panel-to-panel cables remain connected and verify that the U-notches disengage cleanly without pulling the cables.
12. Verify both the 8 mm-per-side width taper and the 42→28 mm rear-depth taper leave useful clearance without interfering with mounted equipment.
13. Verify the upper-only ventilation pattern provides useful airflow while the lower base/wiring area remains solid.
14. Confirm the wider centre hinge gap leaves the lower-centre panel screw accessible with the actual screwdriver/bit you plan to use.

## Not yet finalised

The top closure/latch is intentionally deferred until the first physical hinge test. It should be implemented as a **separate support-free part**, so latch tuning does not require reprinting the fixed template.

