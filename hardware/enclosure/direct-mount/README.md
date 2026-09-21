# Direct-mount LED enclosure

This is the current enclosure design for the four P4 HUB75 panels.

## Geometry

- 4 × nominal 256 × 128 mm LED panels
- 3 × standard printed backplanes + 1 × right-end backplane
- finished LED face: 1024 × 128 mm
- 2 × 1000 mm × 8 mm reinforcement bars
- no printed bezel or rail is allowed in front of the LED PCB

## Expected LED-panel mounting pattern

A supplied reference model, `Hub75 2.5mm Panel v7.stl`, measures 160 × 80 mm. Its four symmetric rear mounting centres were measured as:

| Reference 160 × 80 position | Scaled 256 × 128 position |
| --- | --- |
| 16.69, 7.50 mm | **26.704, 12.0 mm** |
| 143.31, 7.50 mm | **229.296, 12.0 mm** |
| 16.69, 72.50 mm | **26.704, 116.0 mm** |
| 143.31, 72.50 mm | **229.296, 116.0 mm** |

The scale factor is exactly **1.6** in both axes because 160 × 80 → 256 × 128.

Expected mounting-centre spacing:

- **202.592 mm horizontally**
- **104.0 mm vertically**

The CAD now uses those centres with short 10 × 4.2 mm cross-slots for a small amount of tolerance. This is still an expected pattern rather than a vendor mechanical drawing for the purchased P4 modules.

Print `08_mount_pattern_template_PRINT_1.stl` and place it against one real panel before printing four structural backplanes.

## Printable parts

| File | Qty | Purpose |
| --- | ---: | --- |
| `01_backplane_module_PRINT_3.stl` | 3 | Standard 256 × 128 mm rear structure with right-side seam alignment tongues |
| `01b_backplane_right_end_PRINT_1.stl` | 1 | Rightmost backplane; omits unused outer tongues/recess/insert pockets |
| `02_module_joiner_PRINT_3.stl` | 3 | Locks each module seam from the rear with flush countersunk M3 screws |
| `03_rod_end_plug_PRINT_4.stl` | 4 | Retains both 1 m reinforcement bars at both ends |
| `04_matrixportal_mount_PRINT_1.stl` | 1 | Removable MatrixPortal S3 carrier |
| `05_power_distribution_mount_PRINT_1.stl` | 1 | Removable universal fused 5 V distribution carrier |
| `06_cable_clip_PRINT_8.stl` | 8 | M3 screw-down rear cable clips |
| `07_mounting_slot_coupon_PRINT_1.stl` | 1 | Small fit test for slot / insert dimensions |
| `08_mount_pattern_template_PRINT_1.stl` | 1 | Low-material 256 × 128 template to verify all four panel mounting centres |

All STLs are generated from `direct_mount_enclosure.scad`.

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

The expected panel mounting rows are only 12 mm from the top/bottom edges. The bar centres remain at **y=24 mm and y=104 mm**. The bores are now **9.2 mm** for the nominal 8 mm rods, giving 0.6 mm radial nominal clearance, and each module has a **10.4 mm lead-in chamfer** to reduce snagging across four separately printed modules. Narrow printed beams support the bores while leaving the central connector-access area open.

## Non-printed hardware

- 2 × 1000 mm × 8 mm round steel/aluminium bars
- **M3 heat-set inserts: M3 × 6 mm long × 4.5 mm outside diameter**
- M3 × 10 mm **flat-head/countersunk** screws for the three seam joiners (head must fit the 6.4 mm countersink)
- M3 × 8–10 mm screws for the electronics carriers
- 4 × M2.5 screws/nuts for the MatrixPortal S3 carrier; verify the physical board
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

### MatrixPortal S3 carrier

The MatrixPortal-specific geometry ported from PR #77 uses the Adafruit PCB envelope of **44.45 × 63.50 mm** in portrait orientation. The four carrier-local PCB mounting centres are:

| x (mm) | y (mm) |
| ---: | ---: |
| 115.650 | 19.490 |
| 135.335 | 19.490 |
| 115.650 | 60.130 |
| 135.335 | 60.130 |

The carrier now uses **round 2.8 mm M2.5 clearance holes** rather than the former elongated/rotated slots. Each hole has a captive M2.5 hex-nut pocket accessible from the underside. Low 2 mm support ribs tie all four 8 mm standoffs into the carrier side rails so the printed part is one connected shell while leaving the populated PCB underside substantially open.

The MatrixPortal carrier remains removable from the same four M3 backplane attachment points introduced by #82; no backplane insert positions are changed by this MatrixPortal update. CI also verifies that the generated MatrixPortal STL is a single connected component reaching the z=0 print plane.

The fourth/rightmost module uses `01b_backplane_right_end_PRINT_1.stl`. It omits the unused right-side alignment tongues and unused outer seam recess/insert pockets, so the assembled printed structure ends at the nominal **1024 mm** display envelope.

The rod-end plug is now a split, tapered friction/detent design sized for the 9.2 mm bore. Print and test one plug before relying on it for transport retention; filament stiffness and printer calibration still affect the final grip.

## Recommended validation sequence

1. Print the full-pattern template and verify the four expected mounting centres on one physical panel.
2. Print one complete backplane and verify connector/component clearance.
3. Heat-set the M3 inserts from the rear.
4. Bolt the panels to three standard backplanes plus the dedicated right-end backplane using the existing rear mounting points.
5. Join neighbouring backplanes with the alignment tongues/sockets and recessed joiner plates using flush countersunk M3 screws.
6. Insert and centre the two 1 m × 8 mm reinforcement bars.
7. Fit the rod-end plugs, MatrixPortal carrier, power-distribution carrier and cable clips.

## Validation still required

The reference STL gives a much better expected mounting pattern, but it is a **P2.5 160 × 80 model**, while the purchased panels are P4 256 × 128 modules. The pattern is therefore scaled and must still be checked against one physical P4 panel.

Before printing all four backplanes, confirm:

- exact PCB width and height
- the four scaled mounting centres
- screw/boss diameter and thread
- maximum rear component/connector depth
- HUB75 and power connector keep-out zones
