// Assembly-only preview for Panel 1 MatrixPortal side access.
//
// View convention:
// - Panel 1 is the LEFTMOST panel when looking at the illuminated FRONT.
// - This file models the REAR hardware in the same X/Y coordinates.
// - The MatrixPortal long dimension runs horizontally (X).
// - Its SHORT edge (44.45 mm), containing USB-C and Reset/Up/Down/Boot,
//   faces the outside LEFT edge of Panel 1.
//
// Carrier-to-backplane M3 attachment points are shown in blue and are expected
// to land exactly on the four backplane accessory insert centres.
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

// Simplified MatrixPortal PCB reference. Its SHORT service edge sits 10 mm
// outside the Panel 1/backplane x=0 plane.
translate([
    carrier_global_x + matrixportal_pcb_x,
    carrier_global_y + matrixportal_pcb_y,
    carrier_global_z + matrixportal_standoff_z + matrixportal_standoff_h
])
    matrixportal_s3_reference();

// Four carrier/backplane M3 interface points:
// local carrier [6/238, 6/66] + global [6,28]
// => backplane [12/244, 34/94].
for (xx=[accessory_insert_x,module_w-accessory_insert_x])
    for (yy=[accessory_insert_y1,accessory_insert_y2])
        color("blue",0.8)
            translate([xx,yy,depth-1])
                cylinder(d=5,h=8,$fn=24);

// Visual guide for Panel 1 outside/left side plane.
color("red",0.25)
    translate([-0.2,0,0]) cube([0.4,module_h,34]);
