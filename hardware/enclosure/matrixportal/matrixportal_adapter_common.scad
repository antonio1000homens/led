// Issue #178 MatrixPortal S3 screw-on adapter.
// Prototype dimensions follow the non-printing mechanical reference. Confirm
// populated-board, connector and cable clearances against the real board.

include <../direct_mount_enclosure.scad>;
include <../schematics/matrixportal_s3_REFERENCE.scad>;

mp_adapter_w = 66;
mp_adapter_h = 60;
mp_adapter_t = 3.2;
mp_adapter_corner_r = 3;
mp_adapter_centre_x = 222;
mp_adapter_centre_y = 90.5;

pcb_w = 63.5;
pcb_h = 44.45;
pcb_t = 1.6;
pcb_x0 = -32;
pcb_y0 = -22.225;
pcb_standoff_h = 8;
pcb_hole_d = 2.8;
pcb_standoff_d = 8;
pcb_nut_af = 5.0; // M2.5 hex nut nominal across-flats prototype pocket
pcb_nut_depth = 2.2;
pcb_nut_pocket_clearance = 0.25;

enclosure_columns = [224];
enclosure_rows = [71.5, 90.5, 109.5];
boss_d = 7;
boss_h = 4;
boss_overlap = 0.3;
boss_projection = boss_h - boss_overlap;
boss_pocket_d = 7.5;
boss_pocket_depth = 1.2;
enclosure_screw_clearance_d = 3.6;
enclosure_screw_head_d = 7;
enclosure_screw_head_depth = 0.8;
// The local -Z mounting face points toward the wall (+global Z after the
// assembly flip). The pocket roof sits 1.2 mm beyond the cavity-facing tip.
mp_adapter_wall_z = universal_deep_front_z;
adapter_boss_tip_z = mp_adapter_wall_z - boss_h + boss_overlap;
adapter_back_z = adapter_boss_tip_z + boss_pocket_depth;
backplane_connector_clearance = 0.4;
connector_relief_global_x0 =
    service_x + service_w - top_connector_pad_w - backplane_connector_clearance;
connector_relief_global_x1 = mp_adapter_centre_x + mp_adapter_w/2 + 1;
connector_relief_global_y0 = top_connector_pad_y0-backplane_connector_clearance;
connector_relief_global_y1 = top_connector_pad_y1+backplane_connector_clearance;
connector_relief_depth =
    adapter_back_z - (universal_deep_rear_z-top_connector_pad_depth)
        + backplane_connector_clearance;

// Board-hole coordinates from the lower-left after 180 degree in-plane turn.
pcb_hole_x = [7.62, 48.26];
pcb_hole_y = [15.875, 35.56];
pcb_mount_points = [
    for (x = pcb_hole_x)
        for (y = pcb_hole_y)
            [pcb_x0 + x, pcb_y0 + y]
];

function hex_circumdiameter(across_flats) =
    across_flats / cos(30);

module rounded_adapter_outline() {
    offset(r=mp_adapter_corner_r)
        square([mp_adapter_w-2*mp_adapter_corner_r,
                mp_adapter_h-2*mp_adapter_corner_r], center=true);
}

module enclosure_mount_cutters() {
    for (xx = enclosure_columns)
        for (yy = enclosure_rows) {
            lx = xx-mp_adapter_centre_x;
            ly = yy-mp_adapter_centre_y;
            // Clear the projecting boss from the adapter's back face.
            translate([lx,ly,-0.01])
                cylinder(d=boss_pocket_d,h=boss_pocket_depth+0.01);
            // Through screw clearance and a head recess on the board-facing face.
            translate([lx,ly,-0.01])
                cylinder(d=enclosure_screw_clearance_d,h=mp_adapter_t+0.02);
            translate([lx,ly,mp_adapter_t-enclosure_screw_head_depth])
                cylinder(d=enclosure_screw_head_d,
                         h=enclosure_screw_head_depth+0.02);
        }
}

module pcb_standoffs() {
    for (pt = pcb_mount_points)
        translate([pt[0],pt[1],mp_adapter_t])
            cylinder(d=pcb_standoff_d,h=pcb_standoff_h,$fn=48);
}

