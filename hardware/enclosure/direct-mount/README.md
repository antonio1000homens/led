# Direct-mount LED enclosure

This is the current enclosure design for the four P4 HUB75 panels.

## Geometry

- 4 × nominal 256 × 128 mm LED panels
- 3 × standard printed backplanes + 1 × right-end backplane
- finished LED face: 1024 × 128 mm
- 2 × 1000 mm × 6 mm reinforcement bars
- no printed bezel or rail is allowed in front of the LED PCB

## Panel numbering and controller position

Panel numbering is fixed for assembly and wiring:

```text
Front / LED-face view

LEFT                                                        RIGHT
┌────────────┬────────────┬────────────┬────────────┐
│  Panel 1   │  Panel 2   │  Panel 3   │  Panel 4   │
│ controller │            │            │ right-end  │
└────────────┴────────────┴────────────┴────────────┘
     ↑
     MatrixPortal S3 is mounted on the rear of Panel 1

HUB75 data direction: MatrixPortal → Panel 1 → Panel 2 → Panel 3 → Panel 4
```

**Panel 1 is the leftmost panel when looking at the illuminated LED face from the front.** The `stl/04_matrixportal_mount_PRINT_1.stl` carrier attaches to the rear of Panel 1 / `backplane_1`. The MatrixPortal PCB is intentionally shifted to the left so its button/USB edge overhangs the Panel 1 side by about **10 mm**. Panel 4 is the rightmost panel and uses `stl/01b_backplane_right_end_PRINT_1.stl`.

When working from the rear of the assembled display, remember that the apparent left/right order is reversed relative to this front-view numbering. Connect the MatrixPortal HUB75 output to the input connector of Panel 1, then daisy-chain the panel outputs in numerical order through Panel 4.

## Measured P4 panel mounting pattern

The production backplane no longer derives its screw positions from the historical 160 × 80 mm P2.5 reference model.

A calibrated 1:1 ruler photograph of the real P4 panel, cross-checked against the supplied Kiri Engine scan, established the six-boss 3 × 2 layout. The **first printed 1:1 template** then showed the outer boss centres were **2 mm too close to every panel edge**. The first physical template moved the outer holes 2 mm inward from the scan/photo estimate. A subsequent fit showed that correction was **0.5 mm too far inward**, so the outer centres are now moved 0.5 mm back toward every panel edge.

The current production coordinates are:

| X (mm) | Y (mm) |
| ---: | ---: |
| 7.9 | 7.9 |
| 128.0 | 7.9 |
| 248.1 | 7.9 |
| 7.9 | 120.1 |
| 128.0 | 120.1 |
| 248.1 | 120.1 |

This gives:
- **7.9 mm current edge inset target** on all four sides;
- a centre mounting column at **x = 128.0 mm**;
- outer-column spacing of **120.1 mm** either side of centre;
- vertical row spacing of **112.2 mm**.

The production CAD uses **4.5 mm round through-holes** at these six centres. On the structural backplane, each mounting hole now has a **10 mm diameter rear screw well** that is **11 mm deep**, leaving only **5 mm of plastic** between the recessed screw head and the LED-panel boss. This substantially reduces the extra screw length required compared with passing through the full 16 mm backplane, and keeps normal screw heads below the rear surface so they do not interfere with the snap-on lid.

The 1:1 mounting template remains thin and does not reproduce these screw wells; its job is only to verify the six boss centres and locating-pin clearances. The revised template must still be physically rechecked before the structural backplane is accepted.

### Rear backplane footprint

Physical fitting indicates that the moulded **rear** of the LED module is approximately **1 mm smaller overall** than the nominal 256 × 128 mm front/illuminated envelope.

The CAD therefore keeps the nominal panel coordinate system and panel-to-panel pitch at **256 × 128 mm**, but the printed structural backplane is centred inside that envelope with:

- rear backplane footprint: **255 × 127 mm**;
- edge inset: **0.5 mm on all four sides**;
- nominal gap between adjacent rear backplanes: **1.0 mm** when the LED panel fronts remain on a 256 mm pitch.

