// Selected PSU mount - service tray with FRONT-OPERATED snap latch for issue #166.
//
// Physical-fit correction:
//   * usable enclosure opening in Y = 80 mm;
//   * dock Y envelope = 79 mm;
//   * removable tray Y envelope = 79 mm;
//   * PSU itself remains 80 mm wide and therefore overhangs the tray by 0.5 mm
//     per side;
//   * external side channels are removed. Two internal dovetail runners under
//     the tray provide positive capture without increasing the outer width.
//
// The tray still moves in X. The separate front latch flexes vertically in Z:
// press the front thumb tab DOWN and pull the tray toward -X to release it.
// The replaceable latch is secured to the dock by two front-loaded M3 heat-set
// inserts, avoiding repeated thread-forming directly into PETG.

include <psu_mount_common.scad>;

tray_w = 114;
tray_h = 79.0;
tray_t = 2.8;
dock_w = adapter_w;
dock_h = 79.0;

fit_envelope_h = 80.0;
slide_z_clearance = 0.25;

tray_assembled_z = plate_t + slide_z_clearance;

// Keep the dock centre open while preserving both the six-boss screw lands and
// solid strips under the internal dovetail rails.
dock_relief_core_w = 80;
dock_relief_core_h = 26;

// ---------- Internal dovetail slide ----------
//
// Two longitudinal rails sit well inside the 80 mm opening. Their matching
// underside grooves widen upward at a printable slope. The groove stops 8 mm
// short of the +X end, so the tray remains one connected print on the bed and
// the solid tail meets the separate +X hard stop.

dovetail_y = [-25, 25];
dovetail_base_w = 2.4;
dovetail_top_w = 4.0;
dovetail_h = 1.8;
dovetail_skin = 0.4;
dovetail_clearance = 0.3;
dovetail_groove_depth = 1.9;

dovetail_rail_x0 = -dock_w/2 + 2;
dovetail_rail_x1 = tray_w/2 - 8;
dovetail_rail_len = dovetail_rail_x1-dovetail_rail_x0;

dovetail_groove_x0 = -tray_w/2 - 0.2;
dovetail_groove_x1 = tray_w/2 - 7.8;
dovetail_groove_len = dovetail_groove_x1-dovetail_groove_x0;

dovetail_groove_bottom_w = dovetail_base_w + 2*dovetail_clearance;
dovetail_groove_top_w = dovetail_top_w + 2*dovetail_clearance;

// The measured PSU mounting holes are only 3 mm from the 80 mm PSU edges.
// Their 2.8 mm pilots still retain >1 mm of tray material at the 79 mm edge.
// The larger 8 mm support bosses are clipped flush to the tray envelope.
psu_pilot_edge_margin =
    tray_h/2 - (abs(psu_rear_mount_points[0][1]) + psu_mount_pilot_d/2);

assert(dock_h <= fit_envelope_h,
       "PSU dock exceeds the physical 80 mm enclosure opening");
assert(tray_h <= fit_envelope_h,
       "PSU tray exceeds the physical 80 mm enclosure opening");
assert(psu_pilot_edge_margin >= 1.0,
       "Measured PSU pilot holes are too close to the narrowed tray edge");
assert(dovetail_groove_depth < tray_t-0.6,
       "Dovetail groove leaves too little tray roof thickness");

assert(
    dock_relief_core_w/2 + 2 <
        abs(backplane_mount_x[0]) - adapter_screw_head_d/2,
    "Snap-latch service-tray relief cuts into enclosure screw lands in X"
);
assert(
    dock_relief_core_h/2 + 2 <
        abs(backplane_mount_y[0]) - adapter_screw_head_d/2,
    "Snap-latch service-tray relief cuts into enclosure screw lands in Y"
);

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
latch_base_len_y = 16;
latch_base_x_t = 1.8;
latch_base_z_h = 7.0;
latch_mount_pitch = 7;

// The replaceable latch is bolted to brass M3 heat-set inserts in the dock pad.
// The insert bore deliberately matches the existing 3.4 mm heat-set test coupon.
// Heat-set the inserts horizontally from the service/front (-X) face.
latch_insert_bore_d = backplane_boss_hole_d;
latch_insert_depth = 4.2;
latch_insert_back_wall = 1.2;
latch_pad_x_overlap = 0.3;
latch_pad_x_t = latch_insert_depth + latch_insert_back_wall;

