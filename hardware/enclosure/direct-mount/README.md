# Direct-mount LED enclosure

This is the current enclosure design for the four P4 HUB75 panels.

## Geometry

- 4 × nominal 256 × 128 mm LED panels
- 4 × identical printed backplanes
- finished LED face: 1024 × 128 mm
- 2 × 1000 mm × 8 mm reinforcement bars, centred in the 1024 mm assembly
- approximately 12 mm bar setback at each outer end
- no printed bezel or rail is allowed in front of the LED PCB

The panel sits in front of the backplane (`z < 0` in the OpenSCAD model); all enclosure material is behind it (`z >= 0`).

## Printable parts

| File | Qty | Purpose |
| --- | ---: | --- |
| `01_backplane_module_PRINT_4.stl` | 4 | Main 256 × 128 mm rear structure; one per LED panel |
| `02_module_joiner_PRINT_3.stl` | 3 | Locks each module seam from the rear with M3 screws |
| `03_rod_end_plug_PRINT_4.stl` | 4 | Retains both 1 m reinforcement bars at both ends |
| `04_matrixportal_mount_PRINT_1.stl` | 1 | Removable MatrixPortal S3 carrier with M2.5-tolerant slots |
| `05_power_distribution_mount_PRINT_1.stl` | 1 | Removable universal fused 5 V distribution carrier |
| `06_cable_clip_PRINT_8.stl` | 8 | M3 screw-down rear cable clips |
| `07_mounting_slot_coupon_PRINT_1.stl` | 1 | Small fit test before committing to full backplane prints |

All STLs are generated from `direct_mount_enclosure.scad`.

## Non-printed hardware

- 2 × 1000 mm × 8 mm round steel/aluminium bars
- M3 heat-set inserts, nominal 4.7 mm pilot in the current CAD
- M3 × 8–10 mm screws for the three joiners and electronics carriers
- 2–4 × M2.5 screws/nuts for the MatrixPortal S3 carrier (verify the physical board)
- panel mounting screws/washers to match the actual AliExpress panel bosses
- fused 5 V distribution hardware and appropriately rated 5 V input connector/cable

## Assembly

```text
FRONT (LED faces)

┌──────────────┬──────────────┬──────────────┬──────────────┐
│   PANEL 1    │   PANEL 2    │   PANEL 3    │   PANEL 4    │
│  256 × 128   │  256 × 128   │  256 × 128   │  256 × 128   │
└──────────────┴──────────────┴──────────────┴──────────────┘

REAR (printed backplanes)

┌──────────────┬──────────────┬──────────────┬──────────────┐
│ BACKPLANE 1  │ BACKPLANE 2  │ BACKPLANE 3  │ BACKPLANE 4  │
└──────────────┴──────────────┴──────────────┴──────────────┘
       ▲              ▲              ▲
     JOINER 1       JOINER 2       JOINER 3

   ═════════════════ 1000 mm × 8 mm top bar ════════════════
   ════════════════ 1000 mm × 8 mm bottom bar ═════════════
```

1. Heat-set the M3 inserts from the rear of each backplane.
2. Test one physical LED panel against one backplane before printing the remaining three.
3. Bolt the four panels to their backplanes using the existing rear mounting points.
4. Engage the printed alignment tongues/sockets between neighbouring backplanes.
5. Fit one rear joiner plate across each seam and secure it with four M3 screws.
6. Push the two 1 m × 8 mm bars through the continuous top/bottom bores and centre them, leaving about 12 mm at each outer end.
7. Fit the four tapered rod-end plugs.
8. Mount the MatrixPortal and fused power-distribution carriers from the rear using their dedicated insert positions.
9. Route HUB75/power wiring through the large open backplane areas and secure it with cable clips.

## Important validation still required

The AliExpress email identifies the panels as P4 modules and quantity four, but it does not provide the mechanical drawing. The current panel-mount cross-slots are therefore **provisional**.

Before a production print, measure one real panel and update:

- exact PCB width and height
- mounting-hole centre spacing and edge offsets
- screw/boss size
- maximum rear component/connector depth
- connector keep-out zones

Do not print all four backplanes until one-panel fit has been verified.
