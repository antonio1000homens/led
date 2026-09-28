// Canonical modular hinged direct-mount enclosure for four 256 x 128 mm P4 HUB75 panels.
//
// Issue #133 commits the project to the hinged architecture. This is the single
// parametric source of truth for the PR #119-style MOVING panel/template leaf,
// STATIONARY universal equipment base, top-down removable backplane and
// detachable side retainers.
//
// The physically corrected P4 panel coordinates remain the source of truth.
// Component-specific PSU/MatrixPortal geometry belongs on detachable adapters.

module_w = 256;
module_h = 128;
backplane_edge_inset = 0.5;
backplane_w = module_w - 2*backplane_edge_inset;
backplane_h = module_h - 2*backplane_edge_inset;

panel_mount_x = [7.9, 128.0, 248.1];
panel_mount_y = [7.9, 120.1];
panel_mount_hole_d = 4.5;

panel_locator_x = [26.704, 229.296];
panel_locator_y = [12.0, 116.0];
panel_locator_clearance_d = 10.0;

$fn = 48;

// ---------- Proven PR #119 hinge geometry ----------
//
// The equipment enclosure/base is STATIONARY. The LED panel + mounting
// template is the MOVING leaf and opens forward/down. These roles, dimensions
// and support strategy intentionally follow the validated PR #119 hinge.

hinge_rail_d = 6;
hinge_bore_d = 7.2;
hinge_outer_d = 14;
hinge_radius = hinge_outer_d/2;
hinge_axial_clearance = 1.0;

ground_clearance = 20;
hinge_axis_y = ground_clearance; // hinge centreline matches the moving panel's lower edge

moving_plate_t = 2;
fixed_template_t = moving_plate_t; // compatibility alias used by modular equipment geometry
hinge_plate_clearance = 7;
hinge_axis_z = moving_plate_t + hinge_radius + hinge_plate_clearance; // 16 mm

// Full 0-90 degree service arc is part of the proven hinge contract.
service_open_angle = 90;
mechanical_clearance_angle = 90;

// Moving LED/template knuckles from the validated PR #119 geometry.
panel_knuckles = [
    [34,26],
    [92,26],
    [166,28]
];

// Stationary equipment-side knuckles alternate with the moving panel knuckles.
stationary_knuckles = [
    [62,28],
    [136,28],
    [196,24]
];

module rail_hinge_barrel(x0, len, axis_z=hinge_axis_z) {
    translate([x0,hinge_axis_y,axis_z])
        rotate([0,90,0])
            difference() {
                cylinder(d=hinge_outer_d,h=len);
                translate([0,0,-0.2])
                    cylinder(d=hinge_bore_d,h=len+0.4);
            }
}

// ---------- Moving half: LED panel mounting template ----------

panel_band_h = 20;
panel_side_w = 8;

module panel_mount_pattern_template() {
    difference() {
        union() {
            cube([module_w,panel_band_h,moving_plate_t]);
            translate([0,module_h-panel_band_h,0])
                cube([module_w,panel_band_h,moving_plate_t]);
            cube([panel_side_w,module_h,moving_plate_t]);
            translate([module_w-panel_side_w,0,0])
                cube([panel_side_w,module_h,moving_plate_t]);
        }

        for (x=panel_mount_x)
            for (y=panel_mount_y)
                translate([x,y,-0.5])
                    cylinder(d=panel_mount_hole_d,h=moving_plate_t+1);

        for (x=panel_locator_x)
            for (y=panel_locator_y)
                translate([x,y,-0.5])
                    cylinder(d=panel_locator_clearance_d,h=moving_plate_t+1);
    }
}

