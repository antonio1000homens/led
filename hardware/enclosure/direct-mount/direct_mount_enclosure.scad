// Modular direct-mount enclosure/backplane for four 256 x 128 mm P4 HUB75 panels.
// Issue #53 - antonio1000homens/led
//
// P4 physical-panel geometry:
// A calibrated 1:1 ruler photograph plus an independent Kiri Engine scan show
// six brass mounting inserts in a symmetric 3 x 2 pattern:
//   x = 6.4, 128.0, 249.6 mm
//   y = 6.4, 121.6 mm
// These replace the obsolete four-point pattern inferred from a scaled P2.5 panel.
//
// The previously inferred four-point centres (26.704/229.296 x 12/116 mm)
// are retained only as clearance centres for protruding moulded locating pins.
// The physical test print showed at least one of those panel pins entering the
// old slot, so the replacement backplane provides explicit round clearance there.
// Final acceptance remains a physical fit test against the real P4 panel.
//
// Design intent:
// - Print four identical backplane modules and bolt each LED module directly to one backplane.
// - All printed structure remains BEHIND the LED face; nothing masks the 256 x 128 mm front.
// - Two 1000 x 8 mm round reinforcement bars pass through all four modules.
// - Bars are offset from the measured panel mounting rows and locator clearances.
// - Neighbouring modules align with tongue/socket keys and are locked with rear M3 joiner plates.
// - Each 4 mm joiner sits in matching rear recesses so its outside face is almost flush with the backplanes.
// - The LED-panel-facing side of every backplane stays flat and unchanged.
// - Rear electronics carriers use blind M3 heat-set-insert pockets.

$fn = 48;
// `part` is intentionally not assigned here: command-line -D and the per-part
// wrapper SCAD files may set it. If undefined, the default render is backplane.

module_w = 256;
module_h = 128;
depth = 16;
frame = 16;

// Measured/scan-validated P4 brass insert centres.
panel_mount_x = [6.4, 128.0, 249.6];
panel_mount_y = [6.4, 121.6];
panel_mount_hole_d = 4.5; // M3/M4 clearance with small measurement/print tolerance.

// Moulded locating-pin clearance. These four centres correspond to the old
// provisional P2.5-derived slots; they are NOT panel screw locations.
panel_locator_x = [26.704, 229.296];
panel_locator_y = [12.0, 116.0];
panel_locator_clearance_d = 8.0;

slot_len = 10;
slot_w = 4.2;

rod_d = 9.2;
rod_leadin_d = 10.4;
rod_leadin_len = 1.5;
rod_z = depth/2;
rod_y_bottom = 24;
rod_y_top = module_h-24;
rod_beam_h = 12;

joint_len = 6;
joint_w = 11.5;
joint_h = 7.2;
joint_z = 4;
joint_clear = 0.35;
joint_y1 = 37;
joint_y2 = 79;

joiner_insert_x = 8;
joiner_insert_y1 = 50;
joiner_insert_y2 = 78;
joiner_w = 32;
joiner_h = 48;
joiner_t = 4;
joiner_hole_y_inset = 10;
joiner_countersink_d = 6.4;
joiner_countersink_depth = 1.7;
joiner_clear_xy = 0.25;
joiner_clear_z = 0.20;
joiner_recess_depth = joiner_t + joiner_clear_z;
joiner_recess_half_w = joiner_w/2 + joiner_clear_xy;
joiner_recess_y = joiner_insert_y1 - joiner_hole_y_inset - joiner_clear_xy;
joiner_recess_h = joiner_h + 2*joiner_clear_xy;
joiner_recess_surface_z = depth - joiner_recess_depth;
// M3 x 6 x 4.5 mm brass heat-set insert target.
// 4.0 mm is the nominal printed pilot; verify with the coupon for the chosen filament/printer before structural prints.
insert_d = 4.0;
insert_depth = 6.2;

accessory_insert_x = 12;
accessory_insert_y1 = 34;
accessory_insert_y2 = 94;

module slot2d(len=slot_len, w=slot_w) {
    hull() {
        translate([-(len-w)/2,0]) circle(d=w);
        translate([(len-w)/2,0]) circle(d=w);
    }
}

module cross_slot(x,y,h=depth+1) {
    translate([x,y,-0.5]) linear_extrude(height=h) {
        union() {
            slot2d(slot_len, slot_w);
            rotate(90) slot2d(slot_len, slot_w);
        }
    }
}

module blind_insert_pocket(x,y,surface_z=depth,d=insert_d,dep=insert_depth) {
    translate([x,y,surface_z-dep]) cylinder(d=d,h=dep+0.25);
}

