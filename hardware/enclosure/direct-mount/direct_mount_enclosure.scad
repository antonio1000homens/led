// Modular direct-mount enclosure/backplane for four 256 x 128 mm P4 HUB75 panels.
// Issue #53 - antonio1000homens/led
//
// P4 physical-panel geometry:
// A calibrated 1:1 ruler photograph plus an independent Kiri Engine scan show
// six brass mounting inserts in a symmetric 3 x 2 pattern. The first physical
// template moved the outer boss centres 2 mm inward; the next fit showed that
// correction was 0.5 mm too far inward, so the outer centres move 0.5 mm back
// toward every panel edge:
//   x = 7.9, 128.0, 248.1 mm
//   y = 7.9, 120.1 mm
// These replace the obsolete four-point pattern inferred from a scaled P2.5 panel.
//
// The previously inferred four-point centres (26.704/229.296 x 12/116 mm)
// are retained only as clearance centres for protruding moulded locating pins.
// The physical test print showed at least one of those panel locators entering
// the old slot. A 10 mm round clearance intentionally overlaps the 16 mm frame
// opening by 1 mm, avoiding a fragile/tangent zero-thickness boundary.
// Final acceptance remains a physical fit test against the real P4 panel.
//
// Design intent:
// - Print four identical backplane modules and bolt each LED module directly to one backplane.
// - All printed structure remains BEHIND the LED face; nothing masks the 256 x 128 mm front.
// - Two 1000 x 6 mm round reinforcement bars pass through all four modules.
// - Bars are offset from the measured panel mounting rows and locator clearances.
// - Neighbouring modules align with narrowed tongue/socket keys and are locked with two recessed M3 seam straps, leaving a central cable corridor.
// - Each 4 mm joiner sits in matching rear recesses so its outside face is almost flush with the backplanes.
// - The LED-panel-facing side of every backplane stays flat and unchanged.
// - Rear electronics carriers use blind M3 heat-set-insert pockets.

$fn = 48;
// `part` is intentionally not assigned here: command-line -D and the per-part
// wrapper SCAD files may set it. If undefined, the default render is backplane.

// Nominal front-panel envelope / panel-to-panel pitch.
module_w = 256;
module_h = 128;

// The moulded rear of the physical LED module is slightly smaller than the
// 256 x 128 mm illuminated/front envelope. Keep all measured boss coordinates
// in the nominal panel coordinate system, but inset the printed backplane by
// 0.5 mm on every edge: 255 x 127 mm overall.
backplane_edge_inset = 0.5;
backplane_w = module_w - 2*backplane_edge_inset;
backplane_h = module_h - 2*backplane_edge_inset;

depth = 16;
frame = 16;

// Physical-template-corrected P4 brass insert centres.
// First fit: outer bosses moved 2 mm inward from the scan/photo estimate.
// Second fit: those outer holes were 0.5 mm too far inward, so move them
// 0.5 mm back toward their nearest panel edges. Centre X remains 128 mm.
panel_mount_x = [7.9, 128.0, 248.1];
panel_mount_y = [7.9, 120.1];
panel_mount_hole_d = 4.5; // M3/M4 clearance with small measurement/print tolerance.
// Rear counterbores reduce the screw-through plastic stack from 16 mm to 5 mm.
// Normal screw heads therefore sit recessed below the rear surface/lid plane.
panel_mount_local_t = 5;
panel_mount_head_recess_d = 10;
panel_mount_head_recess_depth = depth - panel_mount_local_t;

// Moulded locating-pin clearance. These four centres correspond to the old
// provisional P2.5-derived slots; they are NOT panel screw locations.
panel_locator_x = [26.704, 229.296];
panel_locator_y = [12.0, 116.0];
panel_locator_clearance_d = 10.0;

slot_len = 10;
slot_w = 4.2;

// Reinforcement bars are now nominal 6 mm diameter.
// Preserve the previous 0.6 mm radial running clearance used for the 8 mm
// bars: 6 mm bar -> 7.2 mm bore, with a larger FDM-friendly lead-in.
reinforcement_bar_d = 6;
rod_d = 7.2;
rod_leadin_d = 8.4;
rod_leadin_len = 1.5;
rod_z = depth/2;
rod_y_bottom = 24;
rod_y_top = module_h-24;
rod_beam_h = 12;