module pcb_standoff_cutters() {
    for (pt = pcb_mount_points) {
        // Through clearance; hexagonal captive-nut pocket opens from the top.
        translate([pt[0],pt[1],-0.01])
            cylinder(d=pcb_hole_d,h=mp_adapter_t+pcb_standoff_h+0.02,$fn=32);
        // Side-load the nut so the PCB seats directly on the post top. The
        // screw enters from above and threads into the retained nut below it.
        translate([pt[0],pt[1],mp_adapter_t+pcb_standoff_h-pcb_nut_depth-0.5])
            cylinder(d=hex_circumdiameter(pcb_nut_af)+pcb_nut_pocket_clearance,
                     h=pcb_nut_depth+0.02,$fn=6);
        translate([pt[0]-pcb_standoff_d/2-0.01,
                   pt[1]-(pcb_nut_af+pcb_nut_pocket_clearance)/2,
                   mp_adapter_t+pcb_standoff_h-pcb_nut_depth-0.5])
            cube([pcb_standoff_d/2+0.02,pcb_nut_af+pcb_nut_pocket_clearance,
                  pcb_nut_depth+0.02]);
    }
}

module backplane_connector_clearance_cutter() {
    // The top-right module seam pad projects 6.5 mm from the backplane.
    // Its shallow taper reaches the adapter's rear edge; pocket that region
    // without touching the PCB standoff lands or modifying enclosure geometry.
    translate([
        connector_relief_global_x0-mp_adapter_centre_x,
        mp_adapter_centre_y-connector_relief_global_y1,
        -0.01
    ])
        cube([
            connector_relief_global_x1-connector_relief_global_x0,
            connector_relief_global_y1-connector_relief_global_y0,
            connector_relief_depth+0.01
        ]);
}

module matrixportal_adapter() {
    difference() {
        union() {
            linear_extrude(height=mp_adapter_t)
                rounded_adapter_outline();
            pcb_standoffs();
        }
        enclosure_mount_cutters();
        pcb_standoff_cutters();
        backplane_connector_clearance_cutter();
    }
}

module matrixportal_adapter_installed(show_board=true) {
    translate([mp_adapter_centre_x,mp_adapter_centre_y,adapter_back_z]) {
        // Local +Z is cavity-facing; flip the print pose over the X axis for
        // installation against the backplane. This mirrors local Y only.
        rotate([180,0,0]) {
            matrixportal_adapter();
            if (show_board)
                translate([pcb_x0+pcb_w/2,pcb_y0+pcb_h/2,
                           mp_adapter_t+pcb_standoff_h])
                    rotate([0,0,180])
                        translate([-pcb_w/2,-pcb_h/2,0])
                            matrixportal_s3_reference();
        }
    }
}

module matrixportal_adapter_print_pose() {
    // Print the plate face-down with standoffs vertical. The mounting recesses
    // remain open to the build plate; the 3.2 mm plate contacts Z=0.
    matrixportal_adapter();
}

assert(mp_adapter_w == 66 && mp_adapter_h == 60 && mp_adapter_t == 3.2,
       "Issue #178 adapter prototype envelope changed");
assert(abs(adapter_back_z-(universal_deep_front_z-2.5)) < 0.01,
       "Adapter must register with 1.2 mm boss engagement");
assert(abs((mp_adapter_centre_x-mp_adapter_w/2)-189)<0.01 &&
       abs((mp_adapter_centre_x+mp_adapter_w/2)-255)<0.01 &&
       abs((mp_adapter_centre_y-mp_adapter_h/2)-60.5)<0.01 &&
       abs((mp_adapter_centre_y+mp_adapter_h/2)-120.5)<0.01,
       "Adapter prototype enclosure coordinates drifted");
assert(abs((mp_adapter_centre_x-mp_adapter_w/2)-187-2)<0.01,
       "Adapter plate must retain 2 mm X clearance to the PSU dock plate");
assert(abs((service_x+service_w)-(mp_adapter_centre_x+mp_adapter_w/2)-0.5)<0.01,
       "Adapter must retain 0.5 mm clearance to the nominal right backplane edge");
assert(len(pcb_mount_points) == 4 &&
       abs(pcb_mount_points[0][0]+24.38)<0.001 &&
       abs(pcb_mount_points[0][1]+6.35)<0.001 &&
       abs(pcb_mount_points[1][0]+24.38)<0.001 &&
       abs(pcb_mount_points[1][1]-13.335)<0.001 &&
       abs(pcb_mount_points[2][0]-16.26)<0.001 &&
       abs(pcb_mount_points[2][1]+6.35)<0.001 &&
       abs(pcb_mount_points[3][0]-16.26)<0.001 &&
       abs(pcb_mount_points[3][1]-13.335)<0.001,
       "MatrixPortal mounting-hole coordinates drifted");
