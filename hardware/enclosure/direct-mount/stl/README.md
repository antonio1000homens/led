# Generated STL output

The hinged enclosure is the only supported direct-mount mechanical design.

Manufacturing STLs are generated from the canonical OpenSCAD wrappers in
`../parts/` rather than checked into Git. This prevents stale binary meshes
from surviving after their source changes.

Canonical outputs:

- `01_panel_hinge_template_PRINT_1.stl`
- `02_hinged_equipment_base_PRINT_1.stl`
- `03_universal_equipment_backplane_PRINT_1.stl`
- `04_left_equipment_side_PRINT_1.stl`
- `05_right_equipment_side_PRINT_1.stl`

Use OpenSCAD locally or Windsor Slicer via the repository-root
`.windsor-slicer.yaml`. Windsor Slicer is the final Bambu Studio/H2D
printability gate.