module rod_bore(y) {
    translate([-0.5,y,rod_z])
        rotate([0,90,0]) cylinder(d=rod_d,h=module_w+1.0);

    // FDM-friendly lead-ins reduce snagging when a 1 m rod crosses four prints.
    translate([-0.6,y,rod_z])
        rotate([0,90,0]) cylinder(d1=rod_leadin_d,d2=rod_d,h=rod_leadin_len);
    translate([module_w-rod_leadin_len+0.1,y,rod_z])
        rotate([0,90,0]) cylinder(d1=rod_d,d2=rod_leadin_d,h=rod_leadin_len+0.5);
}

module backplane_body(with_right_tongues=true) {
    union() {
        cube([module_w,frame,depth]);
        translate([0,module_h-frame,0]) cube([module_w,frame,depth]);
        translate([0,frame,0]) cube([frame,module_h-2*frame,depth]);
        translate([module_w-frame,frame,0]) cube([frame,module_h-2*frame,depth]);

        translate([0,rod_y_bottom-rod_beam_h/2,0]) cube([module_w,rod_beam_h,depth]);
        translate([0,rod_y_top-rod_beam_h/2,0]) cube([module_w,rod_beam_h,depth]);

        if (with_right_tongues)
            for (yy=[joint_y1,joint_y2])
                translate([module_w-0.6,yy,joint_z]) cube([joint_len+0.6,joint_w,joint_h]);
    }
}

module joiner_recesses(include_right_side=true) {
    // The 32 mm joiner is centred on a module seam, so each backplane
    // provides half of the pocket. Extra XY/Z clearance prevents a
    // printed joiner from holding either backplane off the LED PCB.
    translate([-0.01,joiner_recess_y,joiner_recess_surface_z])
        cube([joiner_recess_half_w+0.01,joiner_recess_h,joiner_recess_depth+0.01]);
    if (include_right_side)
        translate([module_w-joiner_recess_half_w,joiner_recess_y,joiner_recess_surface_z])
            cube([joiner_recess_half_w+0.01,joiner_recess_h,joiner_recess_depth+0.01]);
}

module backplane(right_end=false) {
    difference() {
        backplane_body(!right_end);

        for (yy=[rod_y_bottom,rod_y_top]) rod_bore(yy);

        // Six real P4 mounting holes: three along each long edge.
        for (x=panel_mount_x)
            for (y=panel_mount_y)
                translate([x,y,-0.5]) cylinder(d=panel_mount_hole_d,h=depth+1);

        // Clearance for the panel's protruding moulded locating pins.
        // Kept separate from the brass mounting holes so the two functions
        // cannot be confused during assembly.
        for (x=panel_locator_x)
            for (y=panel_locator_y)
                translate([x,y,-0.5]) cylinder(d=panel_locator_clearance_d,h=depth+1);

        for (yy=[joint_y1,joint_y2])
            translate([-0.1,yy-joint_clear/2,joint_z-joint_clear/2])
                cube([joint_len+0.2,joint_w+joint_clear,joint_h+joint_clear]);

        joiner_recesses(!right_end);

        // Keep the full heat-set-insert depth, measured from the new recess floor.
        // The right-end module has no unused outer seam hardware.
        for (xx = right_end ? [joiner_insert_x] : [joiner_insert_x,module_w-joiner_insert_x])
            for (yy=[joiner_insert_y1,joiner_insert_y2])
                blind_insert_pocket(xx,yy,joiner_recess_surface_z);

        for (xx=[accessory_insert_x,module_w-accessory_insert_x])
            for (yy=[accessory_insert_y1,accessory_insert_y2]) blind_insert_pocket(xx,yy);
    }
}

module module_joiner() {
    difference() {
        cube([joiner_w,joiner_h,joiner_t]);
        for (xx=[joiner_insert_x,joiner_w-joiner_insert_x])
            for (yy=[joiner_hole_y_inset,joiner_h-joiner_hole_y_inset]) {
                translate([xx,yy,-0.5]) cylinder(d=3.5,h=joiner_t+1);
                // 90-degree countersink for a flush M3 flat-head screw.
                translate([xx,yy,joiner_t-joiner_countersink_depth])
                    cylinder(d1=3.5,d2=joiner_countersink_d,h=joiner_countersink_depth+0.1);
            }
    }
}

module rod_end_plug() {
    cap_t = 2.5;
    stem_len = 11.4;
    difference() {
        union() {
            cylinder(h=cap_t,d=13);
            translate([0,0,cap_t]) cylinder(h=stem_len,d1=9.25,d2=9.05);
            // Compressible detent gives the plug positive friction retention
            // in the 9.2 mm bore without adhesive.
            translate([0,0,cap_t+stem_len-2.0]) cylinder(h=0.9,d=9.45);
        }
        // Split the outer half of the stem so the detent can compress on entry.
        translate([-0.6,-5,cap_t+4.0]) cube([1.2,10,stem_len]);
    }
}