// Keep the centre of each panel seam clear for HUB75/power cabling.
// The previous 11.5 mm alignment tongues occupied too much of the seam;
// PRINT_4 uses narrower 8 mm tongues moved towards the structural rod zones.
joint_len = 6;
joint_w = 8;
joint_h = 7.2;
joint_z = 4;
joint_clear = 0.35;
joint_y1 = 34;
joint_y2 = 86;

// Full-depth cable opening through both vertical seam rails.
// A 16-way HUB75 ribbon is thin but about 20 mm wide, so use a shallow,
// centred 24 mm opening rather than the original 36 mm full-depth cut.
seam_cable_y_min = 52;
seam_cable_y_max = 76;
seam_cable_h = seam_cable_y_max - seam_cable_y_min;
// Only notch the rear 5 mm of the rail. The remaining 11 mm front web makes
// the seam rail substantially stronger while still clearing a flat ribbon.
seam_cable_rear_depth = 5;
seam_cable_front_web_t = depth - seam_cable_rear_depth;

// The seam lock remains a PAIR of recessed straps in one STL/set. The clear
// 24 mm centre gap aligns with the shallow flat-ribbon notch.
joiner_origin_y = 34;
joiner_insert_x = 8;
joiner_insert_y1 = 43;
joiner_insert_y2 = 85;
joiner_w = 32;
joiner_h = 60;
joiner_strap_h = 18;
joiner_t = 4;
joiner_hole_y_inset = 7;
joiner_countersink_d = 6.4;
joiner_countersink_depth = 1.7;
joiner_clear_xy = 0.25;
joiner_clear_z = 0.20;
joiner_recess_depth = joiner_t + joiner_clear_z;
joiner_recess_half_w = joiner_w/2 + joiner_clear_xy;
joiner_recess_strap_h = joiner_strap_h + 2*joiner_clear_xy;
joiner_recess_surface_z = depth - joiner_recess_depth;

// Dedicated rear-lid snap sockets. These deliberately do NOT reuse the 6 mm
// reinforcement-bar bores because those bores are occupied by the bars.
lid_lock_x = [64, 192];
lid_lock_y = [8, 120];
lid_socket_depth = 5.0;
lid_socket_throat_h = 1.8;
lid_socket_throat_d = 5.8;
lid_socket_chamber_d = 6.5;
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
        // Rear frame is centred inside the nominal 256 x 128 front-panel
        // envelope, leaving 0.5 mm clearance on every outside edge.
        translate([backplane_edge_inset,backplane_edge_inset,0])
            cube([backplane_w,frame,depth]);
        translate([
            backplane_edge_inset,
            module_h-backplane_edge_inset-frame,
            0
        ]) cube([backplane_w,frame,depth]);
        translate([
            backplane_edge_inset,
            backplane_edge_inset+frame,
            0
        ]) cube([frame,backplane_h-2*frame,depth]);
        translate([
            module_w-backplane_edge_inset-frame,
            backplane_edge_inset+frame,
            0
        ]) cube([frame,backplane_h-2*frame,depth]);

        translate([
            backplane_edge_inset,
            rod_y_bottom-rod_beam_h/2,
            0
        ]) cube([backplane_w,rod_beam_h,depth]);
        translate([
            backplane_edge_inset,
            rod_y_top-rod_beam_h/2,
            0
        ]) cube([backplane_w,rod_beam_h,depth]);

        if (with_right_tongues)
            for (yy=[joint_y1,joint_y2])
                // Preserve 0.6 mm attachment into this backplane, bridge the
                // 1 mm rear-frame gap at a panel seam, then retain the original
                // 6 mm engagement into the neighbouring socket.
                translate([
                    module_w-backplane_edge_inset-0.6,
                    yy,
                    joint_z
                ]) cube([
                    joint_len + 2*backplane_edge_inset + 0.6,
                    joint_w,
                    joint_h
                ]);
    }
}

