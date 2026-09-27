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
- a 2 mm voxel floating-layer/island proxy;
- no volumetric interference between the stationary base and removable backplane;
- positive backplane contact with the base floor edge;
- top-down insertion clearance and 0.4 mm nominal side-guide clearance;
- shallow perimeter guide limits and side-retainer fit;
- an unobstructed base interior above the floor seat;
- the stationary enclosure and 6 mm rail against the moving panel/template at
  **0, 15, 30, 45, 60, 75 and 90°**;
- neighboring module cores at the 256 mm pitch, with side retainers only at
  the outside edges;
- successful open and closed assembly-preview rendering.

The hinge regression contract includes:

- **14 mm** barrel OD;
- **7.2 mm** printed bore for the 6 mm rail;
- hinge axis at **y=27 mm, z=16 mm**;
- **7 mm** closed template-to-barrel clearance;
- local roots on the moving template only;
- rearward support webs that terminate at the reinforced hinge shelf;
- 3 mm local pads at the stationary hinge roots;
- **2 mm** stationary lower guard with **0.8 mm** barrel clearance.

The previous full-width captive tongue/channel is retired. The backplane is a
plain plate with a lower edge seated on the base; detachable side pieces provide
shallow guides at the perimeter. The validator checks the final contact and
several positions along the vertical insertion path, alongside the hinge sweep.

The final automated manufacturing gate is Windsor Slicer/Bambu Studio using the
models in `.windsor-slicer.yaml`.

## Physical gates

Automated geometry cannot prove real FDM tolerances. Before printing four full
sets:

1. print one moving panel/template leaf and verify the six physical panel bosses;
2. print one stationary equipment base and verify the real 6 mm rail;
3. rotate the panel/template through the full **0–90°** arc while the equipment base remains fixed;
4. confirm the moving panel never contacts the stationary barrel support webs or lower guard;
5. print one universal backplane and confirm top-down insertion, base-edge seating, and upward removal;
6. verify both side pieces engage the stationary base and guide the backplane edges;
7. mate two equipment cores side-by-side at the 256 mm pitch, add retainers at
   the outside edges, and check pin/socket alignment;
8. test representative M3 hardware on the universal boss grid;
9. verify connected HUB75/power cabling remains free through the opening arc.

Record tolerance changes in `direct_mount_enclosure.scad`; never patch an STL directly.
