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

// Physical rail/end-stop contract. The detachable left/right end pieces close
// the rail axis and stop the 6 mm rod at its defined endpoints. The stop face
// reaches the rod end but never extends toward the nearest hinge barrel.
hinge_rail_start_x = 10;
hinge_rail_length = 236;
hinge_rail_end_x = hinge_rail_start_x + hinge_rail_length;
hinge_end_stop_d = hinge_bore_d;

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

hinge_left_barrel_start = min(
    min([for (segment=panel_knuckles) segment[0]]),
    min([for (segment=stationary_knuckles) segment[0]])
);
hinge_right_barrel_end = max(
    max([for (segment=panel_knuckles) segment[0]+segment[1]]),
    max([for (segment=stationary_knuckles) segment[0]+segment[1]])
);

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

// Revised upper enclosure profile and top closure fastening.
// Keep the 40 mm-deep equipment section taller, use a shorter/steeper ramp,
// then finish with a shallow wall parallel to the LED panel all the way to the
// full panel height. The three existing TOP-row panel screw locations are
// reused as removable closure fasteners between the moving panel/template and
// stationary enclosure.
enclosure_panel_clearance = 0.8;
enclosure_front_z = fixed_template_t + enclosure_panel_clearance; // 2.8 mm
enclosure_bottom_depth = 40;

// Single source of truth: closure holes directly reuse the measured panel
// mounting coordinates and diameter. Installed Y includes ground clearance.
panel_closure_x = panel_mount_x;
panel_closure_y = ground_clearance + panel_mount_y[1];
panel_closure_hole_d = panel_mount_hole_d;

backplane_ramp_start_y = 75;
backplane_ramp_end_y = 120;
enclosure_top_y = ground_clearance + module_h;
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
// Two slimmer boss rows are sufficient for detachable adapters.
adapter_boss_d = 7;
adapter_hole_d = 3.4;
adapter_boss_h = 4;
adapter_x = [32,80,128,176,224];

// CI refresh marker: canonical STL corresponds to the 54 mm universal cavity.
// Universal deeper equipment envelope. The 54 mm centre zone remains inset at
// the lower guide interface, because the top-down U-channels need that capture
// geometry. Above the guide towers the rear shell expands to the full service
// width instead of carrying the old 40 mm-depth edge lands up the enclosure.
// The two detachable end pieces now follow this deeper outer profile.
//
// The full-depth centre region is sized around the measured 110 x 80 x 37 mm
// PSU: 54 mm clear depth leaves 17 mm beyond the 37 mm PSU thickness. The deep
// wall remains vertical for 86 mm, then returns to the shallow panel plane
// through a ventilated ramp. The final 10 mm is flat/parallel to the LED panel
// so the enclosure finishes flush at the top edge.
universal_deep_clear_depth = 54;
universal_deep_wall_t = equipment_backplane_t;

// Lower guide-compatible centre span. This is the only place where the old
// side inset remains mechanically necessary.
universal_deep_x0 = service_x + side_guide_w + 0.5;
universal_deep_x1 = service_x + service_w - side_guide_w - 0.5;
universal_deep_w = universal_deep_x1-universal_deep_x0;

// Above the guide towers the enclosure grows to the complete service width.
// A short 8 mm depth transition avoids a sudden unsupported step in the
// upright print while allowing the detachable ends to match the deep shell.
universal_full_x0 = service_x;
universal_full_x1 = service_x + service_w;
universal_full_w = universal_full_x1-universal_full_x0;
universal_edge_guide_clearance_y = 1;
universal_edge_transition_y0 =
    side_guide_y1 + universal_edge_guide_clearance_y;
universal_edge_transition_y1 = universal_edge_transition_y0 + 8;

universal_deep_transition_y0 = 6;
universal_deep_y0 = 12;
universal_deep_y1 = 98;