module moving_panel_root(x0,len) {
    // PR #119: local reinforcement only. The moving leaf deliberately has no
    // full-width lower hinge lip that could collide with the stationary base.
    hull() {
        translate([x0,ground_clearance,0])
            cube([len,7,moving_plate_t]);

        translate([x0,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_outer_d,h=len);
    }
}

module moving_panel_template_installed() {
    difference() {
        union() {
            translate([0,ground_clearance,0])
                panel_mount_pattern_template();

            for (segment=panel_knuckles)
                moving_panel_root(segment[0],segment[1]);
        }

        // One continuous rod bore guarantees all moving knuckles are coaxial.
        translate([-0.2,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_bore_d,h=module_w+0.4);
    }
}

module moving_panel_template_print() {
    // Keep the verified panel/template face flat on the print bed.
    translate([0,-ground_clearance,0])
        moving_panel_template_installed();
}

// Compatibility name used by older previews/tests. This is the installed
// moving panel-side leaf, not a fixed equipment-side template.
module hinge_mount_pattern_template() {
    moving_panel_template_installed();
}

// ---------- Shared moving-envelope coordinates ----------

service_x = backplane_edge_inset;
service_base_y = backplane_edge_inset;
service_top_y = backplane_edge_inset + backplane_h;
service_w = backplane_w;

service_close_clearance = 0.6;
service_front_z = fixed_template_t + service_close_clearance;

// Revised upper enclosure profile for the top-middle rotating panel clamp.
// Keep the 40 mm-deep equipment section taller, use a shorter/steeper ramp,
// then finish with a shallow wall parallel to the LED panel. The stationary
// enclosure stops 10 mm below the panel top, leaving the top-middle screw and
// rotating clamp mechanism exposed when the panel is closed.
enclosure_panel_clearance = 0.8;
enclosure_front_z = fixed_template_t + enclosure_panel_clearance; // 2.8 mm
enclosure_bottom_depth = 40;
panel_clamp_top_clearance = 10;
panel_clamp_pivot_x = panel_mount_x[1];
panel_clamp_pivot_y = ground_clearance + panel_mount_y[1];

// Serviceable rotating tab carried by the MOVING panel/template only. It uses
// the top-middle panel screw as its pivot and never relies on the stationary
// enclosure for retention. The final spacer/washer stack is chosen to match
// the physical LED PCB thickness; the printed part provides the rotating arm.
panel_clamp_tab_t = 3;
panel_clamp_pivot_d = 12;
panel_clamp_tip_d = 10;
panel_clamp_tip_offset = 8.5;
panel_clamp_hub_h = 2;
panel_clamp_hole_d = panel_mount_hole_d + 0.2;

backplane_ramp_start_y = 75;
backplane_ramp_end_y = 120;
enclosure_top_y = ground_clearance + module_h - panel_clamp_top_clearance;
upper_vertical_h = enclosure_top_y - backplane_ramp_end_y;

equipment_backplane_t = 3;
equipment_backplane_lower_rear_z = enclosure_front_z + enclosure_bottom_depth;
equipment_backplane_front_z = equipment_backplane_lower_rear_z - equipment_backplane_t;
equipment_backplane_rear_z = equipment_backplane_lower_rear_z;
// At the top, the backplane itself now runs close and parallel to the moving
// template instead of sitting ~8 mm behind it. Its front face is only the
// intended 0.8 mm service clearance behind the template rear face.
equipment_backplane_top_front_z = enclosure_front_z;
equipment_backplane_top_rear_z =
    equipment_backplane_top_front_z + equipment_backplane_t;

backplane_guide_clearance = 0.4;
backplane_guide_t = 1.2;
backplane_seat_depth = 2.0;
base_seat_y = 4.5;
equipment_backplane_y0 = base_seat_y - backplane_seat_depth;

// Two genuine U-channel side rails rise from the base. For the first 50 mm,
// the removable backplane edges slide DOWN inside these channels rather than
// merely passing between solid guide towers. The 5 mm rail depth provides
// positive side capture while leaving the channel open toward the enclosure
// centre for top-down installation.
side_guide_h = 50;
side_guide_w = 5;
side_guide_clearance = 0.4;
side_guide_wall_t = backplane_guide_t;
side_guide_y0 = service_base_y;
side_guide_y1 = side_guide_y0 + side_guide_h;

// Keep the hidden seam junctions on the cavity-facing side. A taller front
// support pad keeps both pin/socket centres well away from its lower/upper
// edges without closing the vertical backplane channel.
junction_pad_depth = 7;
junction_pad_front_z = equipment_backplane_front_z - junction_pad_depth;
junction_pad_h = 16;

// The bottom seat and the vertical side channels share the same slot envelope
// around the 3 mm backplane. The rails add one wall thickness in front/behind
// that slot while the outer spine closes the U at the module edge.
backplane_slot_front_z = equipment_backplane_front_z - backplane_guide_clearance;
backplane_slot_back_z = equipment_backplane_rear_z + backplane_guide_clearance;
base_rear_z = backplane_slot_back_z + backplane_guide_t;
base_floor_front_z = service_front_z;
base_floor_rear_z = base_rear_z;
base_panel_clearance_y = ground_clearance-hinge_axis_z;
base_panel_clearance_z = hinge_axis_z+moving_plate_t+0.5;

side_guide_slot_front_z = backplane_slot_front_z;
side_guide_slot_back_z = backplane_slot_back_z;
side_guide_front_z = side_guide_slot_front_z - side_guide_wall_t;
side_guide_rear_z = side_guide_slot_back_z + side_guide_wall_t;

// The lower backplane extends into each U-channel and stops short of the outer
// spine by the running clearance. Above the 50 mm rails it returns to full width.
lower_backplane_edge_inset = side_guide_wall_t + side_guide_clearance;

// Small overlap band used to join the steeper ramp into the shallow vertical
// upper wall without creating a disconnected or unsupported top section.
backplane_top_band = 1.5;

// Generic M3 adapter pattern. Component-specific geometry belongs on adapters.
adapter_boss_d = 8;
adapter_hole_d = 3.4;
adapter_boss_h = 5;
adapter_x = [32,80,128,176,224];
// Keep accessory mounting on the vertical lower section so adapters remain
// parallel to the LED plane and do not sit on the tapered ventilation roof.
adapter_y = [18,36,54];

// Fine upper-only ventilation stays within the steeper ramp and below the
// upper alignment/clamp region.
vent_side_margin = 12;
vent_slot_w = 3;
vent_pitch = 8;
upper_vent_y = backplane_ramp_start_y + 10;
upper_vent_h = 28;

// Lower cable/ribbon passages remain below the taper.
cable_slot_len = 20;
cable_slot_w = 6;
cable_slot_x = [64,176];
cable_slot_y = 28;

// Self-mating side alignment. Each edge carries one pin and one socket.
// Right(A pin/B socket) mates Left(A socket/B pin) on another identical module.
connector_pin_d = 4;
connector_socket_d = 4.7;
connector_pin_len = 3;
connector_socket_depth = 3;

// Self-mating junctions are carried by the 50 mm U-channel side rails. They sit
// on the cavity-facing side and remain hidden from the external rear face.
// Both A/B features are inset from the support-pad edges by at least 2 mm even
// at the larger 4.7 mm socket diameter, avoiding the fragile edge condition.
connector_edge_margin = 2.0;
base_connector_y_a = 5.0;
base_connector_y_b = 11.0;
base_connector_z_a = junction_pad_front_z + 2.6;
base_connector_z_b = base_connector_z_a;
side_socket_depth = 2.2;

side_t = 3;
side_panel_clearance = 0.4;
side_connector_overlap = 0.4;
side_connector_bridge = side_panel_clearance + backplane_edge_inset;
side_connector_pin_len =
    connector_pin_len + side_connector_bridge + side_connector_overlap;

// Backplane/side alignment connector. Keep all SOLID connector/pad geometry
// completely below the 75 mm ramp start so nothing protrudes toward the moving
// panel. The vertical release SLOT is only a void and continues upward through
// the ramp to allow 15 mm of top-down service motion at the end plates.
top_connector_y = 71;
top_connector_z = equipment_backplane_rear_z - 1.3;
top_connector_release_travel = 15;
top_connector_slot_lower_span = 20;
top_connector_slot_bottom_y = top_connector_y - top_connector_slot_lower_span;
top_connector_slot_top_y =
    backplane_ramp_start_y + top_connector_release_travel + 0.2;
top_connector_pad_y0 = top_connector_slot_bottom_y;
top_connector_pad_y1 = backplane_ramp_start_y;
top_connector_pad_w = 8;
top_connector_pad_depth = 11;
top_connector_pad_lower_depth = equipment_backplane_t;
top_connector_overlap = 0.4;
top_connector_tab_len = connector_pin_len + top_connector_overlap;
top_connector_tab_root_len = 0.8;
top_connector_tab_h = 8;
top_connector_tab_t = 3.6;
top_connector_tab_slice_h = 1.0;
top_connector_pad_ramp_end_y = top_connector_y - top_connector_tab_h/2;
top_side_pin_len = connector_pin_len + side_connector_overlap;
top_connector_support_margin = 0.5;
top_connector_min_engagement = 1.5;
top_module_seam_gap = module_w - service_w;
top_side_seam_gap = side_panel_clearance + backplane_edge_inset;

// ---------- X-axis connector helpers ----------

module pin_pos_x(x0,y0,z0,len=connector_pin_len,d=connector_pin_d) {
    translate([x0,y0,z0])
        rotate([0,90,0])
            cylinder(d=d,h=len);
}

module pin_neg_x(x0,y0,z0,len=connector_pin_len,d=connector_pin_d) {
    translate([x0,y0,z0])
        rotate([0,-90,0])
            cylinder(d=d,h=len);
}

module socket_pos_x(x0,y0,z0,depth=connector_socket_depth,d=connector_socket_d) {
    translate([x0-0.1,y0,z0])
        rotate([0,90,0])
            cylinder(d=d,h=depth+0.2);
}

module socket_neg_x(x0,y0,z0,depth=connector_socket_depth,d=connector_socket_d) {
    translate([x0+0.1,y0,z0])
        rotate([0,-90,0])
            cylinder(d=d,h=depth+0.2);
}

// Vertical X-axis capture slot. Unlike a closed round socket, this permits the
// mating pin to move in Y during top-down backplane installation/removal.
module vertical_slot_pos_x(
    x0,
    y_bottom,
    y_top,
    z0,
    depth=connector_socket_depth,
    w=connector_socket_d
) {
    translate([x0-0.1,y_bottom,z0-w/2])
        cube([
            depth+0.2,
            y_top-y_bottom+0.2,
            w
        ]);
}

// ---------- Stationary equipment-base hinge geometry ----------

hinge_guard_t = 2;
hinge_guard_clearance = 0.8;
hinge_guard_front_z = hinge_axis_z + hinge_radius + hinge_guard_clearance;
hinge_guard_start_y = base_seat_y - 0.5; // overlaps the stationary floor by 0.5 mm
hinge_guard_top_y = hinge_axis_y;
hinge_guard_bridge_overlap = 0.5;
hinge_guard_bridge_h = 2.0;
hinge_support_root_t = 3.0;
hinge_support_root_y = hinge_axis_y-hinge_radius-1.0;
hinge_support_root_z = hinge_axis_z-1.0;
hinge_support_landing_y = hinge_axis_y-hinge_radius-2.0;
hinge_support_landing_overlap = 0.6;
hinge_support_landing_z = hinge_guard_front_z+hinge_guard_t-hinge_support_landing_overlap;
hinge_support_landing_h = 2.0;

// Continue the hinge load path down into the structural base floor. The anchor
// is fully embedded in the remaining floor behind the 90-degree sweep relief.
hinge_support_base_y = service_base_y;
hinge_support_base_h = base_panel_clearance_y-service_base_y;
hinge_support_base_z = hinge_guard_front_z;
hinge_support_base_t = hinge_guard_t;

module stationary_hinge_barrels() {
    for (segment=stationary_knuckles)
        rail_hinge_barrel(segment[0],segment[1]);
}

module stationary_hinge_support_web(x0,len) {
    // Reinforce the stationary barrel locally, land it on the horizontal hinge
    // shelf, then continue the load path down into the structural base floor.
    // This stays local to each stationary knuckle so the equipment cavity is
    // not closed by a full-width wall.
    union() {
        hull() {
            translate([
                x0,
                hinge_support_root_y,
                hinge_support_root_z
            ])
                cube([len,3,hinge_support_root_t]);

            translate([
                x0,
                hinge_support_landing_y,
                hinge_support_landing_z
            ])
                cube([len,3,hinge_support_landing_h]);
        }

