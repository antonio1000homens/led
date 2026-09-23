# Direct-mount LED enclosure

This is the current enclosure design for the four P4 HUB75 panels.

## Geometry

- 4 × nominal 256 × 128 mm LED panels
- 3 × standard printed backplanes + 1 × right-end backplane
- finished LED face: 1024 × 128 mm
- 2 × 1000 mm × 8 mm reinforcement bars
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

**Panel 1 is the leftmost panel when looking at the illuminated LED face from the front.** The `04_matrixportal_mount_PRINT_1.stl` carrier attaches to the rear of Panel 1 / `backplane_1`. The MatrixPortal PCB is intentionally shifted to the left so its button/USB edge overhangs the Panel 1 side by about **10 mm**. Panel 4 is the rightmost panel and uses `01b_backplane_right_end_PRINT_1.stl`.

When working from the rear of the assembled display, remember that the apparent left/right order is reversed relative to this front-view numbering. Connect the MatrixPortal HUB75 output to the input connector of Panel 1, then daisy-chain the panel outputs in numerical order through Panel 4.

## Measured P4 panel mounting pattern

The production backplane no longer derives its screw positions from the historical 160 × 80 mm P2.5 reference model.

A calibrated 1:1 ruler photograph of the real P4 panel, cross-checked against the supplied Kiri Engine scan, shows **six brass mounting inserts in a symmetric 3 × 2 pattern**:

| X (mm) | Y (mm) |
| ---: | ---: |
| 6.4 | 6.4 |
| 128.0 | 6.4 |
| 249.6 | 6.4 |
| 6.4 | 121.6 |
| 128.0 | 121.6 |
| 249.6 | 121.6 |

This gives:
- **6.4 mm nominal edge inset** on all four sides;
- a centre mounting column at **x = 128.0 mm**;
- outer-column spacing of **121.6 mm** either side of centre;
- vertical row spacing of **115.2 mm**.

The production CAD uses **4.5 mm round through-holes** at these six centres. This provides practical clearance for the panel screws while keeping substantially more edge material than the old 10 mm cross-slots.

### Moulded locating-pin clearance

The failed physical backplane fit also showed a protruding moulded locating pin entering one of the old four provisional P2.5-derived slots. Those old centres are therefore retained **only as locating-pin clearance positions**, not mounting points:

- X = **26.704 / 229.296 mm**
- Y = **12.0 / 116.0 mm**
- clearance diameter = **10.0 mm**

The screw holes and locating-pin clearances are intentionally different shapes so their purpose is obvious.

Print `08_mount_pattern_template_PRINT_1.stl` first and verify all six brass inserts **and** the locating-pin clearances against the real panel before printing the remaining structural backplanes.

## Printable parts

| File | Qty | Purpose |
| --- | ---: | --- |
| `01_backplane_module_PRINT_3.stl` | 3 | Standard 256 × 128 mm rear structure with right-side seam alignment tongues |
| `01b_backplane_right_end_PRINT_1.stl` | 1 | Rightmost backplane; omits unused outer tongues/recess/insert pockets |
| `02_module_joiner_PRINT_3.stl` | 3 | Locks each module seam from the rear with flush countersunk M3 screws |
| `03_rod_end_plug_PRINT_4.stl` | 4 | Retains both 1 m reinforcement bars at both ends |
| `04_matrixportal_mount_PRINT_1.stl` | 1 | Removable MatrixPortal S3 carrier for the rear of Panel 1 / `backplane_1` |
| `05_power_distribution_mount_PRINT_1.stl` | 1 | Removable universal fused 5 V distribution carrier |
| `06_cable_clip_PRINT_8.stl` | 8 | M3 screw-down rear cable clips |
| `07_mounting_slot_coupon_PRINT_1.stl` | 1 | Small fit test for slot / insert dimensions |
| `08_mount_pattern_template_PRINT_1.stl` | 1 | Low-material 256 × 128 template to verify all six brass inserts plus locating-pin clearances |