// Keep the two accessory-boss rows close to the lower/upper edges of the
// full-depth mounting region while retaining a 10 mm material border.
adapter_edge_inset_y = 10;
adapter_y = [
    universal_deep_y0 + adapter_edge_inset_y,
    universal_deep_y1 - adapter_edge_inset_y
];
universal_top_flat_h = 10;
universal_deep_ramp_end_y = enclosure_top_y-universal_top_flat_h;
universal_deep_rear_z =
    enclosure_front_z + universal_deep_clear_depth + universal_deep_wall_t;
universal_deep_front_z =
    universal_deep_rear_z-universal_deep_wall_t;

// Ventilation is confined to the universal deep ramp. The lower vertical wall
// and final 10 mm top wall remain solid; rear cable slots remain retired.
vent_side_margin = 12;
vent_slot_w = 3;
vent_pitch = 8;
ramp_vent_bottom_margin = 6;
ramp_vent_top_margin = 6;
upper_vent_y = universal_deep_y1 + ramp_vent_bottom_margin;
upper_vent_h =
    universal_deep_ramp_end_y-ramp_vent_top_margin-upper_vent_y;

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

// Inner faces and axial lengths for the integrated rod end stops.
left_side_inner_x = -side_panel_clearance;
right_side_inner_x = module_w + side_panel_clearance;
left_rail_end_stop_len = hinge_rail_start_x - left_side_inner_x;
right_rail_end_stop_len = right_side_inner_x - hinge_rail_end_x;

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
                universal_deep_front_z-adapter_boss_h
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
                universal_deep_front_z-adapter_boss_h-0.2
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

// ---------- Top-row closure fasteners ----------

module panel_closure_hole_cutters() {
    for (xx=panel_closure_x)
        translate([
            xx,
            panel_closure_y,
            equipment_backplane_top_front_z-0.5
        ])
            cylinder(
                d=panel_closure_hole_d,
                h=equipment_backplane_t+1
            );
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

        // Finish with a vertical wall parallel to the LED panel and carry it
        // all the way to the panel top. Only the three aligned closure holes
        // are cut through this wall; the top edge remains continuous.
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

// Replace the centre of the native/interface shell with the deeper universal
// equipment volume. The lower guide-compatible side inset is retained only
// below the edge-depth transition; above it the rear shell reaches full width.
module universal_native_backplane_opening() {
    // The centre deep zone starts low enough to preserve the PSU-fit height.
    translate([
        universal_deep_x0,
        universal_deep_y0-0.2,
        -1
    ])
        cube([
            universal_deep_w,
            enclosure_top_y-universal_deep_y0+0.4,
            universal_deep_rear_z+2
        ]);
}

module universal_edge_native_openings() {
    // Remove the old 40 mm-depth side lands only after the U-channel guide
    // interface has finished. The lower capture geometry therefore remains
    // unchanged, while the upper enclosure can run at the full 54 mm profile.
    edge_spans = [
        [service_x, universal_deep_x0-service_x],
        [universal_deep_x1, service_x+service_w-universal_deep_x1]
    ];

    for (span=edge_spans)
        translate([
            span[0],
            universal_edge_transition_y0-0.2,
            -1
        ])
            cube([
                span[1],
                enclosure_top_y-universal_edge_transition_y0+0.4,
                universal_deep_rear_z+2
            ]);
}

module universal_deep_rear_shell() {
    slice_h = 1.0;

    // Print-friendly lower transition immediately above the base seat.
    hull() {
        translate([
            universal_deep_x0,
            universal_deep_transition_y0,
            equipment_backplane_front_z
        ])
            cube([
                universal_deep_w,
                slice_h,
                equipment_backplane_t
            ]);

        translate([
            universal_deep_x0,
            universal_deep_y0-slice_h,
            universal_deep_front_z
        ])
            cube([
                universal_deep_w,
                slice_h,
                universal_deep_wall_t
            ]);
    }

