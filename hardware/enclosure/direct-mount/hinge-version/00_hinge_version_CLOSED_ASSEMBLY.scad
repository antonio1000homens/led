hinge_part = "__preview__";
include <hinge_version.scad>;

// Closed-position inspection:
// - fixed template at z=0..2 mm;
// - moving enclosure front rim at z=2.6 mm;
// - concealed 6 mm rail hinge at y=6.5, z=10.5 mm.
hinge_version_assembly(0);