All STLs are generated from `direct_mount_enclosure.scad`.

### Complete enclosure assembly preview

Open `00_complete_enclosure_ASSEMBLY.scad` to see the nominal assembled rear structure rather than a single printable part. It includes:

- Panels/backplanes 1–4 at x = 0, 256, 512 and 768 mm;
- the dedicated right-end backplane on Panel 4;
- all three recessed seam joiners;
- both 1000 × 8 mm reinforcement rods;
- the MatrixPortal carrier on Panel 1, including the simplified PCB reference and left-side service overhang;
- the power-distribution carrier on Panel 2;
- translucent guide planes at the three nominal panel seams.

The complete assembly file is **not** a printable component and does not replace `direct_mount_enclosure.scad`. The latter remains the shared parametric geometry source; the assembly file simply instantiates those modules at their nominal positions.

CI now validates the assembly placement explicitly. The backplane origins must remain on an exact **256 mm pitch**, all four must share the same Y/Z origin, the joiners must stay on their three nominal seam positions, and the electronics carriers must remain assigned to their intended panels. The existing overall-width and interference checks still run in addition to these placement checks.

### SVG / 2D projection views

The full assembly is a 3D object, so OpenSCAD cannot export `00_complete_enclosure_ASSEMBLY.scad` directly as SVG. Use one of these dedicated 2D projection files instead:

- `00_complete_enclosure_FRONT_VIEW_SVG.scad`
- `00_complete_enclosure_BACK_VIEW_SVG.scad`
- `00_complete_enclosure_LEFT_SIDE_VIEW_SVG.scad`
- `00_complete_enclosure_RIGHT_SIDE_VIEW_SVG.scad`
- `00_complete_enclosure_TOP_VIEW_SVG.scad`
- `00_complete_enclosure_BOTTOM_VIEW_SVG.scad`

Open the desired projection in OpenSCAD, render it, then use **File → Export → Export as SVG**. These files suppress the 3D top-level assembly and apply `projection(cut=false)` from the appropriate viewing direction.

The front view keeps Panel 1 on the left, matching the illuminated face. The rear view is mirrored so it represents the assembly as seen physically from behind. Side/top/bottom files rotate the assembly before projection so depth appears in the 2D drawing.

CI exports every one of these projection files to an actual SVG and checks that a non-empty SVG document is produced, preventing a future change from accidentally turning them back into 3D objects.

### Individual OpenSCAD entry files

Each printable component now also has its own `.scad` entry file. These wrappers select the matching module from the common parametric source so you can open or export one part directly in OpenSCAD without editing the master file:

- `01_backplane_module_PRINT_3.scad`
- `01b_backplane_right_end_PRINT_1.scad`
- `02_module_joiner_PRINT_3.scad`
- `03_rod_end_plug_PRINT_4.scad`
- `04_matrixportal_mount_PRINT_1.scad`
- `05_power_distribution_mount_PRINT_1.scad`
- `06_cable_clip_PRINT_8.scad`
- `07_mounting_slot_coupon_PRINT_1.scad`
- `08_mount_pattern_template_PRINT_1.scad`

The shared geometry remains in `direct_mount_enclosure.scad`; the per-part files are intentionally thin entrypoints rather than independent copies. `matrixportal_s3_REFERENCE.scad` is a non-printing simplified electronics reference, `04_matrixportal_side_access_ASSEMBLY.scad` is the Panel 1 controller-detail preview, and `00_complete_enclosure_ASSEMBLY.scad` is the full four-panel assembly preview.

## Recessed seam joiners

Each `02_module_joiner_PRINT_3.stl` is **32 × 48 × 4 mm** and is centred across a panel seam. The rear face of each neighbouring backplane now provides half of a matching recess:

