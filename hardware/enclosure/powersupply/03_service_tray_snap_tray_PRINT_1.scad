// Printable removable tray with integral pull-release flexure for issue #177.
include <service_tray_snap_latch_common.scad>;

// Stand the plate on its long lower edge. This puts the flexure anchor at the
// first layers so the 30 mm cantilever builds upward instead of leaving the
// main plate floating above a bed-side spring. Z=0 is the tray's Y=+39.5 edge.
translate([0,0,tray_h/2])
    rotate([-90,0,0])
        snap_tray_with_detent_printable();
