# Hinged enclosure mechanical validation

The modular hinged design is the only supported direct-mount enclosure.

The canonical hinge motion follows PR #119: the equipment-side enclosure/base
remains stationary and the LED panel/template is the moving leaf.

## Automated gates

Run:

```bash
python hardware/enclosure/scripts/validate_enclosure.py
```

The validator regenerates all five canonical OpenSCAD parts and verifies:

- non-empty positive-volume meshes;
- the installed backplane contains no permanent rear support feet;
- the manufacturing wrapper rotates the backplane so its **256 mm X dimension
  is the print-vertical axis**;
- the shell above the guide section keeps one constant Y/Z profile across X;
- the old under-ramp support forest and transverse front/rear stabilisers remain
  absent;
- the narrowed lower insertion tongue uses one **1.0 mm-thick** print-only
  breakaway support strip with **0.4 mm overlap**;
- watertight/single-shell geometry after mesh processing;
- bounded printable extents;
- a 2 mm voxel floating-layer/island proxy;
- no volumetric interference between the stationary base and removable backplane;
- positive backplane seating in the recessed rear base groove;
- top-down insertion clearance and 0.6 mm nominal groove clearance;
- dual **40 mm × 5 mm** structural side guides with 0.6 mm running clearance;
- the shorter lower stepped/narrowed backplane insertion section and full-width shoulder above it;
- hidden guide-tower junctions kept within the bed-connected lower band;
- blind inside accessory bosses with a solid external rear skin;
- exactly three slimmer accessory-boss rows (7 mm OD × 4 mm high), with the outer rows 22 mm in from the full-depth-region edges and the third row centred;
- the 2 mm seat depth and rear-edge groove location;
- a 54 mm clear-depth universal equipment zone preserving the smaller lower
  guide/insertion section only where the U-channel capture requires it;
- full-width rear-shell coverage immediately above the guide section with no
  X-dependent edge-depth transition;
- an **84 mm** full-depth equipment region followed by a **12 mm** return ramp;
- seven **24 mm × 1 mm rounded vent slots** on the reinforced lower transition shoulder and
  seven matching slots on the upper return ramp;
- a solid full-depth rear mounting wall for the inward-facing M3 boss grid;
- a final 11.5 mm flat upper wall parallel to the LED panel, keeping at least 1 mm of material between the ramp bend and the three aligned
  4.5 mm top-row closure holes;
- at least 15 mm of vertical release travel through the shortened upper alignment connector;
- no rear cable/ribbon through-slots;
- side-piece fit, hinge-rod clearance, and capped hollow left/right rod sleeves;
- an unobstructed lower equipment volume ahead of the rear groove;
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
- **2 mm** stationary lower guard with **0.8 mm** barrel clearance;
- **6 mm rail from X=10 to X=246 mm**;
- side-piece rod supports matching the **14 mm hinge-barrel OD** with a
  **7.2 mm clearance bore** around the rod span;
- capped outer sections retaining the rail at X=10/246, with hollow sleeves
  continuing from those endpoints to the first barrel at X=34 and final barrel
  end at X=220.

The previous full-width captive tongue/channel is retired. The backplane enters
a 2 mm-deep **recessed groove at the rear of the base**. The shorter lower U-channel
insertion section remains narrower and shallower, but immediately above the
guide tops the backplane uses one full-width **54 mm** profile across the entire
256 mm X length. The full-depth section is **84 mm high**, followed by a stronger
**12 mm** return and an **11.5 mm flat upper wall** at the full 148 mm panel height.
Horizontal rear-wall vents replace the old installed-vertical ramp slots.

The manufacturing STL rotates this geometry so installed X becomes print Z.
The only print-only support is a low breakaway strip beneath the narrowed lower
tongue where that tongue starts 1.8 mm above the left-end print bed. The
backplane reuses the panel's three measured top-row screw positions
(X=7.9/128.0/248.1 mm, installed Y=140.1 mm) as 4.5 mm through-holes. The
validator proves those coordinates remain tied to the panel source geometry and
that all three holes are clear, together with the rear-groove contract, vertical
insertion path, lower usable cavity and complete hinge sweep.

The final automated manufacturing gate is Windsor Slicer/Bambu Studio using the
models in `.windsor-slicer.yaml`.

## Physical gates

Automated geometry cannot prove real FDM tolerances. Before printing four full
sets:

1. print one moving panel/template leaf and verify the six physical panel bosses;
2. print one stationary equipment base and verify the real 6 mm rail;
3. fit the three top closure screws in the closed position, then remove/loosen
   them before rotating the panel/template through the full **0–90°** arc while
   the equipment base remains fixed;
4. confirm the moving panel never contacts the stationary barrel support webs or lower guard;
5. print one universal backplane **side-on with its 256 mm length vertical**,
   remove the small breakaway strip beneath the insertion tongue after cooling,
   then confirm the shortened narrowed lower section slides freely between both 5 mm guides,
   seats 2 mm into the rear groove, and removes upward;
6. confirm the guide towers retain the backplane laterally and the full-width shoulder clears their tops;
7. confirm the 54 mm deep universal region spans the usable backplane width,
   the rounded 24 × 1 mm vents are confined to the reinforced lower transition and longer upper return
   ramp, the long rear boss-mount wall remains solid, the ramps need no slicer
   supports, the final 11.5 mm upper wall is flat/parallel to the panel, there are
   no rear cable/ribbon through-slots, and all three 4.5 mm top closure holes
   align with the panel's top-row mounting points;
8. verify the hidden guide-tower junctions and both outer side pieces engage,
   all exterior faces remain solid, each capped rod stop retains the rail at
   X=10/246, and the hollow 7.2 mm sleeve continues around the rod to the nearest
   hinge barrel without binding;
9. mate two equipment cores side-by-side at the 256 mm pitch and check the hidden pin/socket alignment;
10. test representative M3 hardware on all three inward-facing boss rows and verify the external rear skin is unbroken;
11. verify connected HUB75/power cabling remains free through the opening arc.

Record tolerance changes in `direct_mount_enclosure.scad`; never patch an STL directly.
