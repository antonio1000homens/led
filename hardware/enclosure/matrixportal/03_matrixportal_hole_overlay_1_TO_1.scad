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

    // Dimensions and orientation notes sit outside the board outline. All
    // coordinates remain millimetres, so the exported SVG stays 1:1.
    translate([0,-6])
        text("MATRIXPORTAL S3 PCB OUTLINE 63.50 x 44.45 mm - PRINT AT 100%",
             size=2.0,halign="left",valign="center");
    translate([0,-10])
        text("Hole centres from lower-left: X 7.620 / 48.260; Y 15.875 / 35.560 mm",
             size=1.7,halign="left",valign="center");
    translate([0,pcb_h+2])
        text("USB-C / BUTTON SERVICE EDGE  ->  RIGHT",
             size=1.8,halign="left",valign="center");
    translate([28,-3])
        text("X pitch 40.640 mm; Y pitch 19.685 mm",
             size=1.8,halign="center",valign="center");
}

hole_overlay();
