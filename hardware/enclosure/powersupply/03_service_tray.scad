// Option 3 — removable printed PSU service tray for issue #166.
//
// This is a two-piece prototype:
//   1. dock: remains screwed to the enclosure boss grid;
//   2. tray: carries the PSU and slides horizontally into the dock.
//
// Set layout="assembled" to inspect the fit.  Default layout="print" separates
// the two components so the SCAD can be exported/printed as an experiment.

include <psu_mount_common.scad>;

layout = "print";          // "print" or "assembled"
show_psu = true;

tray_w = 114;
tray_h = 80.6;
tray_t = 2.8;
dock_w = adapter_w;
dock_h = adapter_h;
dock_channel_wall = 1.5;
dock_channel_h = 6.2;
dock_lip = 1.6;
slide_clearance = 0.5;

module tray_plate() {
    difference() {
        rounded_plate(w=tray_w, h=tray_h, t=tray_t, r=2.5);
        // Optional PSU screw pilots; keep them editable in the common file.
        for (pt = psu_rear_mount_points)
            translate([pt[0], pt[1], -0.2])
                cylinder(d=psu_mount_pilot_d, h=tray_t+0.4);
    }

    // Integral airflow rails on the removable tray.
    translate([0,0,tray_t-plate_t])
        integrated_support_rails(length=psu_h-14);

    // Rear stop at +X, leaving the left side open for insertion/service.
    translate([
        psu_w/2 + psu_xy_clearance,
        -psu_h/2,
        tray_t-0.2
    ])
        cube([2.2, psu_h, 5.2]);
}

module dock() {
    difference() {
        rounded_plate(w=dock_w, h=dock_h, t=plate_t, r=corner_r);
        backplane_hole_cutters();

        // Large centre relief means the dock is mostly a perimeter frame and
        // does not create a second solid wall behind the tray/PSU.
        translate([0,0,-0.2])
            linear_extrude(height=plate_t+0.4)
                offset(r=2)
                    square([tray_w-12, tray_h-14], center=true);
    }

    // Top/bottom channels capture the tray edges while it slides in X.
    for (sy=[-1,1]) {
        y_wall = sy*(tray_h/2 + slide_clearance);
        translate([-dock_w/2, y_wall-(sy<0 ? dock_channel_wall : 0), plate_t-0.2])
            cube([dock_w, dock_channel_wall, dock_channel_h+0.2]);

        lip_y = sy>0
            ? y_wall-dock_lip
            : y_wall;
        translate([-dock_w/2, lip_y, plate_t+dock_channel_h-dock_lip-0.1])
            cube([dock_w, dock_lip, dock_lip+0.1]);
    }

    // +X end stop for the tray.
    translate([dock_w/2-2.0, -tray_h/2, plate_t-0.2])
        cube([2.0, tray_h, dock_channel_h+0.2]);

    // Lock screw boss at the insertion edge.
    screw_stop_boss(-dock_w/2+5, 0, h=4.5);
}

module assembled_service_tray() {
    dock();
    translate([0,0,plate_t+0.4])
        tray_plate();

    if (show_psu)
        %translate([-psu_w/2,-psu_h/2,plate_t+0.4+tray_t+support_gap])
            cube([psu_w, psu_h, psu_d]);

    backplane_boss_preview();
}

if (layout == "assembled") {
    assembled_service_tray();
} else {
    translate([-70,0,0]) dock();
    translate([75,0,0]) tray_plate();
}
