// Simplified mechanical reference only; not a printable part.
// PCB envelope and mounting-hole locations match the MatrixPortal S3 carrier model.
// The entire left PCB edge is treated as a service/access edge rather than
// hard-coding individual button positions.

module matrixportal_s3_reference(
    pcb_w=44.45,
    pcb_h=63.50,
    pcb_t=1.6,
    hole_x1=15.875,
    hole_x2=35.560,
    hole_y1=15.240,
    hole_y2=55.880
) {
    difference() {
        color("darkgreen") cube([pcb_w,pcb_h,pcb_t]);
        for (xx=[hole_x1,hole_x2])
            for (yy=[hole_y1,hole_y2])
                translate([xx,yy,-0.5]) cylinder(d=2.8,h=pcb_t+1,$fn=32);
    }

    // Continuous left-side service band: USB-C + Reset/Up/Down/Boot live here.
    color("orange",0.55)
        translate([-0.8,2,pcb_t]) cube([1.6,pcb_h-4,2.2]);

    // Approximate component envelope only, for visual clearance checks.
    color("silver",0.6)
        translate([8,12,pcb_t]) cube([28,38,4]);
}
