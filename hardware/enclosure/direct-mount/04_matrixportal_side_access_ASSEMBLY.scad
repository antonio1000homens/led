// Assembly-only preview for Panel 1 MatrixPortal left-side access.
part = "__library__";
include <direct_mount_enclosure.scad>;
include <matrixportal_s3_REFERENCE.scad>;

carrier_global_x = 6;
carrier_global_y = 28;
carrier_global_z = 16;

// Panel 1 backplane.
color("dimgray")
    backplane(false);

// Printed MatrixPortal carrier.
color("black")
    translate([carrier_global_x,carrier_global_y,carrier_global_z])
        matrixportal_mount();

// Simplified MatrixPortal PCB reference. Its left edge sits 10 mm outside
// the Panel 1/backplane x=0 plane, making the complete left service edge
// reachable from the enclosure side.
translate([
    carrier_global_x + matrixportal_pcb_x,
    carrier_global_y + matrixportal_pcb_y,
    carrier_global_z + matrixportal_standoff_z + matrixportal_standoff_h
])
    matrixportal_s3_reference();

// Visual guide for the Panel 1 left side plane.
color("red",0.25)
    translate([-0.2,0,0]) cube([0.4,module_h,34]);
