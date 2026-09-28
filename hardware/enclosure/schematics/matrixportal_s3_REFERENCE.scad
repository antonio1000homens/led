// Simplified mechanical reference only; not a printable part.
//
// Installed orientation matches the real MatrixPortal S3:
//   long dimension  = 63.50 mm along enclosure X
//   short dimension = 44.45 mm along enclosure Y
//
// USB-C and Reset/Up/Down/Boot are on the LEFT SHORT EDGE. That short edge is
// intentionally the edge that overhangs Panel 1 for service access.
//
// The mounting-hole pattern is the PR #84 physical pattern rotated 90 degrees
// into this landscape orientation: 40.640 mm spacing in X and 19.685 mm in Y.

module matrixportal_s3_reference(
    pcb_w=63.50,
    pcb_h=44.45,
    pcb_t=1.6,
    hole_x1=15.240,
    hole_x2=55.880,
    hole_y1=8.890,
    hole_y2=28.575
) {
    difference() {
        color("darkgreen") cube([pcb_w,pcb_h,pcb_t]);
        for (xx=[hole_x1,hole_x2])
            for (yy=[hole_y1,hole_y2])
                translate([xx,yy,-0.5]) cylinder(d=2.8,h=pcb_t+1,$fn=32);
    }

    // Orange band = the physical short service edge carrying USB-C and buttons.
    color("orange",0.70)
        translate([-0.8,1.5,pcb_t])
            cube([1.6,pcb_h-3,2.2]);

    // Approximate populated component envelope only. This is deliberately not
    // a connector-position model; real connector clearance remains a fit test.
    color("silver",0.6)
        translate([18,7,pcb_t]) cube([32,30,4]);
}
