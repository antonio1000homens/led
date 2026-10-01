// Printable replaceable cantilever latch for the selected PSU service tray.
include <service_tray_snap_latch_common.scad>;

// Preserve the assembled orientation so the cantilever length and bending
// thickness remain in the XY layer plane. In the source assembly the latch is
// elevated to meet the tray; for printing, move that common bottom plane to Z=0.
translate([0,0,-latch_z])
    replaceable_snap_latch();
