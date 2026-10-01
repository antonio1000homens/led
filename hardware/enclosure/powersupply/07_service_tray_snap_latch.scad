// Option 7 - service tray with replaceable snap latch for issue #166.
//
// This is an ALTERNATIVE to 03_service_tray.scad so the latch mechanism can be
// visualised and tested without replacing the screw-lock design.
//
// Parts:
//   1. dock: fixed to the enclosure six-boss grid;
//   2. tray: carries the PSU and slides horizontally from -X toward +X;
//   3. latch: separate replaceable cantilever strip (PETG recommended; PLA is
//      suitable for a short-life dimensional prototype).
//
// The latch sits OUTSIDE the +Y dock wall. Its hook reaches through a small
// wall window. As the tray enters, the tray edge rides over the hook ramp and
// flexes the cantilever outward. When the tray reaches the +X hard stop, a side
// notch aligns with the hook and the latch snaps in automatically.
//
// To remove the tray, pull the external thumb tab outward (+Y) and slide the
// tray back toward -X.
//
// Default layout is assembled for visualisation. Set layout="print" to separate
// dock, tray and latch for export.

include <psu_mount_common.scad>;

layout = "assembled";       // "assembled" or "print"

tray_w = 114;
tray_h = 80.6;
tray_t = 2.8;
dock_w = adapter_w;
dock_h = adapter_h;
dock_channel_wall = 1.5;
dock_channel_h = 6.2;
dock_lip = 1.6;
slide_clearance = 0.5;

tray_assembled_z = plate_t + 0.4;

// Keep the dock centre open but preserve the two X=+/-48 fixing spines.
dock_relief_core_w = 80;
dock_relief_core_h = tray_h-14;

// Snap-latch position: close to the insertion (-X) end so the external release
// tab stays easy to reach when the tray is fully installed.
latch_hook_x = -48;
latch_arm_len = 30;
latch_arm_w = 8;
latch_arm_t = 1.6;
latch_base_len = 12;
latch_base_t = 3.0;
latch_mount_pitch = 7;

latch_hook_depth = 2.0;     // engagement into tray notch
latch_hook_len = 4.0;       // X length of retaining face/ramp
latch_ramp_len = 6.0;       // gentle insertion ramp
latch_release_len = 10.0;
latch_release_w = 12.0;

// Side notch in the tray. The hook aligns here only when tray translation is 0.
tray_notch_len = 6.0;
tray_notch_depth = 2.6;
tray_notch_h = 3.0;
tray_notch_z = 0.8;

// External latch sits just outside the +Y channel wall.
channel_y = tray_h/2 + slide_clearance;
latch_inner_y = channel_y + dock_channel_wall + 0.4;
latch_z = tray_assembled_z + 1.0;

// Window through the +Y channel wall for only the hook nose.
latch_window_x = latch_hook_x;
latch_window_w = latch_ramp_len + 1.0;
latch_window_h = tray_notch_h + 1.0;
latch_window_z = tray_assembled_z + tray_notch_z - 0.5;

assert(
    dock_relief_core_w/2 + 2 <
        abs(backplane_mount_x[0]) - adapter_screw_head_d/2,
    "Snap-latch service-tray relief cuts into enclosure screw lands"
);

module snap_tray_notch_cutter() {
    translate([
        latch_hook_x-tray_notch_len/2,
        tray_h/2-tray_notch_depth,
        tray_notch_z
    ])
        cube([
            tray_notch_len,
            tray_notch_depth+0.4,
            tray_notch_h
        ]);
}

module snap_tray_plate() {
    difference() {
        rounded_plate(w=tray_w, h=tray_h, t=tray_t, r=2.5);

        // PSU screw pilots.
        for (pt = psu_rear_mount_points)
            translate([pt[0], pt[1], -0.2])
                cylinder(d=psu_mount_pilot_d, h=tray_t+0.4);

        // The latch hook snaps into this side notch only at the fully seated
        // tray position.
        snap_tray_notch_cutter();
    }

    translate([0,0,tray_t-plate_t])
        integrated_support_rails(length=psu_h-14);

    raised_psu_mount_bosses(base_z=tray_t, h=support_gap);

    // Existing hard +X end stop on the tray/PSU side.
    translate([
        psu_w/2 + psu_xy_clearance,
        -psu_h/2,
        tray_t-0.2
    ])
        cube([2.2, psu_h, 5.2]);
}

module snap_latch_mount_pad() {
    // Permanent external pad on the dock. Two small pilot holes let the
    // replaceable latch be installed once with ordinary M3 screws.
    base_x = latch_hook_x + latch_arm_len;

