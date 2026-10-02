# Enclosure-centred PSU service tray

Issue #177 replaces the fixed dock's front screw-mounted latch with a pull-release flexure integral to the removable tray. Source geometry is OpenSCAD; checked-in meshes are generated artifacts.

## Parts and interface

| File | Purpose |
| --- | --- |
| `01_service_tray_snap_latch.scad` | Dock/tray assembly preview |
| `02_service_tray_snap_dock_PRINT_1.scad` | Fixed dock with enclosure pockets, runners, stop and underside detent groove |
| `03_service_tray_snap_tray_PRINT_1.scad` | Removable tray with open-ended runner grooves and integral flexure |
| `05_backplane_fit_preview.scad` | Actual enclosure backplane, fit states, PSU envelope and detent section |
| `06_boss_heatset_insert_test.scad` | Optional M3 insert test coupon for the enclosure's blind boss holes |
| `psu_mount_common.scad` | PSU measurements and common mount geometry |
| `service_tray_snap_latch_common.scad` | Dock, tray and flexure geometry |
| `../psu_adapter_interface.scad` | Shared geometry-free mounting-grid offsets and column selection |

## Measured dimensions

The enclosure's reinforced 8 mm shoulder leaves a usable cavity from Y=48.5 to 132.5 mm, centred at Y=90.5. The shared grid uses five X columns `[32,80,128,176,224]` and rows `[71.5,90.5,109.5]`. The dock selects columns 80 and 176, represented locally by X=±48 and row offsets Y=−19/0/+19. The other enclosure bosses remain available for accessories; the dock has relief for the two upper/lower bosses in the unused X=128 column.

A revised dock only fits a backplane with the revised boss rows. Previously printed backplanes retain Y=67.5/86.5/105.5 and will not align. The dock and tray remain 118 × 79 mm and 114 × 79 × 2.8 mm respectively. The 110 × 80 × 37 mm PSU overhangs the tray by 0.5 mm per side. Its diagonally opposed pilots are at (−52,−37) and (+52,+37), Ø2.8 mm. The pilot edge retains 1.1 mm of material.

The two support bars and PSU screw bosses share a top plane at tray-local Z=4.8 mm (2.8 mm plate + 2 mm support). Bars are at X=±34 mm, 5 mm wide and 66 mm long. This is separate from the six enclosure fixings (Ø3.6 clearance, Ø7 × 0.8 mm head recess, Ø7.5 × 1.2 mm locating pockets).

## Slide and pull-release flexure

The tray inserts along +X. Two internal runners at Y=±25 mm use a 2.4 mm base, 4 mm top and 1.8 mm height. Their 96 mm length ends at X=+39 mm; the former +49 mm end was shortened by 10 mm. Matching grooves retain 0.3 mm lateral clearance and open through the tray's +X leading edge. A separate wall at +X stops insertion.

The tray flexure wraps around the dock's −X edge. Its initial PETG coupon geometry uses a 30 mm cantilever, 5 mm X width and 1.2 mm thickness, with 0.5 mm nominal detent engagement into a 0.8 mm deep underside groove (0.3 mm seated clearance above the detent). Pulling the tray cams the detent down; no button press is needed. Beam thickness and engagement are parameters for physical tuning. No release-force value has been measured. Check deflection against the actual backplane and use a PETG coupon before relying on repeated flexing.

Use six M3 ISO 7380 button-head screws with head diameter no greater than 5.7 mm and height no greater than 1.65 mm. With the 0.8 mm recess, the head sits 0.75 mm below the 4.8 mm PSU support plane. Other screw heads require a fresh clearance check.

The dock's six bosses have a nominal 4 mm height and overlap the 3 mm backplane by 0.3 mm, leaving 3.7 mm exposed toward the dock. The assembly preview places the dock so those tips enter the registration pockets by 1.2 mm. The shared interface preserves Ø7 bosses, Ø3.4 blind holes and the 1.2 mm external wall skin. Confirm screw-head clearance for the actual hardware before assembly.

## Render and validate

From the repository root:

```bash
python hardware/enclosure/scripts/generate_stls.py --output-dir build/enclosure-stls
python hardware/enclosure/scripts/validate_psu_adapter.py --generated-dir build/enclosure-stls
python hardware/enclosure/scripts/validate_enclosure.py --generated-dir build/enclosure-stls --workers 4
python hardware/enclosure/scripts/verify_canonical_stls.py --generated-dir build/enclosure-stls
```

The canonical model IDs remain `psu-service-tray-dock` and `psu-service-tray-tray`. Windsor Slicer validation used Bambu Lab H2D 0.4 nozzle, 0.20 mm Standard, Bambu PETG Basic and Textured PEI. The fixed dock prints flat and passes with no warnings. The retained tray wrapper stands the plate on its 2.8 mm lower edge for a 118.8 × 12.75 × 79 mm print pose. Ten removable print tethers bridge the underside flexure to the tray edge; clip them away before assembly. The earlier tray mesh reported `FLOATING_REGION`; the tethers now fuse to both parts and the 1 mm floating-layer proxy passes. Revalidate this exact revision with Bambu Studio before treating it as print-ready. A trial PSU-retention-edge pose (118.8 × 79 × 12.75 mm) was rejected by the 1 mm floating-layer proxy at the upper flexure layers. Inspect support needs for the underside flexure and open grooves in the exact H2D slice. Slicer validation does not start a printer job.

Physical acceptance is separate: print a PETG detent coupon, assemble the real dock and tray, confirm full seating/click/pull release and no PSU rocking, then complete 20 insertion/removal cycles without cracks or permanent flexure deformation.
