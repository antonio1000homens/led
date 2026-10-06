// Adafruit MatrixPortal S3 removable click-dock enclosure mount.
//
// Mechanical source of truth:
//   Adafruit-MatrixPortal-S3-PCB / Adafruit MatrixPortal S3.brd
//   board: 63.50 x 44.45 mm
//   plated mounting holes: 2.50 mm
//   native hole centres: X=7.62/48.26, Y=15.875/35.56 mm
//
// Architecture:
//   1. a fixed dock bolts to four existing universal backplane M3 bosses;
//   2. a removable carrier slides in from the LEFT service opening on two
//      captive dovetail rails;
//   3. a shallow PETG detent on one rail clicks into a matching carrier pocket;
//   4. the carrier stops against a positive end wall at the seated position.
//
// The MatrixPortal drops onto four fixed printed locating pins. Two removable
// slide-lock keeper bars capture grooves near the pin tips, so the PCB needs no
// M2.5 screws or nuts. Normal service still needs no backplane screws: pull the
// carrier from the left opening to undock the complete controller assembly.

// ----- Official PCB geometry -----
mp_pcb_w = 63.50;
mp_pcb_h = 44.45;
mp_pcb_t = 1.60;
mp_pcb_corner_r = 2.54;
mp_pcb_hole_d = 2.50;
mp_pcb_hole_x_native = [7.62,48.26];
mp_pcb_hole_y_native = [15.875,35.56];

// Native service-side component centres from the Eagle board.
mp_usb_y_native = 8.255;
mp_reset_y_native = 38.100;
mp_up_y_native = 28.321;
mp_down_y_native = 18.542;
mp_hub75_x_native = 57.150;
mp_hub75_y_native = 22.225;

// The Eagle board contains a mirrored HUB75 connector on the underside. The
// PCB file does not carry a trustworthy mechanical height, so keep a conservative
// 9 mm reference envelope and provide 2.5 mm additional printed clearance.
// This is deliberately parameterised for a physical-fit correction if required.
mp_underside_connector_h = 9.0;
mp_underside_clearance_margin = 2.5;

// ----- Installed position in the left-most enclosure module -----
// Native USB/button short edge faces -X (the detachable left service side).
mp_board_x0 = 1.50;
mp_board_yc = 82.50;
mp_board_y0 = mp_board_yc - mp_pcb_h/2;
mp_board_service_edge_x = mp_board_x0;

// ----- Fixed dock -----
// Backplane boss columns/rows used by the fixed dock.
mp_backplane_mount_x = [32,80];
mp_backplane_mount_y = [62.5,102.5];

mp_dock_x0 = 1.0;
mp_dock_y0 = 57.5;
mp_dock_w = 86.0;
mp_dock_h = 50.0;
mp_dock_t = 4.2;
mp_dock_corner_r = 3.0;

mp_dock_m3_hole_d = 3.6;
mp_dock_m3_head_d = 7.0;
mp_dock_m3_head_recess = 1.8;
mp_dock_boss_pocket_d = 7.5;
mp_dock_boss_pocket_depth = 1.2;

// ----- Removable MatrixPortal carrier -----
mp_carrier_x0 = mp_dock_x0;
mp_carrier_y0 = mp_dock_y0;
mp_carrier_w = 82.0;
mp_carrier_h = 50.0;
mp_carrier_t = 2.8;
mp_carrier_corner_r = 2.5;

// Low-profile pull tab reaches into the left service opening without projecting
// beyond the existing side-wall outer face.
mp_pull_tab_len = 3.0;
mp_pull_tab_y0 = 21.0;
mp_pull_tab_h = 8.0;

// The carrier rides 0.25 mm above the dock top while captive on the dovetails.
mp_slide_z_clearance = 0.25;
mp_carrier_assembled_z = mp_dock_t + mp_slide_z_clearance;

