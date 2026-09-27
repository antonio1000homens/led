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
hinge_axis_y = ground_clearance + hinge_radius; // 27 mm above stationary floor

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

// Reuse the validated PR #119 enclosure profile on the removable backplane:
// a 40 mm-deep vertical lower equipment section up to 60 mm above the floor,
// tapering to 10 mm at the top of the LED/template.
enclosure_front_z = fixed_template_t + 0.8; // 2.8 mm behind template rear face
enclosure_bottom_depth = 40;
enclosure_top_depth = 10;
backplane_ramp_start_y = 60;
enclosure_top_y = ground_clearance + module_h;

equipment_backplane_t = 3;
equipment_backplane_lower_rear_z = enclosure_front_z + enclosure_bottom_depth;
equipment_backplane_front_z = equipment_backplane_lower_rear_z - equipment_backplane_t;
equipment_backplane_rear_z = equipment_backplane_lower_rear_z;
equipment_backplane_top_rear_z = enclosure_front_z + enclosure_top_depth;
equipment_backplane_top_front_z = equipment_backplane_top_rear_z - equipment_backplane_t;

backplane_guide_clearance = 0.4;
backplane_guide_t = 1.2;
backplane_seat_depth = 2.0;
base_seat_y = 4.5;
equipment_backplane_y0 = base_seat_y - backplane_seat_depth;

// The locating rail is a recessed groove at the BACK edge of the base. It
// does not project into the usable equipment cavity.
backplane_slot_front_z = equipment_backplane_front_z - backplane_guide_clearance;
backplane_slot_back_z = equipment_backplane_rear_z + backplane_guide_clearance;
base_rear_z = backplane_slot_back_z + backplane_guide_t;
base_floor_front_z = service_front_z;
base_floor_rear_z = base_rear_z;

// Supported top closure derived from PR #119. The tapered backplane grows
// forward progressively and finishes 0.8 mm behind the moving template.
backplane_top_band = 1.5;
top_template_clearance = 0.8;
top_link_front_z = fixed_template_t + top_template_clearance;
top_link_start_y = enclosure_top_y - 18;
top_link_anchor_h = 2;
top_link_cap_h = 3;

// Generic M3 adapter pattern. Component-specific geometry belongs on adapters.
adapter_boss_d = 8;
adapter_hole_d = 3.4;
adapter_boss_h = 5;
adapter_x = [32,80,128,176,224];
// Keep accessory mounting on the vertical lower section so adapters remain
// parallel to the LED plane and do not sit on the tapered ventilation roof.
adapter_y = [18,36,54];

// Fine upper-only ventilation, matching the proven PR #119 strategy.
vent_side_margin = 12;
vent_slot_w = 3;
vent_pitch = 8;
upper_vent_y = backplane_ramp_start_y + 10;
upper_vent_h = 50;

// Lower cable/ribbon passages remain below the taper.
cable_slot_len = 20;
cable_slot_w = 6;
cable_slot_x = [64,176];
cable_slot_y = 28;

// Self-mating side alignment. Each edge carries one pin and one socket.
// Right(A pin/B socket) mates Left(A socket/B pin) on another identical module.
connector_pin_d = 4;
connector_socket_d = 4.7;
connector_pin_len = 4;
connector_socket_depth = 4;
// Base side connectors live entirely inside the first 4 mm floor band so
// their horizontal pins are bed-connected from the first print layers.
base_connector_y_a = 2.5;
base_connector_y_b = 2.5;
base_connector_z_a = 18;
base_connector_z_b = 34;
backplane_connector_y_a = 24;
backplane_connector_y_b = 52;
backplane_connector_z = equipment_backplane_front_z;
connector_pad_y = 10;
connector_pad_z = 7;

side_t = 3;
side_panel_clearance = 0.4;
side_connector_overlap = 0.4;
side_connector_bridge = side_panel_clearance + backplane_edge_inset;
side_connector_pin_len =
    connector_pin_len + side_connector_bridge + side_connector_overlap;

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

module stationary_hinge_barrels() {
    for (segment=stationary_knuckles)
        rail_hinge_barrel(segment[0],segment[1]);
}

module stationary_hinge_support_web(x0,len) {
    // Reinforce the stationary barrel locally and terminate its rearward web
    // into the horizontal hinge shelf. The web no longer extends through the
    // enclosure to the rear rail wall, leaving that interior volume clear.
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
        }

        // Recess the top-down backplane rail INTO the rear edge of the base.
        // Only a 2 mm-deep locating groove is removed; there is no internal
        // ramp, lip or captive wall consuming module space.
        translate([
            service_x-0.1,
            equipment_backplane_y0,
            backplane_slot_front_z
        ])
            cube([
                service_w+0.2,
                base_seat_y-equipment_backplane_y0+0.2,
                backplane_slot_back_z-backplane_slot_front_z
            ]);
    }
}

module base_connector_pins() {
    right_x = service_x + service_w;
    left_x = service_x;

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

module backplane_connector_pads() {
    for (yy=[backplane_connector_y_a,backplane_connector_y_b]) {
        translate([
            service_x,
            yy-connector_pad_y/2,
            equipment_backplane_front_z-1
        ])
            cube([8,connector_pad_y,connector_pad_z]);

        translate([
            service_x+service_w-8,
            yy-connector_pad_y/2,
            equipment_backplane_front_z-1
        ])
            cube([8,connector_pad_y,connector_pad_z]);
    }
}

module backplane_connector_pins() {
    right_x = service_x + service_w;
    left_x = service_x;