Boss-hole and locator-clearance coordinates remain referenced to the nominal panel envelope, so shrinking the rear frame does **not** move the measured mounting centres.

The seam alignment tongues are extended across the 1 mm rear-frame gap so they retain the intended engagement in the neighbouring backplane socket. The recessed rear joiners remain centred on the nominal 256 mm panel seams.

This 255 × 127 mm rear footprint still requires a physical fit check against one real panel before printing the remaining backplanes.

### Moulded locating-pin clearance

The failed physical backplane fit also showed a protruding moulded locating pin entering one of the old four provisional P2.5-derived slots. Those old centres are therefore retained **only as locating-pin clearance positions**, not mounting points:

- X = **26.704 / 229.296 mm**
- Y = **12.0 / 116.0 mm**
- clearance diameter = **10.0 mm**

The screw holes and locating-pin clearances are intentionally different shapes so their purpose is obvious.

Print `stl/08_mount_pattern_template_PRINT_1.stl` first and verify all six brass inserts **and** the locating-pin clearances against the real panel before printing the remaining structural backplanes.

## Mechanical validation

The current enclosure validation is orchestrated by one repo script:

```bash
python hardware/enclosure/direct-mount/scripts/validate_enclosure.py
```

CI installs OpenSCAD plus the Python mechanical dependencies and then runs that command. The validator:

- renders every current production printable wrapper exactly once;
- compares each generated mesh with the checked-in manufacturing STL;
- validates the MatrixPortal carrier;
- renders assembly/reference CSG and SVG entrypoints;
- validates the active `hinge-prototype-v2/` print geometry, including a coarse floating-layer/island proxy;
- runs mesh-health and nominal assembly-interface checks.

The older `hinge-version/` experiment remains available for reference but is not part of default CI. Bambu Studio remains the final check for slicer-specific overhang/support diagnostics.

## 6 mm rail hinge prototype

An experimental clamshell/service-tray variant now lives under:

`hinge-version/`

This variant does **not** replace the production direct-mount parts. It reuses the same corrected panel boss and locator coordinates from `direct_mount_enclosure.scad`, but adds:

- a fixed version of the corrected 08 mounting template with alternating hinge knuckles along the bottom;
- a complementary moving equipment enclosure with the matching knuckles;
- a **6 mm metal rail** through 7.2 mm printed bores as the hinge pin;
- a 30 mm-deep equipment cavity with a universal M3/cable-tie slot grid;
- a deeper full-width lower foot for desk stability;
- an assembly preview showing the enclosure opening downward.

See `hinge-version/README.md` for dimensions and the physical validation sequence.

## Directory layout

The direct-mount enclosure is now separated by purpose:

- `direct_mount_enclosure.scad` — shared parametric source of truth.
- `parts/*_PRINT_*.scad` — thin printable-part entrypoints grouped away from the shared library.
- `stl/` — generated manufacturing meshes only; do not edit these by hand.
- `schematics/` — direct-mount detail/reference views (MatrixPortal and lid alignment).
- `../complete_enclosure/` — full four-panel assembly and front/back/side/top/bottom projections, as introduced by PR #102.
- `scripts/assembly_validation.json` and `scripts/validate_*.py` — machine-readable assembly intent and CI validation.
- `README.md` plus `docs/*.md` — physical-fit and validation documentation.

This keeps the files you send to the slicer separate from the editable CAD and from the assembly drawings.

## Printable parts

