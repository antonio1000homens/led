# Generated enclosure STLs

This directory contains the **generated manufacturing meshes** for the direct-mount enclosure.

Do not edit these STL files by hand.

Source of truth:

- `../direct_mount_enclosure.scad`
- the individual `../*_PRINT_*.scad` entrypoints

The `Enclosure / Validate` workflow regenerates the complete STL set with OpenSCAD and compares canonical triangle geometry against these checked-in files.

Use these files for slicing/printing. Use the SCAD files one directory above for design changes.