// Raise the PCB far enough for the mirrored underside HUB75 connector.
mp_board_standoff_d = 7.0;
mp_board_standoff_h =
    mp_underside_connector_h + mp_underside_clearance_margin;

// Tool-free PCB location/retention. The 2.20 mm pins provide 0.30 mm diametral
// clearance through the official 2.50 mm plated holes. A reduced neck near each
// pin tip is captured by the removable keeper bars.
mp_board_pin_d = 2.20;
mp_board_pin_groove_d = 1.60;
mp_board_pin_groove_h = 0.90;
mp_board_pin_tip_h = 0.90;

// Keeper bridge rides above known low-profile parts while the local feet descend
// only around the four mounting-hole keepouts. The high HUB75 envelope starts
// farther right than the right-hand keeper column.
mp_keeper_bridge_clearance = 4.50;
mp_keeper_t = 1.80;
mp_keeper_foot_gap = 0.15;
mp_keeper_foot_h =
    mp_keeper_bridge_clearance-mp_keeper_foot_gap;
mp_keeper_w = 6.50;
mp_keeper_end_margin = 3.50;
mp_keeper_hole_spacing =
    mp_pcb_hole_y_native[1]-mp_pcb_hole_y_native[0];
mp_keeper_len =
    mp_keeper_hole_spacing+2*mp_keeper_end_margin;

// Put the capture layer directly around the reduced pin neck. The terminal
// throat is deliberately slightly narrower than the 1.60 mm neck so the bar
// gives a small PETG click at the locked position.
mp_keeper_entry_d = 2.70;
mp_keeper_slot_w = 1.85;
mp_keeper_throat_w = 1.45;
mp_keeper_lock_travel = 2.00;
mp_keeper_capture_h = mp_board_pin_groove_h;
mp_keeper_upper_clearance_w = 2.75;

mp_board_pin_stem_above_pcb = mp_keeper_bridge_clearance;
mp_board_pin_above_pcb =
    mp_board_pin_stem_above_pcb+
    mp_board_pin_groove_h+
    mp_board_pin_tip_h;

assert(abs(mp_board_standoff_h-11.5)<0.01,
       "MatrixPortal underside clearance contract drifted");
assert(mp_board_standoff_h >=
       mp_underside_connector_h+mp_underside_clearance_margin,
       "MatrixPortal carrier does not clear the underside connector");
assert(mp_board_pin_d <= mp_pcb_hole_d-0.25,
       "MatrixPortal locating pins need at least 0.25 mm diametral hole clearance");
assert(mp_keeper_throat_w < mp_board_pin_groove_d &&
       mp_keeper_slot_w > mp_board_pin_groove_d,
       "Keeper bar throat/slot must click over and then clear the pin groove");
assert(mp_keeper_foot_h < mp_keeper_bridge_clearance,
       "Keeper feet must leave a small board-surface clearance");

// Board coordinates relative to the removable carrier.
mp_board_carrier_x0 = mp_board_x0-mp_carrier_x0;
mp_board_carrier_y0 = mp_board_y0-mp_carrier_y0;

// ----- Slide / click interface -----
// Two captive dovetails guide insertion from left (-X) to right (+X).
// They intentionally avoid both backplane screw rows and PCB standoff centres.
mp_dovetail_y = [12.0,31.0];
mp_dovetail_base_w = 2.4;
mp_dovetail_top_w = 4.0;
mp_dovetail_h = 1.8;
mp_dovetail_skin = 0.4;
mp_dovetail_clearance = 0.30;
mp_dovetail_groove_depth = 1.90;

mp_dovetail_rail_x0 = 2.0;
mp_dovetail_rail_x1 = 74.0;
mp_dovetail_rail_len = mp_dovetail_rail_x1-mp_dovetail_rail_x0;

mp_dovetail_groove_x0 = -0.2;
mp_dovetail_groove_x1 = mp_carrier_w+0.5;
mp_dovetail_groove_len =
    mp_dovetail_groove_x1-mp_dovetail_groove_x0;