// Grow the insert pad outward toward -X so the 79 mm Y fit and tray slide path
// are unchanged. Moving the latch base outward requires an equal increase in
// hook reach so the retaining tooth stays at the original tray-pocket position.
latch_pad_x0 = dock_front_x - latch_pad_x_t + latch_pad_x_overlap;
latch_base_x0 = latch_pad_x0 - latch_base_x_t;
latch_arm_x0 = latch_base_x0 + 0.2;

// Hook reaches from the external arm through a small front window and into the
// tray underside pocket.
latch_hook_reach_x = 8.4 + (latch_pad_x_t - latch_base_x_t);
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
    latch_pad_x_t - latch_insert_depth >= latch_insert_back_wall,
    "Latch heat-set insert socket leaves too little blind back wall"
);
assert(
    (latch_base_len_y-latch_mount_pitch)/2 - latch_insert_bore_d/2 >= 1.5,
    "Latch heat-set insert sockets leave too little PETG at the Y edges"
);
assert(
    latch_base_z_h/2 - latch_insert_bore_d/2 >= 1.5,
    "Latch heat-set insert sockets leave too little PETG above/below the bore"
);

module snap_tray_notch_cutter() {
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

module dovetail_groove_cutter(yc) {
    hull() {
        translate([
            dovetail_groove_x0,
            yc-dovetail_groove_bottom_w/2,
            -0.2
        ])
            cube([
                dovetail_groove_len,
                dovetail_groove_bottom_w,
                dovetail_skin
            ]);

        translate([
            dovetail_groove_x0,
            yc-dovetail_groove_top_w/2,
            dovetail_groove_depth-dovetail_skin
        ])
            cube([
                dovetail_groove_len,
                dovetail_groove_top_w,
                dovetail_skin+0.2
            ]);
    }
}

module clipped_psu_mount_bosses() {
    intersection() {
        raised_psu_mount_bosses(base_z=tray_t, h=support_gap);

        translate([
            -tray_w/2,
            -tray_h/2,
            tray_t-0.5
        ])
            cube([
                tray_w,
                tray_h,
                support_gap+1.0
            ]);
    }
}

module snap_tray_plate() {
    difference() {
        rounded_plate(w=tray_w, h=tray_h, t=tray_t, r=2.5);

        for (pt = psu_rear_mount_points)
            translate([pt[0], pt[1], -0.2])
                cylinder(d=psu_mount_pilot_d, h=tray_t+0.4);

        snap_tray_notch_cutter();

        for (yy=dovetail_y)
            dovetail_groove_cutter(yy);
    }

    translate([0,0,tray_t-plate_t])
        integrated_support_rails(length=psu_h-14);

    clipped_psu_mount_bosses();

    translate([
        psu_w/2 + psu_xy_clearance,
        -tray_h/2,
        tray_t-0.2
    ])
        cube([2.2, tray_h, 5.2]);
}

module front_latch_mount_pad() {
    // Permanent dock pad for two front-loaded brass M3 heat-set inserts.
    // The bores are blind: a solid rear wall remains before the pad overlaps
    // the dock, so an insert cannot be pushed into the tray slide path.
    difference() {
        translate([
            latch_pad_x0,
            latch_base_y-latch_base_len_y/2,
            0
        ])
            cube([
                latch_pad_x_t,
                latch_base_len_y,
                latch_base_z_h
            ]);

        for (dy=[-latch_mount_pitch/2, latch_mount_pitch/2])
            translate([
                latch_pad_x0-0.1,
                latch_base_y+dy,
                latch_base_z_h/2
            ])
                rotate([0,90,0])
                    cylinder(
                        d=latch_insert_bore_d,
                        h=latch_insert_depth+0.1
                    );
    }
}

module dovetail_rail(yc) {
    hull() {
        translate([
            dovetail_rail_x0,
            yc-dovetail_base_w/2,
            plate_t-0.2
        ])
            cube([
                dovetail_rail_len,
                dovetail_base_w,
                dovetail_skin
            ]);

        translate([
            dovetail_rail_x0,
            yc-dovetail_top_w/2,
            plate_t+dovetail_h-dovetail_skin
        ])
            cube([
                dovetail_rail_len,
                dovetail_top_w,
                dovetail_skin
            ]);
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

            for (yy=dovetail_y)
                dovetail_rail(yy);

            translate([
                dock_w/2-2.0,
                -tray_h/2,
                plate_t-0.2
            ])
                cube([
                    2.0,
                    tray_h,
                    dovetail_h+0.8
                ]);

            front_latch_mount_pad();
        }

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

    union() {
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