module joiner_recesses(include_right_side=true) {
    // Two independent strap pockets leave the centre of the seam completely
    // open for cables. Each neighbouring backplane contributes half the width.
    for (yy=[
        joiner_origin_y,
        joiner_origin_y + joiner_h - joiner_strap_h
    ]) {
        translate([
            -0.01,
            yy-joiner_clear_xy,
            joiner_recess_surface_z
        ])
            cube([
                joiner_recess_half_w+0.01,
                joiner_recess_strap_h,
                joiner_recess_depth+0.01
            ]);

        if (include_right_side)
            translate([
                module_w-joiner_recess_half_w,
                yy-joiner_clear_xy,
                joiner_recess_surface_z
            ])
                cube([
                    joiner_recess_half_w+0.01,
                    joiner_recess_strap_h,
                    joiner_recess_depth+0.01
                ]);
    }
}

module seam_cable_openings(include_right_side=true) {
    // Rear-side cable channels through the vertical seam rails.
    //
    // The 24 mm opening accommodates the ribbon width; only the rear 5 mm
    // is notched because the ribbon itself is thin. The remaining 11 mm front
    // web keeps upper/lower frame sections strongly connected.
    translate([
        -0.1,
        seam_cable_y_min,
        seam_cable_front_web_t
    ])
        cube([
            backplane_edge_inset + frame + 0.2,
            seam_cable_h,
            seam_cable_rear_depth + 0.5
        ]);

    if (include_right_side)
        translate([
            module_w-backplane_edge_inset-frame-0.1,
            seam_cable_y_min,
            seam_cable_front_web_t
        ])
            cube([
                backplane_edge_inset + frame + 0.2,
                seam_cable_h,
                seam_cable_rear_depth + 0.5
            ]);
}

module lid_lock_socket(x,y) {
    // Wider blind chamber plus a smaller rear throat gives the matching split
    // PETG peg a positive detent rather than a simple friction fit.
    translate([x,y,depth-lid_socket_depth])
        cylinder(
            d=lid_socket_chamber_d,
            h=lid_socket_depth-lid_socket_throat_h+0.1
        );
    translate([x,y,depth-lid_socket_throat_h])
        cylinder(
            d=lid_socket_throat_d,
            h=lid_socket_throat_h+0.2
        );
}

