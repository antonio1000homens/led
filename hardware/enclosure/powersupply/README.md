# Enclosure-centred PSU service tray

Issue #177 replaces the fixed dock's front screw-mounted latch with a pull-release flexure integral to the removable tray. Source geometry is OpenSCAD; checked-in meshes are generated artifacts.

## Parts and interface

| File | Purpose |
| --- | --- |
| `02_service_tray_snap_dock_PRINT_1.scad` | Fixed dock with enclosure pockets, runners, stop and underside detent groove |
| `03_service_tray_snap_tray_PRINT_1.scad` | Removable tray with open-ended runner grooves and integral flexure |
| `05_backplane_fit_preview.scad` | Actual enclosure backplane, fit states, PSU envelope and detent section |
| `06_boss_heatset_insert_test.scad` | Optional M3 insert test coupon for the enclosure's blind boss holes |
| `07_detent_test_coupon_TEST_1.scad` | Parametric production flexure and mating-groove coupon for PETG fit testing |
| `psu_mount_common.scad` | PSU measurements and common mount geometry |
| `service_tray_snap_latch_common.scad` | Dock, tray and flexure geometry |
| `../psu_adapter_interface.scad` | Shared geometry-free mounting-grid offsets and column selection |

## Measured dimensions

The enclosure's reinforced 8 mm shoulder leaves a usable cavity from Y=48.5 to 132.5 mm, centred at Y=90.5. The shared grid uses five X columns `[32,80,128,176,224]` and rows `[71.5,90.5,109.5]`. The dock selects columns 80 and 176, represented locally by X=±48 and row offsets Y=−19/0/+19. The other enclosure bosses remain available for accessories; the dock has relief for the two upper/lower bosses in the unused X=128 column.

A revised dock only fits a backplane with the revised boss rows. Previously printed backplanes retain Y=67.5/86.5/105.5 and will not align. The dock is 118 × 79 × 4.2 mm and the tray remains 114 × 79 × 2.8 mm. The extra 1 mm dock thickness permits the enclosure screw heads to be recessed below the sliding surface without reducing the structural web above the rear boss pockets. The 110 × 80 × 37 mm PSU overhangs the tray by 0.5 mm per side. After physical fit correction, its diagonally opposed pilots are at (−52,−36) and (+52,+36), Ø2.8 mm: the landscape bottom-left hole moved up 1 mm and the top-right hole moved down 1 mm. The pilot edge now retains 2.1 mm of material.

The two support bars and PSU screw bosses share a top plane at tray-local Z=4.8 mm (2.8 mm plate + 2 mm support). Bars are at X=±34 mm, 5 mm wide and 66 mm long. This is separate from the six enclosure fixings (Ø3.6 clearance, Ø7 × 1.8 mm head recess, Ø7.5 × 1.2 mm locating pockets).

## Slide and pull-release flexure

The tray inserts along +X. Two internal runners at Y=±25 mm use a 2.4 mm base, 4 mm top and 1.8 mm height. Their 96 mm length ends at X=+39 mm; the former +49 mm end was shortened by 10 mm. Matching grooves retain 0.3 mm lateral clearance and open through the tray's +X leading edge. A separate wall at +X stops insertion.

The tray flexure wraps around the dock's −X edge. Its initial PETG coupon geometry uses a 30 mm cantilever, 5 mm X width and 1.2 mm thickness, with 0.5 mm nominal detent engagement into a 0.8 mm deep underside groove (0.3 mm seated clearance above the detent). Pulling the tray cams the detent down; no button press is needed. Beam thickness and engagement are parameters for physical tuning. No release-force value has been measured. Check deflection against the actual backplane and use a PETG coupon before relying on repeated flexing.

Use six M3 ISO 7380 button-head screws with head diameter no greater than 5.7 mm and height no greater than 1.65 mm. The 1.8 mm recess puts that maximum head 0.15 mm below the 4.2 mm dock surface. The tray underside runs at Z=4.45 mm when seated, leaving 0.40 mm over the supported screw-head envelope during insertion/removal. The 4.2 mm dock still retains 1.2 mm of material between the head recess and the 1.2 mm rear registration pocket. Other screw heads require a fresh clearance check.

The dock's six bosses have a nominal 4 mm height and overlap the 3 mm backplane by 0.3 mm, leaving 3.7 mm exposed toward the dock. The assembly preview places the dock so those tips enter the registration pockets by 1.2 mm. The shared interface preserves Ø7 bosses, Ø3.4 blind holes and the 1.2 mm external wall skin. Confirm screw-head clearance for the actual hardware before assembly.