    // Full 54 mm clear-depth centre equipment region.
    translate([
        universal_deep_x0,
        universal_deep_y0-slice_h,
        universal_deep_front_z
    ])
        cube([
            universal_deep_w,
            universal_deep_y1-universal_deep_y0+slice_h,
            universal_deep_wall_t
        ]);

    // Ventilated return ramp.
    hull() {
        translate([
            universal_deep_x0,
            universal_deep_y1-slice_h,
            universal_deep_front_z
        ])
            cube([
                universal_deep_w,
                slice_h,
                universal_deep_wall_t
            ]);

        translate([
            universal_deep_x0,
            universal_deep_ramp_end_y-slice_h,
            equipment_backplane_top_front_z
        ])
            cube([
                universal_deep_w,
                slice_h,
                equipment_backplane_t
            ]);
    }

    // Final 10 mm stays flat/parallel to the panel for a flush top edge.
    translate([
        universal_deep_x0,
        universal_deep_ramp_end_y-slice_h,
        equipment_backplane_top_front_z
    ])
        cube([
            universal_deep_w,
            enclosure_top_y-universal_deep_ramp_end_y+slice_h,
            equipment_backplane_t
        ]);
}

module universal_edge_rear_shell(side="left") {
    // Extend the rear shell from the guide-compatible centre span out to each
    // module edge. The extension begins only above the lower guide towers.
    x0 = side == "left" ? service_x : universal_deep_x1;
    edge_w = side == "left"
        ? universal_deep_x0-service_x
        : service_x+service_w-universal_deep_x1;
    slice_h = 1.0;

    // 40 -> 54 mm depth transition immediately above the guide towers.
    hull() {
        translate([
            x0,
            universal_edge_transition_y0-slice_h,
            equipment_backplane_front_z
        ])
            cube([
                edge_w,
                slice_h,
                equipment_backplane_t
            ]);

        translate([
            x0,
            universal_edge_transition_y1-slice_h,
            universal_deep_front_z
        ])
            cube([
                edge_w,
                slice_h,
                universal_deep_wall_t
            ]);
    }

    // Match the centre region at full depth once clear of the guide towers.
    translate([
        x0,
        universal_edge_transition_y1-slice_h,
        universal_deep_front_z
    ])
        cube([
            edge_w,
            universal_deep_y1-universal_edge_transition_y1+slice_h,
            universal_deep_wall_t
        ]);

    // Follow the same return ramp as the centre shell.
    hull() {
        translate([
            x0,
            universal_deep_y1-slice_h,
            universal_deep_front_z
        ])
            cube([
                edge_w,
                slice_h,
                universal_deep_wall_t
            ]);

        translate([
            x0,
            universal_deep_ramp_end_y-slice_h,
            equipment_backplane_top_front_z
        ])
            cube([
                edge_w,
                slice_h,
                equipment_backplane_t
            ]);
    }

    translate([
        x0,
        universal_deep_ramp_end_y-slice_h,
        equipment_backplane_top_front_z
    ])
        cube([
            edge_w,
            enclosure_top_y-universal_deep_ramp_end_y+slice_h,
            equipment_backplane_t
        ]);
}

module universal_deep_side_wall(side="left") {
    // The centre-zone side walls are now only lower transition ribs. They stop
    // once the outer edge shell has reached full depth, eliminating the tall
    // internal "arms" that previously separated the centre from the end zones.
    x0 = side == "left"
        ? universal_deep_x0
        : universal_deep_x1-universal_deep_wall_t;
    slice_h = 1.0;

    hull() {
        translate([
            x0,
            universal_deep_transition_y0,
            equipment_backplane_front_z
        ])
            cube([
                universal_deep_wall_t,
                slice_h,
                equipment_backplane_t
            ]);
        translate([
            x0,
            universal_deep_y0-slice_h,
            equipment_backplane_front_z
        ])
            cube([
                universal_deep_wall_t,
                slice_h,
                universal_deep_rear_z-equipment_backplane_front_z
            ]);
    }

