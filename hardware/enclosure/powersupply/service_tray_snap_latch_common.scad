// Selected PSU mount - service tray with FRONT-OPERATED snap latch for issue #166.
//
// Parts:
//   1. dock: fixed to the enclosure six-boss grid;
//   2. tray: carries the PSU and slides horizontally from -X toward +X;
//   3. latch: separate replaceable cantilever strip.
//
// Access constraint:
// The installed PSU/backplane assembly is tight at both Y sides. The latch
// therefore lives on the FRONT / insertion (-X) face of the dock. The tray still
// moves in X, while the spring flexes vertically in Z. Pressing the front thumb
// tab DOWN releases the tray; no side access is required.
//
// During insertion the trailing/front lip of the tray rides over the latch ramp
// and bends the cantilever downward. At the +X hard stop, the hook rises into an
// UNDERSIDE pocket behind the tray front lip. The lip then provides a positive
// withdrawal stop.
//
// Module library for the selected snap-latch service tray.

include <psu_mount_common.scad>;

tray_w = 114;
tray_h = 84.0;
tray_t = 2.8;
dock_w = adapter_w;
dock_h = 89.0;
dock_channel_wall = 1.5;
dock_channel_h = 6.2;
dock_lip = 1.6;
slide_clearance = 0.5;

// Measured PSU holes sit at Y=+/-37 mm. With 8 mm mounting bosses, their outer
// edges reach Y=+/-41 mm. An 84 mm tray leaves 1 mm of printed material beyond
// each boss. The 89 mm dock gives 0.5 mm overlap between its base and the outer
// channel walls, keeping the channels fused while staying inside the 92 mm
// full-depth backplane zone.
assert(
    tray_h/2 >= abs(psu_rear_mount_points[0][1]) + psu_mount_boss_d/2 + 1.0,
    "Tray is too narrow for measured PSU mounting bosses"
);
assert(
    dock_h/2 >= tray_h/2 + slide_clearance + dock_channel_wall,
    "Dock base does not reach the service-tray channel walls"
);

tray_assembled_z = plate_t + 0.4;

// Keep the dock centre open but preserve the two X=+/-48 fixing spines.
dock_relief_core_w = 80;
dock_relief_core_h = tray_h-14;

// ---------- Front-operated latch geometry ----------

dock_front_x = -dock_w/2;
tray_front_x = -tray_w/2;

// Cantilever runs in +Y from the free/release end toward its fixed base.
// It bends vertically (Z), not sideways.
latch_hook_y = 0;
latch_arm_len = 30;
latch_arm_x_t = 1.6;
latch_arm_z_t = 1.4;

latch_base_y = latch_hook_y + latch_arm_len;
latch_base_len_y = 12;
latch_base_x_t = 1.8;
latch_base_z_h = 5.0;
latch_mount_pitch = 7;

// Dock pad overlaps the front wall by 0.3 mm and grows only toward -X.
// The replaceable latch base sits immediately in front of it.
latch_pad_x0 = dock_front_x - latch_base_x_t + 0.3;
latch_base_x0 = latch_pad_x0 - latch_base_x_t;
latch_arm_x0 = latch_base_x0 + 0.2;

// Hook reaches from the external arm through a small front window and into the
// tray underside pocket.
latch_hook_reach_x = 8.4;
latch_hook_w_y = 6.0;
latch_hook_top_z = tray_assembled_z + 1.4;
latch_ramp_nose_z = tray_assembled_z - 0.2;

// Leave a solid front lip on the tray. The hook engages a pocket immediately
// behind that lip; the pocket does not open to the front.
tray_lock_lip_x = 1.5;
tray_lock_pocket_len_x = 4.0;
tray_lock_pocket_w_y = 7.0;
tray_lock_pocket_depth_z = 2.0;

latch_release_len_y = 12;
latch_release_x_t = 2.6;
latch_release_z_t = 1.8;

// Window only for the hook/ramp at the front centre.
latch_window_x0 = dock_front_x - 0.4;
latch_window_x1 = tray_front_x + tray_lock_lip_x + tray_lock_pocket_len_x + 0.8;
latch_window_y = latch_hook_w_y + 1.0;
latch_window_z = latch_hook_top_z + 0.5;

assert(
    dock_relief_core_w/2 + 2 <
        abs(backplane_mount_x[0]) - adapter_screw_head_d/2,
    "Snap-latch service-tray relief cuts into enclosure screw lands"
);