mp_dovetail_groove_bottom_w =
    mp_dovetail_base_w+2*mp_dovetail_clearance;
mp_dovetail_groove_top_w =
    mp_dovetail_top_w+2*mp_dovetail_clearance;

// Positive seated stop. A 0.2 mm nominal gap avoids a CAD hard-intersection;
// the click detent establishes the repeatable seated position.
mp_stop_x0 = mp_carrier_w+0.2;
mp_stop_w = 2.0;
mp_stop_h = mp_dovetail_h+0.8;

// PETG click detent: a shallow bump on the lower dovetail flexes through the
// carrier groove and settles into a deeper roof pocket at the seated position.
// It is intentionally modest so the pull tab can release the carrier without
// a separate lever.
mp_detent_x = 69.0;
mp_detent_len = 3.6;
mp_detent_extra_h = 0.60;
mp_detent_pocket_extra_depth = 0.55;
mp_detent_interference =
    mp_detent_extra_h -
    (mp_slide_z_clearance +
     mp_dovetail_groove_depth -
     mp_dovetail_h);

assert(mp_detent_interference > 0.15 &&
       mp_detent_interference < 0.35,
       "MatrixPortal dock detent should retain 0.15-0.35 mm click interference");
assert(mp_dovetail_groove_depth+mp_detent_pocket_extra_depth <
       mp_carrier_t-0.25,
       "Detent pocket leaves too little carrier roof");

// ----- Left-side service opening -----
// The complete carrier + raised PCB now passes through this opening. The
// nominal current enclosure places the PCB rear face at about Z=34.35 mm.
mp_service_center_y = 82.50;
mp_service_size_y = 52.0;
mp_service_center_z = 34.0;
mp_service_size_z = 31.0;
mp_service_corner_r = 2.0;

// Board is still inside the 256 mm module and the carrier covers its footprint.
assert(mp_board_service_edge_x > 0,
       "MatrixPortal service edge must remain inside the 256 mm module");
assert(mp_carrier_x0 <= mp_board_x0 &&
       mp_carrier_x0+mp_carrier_w >= mp_board_x0+mp_pcb_w,
       "carrier must cover the MatrixPortal footprint in X");
assert(mp_carrier_y0 <= mp_board_y0 &&
       mp_carrier_y0+mp_carrier_h >= mp_board_y0+mp_pcb_h,
       "carrier must cover the MatrixPortal footprint in Y");

module mp_rounded_rect_2d(w,h,r) {
    assert(w > 2*r && h > 2*r);
    hull()
        for (x=[r,w-r])
            for (y=[r,h-r])
                translate([x,y]) circle(r=r,$fn=32);
}

module mp_pcb_outline_2d() {
    // Four 2.54 mm rounded corners from the official Dimension layer.
    difference() {
        hull()
            for (x=[mp_pcb_corner_r,mp_pcb_w-mp_pcb_corner_r])
                for (y=[mp_pcb_corner_r,mp_pcb_h-mp_pcb_corner_r])
                    translate([x,y]) circle(r=mp_pcb_corner_r,$fn=48);

        // Small official left-edge relief:
        // (0,35.56) -> (0.889,36.449) -> (0.889,39.624) -> (0,40.513)
        polygon([
            [-0.2,35.56],
            [0.889,36.449],
            [0.889,39.624],
            [-0.2,40.513]
        ]);
    }
}

module matrixportal_s3_reference(show_components=true) {
    difference() {
        color("darkgreen")
            linear_extrude(height=mp_pcb_t)
                mp_pcb_outline_2d();

        for (x=mp_pcb_hole_x_native)
            for (y=mp_pcb_hole_y_native)
                translate([x,y,-0.2])
                    cylinder(d=mp_pcb_hole_d,h=mp_pcb_t+0.4,$fn=32);
    }