        hull() {
            translate([
                x0,
                hinge_support_landing_y,
                hinge_support_landing_z
            ])
                cube([len,3,hinge_support_landing_h]);

            translate([
                x0,
                hinge_support_base_y,
                hinge_support_base_z
            ])
                cube([
                    len,
                    hinge_support_base_h,
                    hinge_support_base_t
                ]);
        }
    }
}

module stationary_hinge_supports() {
    for (segment=stationary_knuckles)
        stationary_hinge_support_web(segment[0],segment[1]);
}

module lower_hinge_guard() {
    // PR #119 full-width stationary guard: closes the low opening behind the
    // panel while remaining completely behind the 14 mm barrel envelope.
    union() {
        translate([
            service_x,
            hinge_guard_start_y,
            hinge_guard_front_z
        ])
            cube([
                service_w,
                hinge_guard_top_y-hinge_guard_start_y,
                hinge_guard_t
            ]);

        // Bridge only at STATIONARY knuckle spans; moving spans stay clear.
        for (segment=stationary_knuckles)
            translate([
                segment[0],
                hinge_axis_y-hinge_guard_bridge_h,
                hinge_axis_z+hinge_radius-hinge_guard_bridge_overlap
            ])
                cube([
                    segment[1],
                    hinge_guard_bridge_h,
                    hinge_guard_clearance
                        + hinge_guard_t
                        + hinge_guard_bridge_overlap
                ]);
    }
}

module side_guide_channel(side="left") {
    x0 = side == "left"
        ? service_x
        : service_x + service_w - side_guide_w;
    spine_x = side == "left"
        ? x0
        : x0 + side_guide_w - side_guide_wall_t;

