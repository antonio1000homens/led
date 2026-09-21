# Direct-mount LED enclosure

This is the current enclosure design for the four P4 HUB75 panels.

## Geometry

- 4 × nominal 256 × 128 mm LED panels
- 4 × identical printed backplanes
- finished LED face: 1024 × 128 mm
- 2 × 1000 mm × 8 mm reinforcement bars
- no printed bezel or rail is allowed in front of the LED PCB

## Provisional physical LED-panel mounting pattern

Issue #76 replaces the old scaled P2.5 reference pattern. The purchased panel envelope is treated as 256 × 128 mm, viewed from the rear in landscape orientation, with the origin at the PCB lower-left corner.

| Boss | x (mm) | y (mm) |
| --- | ---: | ---: |
| bottom-left | **6** | **6** |
| bottom-centre | **128** | **6** |
| bottom-right | **250** | **6** |
| top-left | **6** | **122** |
| top-centre | **128** | **122** |
| top-right | **250** | **122** |

This gives 6 mm left/right and top/bottom edge offsets, 122 mm horizontal spacing, and 116 mm vertical spacing. The values are a photo-derived nominalisation of approximately 5.9 mm measured offsets, not a caliper or vendor drawing.

Mounting-centre spacing:

- **122 mm + 122 mm horizontally**
- **116 mm vertically**

The CAD uses these six centres with short 10 × 4.2 mm cross-slots. The silver centre fastener visible near `(128,64)` is intentionally excluded because it appears to be a factory assembly screw, not a threaded mounting boss.

Print `08_mount_pattern_template_PRINT_1.stl` and place it against one real panel before printing four structural backplanes.

## MatrixPortal S3 carrier geometry

The carrier is centred on the backplane with a 6 mm X offset and 28 mm Y offset. Its four carrier-to-backplane M3 clearance holes are explicitly at `(8,6)`, `(236,6)`, `(8,66)`, and `(236,66)`; these align with backplane heat-set inserts at `(14,34)`, `(242,34)`, `(14,94)`, and `(242,94)`.

The official Adafruit MatrixPortal S3 reference is a 44.45 × 63.50 mm PCB in portrait orientation, with HUB75 at the top and USB-C at the bottom. Its carrier-local plated mounting centres are `(115.650,19.490)`, `(135.335,19.490)`, `(115.650,60.130)`, and `(135.335,60.130)`. The carrier uses four round 2.8 mm M2.5-clearance holes on 19.685 × 40.640 mm spacing, supported by 8 mm diameter posts that start at z=2 mm and finish at the 10 mm PCB mounting surface. Insert one nominal 5.0 mm-across-flats, 2.2 mm-high M2.5 hex nut into the bottom-open captive pocket of each post, then fasten the PCB with M2.5 screws from the PCB side.

The carrier has no elongated MatrixPortal mounting slots. Its top/bottom centre has a 72 mm-wide through-opening under the PCB edge connectors and controls. Four narrow 2 mm-high side ribs plus 6 mm-wide cross-ribs at y=19.490 and y=60.130 join all four posts into one connected printable solid while leaving about 8 mm vertical clearance below the PCB underside; the central populated/connector area is not filled with a solid deck. The HUB75 connector, USB-C, DOWN/UP/RESET buttons, and 5V/GND terminals must remain accessible. The two 5V/GND terminal screws are electrical only and are not mechanical mounting points. The printable carrier SVG is generated directly from the same SCAD source with `part="matrixportal_2d"`; use [`04_matrixportal_mount_ASSEMBLY.svg`](04_matrixportal_mount_ASSEMBLY.svg) as the 1:1 documentation overlay and print it at 100% / Actual Size without scaling.

## Printable parts

| File | Qty | Purpose |
| --- | ---: | --- |
| `01_backplane_module_PRINT_4.stl` | 4 | Main 256 × 128 mm rear structure; one per LED panel |
| `02_module_joiner_PRINT_3.stl` | 3 | Locks each module seam from the rear with M3 screws |
| `03_rod_end_plug_PRINT_4.stl` | 4 | Retains both 1 m reinforcement bars at both ends |
| `04_matrixportal_mount_PRINT_1.stl` | 1 | Removable MatrixPortal S3 carrier |
| `05_power_distribution_mount_PRINT_1.stl` | 1 | Removable universal fused 5 V distribution carrier |
| `06_cable_clip_PRINT_8.stl` | 8 | M3 screw-down rear cable clips |
| `07_mounting_slot_coupon_PRINT_1.stl` | 1 | Small fit test for slot / insert dimensions |
| `08_mount_pattern_template_PRINT_1.stl` | 1 | Low-material 256 × 128 template to verify all six panel mounting centres |