    if (show_components) {
        // USB-C service connector on the native LEFT short edge.
        color("silver")
            translate([-2.2,mp_usb_y_native-4.5,mp_pcb_t])
                cube([4.5,9.0,3.4]);

        // Right-angle Reset / Up / Down actuators on the same service edge.
        for (yy=[mp_reset_y_native,mp_up_y_native,mp_down_y_native])
            color("orange")
                translate([-1.4,yy-2.1,mp_pcb_t+0.4])
                    cube([3.2,4.2,2.8]);

        // Approximate top-side HUB75 connector envelope.
        color("gray")
            translate([mp_hub75_x_native-4.0,
                       mp_hub75_y_native-13.0,
                       mp_pcb_t])
                cube([7.5,26.0,8.0]);

        // Conservative underside connector envelope. Native negative Z becomes
        // the backplane-facing direction in the installed mirrored preview.
        color("deepskyblue",0.75)
            translate([mp_hub75_x_native-4.0,
                       mp_hub75_y_native-13.0,
                       -mp_underside_connector_h])
                cube([7.5,26.0,mp_underside_connector_h]);
    }
}

module mp_dock_mount_cutters(extra=0.6) {
    for (xx=mp_backplane_mount_x)
        for (yy=mp_backplane_mount_y) {
            lx = xx-mp_dock_x0;
            ly = yy-mp_dock_y0;

            // M3 clearance through the fixed dock.
            translate([lx,ly,-extra/2])
                cylinder(
                    d=mp_dock_m3_hole_d,
                    h=mp_dock_t+extra,
                    $fn=32
                );

            // Equipment-side screw head recess sits below the sliding carrier.
            translate([
                lx,
                ly,
                mp_dock_t-mp_dock_m3_head_recess
            ])
                cylinder(
                    d=mp_dock_m3_head_d,
                    h=mp_dock_m3_head_recess+extra/2,
                    $fn=32
                );

            // Back-face socket registers positively on each 7 mm boss body.
            translate([lx,ly,-0.1])
                cylinder(
                    d=mp_dock_boss_pocket_d,
                    h=mp_dock_boss_pocket_depth+0.1,
                    $fn=32
                );
        }
}

module mp_dovetail_rail(yc,with_detent=false) {
    union() {
        hull() {
            translate([
                mp_dovetail_rail_x0,
                yc-mp_dovetail_base_w/2,
                mp_dock_t-0.2
            ])
                cube([
                    mp_dovetail_rail_len,
                    mp_dovetail_base_w,
                    mp_dovetail_skin
                ]);
            translate([
                mp_dovetail_rail_x0,
                yc-mp_dovetail_top_w/2,
                mp_dock_t+mp_dovetail_h-mp_dovetail_skin
            ])
                cube([
                    mp_dovetail_rail_len,
                    mp_dovetail_top_w,
                    mp_dovetail_skin+0.2
                ]);
        }

        if (with_detent)
            hull() {
                // Smooth lead-in/out shoulders rather than a sharp blocking lip.
                translate([
                    mp_detent_x-mp_detent_len/2,
                    yc-mp_dovetail_top_w/2,
                    mp_dock_t+mp_dovetail_h-0.15
                ])
                    cube([0.5,mp_dovetail_top_w,0.15]);
                translate([
                    mp_detent_x-0.45,
                    yc-mp_dovetail_top_w/2,
                    mp_dock_t+mp_dovetail_h+
                        mp_detent_extra_h-0.15
                ])
                    cube([0.9,mp_dovetail_top_w,0.15]);
                translate([
                    mp_detent_x+mp_detent_len/2-0.5,
                    yc-mp_dovetail_top_w/2,
                    mp_dock_t+mp_dovetail_h-0.15
                ])
                    cube([0.5,mp_dovetail_top_w,0.15]);
            }
    }
}