    union() {
        // Front and rear lips capture the 3 mm backplane in Z while leaving
        // the channel open toward the enclosure centre in X.
        translate([x0,side_guide_y0,side_guide_front_z])
            cube([side_guide_w,side_guide_h,side_guide_wall_t]);
        translate([x0,side_guide_y0,side_guide_slot_back_z])
            cube([side_guide_w,side_guide_h,side_guide_wall_t]);

        // Outer spine joins the lips into a true U-shaped rail.
        translate([spine_x,side_guide_y0,side_guide_front_z])
            cube([
                side_guide_wall_t,
                side_guide_h,
                side_guide_rear_z-side_guide_front_z
            ]);

        // Bed-connected internal support for the lower hidden junction only.
        // It stops before the slot, so the backplane can still slide to its seat.
        translate([x0,side_guide_y0,junction_pad_front_z])
            cube([
                side_guide_w,
                junction_pad_h,
                side_guide_front_z-junction_pad_front_z+0.2
            ]);
    }
}

module base_structural_body() {
    difference() {
        union() {
            // Low unobstructed structural floor.
            translate([service_x,service_base_y,service_front_z])
                cube([
                    service_w,
                    base_seat_y-service_base_y,
                    base_rear_z-service_front_z
                ]);

            stationary_hinge_supports();
            stationary_hinge_barrels();
            lower_hinge_guard();

            // True U-channel side rails. The backplane engages inside both
            // channels for the first 50 mm of installed height.
            side_guide_channel("left");
            side_guide_channel("right");

        }

        // Recess the top-down backplane rail INTO the rear edge of the base.
        // Only a 2 mm-deep locating groove is removed; there is no internal
        // ramp, lip or captive wall consuming module space.
        translate([
            service_x+lower_backplane_edge_inset-0.1,
            equipment_backplane_y0,
            backplane_slot_front_z
        ])
            cube([
                service_w-2*lower_backplane_edge_inset+0.2,
                base_seat_y-equipment_backplane_y0+0.2,
                backplane_slot_back_z-backplane_slot_front_z
            ]);

        // The centred bottom-edge hinge brings the open panel's lower band to
        // base_panel_clearance_y. Relieve the front floor lip below the hinge
        // depth while keeping the backplane seat and guide towers intact.
        translate([
            service_x-0.1,
            base_panel_clearance_y,
            base_floor_front_z-0.1
        ])
            cube([
                service_w+0.2,
                base_seat_y-base_panel_clearance_y+0.2,
                base_panel_clearance_z-base_floor_front_z+0.2
            ]);
    }
}

module base_connector_pins() {
    right_x = service_x + service_w;
    left_x = service_x;

