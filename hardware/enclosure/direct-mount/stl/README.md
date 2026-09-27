# Canonical STL outputs

The printable STL meshes in this directory are **versioned manufacturing
outputs** generated from the canonical OpenSCAD wrappers in `../parts/`.

The SCAD files remain the editable source of truth, but each production SCAD
wrapper must have a matching checked-in STL so a user can inspect or print the
current design directly from the repository.

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

## Development workflow

During creation/iteration:

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

GitHub Actions regenerates all five STLs with OpenSCAD and performs the
mechanical/geometry checks. The regenerated meshes are also uploaded as a
downloadable workflow artifact.

CI additionally verifies that each regenerated mesh is geometrically equivalent
to the corresponding checked-in STL, preventing SCAD and STL from drifting.