module matrixportal_s3_dock_print() {
    union() {
        difference() {
            linear_extrude(height=mp_dock_t)
                mp_rounded_rect_2d(
                    mp_dock_w,
                    mp_dock_h,
                    mp_dock_corner_r
                );
            mp_dock_mount_cutters();
        }

        // Lower rail carries the click detent; upper rail is plain guidance.
        mp_dovetail_rail(mp_dovetail_y[0],true);
        mp_dovetail_rail(mp_dovetail_y[1],false);

        // Positive insertion stop lives beyond the carrier leading edge.
        translate([
            mp_stop_x0,
            0,
            mp_dock_t-0.2
        ])
            cube([
                mp_stop_w,
                mp_dock_h,
                mp_stop_h+0.2
            ]);
    }
}

module mp_dovetail_groove_cutter(yc,pocket=false) {
    union() {
        hull() {
            translate([
                mp_dovetail_groove_x0,
                yc-mp_dovetail_groove_bottom_w/2,
                -0.2
            ])
                cube([
                    mp_dovetail_groove_len,
                    mp_dovetail_groove_bottom_w,
                    mp_dovetail_skin
                ]);
            translate([
                mp_dovetail_groove_x0,
                yc-mp_dovetail_groove_top_w/2,
                mp_dovetail_groove_depth-mp_dovetail_skin
            ])
                cube([
                    mp_dovetail_groove_len,
                    mp_dovetail_groove_top_w,
                    mp_dovetail_skin+0.2
                ]);
        }

        if (pocket)
            translate([
                mp_detent_x-mp_detent_len/2-0.4,
                yc-mp_dovetail_groove_top_w/2-0.2,
                mp_dovetail_groove_depth-0.1
            ])
                cube([
                    mp_detent_len+0.8,
                    mp_dovetail_groove_top_w+0.4,
                    mp_detent_pocket_extra_depth+0.2
                ]);
    }
}

module mp_carrier_plate() {
    union() {
        linear_extrude(height=mp_carrier_t)
            mp_rounded_rect_2d(
                mp_carrier_w,
                mp_carrier_h,
                mp_carrier_corner_r
            );

        // Low-profile pull tab is centred in the service opening.
        translate([
            -mp_pull_tab_len,
            mp_pull_tab_y0,
            0
        ])
            cube([
                mp_pull_tab_len+0.5,
                mp_pull_tab_h,
                mp_carrier_t
            ]);
    }
}

module mp_board_locating_pin(local_x,local_y) {
    board_bottom_z = mp_carrier_t+mp_board_standoff_h;
    board_top_z = board_bottom_z+mp_pcb_t;
    groove_z0 = board_top_z+mp_board_pin_stem_above_pcb;

    // Solid standoff supports the PCB around its plated mounting hole.
    translate([local_x,local_y,mp_carrier_t-0.2])
        cylinder(
            d=mp_board_standoff_d,
            h=mp_board_standoff_h+0.2,
            $fn=36
        );

    // 2.20 mm locating stem through the PCB and up to the keeper groove.
    translate([local_x,local_y,board_bottom_z-0.25])
        cylinder(
            d=mp_board_pin_d,
            h=mp_pcb_t+mp_board_pin_stem_above_pcb+0.25,
            $fn=28
        );

    // Reduced keeper neck.
    translate([local_x,local_y,groove_z0])
        cylinder(
            d=mp_board_pin_groove_d,
            h=mp_board_pin_groove_h,
            $fn=24
        );

    // Full-diameter tip prevents a locked keeper bar lifting off the post.
    translate([
        local_x,
        local_y,
        groove_z0+mp_board_pin_groove_h
    ])
        cylinder(
            d=mp_board_pin_d,
            h=mp_board_pin_tip_h,
            $fn=28
        );
}

module matrixportal_s3_carrier_print() {
    union() {
        difference() {
            mp_carrier_plate();

            // Open-ended grooves allow insertion from the left service side.
            mp_dovetail_groove_cutter(mp_dovetail_y[0],true);
            mp_dovetail_groove_cutter(mp_dovetail_y[1],false);
        }