    // Hidden inside the enclosure: right A pin / left B pin.
    pin_pos_x(right_x,base_connector_y_a,base_connector_z_a);
    pin_neg_x(left_x,base_connector_y_b,base_connector_z_b);
}

module base_connector_sockets() {
    right_x = service_x + service_w;
    left_x = service_x;

    socket_neg_x(right_x,base_connector_y_b,base_connector_z_b);
    socket_pos_x(left_x,base_connector_y_a,base_connector_z_a);
}

module hinged_equipment_base() {
    difference() {
        union() {
            base_structural_body();
            base_connector_pins();
        }

        base_connector_sockets();
    }
}

// The equipment base is stationary in service and prints upright on its floor.
module hinged_equipment_base_print() {
    translate([0,base_rear_z,-service_base_y])
        rotate([90,0,0])
            hinged_equipment_base();
}

// ---------- Universal top-down backplane ----------

module rounded_slot_2d(len,w) {
    hull() {
        translate([-(len-w)/2,0]) circle(d=w);
        translate([(len-w)/2,0]) circle(d=w);
    }
}

// Accessory bosses live on the INSIDE face of the backplane. Their M3 holes
// are blind, leaving a continuous solid external rear skin.
adapter_outer_skin = 1.2;
adapter_boss_overlap = 0.3;
adapter_hole_depth =
    adapter_boss_h + equipment_backplane_t - adapter_outer_skin;

module internal_adapter_bosses() {
    for (xx=adapter_x)
        for (yy=adapter_y)
            translate([
                xx,
                yy,
                equipment_backplane_front_z-adapter_boss_h
                    + adapter_boss_overlap
            ])
                cylinder(
                    d=adapter_boss_d,
                    h=adapter_boss_h
                );
}

module internal_adapter_hole_cutters() {
    for (xx=adapter_x)
        for (yy=adapter_y)
            translate([
                xx,
                yy,
                equipment_backplane_front_z-adapter_boss_h-0.2
            ])
                cylinder(
                    d=adapter_hole_d,
                    h=adapter_hole_depth+0.2
                );
}

function tapered_backplane_rear_z_at_y(y) =
    y <= backplane_ramp_start_y
        ? equipment_backplane_lower_rear_z
        : y >= backplane_ramp_end_y
            ? equipment_backplane_top_rear_z
            : equipment_backplane_lower_rear_z +
              (equipment_backplane_top_rear_z-equipment_backplane_lower_rear_z) *
              ((y-backplane_ramp_start_y)/
               (backplane_ramp_end_y-backplane_ramp_start_y));

module top_backplane_connector_pad(side="left") {
    x0 = side == "left"
        ? service_x
        : service_x + service_w - top_connector_pad_w;
    rear0 = tapered_backplane_rear_z_at_y(top_connector_pad_y0);
    rear_mid = tapered_backplane_rear_z_at_y(top_connector_pad_ramp_end_y);
    rear1 = tapered_backplane_rear_z_at_y(top_connector_pad_y1);
    slice_h = 1;

    // Start at the native 3 mm wall thickness, then grow inward at roughly
    // 45 degrees before the connector band. This avoids introducing a high,
    // horizontal cantilever in the upright backplane print orientation.
    union() {
        hull() {
            translate([
                x0,
                top_connector_pad_y0,
                rear0-top_connector_pad_lower_depth
            ])
                cube([
                    top_connector_pad_w,
                    slice_h,
                    top_connector_pad_lower_depth
                ]);

            translate([
                x0,
                top_connector_pad_ramp_end_y-slice_h,
                rear_mid-top_connector_pad_depth
            ])
                cube([
                    top_connector_pad_w,
                    slice_h,
                    top_connector_pad_depth
                ]);
        }