carrier_w = 244;
carrier_h = 72;
carrier_t = 4;
carrier_hole_x = 6;
carrier_hole_y = 6;

// MatrixPortal S3 side-access carrier.
//
// Panel 1 uses the standard #82/#83 four-point carrier-to-backplane interface,
// so the carrier itself still sits at x=6..250 on the 256 mm backplane.
// The MatrixPortal PCB is shifted left within the carrier so its physical left
// edge sits 10 mm beyond the Panel 1 PCB/backplane edge:
//   global board left = carrier global x (6) + matrixportal_pcb_x (-16) = -10 mm.
//
// Adafruit places the MatrixPortal over the matrix edge to keep the left-edge
// USB-C and Reset/Up/Down buttons reachable. This design uses the component-side
// HUB75 IDC connector and a short ribbon cable instead of requiring the board to
// line up with the panel's rear HUB75 connector.
matrixportal_pcb_w = 44.45;
matrixportal_pcb_h = 63.50;
matrixportal_pcb_x = -16.0;
matrixportal_pcb_y = (carrier_h-matrixportal_pcb_h)/2;
matrixportal_side_overhang_global = 10.0;

// Hole offsets within the MatrixPortal PCB, derived from the existing official
// PCB mounting geometry used by PR #84.
matrixportal_hole_x1 = 15.875;
matrixportal_hole_x2 = 35.560;
matrixportal_hole_y1 = 15.240;
matrixportal_hole_y2 = 55.880;

matrixportal_standoff_d = 8;
matrixportal_standoff_z = 2;
matrixportal_standoff_h = 8;
matrixportal_hole_d = 2.8; // round M2.5 clearance hole
matrixportal_nut_af = 5.0; // nominal M2.5 hex nut across flats
matrixportal_nut_h = 2.2;
matrixportal_support_rib_w = 6;
matrixportal_support_rib_h = 2;

// Carrier-local mounting centres after moving the board to the left service edge.
matrixportal_mount_points = [
    [matrixportal_pcb_x + matrixportal_hole_x1, matrixportal_pcb_y + matrixportal_hole_y1],
    [matrixportal_pcb_x + matrixportal_hole_x2, matrixportal_pcb_y + matrixportal_hole_y1],
    [matrixportal_pcb_x + matrixportal_hole_x1, matrixportal_pcb_y + matrixportal_hole_y2],
    [matrixportal_pcb_x + matrixportal_hole_x2, matrixportal_pcb_y + matrixportal_hole_y2]
];

module carrier_frame() {
    difference() {
        union() {
            cube([carrier_w,12,carrier_t]);
            translate([0,carrier_h-12,0]) cube([carrier_w,12,carrier_t]);
            cube([12,carrier_h,carrier_t]);
            translate([carrier_w-12,0,0]) cube([12,carrier_h,carrier_t]);
        }
        // Preserve the #82/#83 validated carrier/backplane interface.
        for (xx=[carrier_hole_x,carrier_w-carrier_hole_x])
            for (yy=[carrier_hole_y,carrier_h-carrier_hole_y])
                translate([xx,yy,-0.5]) cylinder(d=3.5,h=carrier_t+1);
    }
}

module elongated_hole(len=12,d=3.2,h=10) {
    hull() {
        translate([-len/2+d/2,0,0]) cylinder(d=d,h=h);
        translate([ len/2-d/2,0,0]) cylinder(d=d,h=h);
    }
}

module matrixportal_carrier_frame() {
    // Retain the validated full-width carrier so all four M3 backplane points
    // remain unchanged. The MatrixPortal now occupies only the left end.
    difference() {
        union() {
            cube([carrier_w,12,carrier_t]);
            translate([0,carrier_h-12,0]) cube([carrier_w,12,carrier_t]);
            cube([12,carrier_h,carrier_t]);
            translate([carrier_w-12,0,0]) cube([12,carrier_h,carrier_t]);
        }
        // The perimeter frame already leaves a broad open centre. The former
        // 72 mm full-height centre cutout used by the centred MatrixPortal
        // would split this side-access carrier into disconnected left/right
        // shells, so it is intentionally omitted.
        for (xx=[carrier_hole_x,carrier_w-carrier_hole_x])
            for (yy=[carrier_hole_y,carrier_h-carrier_hole_y])
                translate([xx,yy,-0.5]) cylinder(d=3.5,h=carrier_t+1);
    }
}