    difference() {
        translate([
            base_x-latch_base_len/2,
            latch_inner_y,
            latch_z-0.8
        ])
            cube([
                latch_base_len,
                latch_base_t,
                latch_arm_w+1.6
            ]);

        for (dz=[-latch_mount_pitch/2, latch_mount_pitch/2])
            translate([
                base_x,
                latch_inner_y-0.2,
                latch_z+latch_arm_w/2+dz
            ])
                rotate([-90,0,0])
                    cylinder(
                        d=2.8,
                        h=latch_base_t+0.4
                    );
    }
}

module snap_dock() {
    difference() {
        union() {
            difference() {
                rounded_plate(w=dock_w, h=dock_h, t=plate_t, r=corner_r);
                backplane_interface_cutters();

                translate([0,0,-0.2])
                    linear_extrude(height=plate_t+0.4)
                        offset(r=2)
                            square(
                                [dock_relief_core_w, dock_relief_core_h],
                                center=true
                            );
            }

            // Top/bottom channel walls.
            for (sy=[-1,1]) {
                y_wall = sy*(tray_h/2 + slide_clearance);

                translate([
                    -dock_w/2,
                    y_wall-(sy<0 ? dock_channel_wall : 0),
                    plate_t-0.2
                ])
                    cube([
                        dock_w,
                        dock_channel_wall,
                        dock_channel_h+0.2
                    ]);

                lip_y = sy>0
                    ? y_wall-dock_lip
                    : y_wall;
                translate([
                    -dock_w/2,
                    lip_y,
                    plate_t+dock_channel_h-dock_lip-0.1
                ])
                    cube([
                        dock_w,
                        dock_lip,
                        dock_lip+0.1
                    ]);
            }

            // Hard +X stop takes insertion force; latch only prevents withdrawal.
            translate([
                dock_w/2-2.0,
                -tray_h/2,
                plate_t-0.2
            ])
                cube([
                    2.0,
                    tray_h,
                    dock_channel_h+0.2
                ]);

            snap_latch_mount_pad();
        }

        // Small window through +Y channel wall for the flexible hook only.
        translate([
            latch_window_x-latch_window_w/2,
            channel_y-0.4,
            latch_window_z
        ])
            cube([
                latch_window_w,
                dock_channel_wall+0.8,
                latch_window_h
            ]);
    }
}

module replaceable_snap_latch() {
    // Coordinate the latch around its hook. The fixed base is at +X, the free
    // end is at -X. The arm flexes outward in +Y.
    base_x = latch_hook_x + latch_arm_len;
    arm_x0 = latch_hook_x;
    arm_y = latch_inner_y + latch_base_t + 0.4;
    arm_z = latch_z;

    union() {
        // Fixed base.
        difference() {
            translate([
                base_x-latch_base_len/2,
                latch_inner_y,
                arm_z
            ])
                cube([
                    latch_base_len,
                    latch_base_t,
                    latch_arm_w
                ]);

            for (dz=[-latch_mount_pitch/2, latch_mount_pitch/2])
                translate([
                    base_x,
                    latch_inner_y-0.2,
                    arm_z+latch_arm_w/2+dz
                ])
                    rotate([-90,0,0])
                        cylinder(
                            d=3.2,
                            h=latch_base_t+0.4
                        );
        }

        // Cantilever arm.
        translate([
            arm_x0,
            arm_y,
            arm_z
        ])
            cube([
                latch_arm_len,
                latch_arm_t,
                latch_arm_w
            ]);

        // Hook body protrudes inward (-Y) through the wall window.
        translate([
            latch_hook_x-latch_hook_len/2,
            arm_y-latch_hook_depth,
            arm_z+1.0
        ])
            cube([
                latch_hook_len,
                latch_hook_depth+latch_arm_t,
                tray_notch_h-0.4
            ]);

        // Insertion ramp. The tray's leading edge pushes this outward (+Y).
        hull() {
            translate([
                latch_hook_x-latch_ramp_len/2,
                arm_y-latch_hook_depth,
                arm_z+1.0
            ])
                cube([0.8,0.8,tray_notch_h-0.4]);

            translate([
                latch_hook_x+latch_ramp_len/2,
                arm_y,
                arm_z+1.0
            ])
                cube([0.8,0.8,tray_notch_h-0.4]);
        }

        // External thumb tab at free end.
        translate([
            latch_hook_x-latch_release_len/2,
            arm_y,
            arm_z-(latch_release_w-latch_arm_w)/2
        ])
            cube([
                latch_release_len,
                2.6,
                latch_release_w
            ]);
    }
}

module assembled_snap_service_tray() {
    snap_dock();

    translate([0,0,tray_assembled_z])
        snap_tray_plate();

    replaceable_snap_latch();

    backplane_boss_preview();
}

if (layout == "assembled") {
    assembled_snap_service_tray();
} else {
    translate([-80,0,0])
        snap_dock();

    translate([65,0,0])
        snap_tray_plate();

    translate([20,70,0])
        replaceable_snap_latch();
}