        hull() {
            translate([
                x0,
                top_connector_pad_ramp_end_y-slice_h,
                rear_mid-top_connector_pad_depth
            ])
                cube([
                    top_connector_pad_w,
                    slice_h,
                    top_connector_pad_depth
                ]);

            translate([
                x0,
                top_connector_pad_y1-slice_h,
                rear1-top_connector_pad_depth
            ])
                cube([
                    top_connector_pad_w,
                    slice_h,
                    top_connector_pad_depth
                ]);
        }
    }
}

module top_backplane_connector_pin() {
    right_x = service_x + service_w;
    y0 = top_connector_y - top_connector_tab_h/2;
    y1 = top_connector_y + top_connector_tab_h/2;

    // A symmetric ramped tab replaces the round horizontal backplane pin.
    // Installed +Y becomes print +Z, so the tab grows outward gradually,
    // reaches full engagement around top_connector_y, then tapers back.
    union() {
        hull() {
            translate([
                right_x-top_connector_overlap,
                y0,
                top_connector_z-top_connector_tab_t/2
            ])
                cube([
                    top_connector_tab_root_len,
                    top_connector_tab_slice_h,
                    top_connector_tab_t
                ]);

            translate([
                right_x-top_connector_overlap,
                top_connector_y-top_connector_tab_slice_h/2,
                top_connector_z-top_connector_tab_t/2
            ])
                cube([
                    top_connector_tab_len,
                    top_connector_tab_slice_h,
                    top_connector_tab_t
                ]);
        }

        hull() {
            translate([
                right_x-top_connector_overlap,
                top_connector_y-top_connector_tab_slice_h/2,
                top_connector_z-top_connector_tab_t/2
            ])
                cube([
                    top_connector_tab_len,
                    top_connector_tab_slice_h,
                    top_connector_tab_t
                ]);

            translate([
                right_x-top_connector_overlap,
                y1-top_connector_tab_slice_h,
                top_connector_z-top_connector_tab_t/2
            ])
                cube([
                    top_connector_tab_root_len,
                    top_connector_tab_slice_h,
                    top_connector_tab_t
                ]);
        }
    }
}

module top_backplane_connector_slot() {
    vertical_slot_pos_x(
        service_x,
        top_connector_slot_bottom_y,
        top_connector_slot_top_y,
        top_connector_z,
        connector_socket_depth
    );
}

// ---------- Top-middle rotating panel clamp ----------

module panel_rotating_clamp_print() {
    // Flat printable arm with a locally thickened pivot hub. No floating
    // geometry and no dependency on the stationary enclosure.
    difference() {
        union() {
            hull() {
                cylinder(d=panel_clamp_pivot_d,h=panel_clamp_tab_t);
                translate([0,-panel_clamp_tip_offset,0])
                    cylinder(d=panel_clamp_tip_d,h=panel_clamp_tab_t);
            }
            cylinder(
                d=panel_clamp_pivot_d,
                h=panel_clamp_tab_t+panel_clamp_hub_h
            );
        }

        translate([0,0,-0.5])
            cylinder(
                d=panel_clamp_hole_d,
                h=panel_clamp_tab_t+panel_clamp_hub_h+1
            );
    }
}

module panel_rotating_clamp_installed(angle=180) {
    // Preview on the LED/front side of the moving template. 180 degrees points
    // the short arm upward toward the panel top; rotate away to release.
    translate([
        panel_clamp_pivot_x,
        panel_clamp_pivot_y,
        -panel_clamp_tab_t-panel_clamp_hub_h
    ])
        rotate([0,0,angle])
            panel_rotating_clamp_print();
}

module backplane_shell_solid() {
    union() {
        // Stepped vertical lower section. For the first 50 mm the plate is
        // only inset enough to clear the OUTER spines, so each edge projects
        // into and is captured by its 5 mm-deep U-channel. Above the rails the
        // backplane returns to the normal full module width.
        translate([
            service_x+lower_backplane_edge_inset,
            equipment_backplane_y0,
            equipment_backplane_front_z
        ])
            cube([
                service_w-2*lower_backplane_edge_inset,
                side_guide_y1-equipment_backplane_y0,
                equipment_backplane_t
            ]);

        translate([
            service_x,
            side_guide_y1,
            equipment_backplane_front_z
        ])
            cube([
                service_w,
                backplane_ramp_start_y-side_guide_y1,
                equipment_backplane_t
            ]);