module backplane(right_end=false) {
    difference() {
        backplane_body(!right_end);

        for (yy=[rod_y_bottom,rod_y_top]) rod_bore(yy);

        // Six real P4 mounting holes: three along each long edge.
        // Each hole has a 10 mm rear counterbore, leaving only 5 mm of local
        // plastic between the screw head and LED-panel boss. This avoids the
        // need for unusually long screws and keeps heads below the lid plane.
        for (x=panel_mount_x)
            for (y=panel_mount_y) {
                translate([x,y,-0.5])
                    cylinder(d=panel_mount_hole_d,h=depth+1);
                translate([x,y,panel_mount_local_t])
                    cylinder(
                        d=panel_mount_head_recess_d,
                        h=panel_mount_head_recess_depth+0.5
                    );
            }

        // Clearance for the panel's protruding moulded locating pins.
        // Kept separate from the brass mounting holes so the two functions
        // cannot be confused during assembly.
        for (x=panel_locator_x)
            for (y=panel_locator_y)
                translate([x,y,-0.5]) cylinder(d=panel_locator_clearance_d,h=depth+1);

        for (yy=[joint_y1,joint_y2])
            // Socket begins just outside the inset rear-frame edge and keeps
            // the original 6 mm tongue engagement inside the neighbour.
            translate([
                backplane_edge_inset-0.1,
                yy-joint_clear/2,
                joint_z-joint_clear/2
            ])
                cube([
                    joint_len+0.2,
                    joint_w+joint_clear,
                    joint_h+joint_clear
                ]);

        seam_cable_openings(!right_end);
        joiner_recesses(!right_end);

        // Four dedicated snap sockets for the removable rear lid.
        for (xx=lid_lock_x)
            for (yy=lid_lock_y)
                lid_lock_socket(xx,yy);

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
    // One exported STL contains two separate recessed straps. Install both
    // straps at each seam so the 36 mm centre corridor remains unobstructed.
    difference() {
        union() {
            cube([joiner_w,joiner_strap_h,joiner_t]);
            translate([0,joiner_h-joiner_strap_h,0])
                cube([joiner_w,joiner_strap_h,joiner_t]);
        }

        for (xx=[joiner_insert_x,joiner_w-joiner_insert_x])
            for (yy=[joiner_hole_y_inset,joiner_h-joiner_hole_y_inset]) {
                translate([xx,yy,-0.5]) cylinder(d=3.5,h=joiner_t+1);
                // 90-degree countersink for a flush M3 flat-head screw.
                translate([xx,yy,joiner_t-joiner_countersink_depth])
                    cylinder(
                        d1=3.5,
                        d2=joiner_countersink_d,
                        h=joiner_countersink_depth+0.1
                    );
            }
    }
}

module rod_end_plug() {
    cap_t = 2.5;
    stem_len = 11.4;
    difference() {
        union() {
            cylinder(h=cap_t,d=11);
            translate([0,0,cap_t]) cylinder(h=stem_len,d1=7.25,d2=7.05);
            // Compressible detent gives the plug positive friction retention
            // in the 7.2 mm bore without adhesive.
            translate([0,0,cap_t+stem_len-2.0]) cylinder(h=0.9,d=7.45);
        }
        // Split the outer half of the stem so the detent can compress on entry.
        translate([-0.55,-4,cap_t+4.0]) cube([1.1,8,stem_len]);
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

// Separate rear desk stand using the lower centre panel boss.
// Install with the mounting plate against the rear face of the backplane and
// share the lower-centre panel screw. The small underside lip keys against the
// backplane lower edge to resist rotation around the single screw.
// For a complete four-panel display, print two and fit them to the lower-centre
// bosses of Panels 1 and 4.
stand_w = 32;
stand_plate_h = 30;
// Reduced from 5 mm after physical fit so the shared boss screw only needs
// about 3 mm of extra length. Strength is retained by the side ribs.
stand_plate_t = 3;
stand_rear_foot_len = 60;
// A short toe projects under the front of the display to stop the assembly
// pitching forward. It stays below the LED face rather than in front of it.
stand_front_toe_len = 15;
stand_foot_t = 6;
stand_rib_t = 5;
stand_edge_hook_depth = 5;
stand_edge_hook_h = 3;
stand_mount_y = panel_mount_y[0];

module centre_boss_stand() {
    difference() {
        union() {
            // Rear mounting plate.
            cube([stand_w,stand_plate_h,stand_plate_t]);

            // Desk foot spans both sides of the panel plane: 15 mm forward
            // underneath the display and 60 mm rearward. The forward toe gives
            // the stand a front reaction point instead of letting the display
            // pivot forward around the lower boss.
            translate([
                0,
                backplane_edge_inset-stand_foot_t,
                -stand_front_toe_len
            ])
                cube([
                    stand_w,
                    stand_foot_t,
                    stand_front_toe_len + stand_rear_foot_len
                ]);

            // Two triangular side ribs tie the plate into the rearward foot.
            for (xx=[0,stand_w-stand_rib_t])
                hull() {
                    translate([xx,0,0])
                        cube([stand_rib_t,stand_plate_h,stand_plate_t]);
                    translate([
                        xx,
                        backplane_edge_inset-stand_foot_t,
                        stand_rear_foot_len-10
                    ])
                        cube([stand_rib_t,stand_foot_t,10]);
                }

            // Anti-rotation lip: wraps 5 mm under the rear of the backplane edge
            // without reaching the LED-panel-facing plane.
            translate([
                0,
                backplane_edge_inset-stand_edge_hook_h,
                -stand_edge_hook_depth
            ])
                cube([
                    stand_w,
                    stand_edge_hook_h,
                    stand_edge_hook_depth + stand_plate_t
                ]);
        }

        // Shared lower-centre boss screw. The 3 mm plate deliberately keeps
        // the extra screw-length requirement small; use the same screw family
        // as the panel mount and verify safe thread engagement physically.
        translate([stand_w/2,stand_mount_y,-0.5])
            cylinder(d=panel_mount_hole_d,h=stand_plate_t+1);
    }
}

// Print the stand on its side so the triangular ribs and foot build upward
// without large horizontal bridges/supports. Translation keeps the rotated STL
// on z >= 0 for predictable slicer placement.
module centre_boss_stand_print() {
    translate([0,0,stand_w])
        rotate([0,90,0])
            centre_boss_stand();
}

// Modular snap-on rear lid. This is intentionally an open-sided protective
// cover rather than a sealed box: the open perimeter preserves cooling,
// MatrixPortal side access and the new seam cable corridor.
//
// PETG is the preferred material for the split snap pegs because it tolerates
// repeated flexing better than PLA. PLA is acceptable for dimensional test
// prints but is more likely to fatigue at the snap slots.
lid_origin_x = backplane_edge_inset + 1.5;
lid_origin_y = backplane_edge_inset + 1.5;
lid_w = backplane_w - 3;
lid_h = backplane_h - 3;
lid_plate_t = 2.4;
lid_clearance_h = 18;
lid_post_d = 8;
lid_snap_shaft_d = 5.2;
lid_snap_detent_d = 6.1;
lid_snap_len = lid_socket_depth;
lid_snap_slot_w = 1.0;

module lid_snap_post_print(x,y) {
    post_h = lid_clearance_h;
    post_plate_overlap = 0.2;
    snap_post_overlap = 0.4;
    // Overlap the post into the lid plate so the exported STL is one robust
    // connected solid rather than relying on coplanar face contact.
    translate([x,y,lid_plate_t-post_plate_overlap]) {
        cylinder(d=lid_post_d,h=post_h+post_plate_overlap);

        // Preserve the original snap height despite the plate overlap.
        translate([0,0,post_h+post_plate_overlap])
            difference() {
                union() {
                    // Extend the shaft 0.4 mm into the support post. The split
                    // starts at -0.1 mm, leaving a short unsplit root that
                    // joins both flexing fingers to the post as one solid.
                    translate([0,0,-snap_post_overlap])
                        cylinder(
                            d=lid_snap_shaft_d,
                            h=lid_snap_len+snap_post_overlap
                        );
                    translate([0,0,0.8])
                        cylinder(
                            d1=lid_snap_shaft_d,
                            d2=lid_snap_detent_d,
                            h=1.0
                        );
                    translate([0,0,1.8])
                        cylinder(
                            d1=lid_snap_detent_d,
                            d2=lid_snap_shaft_d,
                            h=1.0
                        );
                }

                // Split the snap section so the detent compresses through the
                // 5.8 mm socket throat and expands in the 6.5 mm chamber.
                translate([
                    -lid_snap_slot_w/2,
                    -lid_snap_detent_d,
                    -0.1
                ])
                    cube([
                        lid_snap_slot_w,
                        2*lid_snap_detent_d,
                        lid_snap_len+0.2
                    ]);
            }
    }
}

module rear_lid_print() {
    // Rear plate prints flat on the bed; posts and snap pegs grow upward.
    // Installed, the part is simply flipped so the pegs face the backplane.
    difference() {
        cube([lid_w,lid_h,lid_plate_t]);

        // Ventilation slots. Keep broad solid margins around the snap posts.
        for (xx=[42,84,126,168,210])
            translate([xx-12,lid_h/2-3,-0.1])
                cube([24,6,lid_plate_t+0.2]);
    }

    for (xx=lid_lock_x)
        for (yy=lid_lock_y)
            lid_snap_post_print(
                xx-lid_origin_x,
                yy-lid_origin_y
            );
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
else if (part == "centre_boss_stand") centre_boss_stand_print();
else if (part == "rear_lid") rear_lid_print();
else if (part != "__library__") assert(false, str("Unknown part: ",part));