    translate([
        x0,
        universal_deep_y0-slice_h,
        equipment_backplane_front_z
    ])
        cube([
            universal_deep_wall_t,
            universal_edge_transition_y1-universal_deep_y0+slice_h,
            universal_deep_rear_z-equipment_backplane_front_z
        ]);
}



module universal_backplane_shell_solid() {
    union() {
        difference() {
            backplane_shell_solid();
            universal_native_backplane_opening();
            universal_edge_native_openings();
        }
        universal_deep_rear_shell();
        universal_edge_rear_shell("left");
        universal_edge_rear_shell("right");
        universal_deep_side_wall("left");
        universal_deep_side_wall("right");
    }
}

module ramp_ventilation_cutters() {
    for (x=[
        universal_deep_x0+vent_side_margin :
        vent_pitch :
        universal_deep_x1-vent_side_margin-vent_slot_w
    ])
        translate([
            x,
            upper_vent_y,
            equipment_backplane_top_front_z-2
        ])
            cube([
                vent_slot_w,
                upper_vent_h,
                universal_deep_rear_z-equipment_backplane_top_front_z+4
            ]);
}

module universal_equipment_backplane() {
    difference() {
        union() {
            universal_backplane_shell_solid();

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

        // Three aligned top-row clearance holes let longer panel screws clamp
        // the moving panel/template to the stationary enclosure when closed.
        // These screws must be removed/loosened before opening the hinge.
        panel_closure_hole_cutters();

        // No rear cable/ribbon through-slots. Internal module seams remain
        // open for HUB75 and power cabling.
    }
}

// ---------- Backplane print orientation + removable ramp supports ----------
//
// The physical failure occurred when the tall upright print reached the
// 54 mm -> shallow return ramp. The installed enclosure therefore stays clean:
// no permanent rear feet are added. Instead, the manufacturing wrapper adds
// removable supports directly UNDER the ramp in print coordinates.
//
// Installed +Y maps to print +Z and installed rearward +Z maps to print -Y.
// The support posts rise vertically from the bed and touch the ramp through
// narrow breakaway necks with a small two-layer overlap rather than leaving
// an air gap or relying on coplanar contact. Five X ribs are centred in solid
// bands between the 3 mm ventilation slots, and each rib supports four points
// along the ramp. A thin bed rail ties each rib together and intersects the
// lower backplane wall so the generated STL remains one printable shell.
backplane_print_origin_y = equipment_backplane_rear_z + adapter_boss_h;

ramp_print_support_x = [24,72,120,168,216];
ramp_print_support_levels = [0.25,0.40,0.55,0.75,0.95];
ramp_print_support_post_w = 4;
ramp_print_support_post_d = 2.4;
ramp_print_support_slice_d = 0.4;
ramp_print_support_base_t = 0.8;
ramp_print_support_neck_w = 0.8;
ramp_print_support_neck_h = 1.0;
ramp_print_support_contact_overlap = 0.4;

// Print-space line followed by the cavity-facing surface of the return ramp.
ramp_print_inner_y0 =
    backplane_print_origin_y-universal_deep_front_z;
ramp_print_inner_y1 =
    backplane_print_origin_y-equipment_backplane_top_front_z;
ramp_print_z0 = universal_deep_y1-equipment_backplane_y0;
ramp_print_z1 =
    universal_deep_ramp_end_y-equipment_backplane_y0;

function ramp_print_y_at_level(level) =
    ramp_print_inner_y0 +
    (ramp_print_inner_y1-ramp_print_inner_y0)*level;

function ramp_print_z_at_y(print_y) =
    ramp_print_z0 +
    (ramp_print_z1-ramp_print_z0) *
    ((print_y-ramp_print_inner_y0)/
     (ramp_print_inner_y1-ramp_print_inner_y0));

ramp_print_support_base_y0 =
    ramp_print_y_at_level(ramp_print_support_levels[0])
    - ramp_print_support_post_d/2;
ramp_print_support_base_y1 =
    ramp_print_y_at_level(
        ramp_print_support_levels[len(ramp_print_support_levels)-1]
    ) + ramp_print_support_post_d/2;

// One vertical print-space post with a sloped top that follows the underside
// of the ramp. The main 4 mm post stops 1 mm short of the ramp, then a narrow
// 0.8 mm breakaway neck makes real contact. This prevents Bambu Studio from
// treating the ramp as a floating cantilever while keeping removal practical.
module ramp_print_support_post(xc, level) {
    body_x0 = xc-ramp_print_support_post_w/2;
    neck_x0 = xc-ramp_print_support_neck_w/2;
    yc = ramp_print_y_at_level(level);
    y0 = yc-ramp_print_support_post_d/2;
    y1 = yc+ramp_print_support_post_d/2;
    ramp_z0 = ramp_print_z_at_y(y0);
    ramp_z1 = ramp_print_z_at_y(y1);
    body_z0 = max(ramp_z0-ramp_print_support_neck_h,0.1);
    body_z1 = max(ramp_z1-ramp_print_support_neck_h,0.1);

