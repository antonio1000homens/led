// Modular direct-mount enclosure/backplane for four 256 x 128 mm P4 HUB75 panels.
// Issue #76 - physical P4 panel pattern captured from the user's panel/template photo.
//
// Coordinate system: rear-facing view, landscape panel, origin at the PCB
// lower-left corner; x increases left-to-right and y bottom-to-top.
// The six-point pattern below is a provisional nominalisation of the observed
// approximately 5.9 mm edge offsets. Physically verify one boss before printing
// a structural backplane; do not revert to the superseded P2.5 scaling model.
//
// Design intent:
// - Print four identical backplane modules and bolt each LED module directly to one backplane.
// - All printed structure remains BEHIND the LED face; nothing masks the 256 x 128 mm front.
// - Two 1000 x 8 mm round reinforcement bars pass through all four modules.
// - Bars are offset from the expected panel mounting rows to avoid the mounting slots.
// - Neighbouring modules align with tongue/socket keys and are locked with rear M3 joiner plates.
// - Each 4 mm joiner sits in matching rear recesses so its outside face is almost flush with the backplanes.
// - The LED-panel-facing side of every backplane stays flat and unchanged.
// - Rear electronics carriers use blind M3 heat-set-insert pockets.

$fn = 48;
part = "backplane";

panel_w = 256;
panel_h = 128;
module_w = panel_w;
module_h = panel_h;
depth = 16;
frame = 16;

// Photo-derived nominal physical P4 mounting points, in millimetres.
panel_mount_points = [
    [6,   6],
    [128, 6],
    [250, 6],
    [6,   122],
    [128, 122],
    [250, 122]
];

slot_len = 10;
slot_w = 4.2;

rod_d = 8.6;
rod_z = depth/2;
rod_y_bottom = 24;
rod_y_top = module_h-24;
rod_beam_h = 12;

joint_len = 6;
joint_w = 11.5;
joint_h = 8;
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

module panel_boss_support(point) {
    // Keep the support pad inside the nominal PCB envelope even for the
    // 6 mm edge-offset bosses. The mounting slot itself remains centred on
    // the measured boss coordinate.
    x0 = max(0, point[0]-9);
    y0 = max(0, point[1]-9);
    x1 = min(module_w, point[0]+9);
    y1 = min(module_h, point[1]+9);
    translate([x0,y0,0]) cube([x1-x0,y1-y0,depth]);
}

module backplane_body() {
    union() {
        cube([module_w,frame,depth]);
        translate([0,module_h-frame,0]) cube([module_w,frame,depth]);
        translate([0,frame,0]) cube([frame,module_h-2*frame,depth]);
        translate([module_w-frame,frame,0]) cube([frame,module_h-2*frame,depth]);

        translate([0,rod_y_bottom-rod_beam_h/2,0]) cube([module_w,rod_beam_h,depth]);
        translate([0,rod_y_top-rod_beam_h/2,0]) cube([module_w,rod_beam_h,depth]);

        // Widen the rear support locally around every real panel boss. The
        // outermost supports intentionally remain inside the 256 x 128 envelope.
        for (point=panel_mount_points) panel_boss_support(point);

        for (yy=[joint_y1,joint_y2])
            translate([module_w-0.6,yy,joint_z]) cube([joint_len+0.6,joint_w,joint_h]);
    }
}

module joiner_recesses() {
    // The 32 mm joiner is centred on a module seam, so each backplane
    // provides half of the pocket. Extra XY/Z clearance prevents a
    // printed joiner from holding either backplane off the LED PCB.
    translate([-0.01,joiner_recess_y,joiner_recess_surface_z])
        cube([joiner_recess_half_w+0.01,joiner_recess_h,joiner_recess_depth+0.01]);
    translate([module_w-joiner_recess_half_w,joiner_recess_y,joiner_recess_surface_z])
        cube([joiner_recess_half_w+0.01,joiner_recess_h,joiner_recess_depth+0.01]);
}

module backplane() {
    difference() {
        backplane_body();

        for (yy=[rod_y_bottom,rod_y_top])
            translate([-0.5,yy,rod_z]) rotate([0,90,0]) cylinder(d=rod_d,h=module_w+7);

        for (point=panel_mount_points)
            cross_slot(point[0],point[1]);

        for (yy=[joint_y1,joint_y2])
            translate([-0.1,yy-joint_clear/2,joint_z-joint_clear/2])
                cube([joint_len+0.2,joint_w+joint_clear,joint_h+joint_clear]);

        joiner_recesses();

        // Keep the full heat-set-insert depth, measured from the new recess floor.
        for (xx=[joiner_insert_x,module_w-joiner_insert_x])
            for (yy=[joiner_insert_y1,joiner_insert_y2])
                blind_insert_pocket(xx,yy,joiner_recess_surface_z);

        // Carrier-to-backplane M3 inserts at the centred carrier interface.
        for (point=[[14,34],[242,34],[14,94],[242,94]])
            blind_insert_pocket(point[0],point[1]);
    }
}

module module_joiner() {
    difference() {
        cube([joiner_w,joiner_h,joiner_t]);
        for (xx=[joiner_insert_x,joiner_w-joiner_insert_x])
            for (yy=[joiner_hole_y_inset,joiner_h-joiner_hole_y_inset])
                translate([xx,yy,-0.5]) cylinder(d=3.5,h=joiner_t+1);
    }
}

module rod_end_plug() {
    union() {
        cylinder(h=2.5,d=13);
        translate([0,0,2.5]) cylinder(h=10.5,d1=8.45,d2=8.20);
    }
}

carrier_w = 244;
carrier_h = 72;
carrier_t = 4;

