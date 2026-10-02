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
- the narrowed lower insertion tongue uses a tapered print-only pedestal:
  **32 mm wide at the bed**, **6 mm wide at the tongue**, **4 mm overlap** into
  structural material and a **0.8 mm-high** bed layer extending 10 mm beyond
  each end;
- watertight/single-shell geometry after mesh processing;
- bounded printable extents;
- a 2 mm voxel floating-layer/island proxy;
- no volumetric interference between the stationary base and removable backplane;
- positive backplane seating in the recessed rear base groove;
- top-down insertion clearance and 0.6 mm nominal groove clearance;
- dual **40 mm × 5 mm** structural side guides with 0.6 mm running clearance;
- each guide's 16 mm-high lower junction support tied forward into the hinge
  plate/guard at the same height;
- one 26 mm-footprint triangular floor gusset under each guide, full guide width
  and rising to 75% of guide height; the gussets overlap the guide roots while
  staying completely ahead of the insertion slot;
- a **10 mm rearward triangular buttress** at each guide root, tapering to the
  native rail rear face at the guide top while leaving the slot unchanged;
- a low full-width stationary **rear shelf** ending on the common rear plane;
  left/right 1.2 mm-thick upright guardrails continue about **58.5 mm** inward
  from each side guide to the nearest outer rib tab, while the centre span
  remains open apart from the existing X = **128 mm** centre tab;
- the shorter lower stepped/narrowed backplane insertion section and full-width shoulder above it;
- three rear-only tapered transition ribs centred at X = **64 / 128 / 192 mm**.
  The #170 tongue-side rib/guardrail interface remains at **Y=5.1 mm**, while
  a **12 mm rear spine** behind each channel continues through a matching shelf
  pocket to the enclosure floor at **Y=0.5 mm**. A 6 mm full-height centre with
  3 mm print-Z tapers keeps the extension support-free. Each 18 mm guardrail
  channel remains open with 0.6 mm tongue clearance, 1.2 mm tab thickness and
  0.6 mm rear clearance;
- hidden guide-tower junctions kept within the bed-connected lower band;
- blind inside accessory bosses with a solid external rear skin;
- exactly three slimmer accessory-boss rows (7 mm OD × 4 mm high), with the outer rows 22 mm in from the full-depth-region edges and the third row centred;
- the 2 mm seat depth and rear-edge groove location;
- a 54 mm clear-depth universal equipment zone preserving the smaller lower
  guide/insertion section only where the U-channel capture requires it;
- full-width rear-shell coverage immediately above the guide section with no
  X-dependent edge-depth transition;
- a **92 mm structural full-depth rear-wall region**, of which the lower **8 mm**
  is the reinforced shoulder, leaving **84 mm usable full-depth height above the
  shoulder** for the 80 mm PSU plus 4 mm clearance, followed by a restored **12 mm** return ramp;
- three rows of seven **24 mm × 1 mm rounded vent slots** on the reinforced lower
  transition shoulder, with 1.25 mm solid lands, and four rows of seven matching
  slots across the restored **12 mm upper return ramp**, with at least 1.5 mm
  solid material between rows;
- the full-depth M3 boss wall remains solid apart from its blind mounting holes;
- a final **23.5 mm** flat upper wall parallel to the lifted LED panel; the raised
  enclosure supplies the extra ramp height without reducing the PSU envelope,
  and the three aligned 4.5 mm top-row closure holes retain at least 1 mm of
  material from the ramp bend;
- at least 15 mm of vertical release travel through the shortened upper alignment connector;
- no rear cable/ribbon through-slots;
- side-piece fit, hinge-rod clearance, and capped hollow left/right rod sleeves;
- moving/front-panel hinge-root geometry remains unchanged from the existing
  validated template;
- a **20 mm forward extension** of the stationary base floor, retained as a
  flat floor with no shallow front ramp;
- no volumetric intersection between the stationary base and the unchanged
  moving panel throughout the full hinge sweep;
- an unobstructed lower equipment volume ahead of the rear groove;
- the stationary enclosure and 6 mm rail against the moving panel/template at
  **0, 15, 30, 45, 60, 75 and 90°**;
- neighboring module cores at the 256 mm pitch, with side retainers only at
  the outside edges;
- successful open and closed assembly-preview rendering.

The hinge regression contract includes:

- **14 mm** barrel OD;
- **7.2 mm** printed bore for the 6 mm rail;
- installed moving-panel lower edge and hinge axis at **y=40 mm, z=16 mm**,
  representing a **20 mm lift** from the previous 20 mm baseline;
- stationary base floor extended **20 mm toward the front** while remaining
  clear of the full 0–90° moving-panel sweep;
- **7 mm** closed template-to-barrel clearance;
- local roots on the moving template retained at their existing validated
  geometry; no front-panel/template reprint is introduced by this change;
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
256 mm X length. The full-depth rear wall is **92 mm high** overall; its reinforced
8 mm lower shoulder leaves **84 mm of usable full-depth height above it**, restoring
80 mm PSU fit plus 4 mm clearance. The raised enclosure then provides a restored
**12 mm return ramp** carrying four upper ventilation rows before reaching the
**23.5 mm flat upper wall** at the lifted **168 mm** enclosure/panel height.
The full-depth rear mounting wall remains solid.

The manufacturing STL rotates this geometry so installed X becomes print Z.
The only print-only support is the tapered pedestal beneath the narrowed lower
tongue where that tongue starts 1.8 mm above the left-end print bed. It is
32 mm wide at the bed, narrows to 6 mm at the tongue, overlaps 4 mm into the
structural tongue and uses a 0.8 mm sacrificial bed layer. The
backplane reuses the panel's three measured top-row screw positions
(X=7.9/128.0/248.1 mm, installed Y=160.1 mm) as 4.5 mm through-holes. The
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
4. confirm the unchanged moving panel/template never contacts the stationary
   barrel support webs or lower guard through the complete 0–90° motion;
5. print one universal backplane **side-on with its 256 mm length vertical**,
   remove the 0.8 mm sacrificial bed layer and tapered pedestal beneath the
   insertion tongue after cooling,
   then confirm the shortened narrowed lower section slides freely between both 5 mm guides,
   seats 2 mm into the rear groove without the ribs entering the seat, and
   visibly retains the three shallow gaps between the sliding tongue and rear ribs;
6. inspect the new full-width triangular floor gussets beneath both sliders;
   confirm their broad footprints blend into the base and their tapered tops
   blend into the guide fronts without narrowing the sliding channel. Confirm
   the guide towers retain the backplane laterally and the full-width shoulder
   clears their tops; inspect the forward 16 mm-high ties, 10 mm rear guide-root
   buttresses and low full-width rear shelf. Confirm the two outer
   upright guardrails run continuously from each side guide to the nearest rib,
   the centre span remains open, and each 1.2 mm rib tab rises to the Y=5.1 mm
   tongue-side rib lower edge. Verify the 12 mm-wide rear rib foot continues
   below the rail to Y=2.5 mm while retaining 0.6 mm clearance behind the tab
   and leaving the original backplane slot/running clearance unchanged;
7. confirm the 54 mm deep universal region spans the usable backplane width and
   provides **84 mm clear height above the reinforced shoulder**; verify the rounded
   24 × 1 mm vents are confined to three rows on the lower transition and four
   rows across the restored 12 mm upper return ramp, with solid lands between
   all rows while the full-depth boss wall remains solid; the return needs no
   slicer support, the final 23.5 mm upper wall is flat/parallel to the lifted panel, there are
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
