# Direct-mount LED enclosure

This is the current enclosure design for the four P4 HUB75 panels.

## Geometry

- 4 × nominal 256 × 128 mm LED panels
- 4 × identical printed backplanes
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
| `01_backplane_module_PRINT_4.stl` | 4 | Main 256 × 128 mm rear structure; one per LED panel |
| `02_module_joiner_PRINT_3.stl` | 3 | Locks each module seam from the rear with M3 screws |
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

## Reinforcement-bar change

The expected panel mounting rows are only 12 mm from the top/bottom edges. The earlier 8 mm bar channels were too close to those rows, so the bar centres are now at **y=24 mm and y=104 mm**. Narrow printed beams support the bores while leaving the central connector-access area open.

## Non-printed hardware

- 2 × 1000 mm × 8 mm round steel/aluminium bars
- **M3 heat-set inserts: M3 × 6 mm long × 4.5 mm outside diameter**
- M3 × 8–10 mm screws for the three joiners and electronics carriers
- 2–4 × M2.5 screws/nuts for the MatrixPortal S3 carrier; verify the physical board
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
| Mating screws | **M3 × 8–10 mm** for the joiners/carriers |

For the pictured mixed screw/insert kits, this is the **M3 B** family, specifically the compartment labelled **M3*6*4.5**. The M3 A inserts shown as **M3*6*4.2** are a smaller outside-diameter family and are not the selected project standard.

**CAD fit warning:** the current OpenSCAD source still has `insert_d = 4.7` mm and `insert_depth = 6.2` mm. A 4.7 mm cylindrical pilot is too large to treat as a reliable heat-set pilot for a 4.5 mm OD insert; heat-set inserts need surrounding plastic to flow into the knurling. Before the structural parts are printed, calibrate the insert pilot with `07_mounting_slot_coupon_PRINT_1.stl` and update the CAD. A sensible starting pilot for common M3 inserts in this OD range is around **4.0–4.1 mm**, but the actual printed fit and the insert supplier's dimensions take precedence.

Do not populate every optional insert pocket automatically. Install inserts only where the selected joiners, carrier or cable-management hardware needs them, and keep spare inserts for fit testing/rework.

## Recommended validation sequence

1. Print the full-pattern template and verify the four expected mounting centres on one physical panel.
2. Print one complete backplane and verify connector/component clearance.
3. Heat-set the M3 inserts from the rear.
4. Bolt the four panels to their backplanes using the existing rear mounting points.
5. Join neighbouring backplanes with the alignment tongues/sockets and rear joiner plates.
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
