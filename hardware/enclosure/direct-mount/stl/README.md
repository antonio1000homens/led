# Generated enclosure STLs

This directory contains the **generated manufacturing meshes** for the direct-mount enclosure.

Do not edit these STL files by hand.

Source of truth:

- `../direct_mount_enclosure.scad`
- the individual `../parts/*_PRINT_*.scad` entrypoints

The `Enclosure / Validate` workflow regenerates the complete STL set with OpenSCAD and compares canonical triangle geometry against these checked-in files.

Use these files for slicing/printing. Change shared geometry in `../direct_mount_enclosure.scad` and use the launchers in `../parts/` for individual parts.