        // Raised standoffs with fixed locating/keeper pins. No M2.5 hardware is
        // required on the MatrixPortal itself.
        for (bx=mp_pcb_hole_x_native)
            for (by=mp_pcb_hole_y_native)
                mp_board_locating_pin(
                    mp_board_carrier_x0+bx,
                    mp_board_carrier_y0+by
                );
    }
}

module mp_keeper_lower_keyhole(yc) {
    // Entry circle drops over the full 2.20 mm pin tip.
    translate([0,yc,-0.1])
        cylinder(
            d=mp_keeper_entry_d,
            h=mp_keeper_capture_h+0.2,
            $fn=28
        );

    // Normal running slot from entry toward the terminal click.
    translate([
        -mp_keeper_slot_w/2,
        yc,
        -0.1
    ])
        cube([
            mp_keeper_slot_w,
            mp_keeper_lock_travel-0.70,
            mp_keeper_capture_h+0.2
        ]);

    // Narrow 0.40 mm throat gives the keeper its tactile click.
    translate([
        -mp_keeper_throat_w/2,
        yc+mp_keeper_lock_travel-0.80,
        -0.1
    ])
        cube([
            mp_keeper_throat_w,
            0.45,
            mp_keeper_capture_h+0.2
        ]);

    // Terminal pocket receives the 1.60 mm neck after the throat.
    translate([
        0,
        yc+mp_keeper_lock_travel,
        -0.1
    ])
        cylinder(
            d=mp_keeper_slot_w,
            h=mp_keeper_capture_h+0.2,
            $fn=24
        );
}

module mp_keeper_upper_tip_clearance(yc) {
    // Above the capture layer, keep enough room for the full 2.20 mm pin tip
    // throughout the slide from entry to locked position.
    hull() {
        translate([0,yc,mp_keeper_capture_h-0.05])
            cylinder(
                d=mp_keeper_upper_clearance_w,
                h=mp_keeper_t-mp_keeper_capture_h+0.15,
                $fn=28
            );
        translate([
            0,
            yc+mp_keeper_lock_travel,
            mp_keeper_capture_h-0.05
        ])
            cylinder(
                d=mp_keeper_upper_clearance_w,
                h=mp_keeper_t-mp_keeper_capture_h+0.15,
                $fn=28
            );
    }
}

module mp_keeper_foot_clearance(yc) {
    // Feet slide across only the mounting-hole keepout. Give the full pin stem
    // an elongated clearance path while the keeper moves into lock.
    hull() {
        translate([0,yc,-mp_keeper_foot_h-0.1])
            cylinder(
                d=mp_keeper_entry_d,
                h=mp_keeper_foot_h+0.2,
                $fn=28
            );
        translate([
            0,
            yc+mp_keeper_lock_travel,
            -mp_keeper_foot_h-0.1
        ])
            cylinder(
                d=mp_keeper_entry_d,
                h=mp_keeper_foot_h+0.2,
                $fn=28
            );
    }
}

module matrixportal_s3_keeper_use() {
    y1 = mp_keeper_end_margin;
    y2 = mp_keeper_end_margin+mp_keeper_hole_spacing;

    difference() {
        union() {
            // Elevated bridge stays 4.5 mm above the PCB top surface.
            translate([
                -mp_keeper_w/2,
                0,
                0
            ])
                cube([
                    mp_keeper_w,
                    mp_keeper_len,
                    mp_keeper_t
                ]);

            // Two local feet descend only at the mounting-hole keepouts.
            for (yy=[y1,y2])
                translate([
                    -mp_keeper_w/2,
                    yy-3.1,
                    -mp_keeper_foot_h
                ])
                    cube([
                        mp_keeper_w,
                        6.2,
                        mp_keeper_foot_h+0.15
                    ]);
        }

        for (yy=[y1,y2]) {
            mp_keeper_lower_keyhole(yy);
            mp_keeper_upper_tip_clearance(yy);
            mp_keeper_foot_clearance(yy);
        }
    }
}

