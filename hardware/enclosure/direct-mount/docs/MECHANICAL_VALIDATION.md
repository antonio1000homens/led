# Mechanical validation

## File formats

The editable source of truth for the current enclosure is
`../direct_mount_enclosure.scad` (OpenSCAD).

The checked-in `.stl` files are generated manufacturing artefacts for slicing
and printing. They are intentionally not treated as the design source.

STEP would be useful if this design moves to a parametric CAD package that
supports assemblies and mate constraints, but converting the current generated
STLs to STEP would not recover that design intent. Keeping the existing
OpenSCAD source is therefore preferable for this enclosure.

## Why STL alone is not enough

An STL describes triangle surfaces. It does not say:

- which parts are intended to mate;
- where each part sits in the complete assembly;
- the required clearance at an interface;
- where rods, fastener heads or other non-printed hardware occupy space;
- which checks still require a physical part.

`../scripts/assembly_validation.json` supplies that missing assembly intent for CI. Printable meshes are stored under `../stl/`; direct-mount detail/reference views are stored under `../schematics/`; the complete four-panel assembly/projections live in `../../complete_enclosure/`.

## Automated checks

`../scripts/validate_assembly.py` loads the generated STLs with Trimesh and uses the
Manifold boolean engine to check:

1. every generated STL is a finite, watertight, consistently wound closed
   volume;
2. neighbouring backplanes do not occupy the same solid volume;
3. seam joiners fit the declared recesses without unintended solid overlap;
4. nominal 6 mm reinforcement rods pass through all four backplanes;
5. electronics carriers nominally seat on the backplane;
6. installed recessed joiners remain clear of the electronics carriers;
7. the assembled backplane envelope remains within declared bounds;
8. key screw/peg interfaces are checked point-for-point, including seam-joiner screw rows, MatrixPortal/power-carrier M3 centres, and rear-lid peg/socket centres.

The GitHub Actions workflow first regenerates the STLs from OpenSCAD and verifies that the checked-in meshes under `../stl/` are current, then renders the direct-mount detail views under `../schematics/`, the full assembly/projections under `../../complete_enclosure/`, and runs these mechanical checks.

## Resolved automated findings

The geometry-only findings from issue #81 are now enforced as normal passing
checks rather than expected failures:

- finding 1: the lowered alignment tongues clear the recessed joiners;
- finding 2: countersunk seam fasteners allow carriers to clear the installed
  joiners;
- finding 6: the dedicated right-end backplane keeps the four-module printed
  structure inside the 1024 mm envelope.

The first regenerated validation run measured 0.000000 mm³ intersection for
all three joiner/backplane seam checks and both carrier/joiner checks, with the
assembly bounds exactly x=0.000..1024.000 mm.

The manifest still supports `expected_failure` for future known defects, but
none of these three findings remains exempted.

## Physical validation remains necessary

Automated mesh checks cannot prove tolerances after FDM printing or validate
hardware that has not been modelled. The manifest therefore also records
manual validation gates for:

- the real P4 panel mounting pattern;
- rear LED-panel component and connector keep-outs;
- insertion of the real 1 m x 6 mm rods through four printed modules;
- MatrixPortal and power-distribution hardware fit;
- split rod-end plug retention in the chosen filament/printer.

These physical gates remain part of issues #76 and #81.

## Alignment interfaces added for issue #76

The current manifest records the mating coordinates that are easy to miss in a visual STL review:

- panel mounting template and structural backplane share the same six boss coordinates and four locator-clearance coordinates from the common SCAD;
- each PRINT_4 seam-strap screw row lands on the matching heat-set insert row in the two neighbouring backplanes;
- MatrixPortal and power-carrier mounting holes land on the four accessory inserts of their assigned panel;
- rear-lid snap pegs and backplane sockets use identical XY coordinates;
- the desk-stand screw is tied to the lower-centre panel boss.

The MatrixPortal reference is also explicitly oriented **63.5 × 44.45 mm landscape**, with the short USB/button edge facing the outside of Panel 1.
