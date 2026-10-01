// Printable replaceable cantilever latch for the selected PSU service tray.
include <service_tray_snap_latch_common.scad>;

// Preserve the assembled orientation because it keeps the cantilever length and
// bending thickness in the XY layer plane, but lower the part so its lowest
// feature sits directly on the print bed.
latch_print_min_z = latch_z - (latch_release_w-latch_arm_w)/2;

translate([0,0,-latch_print_min_z])
    replaceable_snap_latch();