    // Main vertical post.
    hull() {
        translate([body_x0,y0,0])
            cube([
                ramp_print_support_post_w,
                ramp_print_support_slice_d,
                body_z0
            ]);
        translate([
            body_x0,
            y1-ramp_print_support_slice_d,
            0
        ])
            cube([
                ramp_print_support_post_w,
                ramp_print_support_slice_d,
                body_z1
            ]);
    }

    // Thin sloped-top breakaway neck. It overlaps the ramp by two 0.20 mm
    // layers so the slicer sees a true structural union rather than coplanar
    // contact, while the 0.8 mm neck remains easy to cut after printing.
    hull() {
        translate([
            neck_x0,
            y0,
            body_z0-ramp_print_support_slice_d
        ])
            cube([
                ramp_print_support_neck_w,
                ramp_print_support_slice_d,
                ramp_print_support_neck_h+
                    ramp_print_support_contact_overlap+
                    ramp_print_support_slice_d
            ]);
        translate([
            neck_x0,
            y1-ramp_print_support_slice_d,
            body_z1-ramp_print_support_slice_d
        ])
            cube([
                ramp_print_support_neck_w,
                ramp_print_support_slice_d,
                ramp_print_support_neck_h+
                    ramp_print_support_contact_overlap+
                    ramp_print_support_slice_d
            ]);
    }
}

module ramp_print_supports() {
    for (xc=ramp_print_support_x) {
        // Thin bed-connected rail. It passes through the print-space location
        // of the lower 40 mm wall, tying the removable supports to the model
        // without adding any geometry to the installed enclosure.
        translate([
            xc-ramp_print_support_post_w/2,
            ramp_print_support_base_y0,
            0
        ])
            cube([
                ramp_print_support_post_w,
                ramp_print_support_base_y1-ramp_print_support_base_y0,
                ramp_print_support_base_t
            ]);

        for (level=ramp_print_support_levels)
            ramp_print_support_post(xc,level);
    }
}

module universal_equipment_backplane_print() {
    union() {
        translate([
            0,
            backplane_print_origin_y,
            -equipment_backplane_y0
        ])
            rotate([90,0,0])
                universal_equipment_backplane();

        ramp_print_supports();
    }
}

// ---------- Detachable side/end pieces ----------

module side_wall_body(side="right") {
    // Outer end pieces close only the display's two outside edges. Internal
    // module seams remain open for HUB75/power cabling. The end profile now
    // follows the universal 54 mm shell instead of forcing the enclosure to
    // retain a 40 mm-depth side land for legacy end-piece compatibility.
    x0 = side == "right"
        ? module_w + side_panel_clearance
        : -side_t - side_panel_clearance;

