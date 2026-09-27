// Canonical modular hinged direct-mount enclosure for four 256 x 128 mm P4 HUB75 panels.
//
// Issue #133 commits the project to the hinged architecture. This is the single
// parametric source of truth for the PR #119-style MOVING panel/template leaf,
// STATIONARY universal equipment base, universal slide-in backplane and
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

base_lower_y1 = 20;
base_front_back_z = 18.5;

rail_beam_y0 = 17;
rail_beam_y1 = 31;
rail_beam_z0 = 32;
rail_beam_z1 = 46;

base_rear_z = 60;
base_beam_t = 6;

// T-slot is deliberately open at both X ends so the backplane slides laterally.
// A side piece closes the end after assembly.
// Support-free one-sided dovetail rail.
//
// Instead of cutting a T-slot out of a solid beam, the rail is built from
// bed-connected front/rear walls. The front wall shifts rearward gradually to
// form the retaining lip. The backplane's enlarged lower head is therefore
// captive in Z but the rail has no horizontal ceiling.
rail_base_y = 4.5;
rail_head_top_y = 22.5;
rail_lip_y = 31;
rail_neck_top_y = 33;
rail_front_z0 = 32;
rail_wall_t = 3;
rail_lip_z0 = 40;
rail_rear_z0 = 46;

// 0.4 mm nominal clearance per exposed rail face for an FDM serviceable fit.
rail_clearance = 0.4;
tongue_head_y0 = 18.9;
tongue_head_y1 = 22.1;
tongue_head_z0 = rail_front_z0 + rail_wall_t + rail_clearance;
tongue_head_z1 = rail_rear_z0 - rail_clearance;
tongue_stem_y0 = rail_lip_y - 0.4;
tongue_stem_y1 = rail_neck_top_y - rail_clearance;
tongue_stem_z0 = rail_lip_z0 + rail_wall_t + rail_clearance;
tongue_stem_z1 = rail_rear_z0 - rail_clearance;

// Backplane: one identical plate for every module.
equipment_backplane_y0 = 31;
equipment_backplane_front_z = 44;
equipment_backplane_t = 3;
equipment_backplane_rear_z = equipment_backplane_front_z + equipment_backplane_t;

// Generic M3 adapter pattern. Component-specific geometry belongs on adapters.
adapter_boss_d = 8;
adapter_hole_d = 3.4;
adapter_boss_h = 5;
adapter_x = [32,80,128,176,224];
adapter_y = [48,80,112];

// Backplane ventilation/cable passages avoid the boss grid.
vent_slot_len = 24;
vent_slot_w = 5;
vent_x = [56,128,200];
vent_y = [64,96];
cable_slot_len = 20;
cable_slot_w = 6;
cable_slot_x = [64,176];
cable_slot_y = 36;

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
base_connector_z_a = 24;
base_connector_z_b = 52;
backplane_connector_y_a = 56;
backplane_connector_y_b = 104;
backplane_connector_z = 44;
connector_pad_y = 10;
connector_pad_z = 7;

side_t = 3;

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
hinge_guard_start_y = rail_base_y - 0.5; // overlaps the stationary floor by 0.5 mm
hinge_guard_top_y = hinge_axis_y;
hinge_guard_bridge_overlap = 0.5;
hinge_guard_bridge_h = 2.0;

module stationary_hinge_barrels() {
    for (segment=stationary_knuckles)
        rail_hinge_barrel(segment[0],segment[1]);
}

