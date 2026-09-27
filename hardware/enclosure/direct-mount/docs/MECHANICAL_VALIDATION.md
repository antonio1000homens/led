# Hinged enclosure mechanical validation

The modular hinged design is the only supported direct-mount enclosure.

## Automated gates

Run:

```bash
python hardware/enclosure/direct-mount/scripts/validate_enclosure.py
```

The validator regenerates all five canonical OpenSCAD parts and verifies:

- non-empty positive-volume meshes;
- watertight/single-shell geometry after mesh processing;
- bounded printable extents;
- a coarse floating-layer/island proxy;
- no volumetric interference between installed base and backplane;
- representative base/fixed-template hinge sweep clearance through the designed **72°** service angle;
- successful open and closed assembly-preview rendering.

The final automated manufacturing gate is Windsor Slicer/Bambu Studio using the
models in `.windsor-slicer.yaml`.

## Physical gates

Automated geometry cannot prove real FDM tolerances. Before printing four full
sets:

1. print one panel hinge template and verify the six physical panel bosses;
2. print one hinge/base and verify the real 6 mm rail and full service rotation;
3. print one universal backplane and confirm the 0.4 mm nominal slide clearance;
4. verify both side pieces engage base and backplane and retain the slide;
5. mate two identical assemblies side-by-side and check pin/socket alignment;
6. test representative M3 hardware on the universal boss grid;
7. verify connected HUB75/power cabling remains free through the opening arc.

Record any tolerance adjustment in `direct_mount_enclosure.scad`; never patch
an STL mesh directly.