| File | Qty | Purpose |
| --- | ---: | --- |
| `stl/01_backplane_module_PRINT_3.stl` | 3 | Standard centred 255 × 127 mm rear structure on a 256 × 128 mm panel pitch, with seam alignment tongues |
| `stl/01b_backplane_right_end_PRINT_1.stl` | 1 | Rightmost 255 × 127 mm backplane; omits unused outer tongues/recess/insert pockets |
| `stl/02_module_joiner_PRINT_4.stl` | 3 sets | Each STL contains the two recessed seam straps needed for one panel seam, leaving the centre open for cables |
| `stl/03_rod_end_plug_PRINT_4.stl` | 4 | Retains both 1 m reinforcement bars at both ends |
| `stl/04_matrixportal_mount_PRINT_1.stl` | 1 | Removable MatrixPortal S3 carrier for the rear of Panel 1 / `backplane_1` |
| `stl/05_power_distribution_mount_PRINT_1.stl` | 1 | Removable universal fused 5 V distribution carrier |
| `stl/06_cable_clip_PRINT_8.stl` | 8 | M3 screw-down rear cable clips |
| `stl/07_mounting_slot_coupon_PRINT_1.stl` | 1 | Small fit test for slot / insert dimensions |
| `stl/08_mount_pattern_template_PRINT_1.stl` | 1 | Low-material 256 × 128 template to verify all six corrected brass-boss centres plus locating-pin clearances |
| `stl/09_centre_boss_desk_stand_PRINT_3.stl` | 2 | Separate centre-boss desk stands with a thinner 3 mm screw stack and 15 mm forward anti-tip toe |
| `stl/10_rear_lid_PRINT_4.stl` | 4 | Open-sided snap-on rear lids with ventilation slots and four dedicated round locking pegs |

All STLs are generated from `direct_mount_enclosure.scad`. Individual printable launchers are under `parts/`, validators/manifests under `scripts/`, and non-README mechanical notes under `docs/`.

### Complete enclosure assembly preview

Open `../complete_enclosure/00_complete_enclosure_ASSEMBLY.scad` to see the nominal assembled rear structure rather than a single printable part. It includes:

- Panels/backplanes 1–4 at x = 0, 256, 512 and 768 mm;
- the dedicated right-end backplane on Panel 4;
- all three recessed seam-strap sets, with the cable corridor left open;
- both 1000 × 6 mm reinforcement rods;
- the MatrixPortal carrier on Panel 1, including the simplified PCB reference and left-side service overhang;
- the power-distribution carrier on Panel 2;
- translucent guide planes at the three nominal panel seams.

The complete assembly file is **not** a printable component and does not replace `direct_mount_enclosure.scad`. The latter remains the shared parametric geometry source; the assembly file simply instantiates those modules at their nominal positions.

CI now validates the assembly placement explicitly. The backplane origins must remain on an exact **256 mm pitch**, all four must share the same Y/Z origin, the joiners must stay on their three nominal seam positions, and the electronics carriers must remain assigned to their intended panels. The existing overall-width and interference checks still run in addition to these placement checks.

### SVG / 2D projection views

The full assembly is a 3D object, so OpenSCAD cannot export `../complete_enclosure/00_complete_enclosure_ASSEMBLY.scad` directly as SVG. Use one of these dedicated 2D projection files instead:

- `../complete_enclosure/00_complete_enclosure_FRONT_VIEW_SVG.scad`
- `../complete_enclosure/00_complete_enclosure_BACK_VIEW_SVG.scad`
- `../complete_enclosure/00_complete_enclosure_LEFT_SIDE_VIEW_SVG.scad`
- `../complete_enclosure/00_complete_enclosure_RIGHT_SIDE_VIEW_SVG.scad`
- `../complete_enclosure/00_complete_enclosure_TOP_VIEW_SVG.scad`
- `../complete_enclosure/00_complete_enclosure_BOTTOM_VIEW_SVG.scad`

Open the desired projection in OpenSCAD, render it, then use **File → Export → Export as SVG**. These files suppress the 3D top-level assembly and apply `projection(cut=false)` from the appropriate viewing direction.

The front view keeps Panel 1 on the left, matching the illuminated face. The rear view is mirrored so it represents the assembly as seen physically from behind. Side/top/bottom files rotate the assembly before projection so depth appears in the 2D drawing.

CI exports every one of these projection files to an actual SVG and checks that a non-empty SVG document is produced, preventing a future change from accidentally turning them back into 3D objects.