## Bill of materials

| Qty | Item | Specification / note |
| ---: | --- | --- |
| 1 | Universal equipment backplane | Must use the revised boss rows Y=71.5/90.5/109.5; older printed backplanes are incompatible. |
| 1 | Fixed PSU dock | Print in PETG; 118 × 79 × 4.2 mm. |
| 1 | Sliding PSU tray | Print in PETG; 114 × 79 × 2.8 mm plate with integral flexure. |
| 1 | PSU | Measured envelope 110 × 80 × 37 mm; corrected diagonal mounting pilots at (−52,−36) and (+52,+36) mm. |
| 6 | Dock-to-backplane screws | M3 ISO 7380 button head; head diameter ≤5.7 mm and head height ≤1.65 mm. Screw length is not established by the available measurements: verify engagement in the Ø3.4 mm blind boss bores and ensure the tips preserve the 1.2 mm exterior wall skin before ordering. |
| 2 | PSU-to-tray screws | Use the PSU's specified thread and length through the Ø2.8 mm tray pilots; the PSU thread and screw length were not measured here. |
| 1 each | Detent coupon pieces | Optional PETG fit test: flexure coupon and matching groove coupon from `07_detent_test_coupon_TEST_1.scad`. |

Assembly order: attach the dock to the revised backplane using the six M3 screws and locating pockets; fit the PSU to the tray with the PSU-specified fasteners; then feed the loaded tray from −X along the runners until its +X hard stop seats and the flexure engages. Pull the tray deliberately to release it. Verify the coupon and assembled fit physically before relying on repeated service cycles.

## Render and validate

From the repository root:

```bash
python hardware/enclosure/scripts/generate_stls.py --output-dir build/enclosure-stls
python hardware/enclosure/scripts/validate_psu_adapter.py --generated-dir build/enclosure-stls
python hardware/enclosure/scripts/validate_enclosure.py --generated-dir build/enclosure-stls --workers 4
python hardware/enclosure/scripts/verify_canonical_stls.py --generated-dir build/enclosure-stls
```

The canonical model IDs remain `psu-service-tray-dock` and `psu-service-tray-tray`. Slice the dock flat. The tray print wrapper stands the plate on its 2.8 mm lower edge for a 118.8 × 13.75 × 79 mm pose; the underside flexure requires generated supports in this orientation. With Bambu Lab H2D 0.4 nozzle, 0.20 mm Standard, Bambu PETG Basic and Textured PEI, use `enable_support=1`, `support_type=tree(auto)`, `support_on_build_plate_only=0`, `support_threshold_angle=30`, `support_top_z_distance=0.2`, `support_bottom_z_distance=0.2`, and `brim_type=auto_brim` / `brim_width=5`. Bambu Studio 02.08.02.61 sliced the tray successfully with those settings and generated support features. Windsor's stock profile leaves support disabled and therefore reports `FLOATING_REGION`; that result means the unsupported profile is not print-ready, not that CAD should contain a permanent support rib. Inspect the generated supports around the flexure and open grooves before printing. A trial PSU-retention-edge pose (118.8 × 79 × 13.75 mm) was rejected by the 1 mm proxy at the upper flexure layers. Slicer validation does not start a printer job.

Render the two PETG detent coupon pieces separately (the default is the flexure):

```bash
openscad -o /tmp/psu-detent-flexure-coupon.stl hardware/enclosure/powersupply/07_detent_test_coupon_TEST_1.scad
openscad -D coupon_part=1 -o /tmp/psu-detent-groove-coupon.stl hardware/enclosure/powersupply/07_detent_test_coupon_TEST_1.scad
```

The flexure coupon reuses the production tab geometry and edge-on pose; slice it with the tray's support and brim settings. The matching groove is cropped from the production dock and prints flat without support. The coupon is for checking fit and qualitative release feel, not measuring a specified force. Adjust `detent_beam_thickness_z` or `detent_peak_z` in the common source if the printed sample needs tuning, then regenerate and revalidate all affected models.

Physical acceptance is separate: first check the PETG coupon for engagement and deliberate pull release. Then assemble the real dock and tray, confirm full seating, a perceptible click and no PSU rocking, and complete 20 insertion/removal cycles without cracks or permanent flexure deformation. Record physical acceptance separately from CAD and slicer validation.