        // Shorter/steeper supported ramp from the 40 mm lower depth to the
        // 10 mm shallow upper depth.
        hull() {
            translate([
                service_x,
                backplane_ramp_start_y-1.0,
                equipment_backplane_front_z
            ])
                cube([service_w,2.0,equipment_backplane_t]);

            translate([
                service_x,
                backplane_ramp_end_y-backplane_top_band,
                equipment_backplane_top_front_z
            ])
                cube([
                    service_w,
                    backplane_top_band,
                    equipment_backplane_t
                ]);
        }

        // Finish with a vertical wall parallel to the LED panel. This provides
        // a rigid upper edge for the future rotating clamp while leaving the
        // final 10 mm below the panel top completely open.
        translate([
            service_x,
            backplane_ramp_end_y-backplane_top_band,
            equipment_backplane_top_front_z
        ])
            cube([
                service_w,
                enclosure_top_y-backplane_ramp_end_y+backplane_top_band,
                equipment_backplane_t
            ]);
    }
}

module ramp_ventilation_cutters() {
    // Ventilation exists only in the tapered upper section. Narrow 3 mm
    // vertical slits leave 5 mm ribs on an 8 mm pitch, matching PR #119.
    for (x=[
        service_x+vent_side_margin :
        vent_pitch :
        service_x+service_w-vent_side_margin-vent_slot_w
    ]) {
        translate([
            x,
            upper_vent_y,
            equipment_backplane_top_front_z-2
        ])
            cube([
                vent_slot_w,
                upper_vent_h,
                equipment_backplane_lower_rear_z-equipment_backplane_top_rear_z
                    + equipment_backplane_t + 4
            ]);
    }
}

module universal_equipment_backplane() {
    difference() {
        union() {
            backplane_shell_solid();

            top_backplane_connector_pad("left");
            top_backplane_connector_pad("right");
            top_backplane_connector_pin();

            internal_adapter_bosses();
        }

        // Left-edge vertical guide slot mates with the right-edge pin on the
        // previous module, or the left outer side plate. The vertical opening
        // preserves the removable backplane's top-down service path.
        top_backplane_connector_slot();

        // Blind M3 holes open only toward the equipment cavity. The outside
        // rear face remains a solid uninterrupted skin.
        internal_adapter_hole_cutters();

        ramp_ventilation_cutters();

        // Lower cable/ribbon passages stay in the orthogonal section.
        for (xx=cable_slot_x)
            translate([
                xx,
                cable_slot_y,
                equipment_backplane_front_z-0.5
            ])
                linear_extrude(height=equipment_backplane_t+1)
                    rounded_slot_2d(cable_slot_len,cable_slot_w);
    }
}

// Print upright on the lower locating edge. Installed +Y maps to print +Z;
// rearward +Z maps to print -Y. The 40 -> 10 mm upper taper therefore grows
// progressively from supported lower layers.
module universal_equipment_backplane_print() {
    translate([
        0,
        equipment_backplane_rear_z+adapter_boss_h,
        -equipment_backplane_y0
    ])
        rotate([90,0,0])
            universal_equipment_backplane();
}

// ---------- Detachable side/end pieces ----------

module side_wall_body(side="right") {
    // Outer side pieces close only the display's outside edges. Internal module
    // seams omit these pieces so HUB75/power cabling can pass between modules.
    x0 = side == "right"
        ? module_w + side_panel_clearance
        : -side_t - side_panel_clearance;

    union() {
        // Orthogonal lower wall follows the same 40 mm equipment depth as the
        // removable backplane's vertical insertion section.
        translate([x0,service_base_y,enclosure_front_z])
            cube([
                side_t,
                backplane_ramp_start_y-service_base_y,
                equipment_backplane_lower_rear_z-enclosure_front_z
            ]);

        // Upper side follows the steeper 40 -> 10 mm ramp.
        hull() {
            translate([
                x0,
                backplane_ramp_start_y-1,
                enclosure_front_z
            ])
                cube([
                    side_t,
                    2,
                    equipment_backplane_lower_rear_z-enclosure_front_z
                ]);

            translate([
                x0,
                backplane_ramp_end_y-backplane_top_band,
                enclosure_front_z
            ])
                cube([
                    side_t,
                    backplane_top_band,
                    equipment_backplane_top_rear_z-enclosure_front_z
                ]);
        }

        // Match the backplane's shallow vertical clamp-support region.
        translate([
            x0,
            backplane_ramp_end_y-backplane_top_band,
            enclosure_front_z
        ])
            cube([
                side_t,
                enclosure_top_y-backplane_ramp_end_y+backplane_top_band,
                equipment_backplane_top_rear_z-enclosure_front_z
            ]);
    }
}

module side_hinge_bore(side="right") {
    x0 = side == "right"
        ? module_w + side_panel_clearance - 0.5
        : -side_t - side_panel_clearance - 0.5;
    translate([x0,hinge_axis_y,hinge_axis_z])
        rotate([0,90,0])
            cylinder(d=hinge_bore_d,h=side_t+1.0);
}

module right_side_pins() {
    // One inward-facing pin mates with the hidden B socket in the right guide
    // tower. It is entirely behind the solid outside wall.
    x_start = module_w + side_panel_clearance + side_connector_overlap;