### Individual OpenSCAD entry files

Each printable component now also has its own `.scad` entry file. These wrappers select the matching module from the common parametric source so you can open or export one part directly in OpenSCAD without editing the master file:

- `parts/01_backplane_module_PRINT_3.scad`
- `parts/01b_backplane_right_end_PRINT_1.scad`
- `parts/02_module_joiner_PRINT_4.scad`
- `parts/03_rod_end_plug_PRINT_4.scad`
- `parts/04_matrixportal_mount_PRINT_1.scad`
- `parts/05_power_distribution_mount_PRINT_1.scad`
- `parts/06_cable_clip_PRINT_8.scad`
- `parts/07_mounting_slot_coupon_PRINT_1.scad`
- `parts/08_mount_pattern_template_PRINT_1.scad`
- `parts/09_centre_boss_desk_stand_PRINT_3.scad`
- `parts/10_rear_lid_PRINT_4.scad`

The shared geometry remains in `direct_mount_enclosure.scad`; the per-part files are intentionally thin entrypoints rather than independent copies. `schematics/matrixportal_s3_REFERENCE.scad` is a non-printing simplified electronics reference, `schematics/04_matrixportal_side_access_ASSEMBLY.scad` is the Panel 1 controller-detail preview, and `../complete_enclosure/00_complete_enclosure_ASSEMBLY.scad` is the full four-panel assembly preview.

## Seam cable corridor and recessed joiner straps

The first cable-corridor revision cut through the full 16 mm depth of each seam rail and split the backplane into upper/lower solids. The corrected design keeps each backplane as **one connected printed part** and treats the HUB75 link as what it actually is: a wide but very thin ribbon.

The seam route is therefore a **shallow rear notch**:

- ribbon opening height: **24 mm**, from **y=52 mm to y=76 mm**
- notch depth from the rear: **5 mm**
- retained panel-facing structural thickness: **11 mm**
- alignment tongues remain **8 mm wide** at y=34–42 mm and y=86–94 mm

A typical 16-way HUB75 ribbon is around 20 mm wide but only a small fraction of that in thickness, so the 24 mm × 5 mm notch gives width/bend tolerance without unnecessarily removing most of the rail depth.

CI explicitly requires both standard and right-end backplane STLs to contain **exactly one connected component**, preventing another full-depth seam cut from silently splitting the module.

`stl/02_module_joiner_PRINT_4.stl` still contains two recessed straps for one seam:

- lower strap: nominal y = **34–52 mm**
- ribbon notch: nominal y = **52–76 mm**
- upper strap: nominal y = **76–94 mm**
- four countersunk M3 screws total per seam
- screw/insert rows: **y=43 mm** and **y=85 mm**
- each strap: **32 × 18 × 4 mm**
- recess depth remains **4.2 mm**, leaving 0.2 mm depth clearance
- joiner M3 heat-set pockets retain their full **6.2 mm** depth from the recess floor

The alignment tongues remain 7.2 mm high from z=4 mm, finishing at z=11.2 mm. The strap pocket floor remains z=11.8 mm, leaving **0.6 mm nominal Z clearance** between a tongue and an installed strap.

The strap screw-hole rows are now explicitly aligned to the backplane insert rows: with the joiner set installed at y=34 mm, local hole rows y=9/51 mm land at global **y=43/85 mm**, exactly matching the backplane heat-set-insert centres. CI validates this point-for-point.

The strap through-holes retain the **6.4 mm × 1.7 mm 90° countersink**. Use M3 flat-head/countersunk screws whose heads fit fully within that envelope.

The notch remains a physical validation item: route the real ribbon through one assembled seam and check that it lies naturally without being pinched by the 11 mm front web, the alignment tongues or the seam straps.

## Reinforcement-bar change