module matrixportal_s3_keeper_print() {
    // Print the bridge flat on the bed with its two feet rising upward. This
    // avoids support beneath the elevated in-use bridge.
    translate([
        mp_keeper_w/2,
        mp_keeper_len,
        mp_keeper_t
    ])
        rotate([180,0,0])
            matrixportal_s3_keeper_use();
}

module matrixportal_s3_keepers_carrier_local(locked=true) {
    board_top_z =
        mp_carrier_t+
        mp_board_standoff_h+
        mp_pcb_t;
    keeper_y0 =
        mp_board_carrier_y0+
        mp_pcb_hole_y_native[0]-
        mp_keeper_end_margin-
        (locked ? mp_keeper_lock_travel : 0);

    for (bx=mp_pcb_hole_x_native)
        translate([
            mp_board_carrier_x0+bx,
            keeper_y0,
            board_top_z+mp_keeper_bridge_clearance
        ])
            matrixportal_s3_keeper_use();
}

module matrixportal_s3_dock_installed(boss_tip_z) {
    // Print +Z maps toward the panel (negative installed enclosure Z).
    translate([mp_dock_x0,mp_dock_y0,boss_tip_z])
        mirror([0,0,1])
            matrixportal_s3_dock_print();
}

module matrixportal_s3_carrier_installed(boss_tip_z,slide_x=0) {
    translate([
        mp_carrier_x0+slide_x,
        mp_carrier_y0,
        boss_tip_z
    ])
        mirror([0,0,1])
            translate([0,0,mp_carrier_assembled_z])
                matrixportal_s3_carrier_print();
}

module matrixportal_s3_keepers_installed(
    boss_tip_z,
    slide_x=0,
    locked=true
) {
    translate([
        mp_carrier_x0+slide_x,
        mp_carrier_y0,
        boss_tip_z
    ])
        mirror([0,0,1])
            translate([0,0,mp_carrier_assembled_z])
                matrixportal_s3_keepers_carrier_local(locked);
}

module matrixportal_s3_reference_installed(
    boss_tip_z,
    show_components=true,
    slide_x=0
) {
    board_back_z =
        boss_tip_z -
        mp_carrier_assembled_z -
        mp_carrier_t -
        mp_board_standoff_h;

    translate([
        mp_board_x0+slide_x,
        mp_board_y0,
        board_back_z
    ])
        mirror([0,0,1])
            matrixportal_s3_reference(show_components);
}

module mp_rounded_rect_x_cutter(
    x0,
    x_len,
    center_y,
    center_z,
    size_y,
    size_z,
    corner_r
) {
    assert(size_y > 2*corner_r && size_z > 2*corner_r);
    hull()
        for (yy=[
            center_y-size_y/2+corner_r,
            center_y+size_y/2-corner_r
        ])
            for (zz=[
                center_z-size_z/2+corner_r,
                center_z+size_z/2-corner_r
            ])
                translate([x0,yy,zz])
                    rotate([0,90,0])
                        cylinder(r=corner_r,h=x_len,$fn=32);
}

module matrixportal_left_side_service_cutter() {
    // These enclosure variables are provided by direct_mount_enclosure.scad.
    x0 = -side_panel_clearance-side_t-1.0;
    x1 = side_upper_overlap+1.0;

    mp_rounded_rect_x_cutter(
        x0,
        x1-x0,
        mp_service_center_y,
        mp_service_center_z,
        mp_service_size_y,
        mp_service_size_z,
        mp_service_corner_r
    );
}

module matrixportal_left_equipment_side() {
    difference() {
        equipment_side("left");
        matrixportal_left_side_service_cutter();
    }
}