module matrixportal_post_supports() {
    // Each row is tied into the existing left rail. The outer PCB standoff is
    // allowed to sit slightly left of the carrier origin; its 8 mm boss still
    // overlaps the x=0..12 carrier rail and remains entirely inside Panel 1
    // once the carrier is translated +6 mm onto the backplane.
    for (row_y=[
        matrixportal_pcb_y + matrixportal_hole_y1,
        matrixportal_pcb_y + matrixportal_hole_y2
    ])
        translate([0,row_y-matrixportal_support_rib_w/2,0])
            cube([
                matrixportal_pcb_x + matrixportal_hole_x2,
                matrixportal_support_rib_w,
                matrixportal_support_rib_h
            ]);
}

module matrixportal_mount() {
    difference() {
        union() {
            matrixportal_carrier_frame();
            matrixportal_post_supports();

            for (point=matrixportal_mount_points)
                translate([point[0],point[1],matrixportal_standoff_z])
                    cylinder(d=matrixportal_standoff_d,h=matrixportal_standoff_h);
        }

        for (point=matrixportal_mount_points)
            translate([point[0],point[1],-0.5])
                cylinder(d=matrixportal_hole_d,h=carrier_t+7);

        // Captive M2.5 nut pockets remain accessible from the rear/underside.
        for (point=matrixportal_mount_points)
            translate([point[0],point[1],-0.01])
                rotate([0,0,30])
                    cylinder(d=matrixportal_nut_af,h=matrixportal_nut_h,$fn=6);

        // Preserve the existing central service opening.
        translate([carrier_w/2-22,carrier_h/2-6,-0.5]) cube([44,12,carrier_t+1]);
    }
}

module power_distribution_mount() {
    difference() {
        union() {
            carrier_frame();
            translate([(carrier_w-126)/2,(carrier_h-52)/2,0]) cube([126,52,carrier_t]);
        }
        for (xx=[carrier_w/2-48,carrier_w/2+48])
            for (yy=[carrier_h/2-16,carrier_h/2+16])
                translate([xx,yy,-0.5]) elongated_hole(20,4.2,carrier_t+1);
        for (yy=[carrier_h/2-12,carrier_h/2+12])
            translate([carrier_w/2+56,yy,-0.5]) cube([3.5,12,carrier_t+1]);
    }
}

module cable_clip() {
    difference() {
        union() {
            cube([24,14,4]);
            translate([12,14,6]) rotate([90,0,0]) cylinder(d=12,h=14);
        }
        translate([12,15,6]) rotate([90,0,0]) cylinder(d=7,h=16);
        translate([10.5,-1,8]) cube([3,16,6]);
        translate([4,7,-0.5]) cylinder(d=3.5,h=5);
    }
}

module mounting_slot_coupon() {
    coupon_t = 8;
    difference() {
        cube([42,42,coupon_t]);
        translate([21,21,-0.5]) linear_extrude(height=coupon_t+1) {
            union() {
                slot2d(slot_len,slot_w);
                rotate(90) slot2d(slot_len,slot_w);
            }
        }
        // Reproduce the production 6.2 mm blind heat-set pocket exactly.
        blind_insert_pocket(7,7,coupon_t,insert_d,insert_depth);
    }
}

module mount_pattern_template() {
    template_t = 2;
    band_h = 20;
    side_w = 8;
    difference() {
        union() {
            cube([module_w,band_h,template_t]);
            translate([0,module_h-band_h,0]) cube([module_w,band_h,template_t]);
            cube([side_w,module_h,template_t]);
            translate([module_w-side_w,0,0]) cube([side_w,module_h,template_t]);
        }
        for (x=panel_mount_x)
            for (y=panel_mount_y)
                translate([x,y,-0.5]) cylinder(d=panel_mount_hole_d,h=template_t+1);

        for (x=panel_locator_x)
            for (y=panel_locator_y)
                translate([x,y,-0.5]) cylinder(d=panel_locator_clearance_d,h=template_t+1);
    }
}

if (is_undef(part) || part == "backplane") backplane(false);
else if (part == "backplane_right") backplane(true);
else if (part == "joiner") module_joiner();
else if (part == "rod_plug") rod_end_plug();
else if (part == "matrixportal_mount") matrixportal_mount();
else if (part == "power_mount") power_distribution_mount();
else if (part == "cable_clip") cable_clip();
else if (part == "slot_coupon") mounting_slot_coupon();
else if (part == "mount_pattern_template") mount_pattern_template();
else if (part != "__library__") assert(false, str("Unknown part: ",part));