    pin_neg_x(
        x_start,
        base_connector_y_b,
        base_connector_z_b,
        side_connector_pin_len
    );
}

module right_side_sockets() {
    // Blind lower socket plus the upper vertical alignment slot. Both remain
    // open only toward the enclosure side; the outside wall stays solid.
    x_inner = module_w + side_panel_clearance;
    socket_pos_x(
        x_inner,
        base_connector_y_a,
        base_connector_z_a,
        side_socket_depth
    );
    vertical_slot_pos_x(
        x_inner,
        top_connector_slot_bottom_y,
        top_connector_slot_top_y,
        top_connector_z,
        side_socket_depth
    );
}

module left_side_pins() {
    // Lower pin mates with the base guide. The upper pin aligns the top of the
    // removable backplane while still allowing vertical service motion.
    x_start = -side_panel_clearance - side_connector_overlap;

    pin_pos_x(
        x_start,
        base_connector_y_a,
        base_connector_z_a,
        side_connector_pin_len
    );
    pin_pos_x(
        x_start,
        top_connector_y,
        top_connector_z,
        top_side_pin_len
    );
}

module left_side_sockets() {
    // Blind inward-facing socket; the outer face remains unbroken.
    x_inner = -side_panel_clearance;
    socket_neg_x(
        x_inner,
        base_connector_y_b,
        base_connector_z_b,
        side_socket_depth
    );
}

module equipment_side(side="right") {
    assert(side == "right" || side == "left");

    difference() {
        union() {
            side_wall_body(side);
            if (side == "right")
                right_side_pins();
            else
                left_side_pins();
        }

        if (side == "right")
            right_side_sockets();
        else
            left_side_sockets();

        side_hinge_bore(side);
    }
}

module equipment_side_print(side="right") {
    // Mirror the print face so each side's connector pins grow from its wall.
    if (side == "right")
        rotate([0,90,0]) equipment_side(side);
    else
        rotate([0,-90,0]) equipment_side(side);
}

// ---------- Assembly / previews ----------

module stationary_equipment_module_core() {
    hinged_equipment_base();
    universal_equipment_backplane();
}

module stationary_equipment_enclosure() {
    stationary_equipment_module_core();
    equipment_side("left");
    equipment_side("right");
}

module moving_panel_at_angle(angle=0) {
    translate([0,hinge_axis_y,hinge_axis_z])
        rotate([-angle,0,0])
            translate([0,-hinge_axis_y,-hinge_axis_z])
                moving_panel_template_installed();
}

module moving_panel_clamp_at_angle(angle=0, clamp_angle=180) {
    translate([0,hinge_axis_y,hinge_axis_z])
        rotate([-angle,0,0])
            translate([0,-hinge_axis_y,-hinge_axis_z])
                panel_rotating_clamp_installed(clamp_angle);
}

module hinge_rail_preview(length=236) {
    translate([10,hinge_axis_y,hinge_axis_z])
        rotate([0,90,0])
            cylinder(d=hinge_rail_d,h=length);
}

module direct_mount_assembly(open_angle=service_open_angle) {
    // Equipment enclosure remains fixed/stationary.
    color([0.12,0.12,0.14])
        hinged_equipment_base();

    color([0.18,0.22,0.25])
        universal_equipment_backplane();

    color([0.30,0.30,0.34]) {
        equipment_side("left");
        equipment_side("right");
    }

    color([0.62,0.62,0.66])
        hinge_rail_preview();

    // LED panel/template is the moving leaf and opens forward/down.
    color([0.25,0.25,0.28])
        moving_panel_at_angle(open_angle);

    // The retention tab belongs entirely to the moving panel. Closed preview
    // shows it pointing upward over the panel edge; open preview rotates it
    // sideways so it remains visually distinct from the stationary enclosure.
    color([0.85,0.55,0.18])
        moving_panel_clamp_at_angle(
            open_angle,
            open_angle > 0 ? 90 : 180
        );
}

if (!is_undef(hinge_part)) {
    if (hinge_part == "panel_template" || hinge_part == "fixed_template")
        moving_panel_template_print();
    else if (hinge_part == "equipment_base")
        hinged_equipment_base_print();
    else if (hinge_part == "universal_backplane")
        universal_equipment_backplane_print();
    else if (hinge_part == "side_left")
        equipment_side_print("left");
    else if (hinge_part == "side_right")
        equipment_side_print("right");
    else if (hinge_part == "panel_clamp")
        panel_rotating_clamp_print();
    else if (hinge_part == "assembly")
        direct_mount_assembly();
    else
        assert(false,str("Unknown hinge_part: ",hinge_part));
}