module snap_tray_notch_cutter() {
    // Underside pocket behind the front retaining lip.
    translate([
        tray_front_x + tray_lock_lip_x,
        -tray_lock_pocket_w_y/2,
        -0.1
    ])
        cube([
            tray_lock_pocket_len_x,
            tray_lock_pocket_w_y,
            tray_lock_pocket_depth_z+0.1
        ]);
}

module snap_tray_plate() {
    difference() {
        rounded_plate(w=tray_w, h=tray_h, t=tray_t, r=2.5);

        // PSU screw pilots.
        for (pt = psu_rear_mount_points)
            translate([pt[0], pt[1], -0.2])
                cylinder(d=psu_mount_pilot_d, h=tray_t+0.4);

        // Front-centre underside latch pocket.
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

module front_latch_mount_pad() {
    // Permanent front pad fused to the dock. Two horizontal M3 pilots accept
    // the replaceable latch base before the dock is installed.
    difference() {
        translate([
            latch_pad_x0,
            latch_base_y-latch_base_len_y/2,
            0
        ])
            cube([
                latch_base_x_t,
                latch_base_len_y,
                latch_base_z_h
            ]);

        for (dy=[-latch_mount_pitch/2, latch_mount_pitch/2])
            translate([
                latch_pad_x0-0.2,
                latch_base_y+dy,
                latch_base_z_h/2
            ])
                rotate([0,90,0])
                    cylinder(
                        d=2.8,
                        h=latch_base_x_t+0.4
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

            // +/-Y channels capture the tray edges while it slides in X.
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

            front_latch_mount_pad();
        }

        // Front-centre hook window. Nothing protrudes from either Y side.
        translate([
            latch_window_x0,
            -latch_window_y/2,
            -0.2
        ])
            cube([
                latch_window_x1-latch_window_x0,
                latch_window_y,
                latch_window_z+0.4
            ]);
    }
}

module replaceable_snap_latch() {
    arm_x1 = latch_arm_x0 + latch_arm_x_t;
    hook_x1 = arm_x1 + latch_hook_reach_x;

    union() {
        // Fixed base against the front dock pad.
        difference() {
            translate([
                latch_base_x0,
                latch_base_y-latch_base_len_y/2,
                0
            ])
                cube([
                    latch_base_x_t,
                    latch_base_len_y,
                    latch_base_z_h
                ]);

            for (dy=[-latch_mount_pitch/2, latch_mount_pitch/2])
                translate([
                    latch_base_x0-0.2,
                    latch_base_y+dy,
                    latch_base_z_h/2
                ])
                    rotate([0,90,0])
                        cylinder(
                            d=3.2,
                            h=latch_base_x_t+0.4
                        );
        }

        // Leaf spring. It starts on Z=0 so the separate latch prints flat and
        // can flex downward after assembly without needing side clearance.
        translate([
            latch_arm_x0,
            latch_hook_y,
            0
        ])
            cube([
                latch_arm_x_t,
                latch_arm_len,
                latch_arm_z_t
            ]);

        // Low hook body through the front window.
        translate([
            arm_x1-0.2,
            latch_hook_y-latch_hook_w_y/2,
            0
        ])
            cube([
                latch_hook_reach_x+0.2,
                latch_hook_w_y,
                latch_ramp_nose_z
            ]);

        // Insertion ramp: low at the front, high inside the tray pocket.
        hull() {
            translate([
                tray_front_x-0.4,
                latch_hook_y-latch_hook_w_y/2,
                latch_ramp_nose_z-0.4
            ])
                cube([0.8,latch_hook_w_y,0.4]);

            translate([
                tray_front_x + tray_lock_lip_x + 1.7,
                latch_hook_y-latch_hook_w_y/2,
                latch_hook_top_z-0.4
            ])
                cube([0.8,latch_hook_w_y,0.4]);
        }

        // Square retaining tooth behind the tray front lip.
        translate([
            tray_front_x + tray_lock_lip_x + 0.4,
            latch_hook_y-latch_hook_w_y/2,
            latch_ramp_nose_z
        ])
            cube([
                1.4,
                latch_hook_w_y,
                latch_hook_top_z-latch_ramp_nose_z
            ]);

        // Front thumb pad: press DOWN, then pull tray toward -X.
        translate([
            latch_base_x0-latch_release_x_t+0.2,
            latch_hook_y-latch_release_len_y/2,
            0
        ])
            cube([
                latch_release_x_t,
                latch_release_len_y,
                latch_release_z_t
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