The current brass-insert rows are **7.9 mm from the top/bottom edges** after the second physical fit moved the first correction 0.5 mm back outward. The locating-pin clearance rows are at 12/116 mm. The bar centres remain at **y=24 mm and y=104 mm**. The bores are now **7.2 mm** for nominal **6 mm rods**, preserving 0.6 mm radial nominal clearance, and each module has an **8.4 mm lead-in chamfer** to reduce snagging across four separately printed modules. Narrow printed beams support the bores while leaving the central connector-access area open.

## Non-printed hardware

- 2 × 1000 mm × 6 mm round steel/aluminium bars
- **M3 heat-set inserts: M3 × 6 mm long × 4.5 mm outside diameter**
- M3 × 10 mm **flat-head/countersunk** screws for the three seam joiners (head must fit the 6.4 mm countersink)
- M3 × 8–10 mm screws for the electronics carriers
- 4 × M2.5 screws/nuts for the MatrixPortal S3 carrier; verify the physical board
- 1 × short 16-way / 2×8 HUB75 IDC ribbon cable from the MatrixPortal component-side HUB75 connector to Panel 1 input
- panel mounting screws/washers to match the actual P4 panel bosses
- for each desk stand, one panel-mount screw approximately **3 mm longer** than the normal lower-centre boss screw, while preserving safe thread engagement
- fused 5 V distribution hardware and appropriately rated 5 V input connector/cable

### Heat-set insert purchasing spec

Use brass, knurled heat-set inserts intended for thermoplastic/3D-printed parts with:

| Property | Required / target value |
| --- | --- |
| Internal thread | **M3 × 0.5** |
| Insert length | **6 mm** |
| Maximum outside diameter | **about 4.5 mm** |
| Listing shorthand | **M3 × 6 × 4.5** when the seller uses thread × length × OD |
| Mating screws | **M3 × 10 mm countersunk** for seam joiners; **M3 × 8–10 mm** for carriers |

For the pictured mixed screw/insert kits, this is the **M3 B** family, specifically the compartment labelled **M3*6*4.5**. The M3 A inserts shown as **M3*6*4.2** are a smaller outside-diameter family and are not the selected project standard.

**CAD fit:** the OpenSCAD source uses a **4.0 mm nominal pilot** (`insert_d = 4.0`) and **6.2 mm blind-pocket depth** for the selected M3 × 6 × 4.5 mm insert. The revised `stl/07_mounting_slot_coupon_PRINT_1.stl` is 8 mm thick and reproduces that exact blind pocket, leaving 1.8 mm of material beneath it. Print the coupon first and verify the fit with the actual insert and chosen filament before committing to the structural backplanes. If the insert is excessively tight or loose on the real printer, adjust the pilot in small increments (for example 0.1 mm) and regenerate the STLs.

Do not populate every optional insert pocket automatically. Install inserts only where the selected joiners, carrier or cable-management hardware needs them, and keep spare inserts for fit testing/rework.

## Carrier and end-module changes

The removable carrier attachment points are now **12 mm from each backplane edge** rather than 8 mm. Matching carrier holes are 6 mm from each edge of the 244 mm carrier, leaving about **4.25 mm nominal plastic ligament** outside a 3.5 mm mounting hole. The MatrixPortal improvements deliberately preserve these #82/#83 carrier-to-backplane positions.

### MatrixPortal S3 carrier — left-side service access

The MatrixPortal carrier keeps the **244 × 72 mm** four-point M3 attachment interface introduced by #82/#83. Its four carrier holes are at local **x=6/238 mm, y=6/66 mm**. With the carrier installed at **[6, 28, 16]** on Panel 1, those become global **x=12/244 mm, y=34/94 mm**, exactly matching the four backplane accessory inserts. CI now checks these point coordinates explicitly.

The earlier enclosure model had the MatrixPortal rotated incorrectly. The physical board is approximately **63.50 × 44.45 mm**, and the USB-C plus Reset/Up/Down/Boot controls are on the **44.45 mm short edge**. The carrier now models it in **landscape orientation**:

- long board dimension: **63.50 mm along X**;
- short board dimension: **44.45 mm along Y**;
- the short control edge faces the outside/left edge of Panel 1;
- PCB origin in the carrier: **x=-16.0 mm, y=13.775 mm**;
- installed PCB bounds: approximately **x=-10..53.5 mm, y=41.775..86.225 mm**.

The four carrier-local PCB mounting centres after the 90° orientation correction are:

| x (mm) | y (mm) |
| ---: | ---: |
| -0.760 | 22.665 |
| 39.880 | 22.665 |
| -0.760 | 42.350 |
| 39.880 | 42.350 |

These retain the physical **40.640 × 19.685 mm** MatrixPortal hole spacing; only the board orientation changed.

The carrier uses **round 2.8 mm M2.5 clearance holes** with captive M2.5 hex-nut pockets accessible from the underside. Low support ribs tie the standoffs into the left carrier rail.

Do **not** make separate button apertures in a future side wall. Keep the complete MatrixPortal short service edge unobstructed so USB-C plus Reset/Up/Down/Boot remain reachable. The board still overhangs Panel 1 by approximately **10 mm** at this edge.

For this side-access arrangement use the MatrixPortal's **component-side 2×8 HUB75 IDC connector** and a short ribbon cable to Panel 1 input. The controller therefore does not depend on the exact rear-panel HUB75 connector position.

For a visual check, open `schematics/04_matrixportal_side_access_ASSEMBLY.scad`. The short service edge is highlighted and the four carrier-to-backplane M3 centres are shown in blue.

The fourth/rightmost module uses `stl/01b_backplane_right_end_PRINT_1.stl`. It omits the unused right-side alignment tongues and unused outer seam recess/insert pockets, so the assembled printed structure ends at the nominal **1024 mm** display envelope.

The rod-end plug is now a split, tapered friction/detent design sized for the 7.2 mm bore used by the 6 mm reinforcement bars. Print and test one plug before relying on it for transport retention; filament stiffness and printer calibration still affect the final grip.

## Snap-on rear lid

`stl/10_rear_lid_PRINT_4.stl` is a separately printed lid for each 255 × 127 mm rear module. It is intentionally **open-sided** rather than a sealed box so airflow, MatrixPortal side access and the panel-to-panel ribbon route remain available.

The lid now uses **the exact same XY coordinate system and 255 × 127 mm outer footprint as the rear backplane**. The previous design hid a +2 mm placement offset in the lid-local coordinates, which made the pin/socket relationship difficult to inspect and easy to misread.

The four backplane socket centres and the four lid peg centres are now literally identical:

- x = **64 / 192 mm**
- y = **8 / 120 mm**

No installation offset is required to make the pins line up. CI records this as an explicit alignment interface, and `schematics/10_rear_lid_alignment_ASSEMBLY.scad` overlays the installed lid on a backplane with the common centres highlighted.

The lid plate sits approximately **18 mm behind the rear face of the backplane** and is 2.4 mm thick. It requires no screws.

These lid sockets are **not** the 6 mm reinforcement-bar holes; the reinforcement bores are occupied by the bars.

Snap geometry:

- socket throat: **5.8 mm**
- internal socket chamber: **6.5 mm**
- peg shaft: **5.2 mm**
- peg detent: **6.1 mm**

The split detent compresses through the throat and expands in the blind chamber. **PETG is preferred** because the snap fingers flex repeatedly. PLA remains useful for an initial dimensional test but is less suitable for repeated removal/refitting.

Before printing all four lids, test one and confirm snap force, removal force, MatrixPortal/power clearance, ventilation and cable egress.

## Separate centre-boss desk stand

`stl/09_centre_boss_desk_stand_PRINT_3.stl` is an optional, separately printed rear desk stand. Each stand:

