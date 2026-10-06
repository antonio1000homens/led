// Adafruit MatrixPortal S3 detachable enclosure mount.
//
// Mechanical source of truth:
//   Adafruit-MatrixPortal-S3-PCB / Adafruit MatrixPortal S3.brd
//   board: 63.50 x 44.45 mm
//   plated mounting holes: 2.50 mm
//   native hole centres: X=7.62/48.26, Y=15.875/35.56 mm
//
// The printable adapter uses the existing universal backplane M3 boss grid.
// A dedicated right-side variant opens a service window for USB-C and the
// Reset/Up/Down buttons while leaving the generic right side unchanged.

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

// ----- Installed position in the right-most enclosure module -----
// Rotate the PCB 180 degrees in XY so its USB/button short edge faces +X
// (the detachable right side) and the HUB75 edge faces inward.
mp_board_x0 = 191.00;
mp_board_yc = 82.50;
mp_board_y0 = mp_board_yc - mp_pcb_h/2;
mp_board_service_edge_x = mp_board_x0 + mp_pcb_w;

// Rotated mounting-hole centres in board-local coordinates.
mp_pcb_hole_x_rot = [for (x=mp_pcb_hole_x_native) mp_pcb_w-x];
mp_pcb_hole_y_rot = [for (y=mp_pcb_hole_y_native) mp_pcb_h-y];

// ----- Detachable adapter plate -----
// Backplane boss columns/rows used by this adapter.
mp_backplane_mount_x = [176,224];
mp_backplane_mount_y = [62.5,102.5];

mp_adapter_x0 = 169.0;
mp_adapter_y0 = 55.0;
mp_adapter_w = 86.0;
mp_adapter_h = 55.0;
mp_adapter_t = 3.0;
mp_adapter_corner_r = 3.0;

mp_adapter_m3_hole_d = 3.4;
mp_adapter_m3_head_d = 6.5;
mp_adapter_m3_head_recess = 1.8;

mp_board_standoff_d = 7.0;
mp_board_standoff_h = 6.0;
mp_board_screw_clearance_d = 2.8;
// Captive M2.5 nut pocket: approximately 5 mm across flats.
mp_board_nut_pocket_d = 6.0;
mp_board_nut_pocket_h = 2.3;

// ----- Right-side service opening -----
// The four service controls span roughly Y=66.6..96.5 mm after rotation.
// Keep a modest common opening so USB-C plugs and fingers can reach all three
// buttons without weakening the rear connector zone.
mp_service_center_y = 81.55;
mp_service_size_y = 40.0;
mp_service_center_z = 44.0;
mp_service_size_z = 14.0;
mp_service_corner_r = 2.0;

assert(mp_board_service_edge_x < 256,
       "MatrixPortal service edge must remain inside the 256 mm module");
assert(mp_adapter_x0 <= mp_board_x0 &&
       mp_adapter_x0+mp_adapter_w >= mp_board_service_edge_x,
       "adapter plate must cover the MatrixPortal footprint in X");
assert(mp_adapter_y0 <= mp_board_y0 &&
       mp_adapter_y0+mp_adapter_h >= mp_board_y0+mp_pcb_h,
       "adapter plate must cover the MatrixPortal footprint in Y");

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

        // Approximate opposing HUB75 connector envelope.
        color("gray")
            translate([mp_hub75_x_native-4.0,mp_hub75_y_native-13.0,mp_pcb_t])
                cube([7.5,26.0,8.0]);
    }
}

module matrixportal_s3_adapter_print() {
    difference() {
        union() {
            linear_extrude(height=mp_adapter_t)
                mp_rounded_rect_2d(
                    mp_adapter_w,
                    mp_adapter_h,
                    mp_adapter_corner_r
                );

            // Four PCB standoffs align with the official Eagle hole pattern,
            // rotated so the service edge faces the enclosure's right side.
            for (bx=mp_pcb_hole_x_rot)
                for (by=mp_pcb_hole_y_rot)
                    translate([
                        mp_board_x0+bx-mp_adapter_x0,
                        mp_board_y0+by-mp_adapter_y0,
                        mp_adapter_t
                    ])
                        cylinder(
                            d=mp_board_standoff_d,
                            h=mp_board_standoff_h,
                            $fn=36
                        );
        }

        // M3 clearance holes into four existing universal backplane bosses.
        for (xx=mp_backplane_mount_x)
            for (yy=mp_backplane_mount_y) {
                translate([
                    xx-mp_adapter_x0,
                    yy-mp_adapter_y0,
                    -0.2
                ])
                    cylinder(
                        d=mp_adapter_m3_hole_d,
                        h=mp_adapter_t+0.4,
                        $fn=32
                    );

                // Recess the screw heads so they stay below the PCB envelope.
                translate([
                    xx-mp_adapter_x0,
                    yy-mp_adapter_y0,
                    mp_adapter_t-mp_adapter_m3_head_recess
                ])
                    cylinder(
                        d=mp_adapter_m3_head_d,
                        h=mp_adapter_m3_head_recess+0.2,
                        $fn=32
                    );
            }

        // M2.5 board screw passages plus top-loading captive nut pockets.
        for (bx=mp_pcb_hole_x_rot)
            for (by=mp_pcb_hole_y_rot) {
                local_x = mp_board_x0+bx-mp_adapter_x0;
                local_y = mp_board_y0+by-mp_adapter_y0;

                translate([local_x,local_y,mp_adapter_t-0.2])
                    cylinder(
                        d=mp_board_screw_clearance_d,
                        h=mp_board_standoff_h+0.4,
                        $fn=28
                    );

                translate([
                    local_x,
                    local_y,
                    mp_adapter_t+mp_board_standoff_h-mp_board_nut_pocket_h
                ])
                    cylinder(
                        d=mp_board_nut_pocket_d,
                        h=mp_board_nut_pocket_h+0.2,
                        $fn=6
                    );
            }
    }
}

module matrixportal_s3_adapter_installed(boss_tip_z) {
    // Print geometry grows in +Z; installed geometry grows toward the panel
    // (negative enclosure Z) from the front tips of the universal bosses.
    translate([mp_adapter_x0,mp_adapter_y0,boss_tip_z])
        mirror([0,0,1])
            matrixportal_s3_adapter_print();
}

module matrixportal_s3_reference_installed(boss_tip_z,show_components=true) {
    board_back_z =
        boss_tip_z-mp_adapter_t-mp_board_standoff_h;

    // Native service edge is at local X=0. Rotate 180 degrees so it lands at
    // installed +X, next to the right-side service opening.
    translate([
        mp_board_x0+mp_pcb_w,
        mp_board_y0+mp_pcb_h,
        board_back_z-mp_pcb_t
    ])
        rotate([0,0,180])
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

module matrixportal_right_side_service_cutter() {
    // These enclosure variables are provided by direct_mount_enclosure.scad.
    x0 = module_w-side_upper_overlap-1.0;
    x1 = module_w+side_panel_clearance+side_t+1.0;

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

module matrixportal_right_equipment_side() {
    difference() {
        equipment_side("right");
        matrixportal_right_side_service_cutter();
    }
}