module stationary_hinge_support_web(x0,len) {
    // Proven PR #119 support strategy: begin at the BOTTOM tangent of the
    // stationary barrel, then slope strongly rearward into the bed-connected
    // base. This leaves the moving panel's forward/down sweep corridor open.
    hull() {
        translate([
            x0,
            hinge_axis_y-hinge_radius-1.0,
            hinge_axis_z-1.0
        ])
            cube([len,3,2]);

        translate([
            x0,
            service_base_y,
            rail_rear_z0
        ])
            cube([len,2,2]);
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
    union() {
        // Stationary floor strip. In the upright print this is the bed contact.
        translate([service_x,service_base_y,service_front_z])
            cube([
                service_w,
                rail_base_y-service_base_y,
                base_rear_z-service_front_z
            ]);

        // Rear rail wall grows directly from the stationary floor.
        translate([service_x,rail_base_y,rail_rear_z0])
            cube([
                service_w,
                rail_lip_y-rail_base_y,
                rail_wall_t
            ]);

        // Front lower rail wall. It remains behind the hinge sweep because the
        // proven hinge axis is now y=27/z=16 and the panel is the moving leaf.
        translate([service_x,rail_base_y,rail_front_z0])
            cube([
                service_w,
                rail_head_top_y-rail_base_y,
                rail_wall_t
            ]);

        // Support-free retaining lip for the removable backplane.
        hull() {
            translate([service_x,rail_head_top_y-0.1,rail_front_z0])
                cube([service_w,0.2,rail_wall_t]);
            translate([service_x,rail_lip_y,rail_lip_z0])
                cube([service_w,0.2,rail_wall_t]);
        }

        translate([service_x,rail_lip_y,rail_lip_z0])
            cube([
                service_w,
                rail_neck_top_y-rail_lip_y,
                rail_wall_t
            ]);

        stationary_hinge_supports();
        stationary_hinge_barrels();
        lower_hinge_guard();
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

// ---------- Universal slide-in backplane ----------

module rounded_slot_2d(len,w) {
    hull() {
        translate([-(len-w)/2,0]) circle(d=w);
        translate([(len-w)/2,0]) circle(d=w);
    }
}

module backplane_tslot_tongue() {
    // Enlarged lower head, trapped between the front/rear rail walls.
    translate([
        service_x,
        tongue_head_y0,
        tongue_head_z0
    ])
        cube([
            service_w,
            tongue_head_y1-tongue_head_y0,
            tongue_head_z1-tongue_head_z0
        ]);

    // Matching sloped shoulder into the narrow stem.
    hull() {
        translate([
            service_x,
            tongue_head_y1-0.1,
            tongue_head_z0
        ])
            cube([
                service_w,
                0.2,
                tongue_head_z1-tongue_head_z0
            ]);

        translate([
            service_x,
            tongue_stem_y0,
            tongue_stem_z0
        ])
            cube([
                service_w,
                0.2,
                tongue_stem_z1-tongue_stem_z0
            ]);
    }

    // Narrow stem overlaps the lower edge of the backplane plate.
    translate([
        service_x,
        tongue_stem_y0,
        tongue_stem_z0
    ])
        cube([
            service_w,
            tongue_stem_y1-tongue_stem_y0,
            tongue_stem_z1-tongue_stem_z0
        ]);
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

module universal_equipment_backplane() {
    difference() {
        union() {
            backplane_tslot_tongue();

            translate([
                service_x,
                equipment_backplane_y0,
                equipment_backplane_front_z
            ])
                cube([
                    service_w,
                    service_top_y-equipment_backplane_y0,
                    equipment_backplane_t
                ]);

            backplane_connector_pads();
            backplane_connector_pins();

            // Repeated universal adapter bosses.
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

        // Upper ventilation.
        for (xx=vent_x)
            for (yy=vent_y)
                translate([
                    xx,
                    yy,
                    equipment_backplane_front_z-0.5
                ])
                    linear_extrude(height=equipment_backplane_t+1)
                        rounded_slot_2d(vent_slot_len,vent_slot_w);

        // Lower cable/ribbon passages.
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

// Print on the lower edge: 255 mm across the bed, ~109 mm high, and only the
// backplane depth/bosses in the second bed dimension. This keeps the T-slot
// tongue and bosses growing vertically instead of creating floating islands.
module universal_equipment_backplane_print() {
    translate([
        0,
        equipment_backplane_rear_z+adapter_boss_h,
        -tongue_head_y0
    ])
        rotate([90,0,0])
            universal_equipment_backplane();
}

// ---------- Detachable side/end pieces ----------

module side_wall_body(side="right") {
    x0 = side == "right"
        ? service_x + service_w
        : service_x - side_t;

    union() {
        // Main end wall closes the universal backplane cavity.
        translate([x0,service_base_y,service_front_z])
            cube([
                side_t,
                service_top_y-service_base_y,
                equipment_backplane_rear_z-service_front_z
            ]);

        // Lower rear-foot extension.
        translate([x0,service_base_y,equipment_backplane_rear_z])
            cube([
                side_t,
                rail_beam_y1-service_base_y,
                base_rear_z-equipment_backplane_rear_z
            ]);
    }
}

module right_side_pins() {
    x_inner = service_x + service_w;

    // Base B socket and backplane B socket.
    pin_neg_x(x_inner+0.8,base_connector_y_b,base_connector_z_b,connector_pin_len+0.8);
    pin_neg_x(x_inner+0.8,backplane_connector_y_b,backplane_connector_z,connector_pin_len+0.8);
}

module right_side_sockets() {
    x_inner = service_x + service_w;

    // Base A pin and backplane A pin.
    socket_pos_x(x_inner,base_connector_y_a,base_connector_z_a);
    socket_pos_x(x_inner,backplane_connector_y_a,backplane_connector_z);
}

module left_side_pins() {
    x_inner = service_x;

    // Base A socket and backplane A socket.
    pin_pos_x(x_inner-0.8,base_connector_y_a,base_connector_z_a,connector_pin_len+0.8);
    pin_pos_x(x_inner-0.8,backplane_connector_y_a,backplane_connector_z,connector_pin_len+0.8);
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
    }
}

module equipment_side_print(side="right") {
    // Lay each side wall broad-face-down. The left piece is flipped the opposite
    // way so its inward-facing pins grow upward from the wall rather than
    // beginning below the print plane.
    if (side == "right")
        rotate([0,90,0])
            equipment_side(side);
    else
        rotate([0,-90,0])
            equipment_side(side);
}

// ---------- Assembly / previews ----------

module stationary_equipment_enclosure() {
    hinged_equipment_base();
    universal_equipment_backplane();
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

