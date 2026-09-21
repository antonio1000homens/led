# Mechanical validation

## File formats

The editable source of truth for the current enclosure is
`direct_mount_enclosure.scad` (OpenSCAD).

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

`assembly_validation.json` supplies that missing assembly intent for CI.

## Automated checks

`validate_assembly.py` loads the generated STLs with Trimesh and uses the
Manifold boolean engine to check:

1. every generated STL is a finite, watertight, consistently wound closed
   volume;
2. neighbouring backplanes do not occupy the same solid volume;
3. seam joiners fit the declared recesses without unintended solid overlap;
4. nominal 8 mm reinforcement rods pass through all four backplanes;
5. electronics carriers nominally seat on the backplane;
6. declared hardware envelopes such as seam screw heads do not collide with
   carrier geometry;
7. the assembled backplane envelope remains within declared bounds.

The GitHub Actions workflow first regenerates the STLs from OpenSCAD and
verifies that the checked-in meshes are current, then runs these mechanical
checks.

## Known failures

Existing unresolved mechanical findings from issue #81 are represented as
`expected_failure` checks. They are printed as `XFAIL` rather than silently
being treated as compatible.

At present this includes:

- finding 1: alignment tongue / recessed joiner interference;
- finding 2: representative seam screw-head / carrier interference;
- finding 6: rightmost alignment tongue extending the nominal 1024 mm
  backplane envelope.

When one of these designs is corrected, remove its
`expected_failure` marker so the interface becomes a required passing check.

## Physical validation remains necessary

Automated mesh checks cannot prove tolerances after FDM printing or validate
hardware that has not been modelled. The manifest therefore also records
manual validation gates for:

- the real P4 panel mounting pattern;
- rear LED-panel component and connector keep-outs;
- insertion of the real 1 m x 8 mm rods through four printed modules;
- MatrixPortal and power-distribution hardware fit.

These physical gates remain part of issues #76 and #81.
