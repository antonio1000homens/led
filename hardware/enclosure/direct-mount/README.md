# Modular hinged direct-mount enclosure

Issue #133 makes this the **canonical enclosure architecture**.

The repository no longer carries the previous non-hinged rear-backplane/lid
system or the earlier hinge prototypes. All printable enclosure geometry comes
from `direct_mount_enclosure.scad` and five thin wrappers under `parts/`.

## Architecture

```text
LED panel
   |
fixed hinge template
   |
6 mm metal hinge rail
   |
universal hinge/base
   |
lateral captive slide rail
   |
universal equipment backplane
   |
   +-- detachable left side
   +-- detachable right side
   +-- future PSU adapter
   +-- future MatrixPortal adapter
   +-- future power/cable adapters
```

Every hinge/base and every backplane is interchangeable between all four panel
positions. Position- or component-specific behaviour belongs on detachable
side pieces or accessory adapters.

## Canonical printable parts

| Wrapper | Purpose |
| --- | --- |
| `parts/01_panel_hinge_template_PRINT_1.scad` | Fixed panel-side hinge template using the physically corrected P4 mounting geometry |
| `parts/02_hinged_equipment_base_PRINT_1.scad` | Universal moving hinge/base, desk-foot structure and captive backplane rail |
| `parts/03_universal_equipment_backplane_PRINT_1.scad` | Universal slide-in equipment plate with generic M3 adapter bosses |
| `parts/04_left_equipment_side_PRINT_1.scad` | Detachable left end/rail retainer |
| `parts/05_right_equipment_side_PRINT_1.scad` | Detachable right end/rail retainer |

Generated STL binaries are intentionally not versioned. See `stl/README.md`.

## Panel mounting geometry

The six physically corrected brass insert centres remain:

- X = **7.9 / 128.0 / 248.1 mm**
- Y = **7.9 / 120.1 mm**

The four moulded-locator clearance centres remain:

- X = **26.704 / 229.296 mm**
- Y = **12.0 / 116.0 mm**
- clearance diameter = **10 mm**

The nominal panel envelope is 256 × 128 mm. The rear moving/backplane envelope
uses the existing 0.5 mm edge inset.

## Hinge

The proven concealed hinge is retained:

- metal rail: **6.0 mm**
- printed bore: **7.2 mm**
- barrel OD: **13 mm**
- hinge axis: **y=11.5 mm, z=10.5 mm**
- fixed and moving knuckles remain alternating;
- the centre panel screw service gap is preserved.

The moving base can be printed independently, allowing hinge rotation and rail
fit to be tested before printing the full backplane.

## Slide-in backplane

The backplane inserts laterally into a support-friendly captive rail. The rail
uses bed-connected walls and a progressively formed retaining lip instead of a
roofed T-slot, avoiding the floating-region failure mode seen in earlier
iterations.

Nominal mating clearance is **0.4 mm per exposed rail face**.

Once installed, the detachable side pieces close the lateral path and act as
positive backplane retainers. Glue is not part of the normal assembly.

## Universal accessory interface

Every backplane carries the same M3-ready boss grid:

- X = **32 / 80 / 128 / 176 / 224 mm**
- Y = **48 / 80 / 112 mm**
- boss OD = **8 mm**
- boss height = **5 mm**
- through-hole = **3.4 mm**

PSU, MatrixPortal and future electronics should use detachable adapter plates
that attach to this grid. Do not add component-specific footprints to the
universal backplane.

## Side alignment

The base and backplane both expose complementary pin/socket features on their
left and right edges so identical neighbouring modules self-align.

- pin diameter: **4.0 mm**
- socket diameter: **4.7 mm**
- nominal engagement: **4 mm**

These features provide alignment/retention, not the primary structural load.

## Assembly previews

- `schematics/00_hinged_enclosure_ASSEMBLY.scad`
- `schematics/00_hinged_enclosure_CLOSED_ASSEMBLY.scad`

`schematics/matrixportal_s3_REFERENCE.scad` remains as a mechanical reference
for a future detachable MatrixPortal adapter.

## Validation

Run:

```bash
python hardware/enclosure/direct-mount/scripts/validate_enclosure.py
```

CI regenerates every canonical printable part, checks mesh health,
floating-layer proxies, rail interference and representative hinge sweep
clearances. It also renders the open/closed assembly previews.

The final printability gate is Windsor Slicer using the repository-root
`.windsor-slicer.yaml` and the real Bambu Studio H2D profile.

## Physical acceptance order

1. Print one fixed hinge template and one base.
2. Confirm the real 6 mm rail fits and rotates freely.
3. Print one universal backplane and verify full-length rail travel.
4. Print both side pieces and verify pin/socket engagement and slide retention.
5. Verify two identical module assemblies align side-by-side.
6. Fit representative M3 hardware/adapters to the boss grid.
7. Only then print the remaining modules.

PETG remains preferred for the hinge/base and repeatedly used side connectors.
