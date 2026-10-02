# Canonical STL outputs

The printable STL meshes in this directory are **versioned manufacturing
outputs** generated from the canonical OpenSCAD wrappers in `../parts/` and
`../powersupply/`.

The SCAD files remain the editable source of truth, but each production print
wrapper has a matching checked-in STL so the current design can be inspected or
loaded directly into Bambu Studio without relying on an expiring CI artifact.

Canonical pairs:

- `../parts/01_panel_hinge_template_PRINT_1.scad`
  → `01_panel_hinge_template_PRINT_1.stl`
- `../parts/02_hinged_equipment_base_PRINT_1.scad`
  → `02_hinged_equipment_base_PRINT_1.stl`
- `../parts/03_universal_equipment_backplane_PRINT_1.scad`
  → `03_universal_equipment_backplane_PRINT_1.stl`
- `../parts/04_left_equipment_side_PRINT_1.scad`
  → `04_left_equipment_side_PRINT_1.stl`
- `../parts/05_right_equipment_side_PRINT_1.scad`
  → `05_right_equipment_side_PRINT_1.stl`
- `../powersupply/02_service_tray_snap_dock_PRINT_1.scad`
  → `06_psu_service_tray_snap_dock_PRINT_1.stl`
- `../powersupply/03_service_tray_snap_tray_PRINT_1.scad`
  → `07_psu_service_tray_snap_tray_PRINT_1.stl`
- `../powersupply/04_service_tray_snap_latch_PRINT_1.scad`
  → `08_psu_service_tray_snap_latch_PRINT_1.stl`

## Development workflow

During creation/iteration:

```bash
python hardware/enclosure/scripts/generate_stls.py
```

Then:

1. edit the SCAD;
2. regenerate the matching STL;
3. inspect/validate geometry;
4. when useful, explicitly run Windsor Slicer/Bambu Studio to validate actual
   printability;
5. iterate until satisfied;
6. commit the final SCAD and matching STL together.

Bambu slicing is **not** a normal GitHub Actions/PR step. Generated `.3mf`
files are iteration/validation artifacts and are not canonical repository
outputs.

## Pull-request validation

GitHub Actions regenerates all **eight** canonical STLs with OpenSCAD and runs
the normal mechanical/geometry checks. The regenerated meshes are also uploaded
as a downloadable workflow artifact.

CI additionally verifies that each regenerated mesh is geometrically equivalent
to the corresponding checked-in STL, preventing SCAD and STL from drifting.
