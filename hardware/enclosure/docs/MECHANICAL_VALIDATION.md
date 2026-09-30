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
- the manufacturing wrapper adds five removable under-ramp support ribs, each
  with five vertical posts covering roughly 15% through 95% of the return ramp;
- support ribs sit in solid X bands between ventilation slots and touch the
  ramp through 0.8 mm-wide × 1.0 mm-high breakaway necks;
- the old transverse front/rear stabilisers remain absent;
- watertight/single-shell geometry after mesh processing;
- bounded printable extents;
- a 2 mm voxel floating-layer/island proxy;
- no volumetric interference between the stationary base and removable backplane;
- positive backplane seating in the recessed rear base groove;
- top-down insertion clearance and 0.4 mm nominal groove clearance;
- dual **30 mm × 5 mm** structural side guides with 0.4 mm running clearance;
- the lower 30 mm stepped/narrowed backplane section and full-width shoulder above it;
- hidden guide-tower junctions kept within the bed-connected lower band;
- blind inside accessory bosses with a solid external rear skin;
- exactly two slimmer accessory-boss rows (7 mm OD × 4 mm high), positioned 10 mm in from the lower/upper edges of the full-depth mounting region;
- the 2 mm seat depth and rear-edge groove location;
- a 54 mm clear-depth universal equipment centre zone preserving the lower
  guide-compatible inset only where the U-channel capture requires it;
- an 8 mm 40 -> 54 mm edge-depth transition immediately above the guide towers;
- full-width rear-shell coverage above that transition, with the detachable
  left/right end pieces matching the same deep profile;
- an 86 mm full-depth vertical centre equipment region;
- ramp-only ventilation, with the lower wall and final upper wall remaining solid;
- a final 10 mm flat upper wall parallel to the LED panel and three aligned
  4.5 mm top-row closure holes;
- at least 15 mm of vertical release travel through the shortened upper alignment connector;
- no rear cable/ribbon through-slots;
- side-piece fit, hinge-rod clearance, and integrated left/right rod end stops;
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
- integrated end-piece stops terminating exactly at those rail endpoints while
  remaining clear of the first barrel at X=34 and final barrel end at X=220.

The previous full-width captive tongue/channel is retired. The backplane enters
a 2 mm-deep **recessed groove at the rear of the base**. The shallower side
inset now remains only through the lower U-channel guide interface. Above the
guide towers, an 8 mm transition carries both edge strips back to the same
**54 mm** rear depth as the centre zone, and the detachable end pieces follow
that profile. The 86 mm-high centre zone still provides the PSU-fit volume,
then the enclosure returns toward the panel through a ventilated ramp and
finishes with a **10 mm flat upper wall** at the full 148 mm panel height. The backplane reuses the panel's three measured top-row
screw positions
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
5. print one universal backplane with the removable under-ramp support ribs,
   confirm the print remains stable as it enters and traverses the return ramp,
   remove the ribs after cooling, then confirm the narrowed lower 30 mm slides
   between both 5 mm guides, seats 2 mm into the rear groove, and removes upward;
6. confirm the guide towers retain the backplane laterally and the full-width shoulder clears their tops;
7. confirm the 54 mm deep universal region spans the usable backplane width,
   ventilation exists only in the return ramp, the final 10 mm upper wall is
   flat/parallel to the panel, there are no rear cable/ribbon through-slots, and
   all three 4.5 mm top closure holes align with the panel's top-row mounting points;
8. verify the hidden guide-tower junctions and both outer side pieces engage,
   all exterior faces remain solid, and each integrated rod end stop reaches
   its rail endpoint without extending into a hinge-barrel span;
9. mate two equipment cores side-by-side at the 256 mm pitch and check the hidden pin/socket alignment;
10. test representative M3 hardware on the inward-facing lower boss grid and verify the external rear skin is unbroken;
11. verify connected HUB75/power cabling remains free through the opening arc.

Record tolerance changes in `direct_mount_enclosure.scad`; never patch an STL directly.