    union() {
        // Preserve the lower 40 mm guide interface where the removable
        // backplane is captured by the base U-channels.
        translate([x0,service_base_y,enclosure_front_z])
            cube([
                side_t,
                universal_edge_transition_y0-service_base_y,
                equipment_backplane_lower_rear_z-enclosure_front_z
            ]);

        // Follow the same short 40 -> 54 mm depth transition used at the
        // backplane edge immediately above the guide towers.
        hull() {
            translate([
                x0,
                universal_edge_transition_y0-1,
                enclosure_front_z
            ])
                cube([
                    side_t,
                    1,
                    equipment_backplane_lower_rear_z-enclosure_front_z
                ]);

            translate([
                x0,
                universal_edge_transition_y1-1,
                enclosure_front_z
            ])
                cube([
                    side_t,
                    1,
                    universal_deep_rear_z-enclosure_front_z
                ]);
        }

        // Full-depth outer end through the universal equipment zone.
        translate([
            x0,
            universal_edge_transition_y1-1,
            enclosure_front_z
        ])
            cube([
                side_t,
                universal_deep_y1-universal_edge_transition_y1+1,
                universal_deep_rear_z-enclosure_front_z
            ]);

        // Match the universal deep return ramp.
        hull() {
            translate([
                x0,
                universal_deep_y1-1,
                enclosure_front_z
            ])
                cube([
                    side_t,
                    1,
                    universal_deep_rear_z-enclosure_front_z
                ]);

            translate([
                x0,
                universal_deep_ramp_end_y-backplane_top_band,
                enclosure_front_z
            ])
                cube([
                    side_t,
                    backplane_top_band,
                    equipment_backplane_top_rear_z-enclosure_front_z
                ]);
        }

        // Final top region remains flat and flush with the panel.
        translate([
            x0,
            universal_deep_ramp_end_y-backplane_top_band,
            enclosure_front_z
        ])
            cube([
                side_t,
                enclosure_top_y-universal_deep_ramp_end_y+backplane_top_band,
                equipment_backplane_top_rear_z-enclosure_front_z
            ]);
    }
}

module side_rail_end_stop(side="right") {
    // Integrated solid end stop on each detachable outer side. Each plug grows
    // inward exactly to the corresponding rod endpoint. In the side-piece
    // print orientation this cylinder grows vertically from the wall, so it
    // does not introduce a floating cantilever.
    if (side == "left") {
        translate([left_side_inner_x,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_end_stop_d,h=left_rail_end_stop_len);
    } else {
        translate([right_side_inner_x,hinge_axis_y,hinge_axis_z])
            rotate([0,-90,0])
                cylinder(d=hinge_end_stop_d,h=right_rail_end_stop_len);
    }
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
            side_rail_end_stop(side);
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

module hinge_rail_preview(length=hinge_rail_length) {
    translate([hinge_rail_start_x,hinge_axis_y,hinge_axis_z])
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

    // The three top-row closure screws are hardware, not printed geometry.
    // They are intentionally omitted from the motion preview because the panel
    // may only open after those fasteners are removed/loosened.
}


// Full four-module display preview. Adjacent modules mate directly across their
// seams; detachable side retainers are fitted only at the two outside edges.
module complete_direct_mount_assembly(open_angle=service_open_angle) {
    for (i=[0:3]) {
        translate([i*module_w,0,0]) {
            color([0.12,0.12,0.14])
                hinged_equipment_base();

            color([0.18,0.22,0.25])
                universal_equipment_backplane();

            color([0.62,0.62,0.66])
                hinge_rail_preview();

            color([0.25,0.25,0.28])
                moving_panel_at_angle(open_angle);
        }
    }

    // Only the outermost edges receive detachable end pieces. Internal module
    // seams use the self-mating base/backplane connector geometry.
    color([0.30,0.30,0.34]) {
        equipment_side("left");
        translate([3*module_w,0,0])
            equipment_side("right");
    }
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