- **16.25 mm** pocket width per backplane, giving 0.25 mm lateral clearance on each outer joiner edge
- **48.5 mm** pocket height, giving 0.25 mm clearance at each end
- **4.2 mm** pocket depth for the 4 mm joiner, leaving 0.2 mm depth clearance
- the joiner M3 heat-set pockets retain their full **6.2 mm** depth measured from the recess floor

The panel-facing surface is unchanged, so the backplane still sits directly and flush against the rear mounting face of the LED panel. When two backplanes meet, the joiner is recessed into their rear faces rather than being trapped between a backplane and the LED PCB.

The alignment tongues are now 7.2 mm high from z=4 mm, finishing at z=11.2 mm. The joiner pocket floor is z=11.8 mm, leaving **0.6 mm nominal Z clearance** between each tongue and the installed joiner.

The joiner through-holes now include a **6.4 mm × 1.7 mm 90° countersink**. Use M3 flat-head/countersunk screws whose heads fit fully within that envelope so no screw head stands proud into an electronics carrier.

## Reinforcement-bar change

The measured brass-insert rows are **6.4 mm from the top/bottom edges**. The locating-pin clearance rows are at 12/116 mm. The bar centres remain at **y=24 mm and y=104 mm**. The bores are now **9.2 mm** for the nominal 8 mm rods, giving 0.6 mm radial nominal clearance, and each module has a **10.4 mm lead-in chamfer** to reduce snagging across four separately printed modules. Narrow printed beams support the bores while leaving the central connector-access area open.

## Non-printed hardware

- 2 × 1000 mm × 8 mm round steel/aluminium bars
- **M3 heat-set inserts: M3 × 6 mm long × 4.5 mm outside diameter**
- M3 × 10 mm **flat-head/countersunk** screws for the three seam joiners (head must fit the 6.4 mm countersink)
- M3 × 8–10 mm screws for the electronics carriers
- 4 × M2.5 screws/nuts for the MatrixPortal S3 carrier; verify the physical board
- 1 × short 16-way / 2×8 HUB75 IDC ribbon cable from the MatrixPortal component-side HUB75 connector to Panel 1 input
- panel mounting screws/washers to match the actual P4 panel bosses
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

**CAD fit:** the OpenSCAD source uses a **4.0 mm nominal pilot** (`insert_d = 4.0`) and **6.2 mm blind-pocket depth** for the selected M3 × 6 × 4.5 mm insert. The revised `07_mounting_slot_coupon_PRINT_1.stl` is 8 mm thick and reproduces that exact blind pocket, leaving 1.8 mm of material beneath it. Print the coupon first and verify the fit with the actual insert and chosen filament before committing to the structural backplanes. If the insert is excessively tight or loose on the real printer, adjust the pilot in small increments (for example 0.1 mm) and regenerate the STLs.

Do not populate every optional insert pocket automatically. Install inserts only where the selected joiners, carrier or cable-management hardware needs them, and keep spare inserts for fit testing/rework.

## Carrier and end-module changes

The removable carrier attachment points are now **12 mm from each backplane edge** rather than 8 mm. Matching carrier holes are 6 mm from each edge of the 244 mm carrier, leaving about **4.25 mm nominal plastic ligament** outside a 3.5 mm mounting hole. The MatrixPortal improvements deliberately preserve these #82/#83 carrier-to-backplane positions.

### MatrixPortal S3 carrier — left-side service access

The MatrixPortal carrier keeps the same **244 × 72 mm** four-point M3 attachment interface introduced by #82/#83, but the PCB itself is no longer centred on the carrier. It is shifted to the **left end of Panel 1** so the physical PCB edge containing USB-C and the user buttons is accessible from the enclosure side.

The MatrixPortal PCB envelope remains **44.45 × 63.50 mm** in portrait orientation. Within the carrier its PCB origin is now `x=-16.0 mm`, `y=4.25 mm`. Because the complete carrier is installed at `x=+6 mm` on Panel 1, the PCB's left edge lands at **x=-10 mm relative to the Panel 1/backplane edge**. The printed carrier/standoffs remain within the Panel 1 structural envelope; only the electronics board overhangs.

