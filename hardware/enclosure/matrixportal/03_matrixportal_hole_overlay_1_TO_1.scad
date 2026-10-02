// Export as SVG with OpenSCAD --projection=orthogonal. Print at Actual Size.
// Compare all four holes with the physical MatrixPortal before printing the
// adapter. The outline shown is nominal PCB geometry, not a connector model.
include <matrixportal_adapter_common.scad>;

module hole_overlay() {
    difference() {
        square([pcb_w,pcb_h]);
        for (pt = pcb_mount_points)
            translate([pt[0]-pcb_x0,pt[1]-pcb_y0])
                circle(d=pcb_hole_d,$fn=64);
    }
    for (pt = pcb_mount_points)
        translate([pt[0]-pcb_x0,pt[1]-pcb_y0])
            circle(d=5.4,$fn=64);
    // 20 mm scale bar, contained within the PCB outline so SVG page bounds
    // remain exactly the measured 63.50 x 44.45 mm board envelope.
    translate([1,1]) square([20,0.35]);
}

hole_overlay();