- attaches at the **lower centre boss** (x = 128 mm, y = 7.9 mm);
- shares that panel/backplane mounting screw rather than adding a new panel hole;
- uses a 32 mm wide **3 mm mounting plate**, reduced from 5 mm so the shared boss screw only needs about 3 mm of extra length;
- retains the **60 mm rearward foot** and adds a **15 mm forward toe underneath the display** so the support footprint straddles the panel plane and resists forward tipping;
- includes an underside anti-rotation lip that keys against the **rear portion** of the backplane lower edge without reaching the LED-panel-facing plane;
- lifts the panel/backplane lower edge by approximately 6 mm when the foot is resting on a desk;
- is exported **pre-oriented on its side** so the ribs/foot can be printed with minimal support rather than as an installed-orientation L shape.

For the complete four-panel display, print **two stands** and fit them to the lower-centre bosses of Panels 1 and 4. Use the same screw family as the panel boss but approximately 3 mm longer to account for the thinner stand mounting plate. Confirm the actual screw thread and safe engagement depth before use. The 15 mm toe sits below the panel/LED face; it should not obscure the display.

The stand is deliberately not fused into the backplane, so it can be omitted for wall mounting or reprinted independently if a different desk angle/foot length is later preferred.

The new recessed panel screw wells reduce screw length for **ordinary panel mounting points**. Where a desk stand is fitted, the lower-centre screw still clamps through the 3 mm stand plate at the rear surface, so that fastener remains the stand-specific longer screw described above. The rear lid has sufficient nominal internal clearance to cover the stand plate/screw head, but that combined fit remains a physical validation item.

## Recommended validation sequence

1. Print the **revised** full-pattern template and verify all six corrected brass-boss centres plus the four 10 mm locating-pin clearances on one physical panel.
2. Only after the revised template fits, print one complete replacement backplane and verify all six screw holes, locating-pin clearance, connector/component clearance and flat seating.
3. Heat-set the M3 inserts from the rear.
4. Bolt the panels to three standard backplanes plus the dedicated right-end backplane using the existing rear mounting points.
5. Join neighbouring backplanes with the narrowed alignment tongues/sockets and the two recessed PRINT_4 seam straps, then route the real flat ribbon through the 24 mm-high × 5 mm-deep rear notch.
6. Insert and centre the two 1 m × 6 mm reinforcement bars.
7. If desk-standing is required, fit two centre-boss stands to the lower-centre bosses of Panels 1 and 4 and verify that the anti-rotation lips seat correctly and the assembled display is stable.
8. Fit the MatrixPortal carrier to the rear of Panel 1 / `backplane_1`; confirm the **short 44.45 mm service edge** overhang gives comfortable access to USB-C and all buttons. Connect the MatrixPortal component-side HUB75 connector to Panel 1 input with a short 2×8 IDC ribbon, then daisy-chain Panels 1 → 2 → 3 → 4. Fit the rod-end plugs, power-distribution carrier and cable clips.
9. Print one `stl/10_rear_lid_PRINT_4.stl` in PETG and verify all four snap locks, electronics clearance, ventilation and cable egress before printing the remaining three lids.

## Validation still required

The six-point layout is based on the calibrated real-panel photograph and independently supported by the 3D scan. The first physical template drove a 2 mm inward correction; the next fit showed that was 0.5 mm too far inward. The latest coordinates are now in CAD, but the replacement is not production-accepted until the revised template/backplane is physically fitted.

Before printing the remaining backplanes, confirm:

- the six brass mounting holes accept screws without forcing or drilling;
- the moulded locating pins enter the new 10 mm clearances without contacting the backplane;
- the panel/backplane sits flat;
- the 10 mm rear screw wells accept the actual panel screw heads, leave the heads below the rear/lid plane, and the selected screws still achieve safe boss engagement without bottoming out;
- maximum rear component/connector depth remains clear;
- HUB75 and power connector keep-out zones remain accessible;
- the actual inter-panel flat ribbon crosses each 24 mm-high × 5 mm-deep rear seam notch without pinching;
- the PRINT_4 seam straps and 8 mm alignment tongues do not interfere with the cable route;
- one PETG rear lid snaps in/out without cracking, excessive force or electronics contact;
- MatrixPortal left-side button/USB access remains usable with the lid fitted.
