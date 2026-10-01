// Option 3 - removable printed PSU service tray for issue #166.
//
// This is a two-piece prototype:
//   1. dock: remains screwed to the enclosure boss grid;
//   2. tray: carries the PSU and slides horizontally into the dock.
//
// Set layout="assembled" to inspect the fit.  Default layout="print" separates
// the two components so the SCAD can be exported/printed as an experiment.

include <psu_mount_common.scad>;

layout = "print";          // "print" or "assembled"

tray_w = 114;
tray_h = 80.6;
tray_t = 2.8;
dock_w = adapter_w;
dock_h = adapter_h;
dock_channel_wall = 1.5;
dock_channel_h = 6.2;
dock_lip = 1.6;
slide_clearance = 0.5;

// Service lock: the tray path stays completely clear during insertion.
// Once the tray is fully seated against the +X stop, an M3 screw is inserted
// from outside the +Y dock wall into a reinforced clearance hole in the tray.
// Removing that screw restores a completely unobstructed slide path.
tray_lock_x = -45;
tray_lock_pad_w = 12;
tray_lock_pad_depth = 10;
tray_lock_pad_h = 4.0;
tray_lock_hole_d = 3.8;

dock_lock_boss_d = 8.0;
dock_lock_boss_len = 6.0;
dock_lock_pilot_d = 2.8;   // prototype M3 tapping pilot; heat-set can follow testing

tray_assembled_z = plate_t + 0.4;
tray_lock_axis_z_local = tray_lock_pad_h/2;
dock_lock_axis_z = tray_assembled_z + tray_lock_axis_z_local;

// Keep a large central opening, but preserve two full-height side fixing spines
// around X=+/-48. With the 2 mm rounded offset below, an 80 mm core produces an
// 84 mm-wide opening (X=-42..+42), leaving the six screw lands intact.
dock_relief_core_w = 80;
dock_relief_core_h = tray_h-14;

assert(
    dock_relief_core_w/2 + 2 <
        abs(backplane_mount_x[0]) - adapter_screw_head_d/2,
    "Service-tray relief cuts into enclosure screw lands"
);

module tray_lock_pad() {
    translate([
        tray_lock_x-tray_lock_pad_w/2,
        tray_h/2-tray_lock_pad_depth,
        0
    ])
        cube([
            tray_lock_pad_w,
            tray_lock_pad_depth,
            tray_lock_pad_h
        ]);
}

module tray_lock_hole_cutter() {
    translate([
        tray_lock_x,
        tray_h/2-tray_lock_pad_depth-0.2,
        tray_lock_axis_z_local
    ])
        rotate([-90,0,0])
            cylinder(
                d=tray_lock_hole_d,
                h=tray_lock_pad_depth+0.6
            );
}

module tray_plate() {
    difference() {
        union() {
            rounded_plate(w=tray_w, h=tray_h, t=tray_t, r=2.5);
            tray_lock_pad();
        }

        // PSU screw pilots pass through both tray and raised support bosses.
        for (pt = psu_rear_mount_points)
            translate([pt[0], pt[1], -0.2])
                cylinder(d=psu_mount_pilot_d, h=tray_t+0.4);

        // Side-entry lock hole. It is only occupied by the M3 screw after the
        // tray is fully home; nothing protrudes into the insertion path.
        tray_lock_hole_cutter();
    }

    // Integral airflow rails on the removable tray.
    translate([0,0,tray_t-plate_t])
        integrated_support_rails(length=psu_h-14);

    // The two PSU fixing points are raised by the same 2 mm as the support
    // rails, so the PSU sits on one common plane instead of bridging between
    // rails and lower screw locations.
    raised_psu_mount_bosses(base_z=tray_t, h=support_gap);

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
        backplane_interface_cutters();

        // Large centre relief keeps the dock light while deliberately stopping
        // before the two X=+/-48 fixing spines. All six enclosure screw lands
        // therefore remain connected to the dock perimeter.
        translate([0,0,-0.2])
            linear_extrude(height=plate_t+0.4)
                offset(r=2)
                    square(
                        [dock_relief_core_w, dock_relief_core_h],
                        center=true
                    );
    }

    // Top/bottom channels capture the tray edges while it slides in X.
    // The +Y wall also carries an EXTERNAL lock boss. Its screw axis is
    // perpendicular to tray travel, so the boss itself never enters the slide
    // envelope.
    for (sy=[-1,1]) {
        y_wall = sy*(tray_h/2 + slide_clearance);

        if (sy > 0) {
            difference() {
                union() {
                    translate([
                        -dock_w/2,
                        y_wall,
                        plate_t-0.2
                    ])
                        cube([
                            dock_w,
                            dock_channel_wall,
                            dock_channel_h+0.2
                        ]);

                    // External boss grows away from the tray channel.
                    translate([
                        tray_lock_x,
                        y_wall+dock_channel_wall-0.3,
                        dock_lock_axis_z
                    ])
                        rotate([-90,0,0])
                            cylinder(
                                d=dock_lock_boss_d,
                                h=dock_lock_boss_len+0.3
                            );
                }

                // M3 pilot passes through the external boss and channel wall.
                // The screw is installed only after the tray is fully seated.
                translate([
                    tray_lock_x,
                    y_wall-0.4,
                    dock_lock_axis_z
                ])
                    rotate([-90,0,0])
                        cylinder(
                            d=dock_lock_pilot_d,
                            h=dock_channel_wall+dock_lock_boss_len+1.0
                        );
            }
        } else {
            translate([
                -dock_w/2,
                y_wall-dock_channel_wall,
                plate_t-0.2
            ])
                cube([
                    dock_w,
                    dock_channel_wall,
                    dock_channel_h+0.2
                ]);
        }

        lip_y = sy>0
            ? y_wall-dock_lip
            : y_wall;
        translate([-dock_w/2, lip_y, plate_t+dock_channel_h-dock_lip-0.1])
            cube([dock_w, dock_lip, dock_lip+0.1]);
    }

    // +X end stop defines the fully seated position before the side-lock screw
    // is inserted.
    translate([dock_w/2-2.0, -tray_h/2, plate_t-0.2])
        cube([2.0, tray_h, dock_channel_h+0.2]);
}

module assembled_service_tray() {
    dock();
    translate([0,0,tray_assembled_z])
        tray_plate();

    backplane_boss_preview();
}

if (layout == "assembled") {
    assembled_service_tray();
} else {
    translate([-70,0,0]) dock();
    translate([75,0,0]) tray_plate();
}
