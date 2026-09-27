# Hinged enclosure mechanical validation

The modular hinged design is the only supported direct-mount enclosure.

The canonical hinge motion follows PR #119: the equipment-side enclosure/base
remains stationary and the LED panel/template is the moving leaf.

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
- no volumetric interference between the stationary base and removable backplane;
- the stationary equipment enclosure against the moving panel/template at
  **0, 15, 30, 45, 60, 75 and 90°**;
- successful open and closed assembly-preview rendering.

The hinge regression contract includes:

- **14 mm** barrel OD;
- **7.2 mm** printed bore for the 6 mm rail;
- hinge axis at **y=27 mm, z=16 mm**;
- **7 mm** closed template-to-barrel clearance;
- local roots on the moving template only;
- rearward bottom-tangent support webs on the stationary hinge knuckles;
- **2 mm** stationary lower guard with **0.8 mm** barrel clearance.

The final automated manufacturing gate is Windsor Slicer/Bambu Studio using the
models in `.windsor-slicer.yaml`.

## Physical gates

Automated geometry cannot prove real FDM tolerances. Before printing four full
sets:

1. print one moving panel/template leaf and verify the six physical panel bosses;
2. print one stationary equipment base and verify the real 6 mm rail;
3. rotate the panel/template through the full **0–90°** arc while the equipment base remains fixed;
4. confirm the moving panel never contacts the stationary barrel support webs or lower guard;
5. print one universal backplane and confirm the 0.4 mm nominal slide clearance;
6. verify both side pieces engage the stationary base/backplane and retain the slide;
7. mate two identical equipment assemblies side-by-side and check pin/socket alignment;
8. test representative M3 hardware on the universal boss grid;
9. verify connected HUB75/power cabling remains free through the opening arc.

Record tolerance changes in `direct_mount_enclosure.scad`; never patch an STL directly.