// Carrier-to-backplane M3 clearance holes. The carrier is centred on the
// 256 x 128 mm backplane at offset (6,28), so these land at
// (14,34), (242,34), (14,94), and (242,94) on the backplane.
carrier_mount_points = [
    [8,   6],
    [236, 6],
    [8,   66],
    [236, 66]
];
carrier_mount_hole_d = 3.5;

// Adafruit MatrixPortal S3 PCB mounting-hole pattern.
// Source: Adafruit MatrixPortal S3 PCB layout (MOUNTINGHOLE_2.5_PLATED centres).
// Portrait orientation: HUB75 at the top and USB-C at the bottom.
matrixportal_pcb_w = 44.45;
matrixportal_pcb_h = 63.50;
matrixportal_pcb_x = (carrier_w-matrixportal_pcb_w)/2;
matrixportal_pcb_y = (carrier_h-matrixportal_pcb_h)/2;
matrixportal_hole_spacing_x = 19.685;
matrixportal_hole_spacing_y = 40.640;
matrixportal_standoff_d = 8;
matrixportal_standoff_h = 6;
matrixportal_hole_d = 2.8; // round M2.5 clearance hole
matrixportal_nut_af = 5.0; // nominal M2.5 hex nut across flats
matrixportal_nut_h = 2.2;
matrixportal_support_rib_w = 6;
matrixportal_support_rib_h = 2;

// Explicit carrier-local coordinates from the official Adafruit PCB geometry.
matrixportal_mount_points = [
    [115.650, 19.490],
    [135.335, 19.490],
    [115.650, 60.130],
    [135.335, 60.130]
];

module carrier_frame() {
    difference() {
        union() {
            cube([carrier_w,12,carrier_t]);
            translate([0,carrier_h-12,0]) cube([carrier_w,12,carrier_t]);
            cube([12,carrier_h,carrier_t]);
            translate([carrier_w-12,0,0]) cube([12,carrier_h,carrier_t]);
        }
        for (point=carrier_mount_points)
            translate([point[0],point[1],-0.5])
                cylinder(d=carrier_mount_hole_d,h=carrier_t+1);
    }
}

module elongated_hole(len=12,d=3.2,h=10) {
    hull() {
        translate([-len/2+d/2,0,0]) cylinder(d=d,h=h);
        translate([ len/2-d/2,0,0]) cylinder(d=d,h=h);
    }
}

module matrixportal_carrier_frame() {
    // Keep the carrier perimeter and inward M3 mounting points, but open the
    // top/bottom centre under the MatrixPortal edge connectors and buttons.
    difference() {
        union() {
            cube([carrier_w,12,carrier_t]);
            translate([0,carrier_h-12,0]) cube([carrier_w,12,carrier_t]);
            cube([12,carrier_h,carrier_t]);
            translate([carrier_w-12,0,0]) cube([12,carrier_h,carrier_t]);
        }
        translate([(carrier_w-72)/2,-0.5,-0.5])
            cube([72,carrier_h+1,carrier_t+1]);
        for (point=carrier_mount_points)
            translate([point[0],point[1],-0.5])
                cylinder(d=carrier_mount_hole_d,h=carrier_t+1);
    }
}

module matrixportal_post_supports() {
    // Tie each post back to a side rail without recreating a solid centre
    // deck. These ribs are only 2 mm high; with the 6 mm post rise they leave
    // 8 mm clearance below the PCB underside and its populated components.
    for (point=matrixportal_mount_points) {
        if (point[0] < carrier_w/2)
            translate([12,point[1]-matrixportal_support_rib_w/2,0])
                cube([point[0]-12,matrixportal_support_rib_w,matrixportal_support_rib_h]);
        else
            translate([point[0],point[1]-matrixportal_support_rib_w/2,0])
                cube([carrier_w-12-point[0],matrixportal_support_rib_w,matrixportal_support_rib_h]);
    }
}

module matrixportal_mount() {
    difference() {
        union() {
            matrixportal_carrier_frame();
            matrixportal_post_supports();

            // Standoffs centred on the MatrixPortal S3's four M2.5 mounting holes.
            for (point=matrixportal_mount_points)
                    translate([point[0],point[1],carrier_t])
                        cylinder(d=matrixportal_standoff_d,h=matrixportal_standoff_h);
        }

        // Round holes are intentional: the paper fit check exposed the former
        // elongated-slot/90-degree orientation mistake in PR #77.
        for (point=matrixportal_mount_points)
                translate([point[0],point[1],-0.5])
                    cylinder(d=matrixportal_hole_d,h=carrier_t+7);

        // Captive M2.5 nut pockets open on the underside of each post.
        for (point=matrixportal_mount_points)
            translate([point[0],point[1],carrier_t-0.01])
                rotate([0,0,30])
                    cylinder(d=matrixportal_nut_af,h=matrixportal_nut_h,$fn=6);

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
    difference() {
        cube([42,42,6]);
        translate([21,21,-0.5]) linear_extrude(height=7) {
            union() {
                slot2d(slot_len,slot_w);
                rotate(90) slot2d(slot_len,slot_w);
            }
        }
        translate([7,7,-0.5]) cylinder(d=insert_d,h=6.7);
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
        for (point=panel_mount_points)
            cross_slot(point[0],point[1],template_t+1);
    }
}

if (part == "backplane") backplane();
else if (part == "joiner") module_joiner();
else if (part == "rod_plug") rod_end_plug();
else if (part == "matrixportal_mount") matrixportal_mount();
else if (part == "power_mount") power_distribution_mount();
else if (part == "cable_clip") cable_clip();
else if (part == "slot_coupon") mounting_slot_coupon();
else if (part == "mount_pattern_template") mount_pattern_template();
else if (part == "backplane_2d") projection(cut=false) backplane();
else if (part == "matrixportal_2d") projection(cut=false) matrixportal_mount();
else assert(false, str("Unknown part: ",part));