    pin_pos_x(right_x,backplane_connector_y_a,backplane_connector_z);
    pin_neg_x(left_x,backplane_connector_y_b,backplane_connector_z);
}

module backplane_connector_sockets() {
    right_x = service_x + service_w;
    left_x = service_x;

    socket_neg_x(right_x,backplane_connector_y_b,backplane_connector_z);
    socket_pos_x(left_x,backplane_connector_y_a,backplane_connector_z);
}

function tapered_backplane_rear_z_at_y(y) =
    equipment_backplane_lower_rear_z +
    (equipment_backplane_top_rear_z-equipment_backplane_lower_rear_z) *
    ((y-backplane_ramp_start_y)/(enclosure_top_y-backplane_ramp_start_y));

module backplane_shell_solid() {
    union() {
        // Vertical lower section: this is the portion that enters the rear
        // top-down base groove and carries accessory adapters.
        translate([
            service_x,
            equipment_backplane_y0,
            equipment_backplane_front_z
        ])
            cube([
                service_w,
                backplane_ramp_start_y-equipment_backplane_y0,
                equipment_backplane_t
            ]);

        // Upper enclosure ramps forward from the 40 mm lower depth to the
        // 10 mm top depth. The hull is continuously supported in the upright
        // print orientation.
        hull() {
            translate([
                service_x,
                backplane_ramp_start_y-1.0,
                equipment_backplane_front_z
            ])
                cube([service_w,2.0,equipment_backplane_t]);

            translate([
                service_x,
                enclosure_top_y-backplane_top_band,
                equipment_backplane_top_front_z
            ])
                cube([
                    service_w,
                    backplane_top_band,
                    equipment_backplane_t
                ]);
        }
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

module backplane_top_link() {
    // Grow the roof from an anchor on the already-supported tapered wall toward
    // the top of the moving front plate. This avoids a front-first floating
    // cantilever while closing the enclosure to within 0.8 mm of the template.
    anchor_rear_z = tapered_backplane_rear_z_at_y(top_link_start_y);

    hull() {
        translate([
            service_x,
            top_link_start_y,
            anchor_rear_z-equipment_backplane_t
        ])
            cube([
                service_w,
                top_link_anchor_h,
                equipment_backplane_t
            ]);

        translate([
            service_x,
            enclosure_top_y-top_link_cap_h,
            top_link_front_z
        ])
            cube([
                service_w,
                top_link_cap_h,
                equipment_backplane_top_rear_z-top_link_front_z
            ]);
    }
}

module universal_equipment_backplane() {
    difference() {
        union() {
            backplane_shell_solid();
            backplane_top_link();

            backplane_connector_pads();
            backplane_connector_pins();

            // Repeated universal adapter bosses on the vertical lower section.
            for (xx=adapter_x)
                for (yy=adapter_y)
                    translate([
                        xx,
                        yy,
                        equipment_backplane_rear_z
                    ])
                        cylinder(d=adapter_boss_d,h=adapter_boss_h);
        }

        backplane_connector_sockets();

        // Through-holes in every adapter boss/plate location.
        for (xx=adapter_x)
            for (yy=adapter_y)
                translate([
                    xx,
                    yy,
                    equipment_backplane_front_z-0.5
                ])
                    cylinder(
                        d=adapter_hole_d,
                        h=equipment_backplane_t+adapter_boss_h+1
                    );

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

        // Upper side follows the removable backplane taper and its supported
        // top closure toward the moving panel/template.
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
                enclosure_top_y-top_link_cap_h,
                top_link_front_z
            ])
                cube([
                    side_t,
                    top_link_cap_h,
                    equipment_backplane_top_rear_z-top_link_front_z
                ]);
        }
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
    // Start 0.4 mm inside the side wall so the printed pins grow directly from
    // the wall in the flat print orientation, then bridge the perimeter gap
    // into the universal module sockets.
    x_start = module_w + side_panel_clearance + side_connector_overlap;

    pin_neg_x(
        x_start,
        base_connector_y_b,
        base_connector_z_b,
        side_connector_pin_len
    );
    pin_neg_x(
        x_start,
        backplane_connector_y_b,
        backplane_connector_z,
        side_connector_pin_len
    );
}

module right_side_sockets() {
    x_inner = service_x + service_w;

    // Base A pin and backplane A pin.
    socket_pos_x(x_inner,base_connector_y_a,base_connector_z_a);
    socket_pos_x(x_inner,backplane_connector_y_a,backplane_connector_z);
}

module left_side_pins() {
    x_start = -side_panel_clearance - side_connector_overlap;

    pin_pos_x(
        x_start,
        base_connector_y_a,
        base_connector_z_a,
        side_connector_pin_len
    );
    pin_pos_x(
        x_start,
        backplane_connector_y_a,
        backplane_connector_z,
        side_connector_pin_len
    );
}

module left_side_sockets() {
    x_inner = service_x;

    // Base B pin and backplane B pin.
    socket_neg_x(x_inner,base_connector_y_b,base_connector_z_b);
    socket_neg_x(x_inner,backplane_connector_y_b,backplane_connector_z);
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
    else if (hinge_part == "assembly")
        direct_mount_assembly();
    else
        assert(false,str("Unknown hinge_part: ",hinge_part));
}