All STLs are generated from `direct_mount_enclosure.scad`.
The checked-in `01_backplane_module_PRINT_4.svg` is a 1:1 2D projection generated from the same SCAD source using `part="backplane_2d"`; print it at 100% / Actual Size for a paper fit check.

## Recessed seam joiners

Each `02_module_joiner_PRINT_3.stl` is **32 × 48 × 4 mm** and is centred across a panel seam. The rear face of each neighbouring backplane now provides half of a matching recess:

- **16.25 mm** pocket width per backplane, giving 0.25 mm lateral clearance on each outer joiner edge
- **48.5 mm** pocket height, giving 0.25 mm clearance at each end
- **4.2 mm** pocket depth for the 4 mm joiner, leaving 0.2 mm depth clearance
- the joiner M3 heat-set pockets retain their full **6.2 mm** depth measured from the recess floor

The panel-facing surface is unchanged, so the backplane still sits directly and flush against the rear mounting face of the LED panel. When two backplanes meet, the joiner is recessed into their rear faces rather than being trapped between a backplane and the LED PCB.

## Reinforcement-bar change

The expected panel mounting rows are only 12 mm from the top/bottom edges. The earlier 8 mm bar channels were too close to those rows, so the bar centres are now at **y=24 mm and y=104 mm**. Narrow printed beams support the bores while leaving the central connector-access area open.

## Non-printed hardware

- 2 × 1000 mm × 8 mm round steel/aluminium bars
- **M3 heat-set inserts: M3 × 6 mm long × 4.5 mm outside diameter**
- M3 × 8–10 mm screws for the three joiners and electronics carriers
- 2–4 × M2.5 screws/nuts for the MatrixPortal S3 carrier; verify the physical board
- panel mounting screws/washers to match the actual P4 panel bosses
- fused 5 V distribution hardware and appropriately rated 5 V input connector/cable

The MatrixPortal S3 carrier uses the PCB's 19.685 mm × 40.64 mm hole spacing
in carrier x/y respectively, with four round 2.8 mm M2.5-clearance holes. It
does not use elongated PCB mounting slots.

### Heat-set insert purchasing spec

Use brass, knurled heat-set inserts intended for thermoplastic/3D-printed parts with:

| Property | Required / target value |
| --- | --- |
| Internal thread | **M3 × 0.5** |
| Insert length | **6 mm** |
| Maximum outside diameter | **about 4.5 mm** |
| Listing shorthand | **M3 × 6 × 4.5** when the seller uses thread × length × OD |
| Mating screws | **M3 × 8–10 mm** for the joiners/carriers |

For the pictured mixed screw/insert kits, this is the **M3 B** family, specifically the compartment labelled **M3*6*4.5**. The M3 A inserts shown as **M3*6*4.2** are a smaller outside-diameter family and are not the selected project standard.

**CAD fit:** the OpenSCAD source now uses a **4.0 mm nominal pilot** (`insert_d = 4.0`) and **6.2 mm blind-pocket depth** for the selected M3 × 6 × 4.5 mm insert. Print `07_mounting_slot_coupon_PRINT_1.stl` first and verify the fit with the actual insert and chosen filament before committing to all four backplanes. If the insert is excessively tight or loose on the real printer, adjust the pilot in small increments (for example 0.1 mm) and regenerate the STLs.

Do not populate every optional insert pocket automatically. Install inserts only where the selected joiners, carrier or cable-management hardware needs them, and keep spare inserts for fit testing/rework.

## Recommended validation sequence

1. Print the full-pattern template and verify all six nominal mounting centres on one physical panel.
2. Print one complete backplane and verify connector/component clearance.
3. Heat-set the M3 inserts from the rear.
4. Bolt the four panels to their backplanes using the existing rear mounting points.
5. Join neighbouring backplanes with the alignment tongues/sockets and rear joiner plates.
6. Insert and centre the two 1 m × 8 mm reinforcement bars.
7. Fit the rod-end plugs, MatrixPortal carrier, power-distribution carrier and cable clips.
8. Overlay `04_matrixportal_mount_ASSEMBLY.svg` on the carrier/backplane paper projections and check the MatrixPortal orientation, four PCB holes, four carrier M3 holes, and connector/button/terminal access.

## Validation still required

The six-point pattern is derived from the physical-panel photograph and is now explicit in the SCAD, but must still be checked against one physical P4 panel before structural printing.

Before printing all four backplanes, confirm:

- exact PCB width and height
- all six mounting centres, especially the nominal 6 mm edge offset
- screw/boss diameter and thread
- maximum rear component/connector depth
- HUB75 and power connector keep-out zones