The four carrier-local PCB mounting centres are therefore:

| x (mm) | y (mm) |
| ---: | ---: |
| -0.125 | 19.490 |
| 19.560 | 19.490 |
| -0.125 | 60.130 |
| 19.560 | 60.130 |

The carrier uses **round 2.8 mm M2.5 clearance holes** with captive M2.5 hex-nut pockets accessible from the underside. Low 2 mm ribs tie the four 8 mm standoffs into the existing left carrier rail. The two outer standoffs slightly cross the carrier-local x=0 plane but, after the carrier's +6 mm backplane offset, still remain behind the Panel 1 footprint.

Do **not** make three separate button holes in a future side cover. Leave one continuous side-service opening for the MatrixPortal's left edge so USB-C plus Reset/Up/Down/Boot remain reachable despite small production tolerances and connector protrusion. The current target is to keep at least the PCB's **10 mm side overhang** unobstructed.

For this side-access arrangement use the MatrixPortal's **component-side 2×8 HUB75 IDC connector** and a short ribbon cable to Panel 1 input. This avoids making the carrier depend on the still-unmeasured position of the physical panel's rear HUB75 connector.

The MatrixPortal carrier remains removable from the same four M3 backplane attachment points introduced by #82; no backplane insert positions are changed. **For the assembled display it is assigned specifically to Panel 1 / `backplane_1`, the HUB75 input end of the chain.** CI verifies that the generated MatrixPortal STL is one connected component reaching the z=0 print plane.

For a visual mechanical check, open `04_matrixportal_side_access_ASSEMBLY.scad`. It shows Panel 1, the printed carrier, a simplified MatrixPortal PCB reference, and the x=0 panel side plane.

The fourth/rightmost module uses `01b_backplane_right_end_PRINT_1.stl`. It omits the unused right-side alignment tongues and unused outer seam recess/insert pockets, so the assembled printed structure ends at the nominal **1024 mm** display envelope.

The rod-end plug is now a split, tapered friction/detent design sized for the 9.2 mm bore. Print and test one plug before relying on it for transport retention; filament stiffness and printer calibration still affect the final grip.

## Recommended validation sequence

1. Print the full-pattern template and verify all **six brass mounting centres** plus the four 10 mm locating-pin clearances on one physical panel.
2. Print one complete replacement backplane and verify all six screw holes, locating-pin clearance, connector/component clearance and flat seating.
3. Heat-set the M3 inserts from the rear.
4. Bolt the panels to three standard backplanes plus the dedicated right-end backplane using the existing rear mounting points.
5. Join neighbouring backplanes with the alignment tongues/sockets and recessed joiner plates using flush countersunk M3 screws.
6. Insert and centre the two 1 m × 8 mm reinforcement bars.
7. Fit the MatrixPortal carrier to the rear of Panel 1 / `backplane_1`; confirm the PCB overhang gives comfortable access to USB-C and all left-edge buttons. Connect the MatrixPortal component-side HUB75 connector to Panel 1 input with a short 2×8 IDC ribbon, then daisy-chain Panels 1 → 2 → 3 → 4. Fit the rod-end plugs, power-distribution carrier and cable clips.

## Validation still required

The six-point mounting pattern is now based on the calibrated real-panel photograph and independently supported by the 3D scan, rather than by P2.5 scaling. The replacement is still not considered production-accepted until the revised template/backplane is physically fitted.

Before printing the remaining backplanes, confirm:

- the six brass mounting holes accept screws without forcing or drilling;
- the moulded locating pins enter the new 10 mm clearances without contacting the backplane;
- the panel/backplane sits flat;
- screw/boss diameter and thread are correct for the selected fasteners;
- maximum rear component/connector depth remains clear;
- HUB75 and power connector keep-out zones remain accessible;
- MatrixPortal left-side button/USB access works with the real PCB and any final side cover fitted.
