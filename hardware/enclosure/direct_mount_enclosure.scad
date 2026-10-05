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

// Physical rail/side-support contract. The detachable outer end pieces retain
// the 6 mm rod axially, then continue inward as hollow sleeves around the rod
// until they meet the nearest hinge barrel. The sleeve uses the same outer
// diameter as the hinge barrels and the same 7.2 mm running bore, so the rod is
// supported without becoming bonded to the side piece.
hinge_rail_start_x = 10;
hinge_rail_length = 236;
hinge_rail_end_x = hinge_rail_start_x + hinge_rail_length;
side_rod_sleeve_outer_d = hinge_outer_d;
side_rod_sleeve_bore_d = hinge_bore_d;

// Raise the complete installed moving leaf/hinge 20 mm above the previous
// 20 mm baseline. The print wrapper subtracts this installation offset, so the
// moving panel/template STL itself remains unchanged.
baseline_ground_clearance = 20;
hinge_install_lift = 20;
ground_clearance = baseline_ground_clearance + hinge_install_lift;
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

// Physical PETG fit: give the removable tongue a little more running room in
// the rear seat so it does not bow while being pushed home.
backplane_guide_clearance = 0.6;
backplane_guide_t = 1.2;
backplane_seat_depth = 2.0;
base_seat_y = 4.5;
equipment_backplane_y0 = base_seat_y - backplane_seat_depth;

// Two genuine U-channel side rails rise from the base. The physical-print
// feedback showed that 50 mm of engagement was unnecessarily long and prone
// to binding, so the removable backplane now uses a 40 mm guided insertion
// length and slides DOWN inside these channels rather than
// merely passing between solid guide towers. The 5 mm rail depth provides
// positive side capture while leaving the channel open toward the enclosure
// centre for top-down installation.
side_guide_h = 40;
side_guide_w = 5;
side_guide_clearance = 0.6;
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
// Take advantage of the extra 20 mm installed hinge height to extend the
// stationary base floor 20 mm toward the front without entering the moving
// panel's 0-90 degree service sweep.
base_front_extension = 20;
base_floor_front_z = service_front_z - base_front_extension;
base_floor_rear_z = base_rear_z;


// The old 20 mm hinge height needed a local front-floor relief for the open
// panel. At the raised 40 mm hinge height that relief no longer reaches the
// structural floor, so clamp it to the rear-seat edge and keep a full floor.
base_panel_clearance_y = min(
    base_seat_y,
    ground_clearance-hinge_axis_z
);
base_panel_clearance_z = hinge_axis_z+moving_plate_t+0.5;

side_guide_slot_front_z = backplane_slot_front_z;
side_guide_slot_back_z = backplane_slot_back_z;
side_guide_front_z = side_guide_slot_front_z - side_guide_wall_t;
side_guide_rear_z = side_guide_slot_back_z + side_guide_wall_t;

// The lower backplane extends into each U-channel and stops short of the outer
// spine by the running clearance. Above the 40 mm rails it returns to full width.
lower_backplane_edge_inset = side_guide_wall_t + side_guide_clearance;

// Small overlap band used to join the steeper ramp into the shallow vertical
// upper wall without creating a disconnected or unsupported top section.
backplane_top_band = 1.5;

// Generic M3 adapter pattern. Component-specific geometry belongs on adapters.
adapter_boss_d = 7;
adapter_hole_d = 3.4;
adapter_boss_h = 4;
include <psu_adapter_interface.scad>;
adapter_x = psu_adapter_all_columns;

// Universal equipment envelope for side-on vertical printing.
//
// The production backplane is printed with its 256 mm X dimension vertical.
// Above the 40 mm guide/insertion section, the shell therefore keeps one
// identical Y/Z cross-section across the complete X length. Only the narrowed
// lower insertion tongue differs at the two ends; its first layers receive a
// small print-only breakaway support in the manufacturing wrapper.
universal_deep_clear_depth = 54;
universal_deep_wall_t = equipment_backplane_t;
// The original 3 mm shoulder was the only bridge between the sliding tongue
// and the deep enclosure and proved too fragile in a physical print. Make it
// a real structural shelf instead of relying on the wall thickness alone.
universal_guide_shoulder_t = 8;

// The installed lower tongue remains narrow enough to slide inside the two
// U-channel guides. Above the guide tops the shell immediately uses the full
// service width; there is no longer an X-dependent edge-depth transition.
universal_deep_x0 = service_x;
universal_deep_x1 = service_x + service_w;
universal_deep_w = service_w;
universal_full_x0 = universal_deep_x0;
universal_full_x1 = universal_deep_x1;
universal_full_w = universal_deep_w;

// The full-depth equipment zone begins immediately above the guide section.
// The reinforced 8 mm shoulder now consumes part of that nominal height, so
// size the rear wall from the ACTUAL clear PSU envelope above the shoulder
// rather than from the guide height alone. This prevents the shorter 40 mm
// guides from pulling the upper taper down into the measured 80 mm PSU.
universal_deep_y0 = side_guide_y1;
universal_psu_h = 80;
universal_psu_vertical_clearance = 4;

// Preserve the full 80 mm PSU + 4 mm clearance above the reinforced
// shoulder, then use part of the extra height created by the raised hinge to
// restore the proven 12 mm upper return ramp. The remaining shallow closure
// wall is still comfortably tall enough for the lifted top-row closure screws.
universal_deep_y1 =
    universal_deep_y0 +
    universal_guide_shoulder_t +
    universal_psu_h +
    universal_psu_vertical_clearance;
universal_return_ramp_h = 12;
universal_deep_ramp_end_y =
    universal_deep_y1 + universal_return_ramp_h;
universal_top_flat_h =
    enclosure_top_y-universal_deep_ramp_end_y;

universal_deep_rear_z =
    enclosure_front_z + universal_deep_clear_depth + universal_deep_wall_t;
universal_deep_front_z =
    universal_deep_rear_z-universal_deep_wall_t;

// Centre all universal accessory bosses on the usable PSU cavity ABOVE the
// reinforced 8 mm shoulder. The five columns remain universal; the PSU dock
// uses only X=80/176 and its two unused central-column bosses must clear.
usable_y0 = universal_deep_y0 + universal_guide_shoulder_t;
usable_y1 = universal_deep_y1;
usable_yc = (usable_y0 + usable_y1)/2;
adapter_y = [for (dy=psu_adapter_mount_row_offsets) usable_yc+dy];
assert(abs(usable_y0-48.5)<0.01 && abs(usable_y1-132.5)<0.01 &&
       abs(usable_yc-90.5)<0.01,
       "PSU adapter interface must centre on the 84 mm usable cavity");

// Ventilation belongs on the enclosure's transition surfaces, NOT the rear
// mounting wall. Keep a solid rear skin for the adapter bosses and place
// horizontal slots across X on both the lower guide-to-depth shoulder and the
// upper return ramp. With installed X mapped to print Z these slots become
// vertical channels in the side-on print orientation.
// Use more, shorter vents with a 1 mm throat. Combined with the longer return
// ramp this avoids the broad finger-sized openings produced by the old steep
// 4 mm ramp while retaining distributed airflow.
vent_slot_len = 24;
vent_slot_gap = 10;
vent_slot_count = 7;
vent_slot_x0 =
    universal_deep_x0 +
    (universal_deep_w -
     (vent_slot_count*vent_slot_len +
      (vent_slot_count-1)*vent_slot_gap))/2;
vent_slot_y_h = 1.0;

// The reinforced lower shoulder is only 8 mm high, so use three rows rather
// than squeezing four rows into it. Keep 1.25 mm solid margins at both ends
// and 1.25 mm solid lands between each 1 mm opening.
bottom_ramp_vent_rows = 3;
bottom_ramp_vent_margin_y = 1.25;
bottom_ramp_vent_row_gap =
    (universal_guide_shoulder_t -
     2*bottom_ramp_vent_margin_y -
     bottom_ramp_vent_rows*vent_slot_y_h) /
    (bottom_ramp_vent_rows-1);
bottom_ramp_vent_y = [
    for (row=[0:bottom_ramp_vent_rows-1])
        universal_deep_y0 +
        bottom_ramp_vent_margin_y +
        row*(vent_slot_y_h+bottom_ramp_vent_row_gap)
];

// Four ventilation rows cross the restored 12 mm upper return ramp. Keep
// 1.5 mm solid margins at both ends and distribute the remaining material
// evenly between rows. The main rear mounting wall therefore stays solid.
top_ramp_vent_rows = 4;
top_ramp_vent_margin_y = 1.5;
top_ramp_vent_row_gap =
    (universal_return_ramp_h -
     2*top_ramp_vent_margin_y -
     top_ramp_vent_rows*vent_slot_y_h) /
    (top_ramp_vent_rows-1);
top_ramp_vent_y = [
    for (row=[0:top_ramp_vent_rows-1])
        universal_deep_y1 +
        top_ramp_vent_margin_y +
        row*(vent_slot_y_h+top_ramp_vent_row_gap)
];

// Self-mating side alignment. Each edge carries one pin and one socket.
// Right(A pin/B socket) mates Left(A socket/B pin) on another identical module.
connector_pin_d = 4;
connector_socket_d = 4.7;
connector_pin_len = 3;
connector_socket_depth = 3;

// Self-mating junctions are carried by the 40 mm U-channel side rails. They sit
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

// The detachable end caps now cover both the base and upper enclosure.
// In the upper enclosure, overlap the actual module edge by 10 mm. The side's
// inner face sits 0.9 mm outside that edge (0.4 mm panel clearance + 0.5 mm
// backplane inset), so the total local X reach from the side inner face is 10.9 mm.
side_upper_overlap = 10;
side_upper_intrusion_depth =
    side_upper_overlap + side_panel_clearance + backplane_edge_inset;
side_upper_core_clearance_x = 0.2;

// Copy the exact side silhouette of the live base from a thin edge slice rather
// than maintaining a second hand-authored approximation.
base_side_profile_slice_w = 0.2;

// Keep the upper module-to-module connector/release region free of the 10 mm
// return. The side's existing locating pin/socket geometry still occupies this
// zone and mates with the current backplane connector.
side_upper_connector_keepout_margin_y = 1.0;
side_upper_connector_keepout_margin_z = 1.0;

// Left outer end: fused/switched IEC C14 snap-in inlet.
//
// Keep this interface derived from the CURRENT detachable-side envelope rather
// than from the older base/backplane dimensions that originally accompanied
// PR #165. The measured connector is portrait: 44 mm high (installed Y) by
// 27 mm wide (installed Z).
c14_cutout_nominal_z = 27;
c14_cutout_nominal_y = 44;
c14_cutout_clearance_per_edge = 0.10;
c14_cutout_z =
    c14_cutout_nominal_z + 2*c14_cutout_clearance_per_edge;
c14_cutout_y =
    c14_cutout_nominal_y + 2*c14_cutout_clearance_per_edge;
c14_cutout_corner_r = 2.0;

// Keep the conservative visible-flange envelope from the original part family,
// rotated into portrait orientation. The measured 44 x 27 mm body sits inside it.
c14_flange_z = 30.5;
c14_flange_y = 50.0;

// Measured enclosure intrusion from the inside face of the side panel.
c14_body_depth = 30;

// Preserve the normal 3 mm side wall and recess only the hidden latch area.
// 1.4 mm remains the physical-fit tuning value for the spring-clip land.
c14_snap_panel_t = 1.4;
c14_snap_relief_margin = 2.0;
c14_mount_upper_margin_y = 3.0;
c14_side_material_depth = side_t + side_upper_intrusion_depth;

// Anchor the inlet to the present full-depth side region. This automatically
// follows the current base/enclosure format without reviving stale dimensions.
// The canonical left-side STL is regenerated from the standard part wrapper.
c14_center_y =
    universal_deep_y1 - c14_flange_y/2 - c14_mount_upper_margin_y;
c14_center_z =
    (enclosure_front_z + universal_deep_rear_z)/2;

c14_left_inner_x = -side_panel_clearance;
c14_left_outer_x = c14_left_inner_x - side_t;
c14_relief_y = c14_cutout_y + 2*c14_snap_relief_margin;
c14_relief_z = c14_cutout_z + 2*c14_snap_relief_margin;
c14_relief_corner_r =
    c14_cutout_corner_r + c14_snap_relief_margin;

// Occupied connector body envelope inside the enclosure. This is deliberately
// separate from the cutout/relief so collision tests include the full 30 mm
// projection behind the side wall.
c14_body_x0 = c14_left_inner_x;
c14_body_x1 = c14_body_x0 + c14_body_depth;
c14_body_y0 = c14_center_y - c14_cutout_nominal_y/2;
c14_body_y1 = c14_center_y + c14_cutout_nominal_y/2;
c14_body_z0 = c14_center_z - c14_cutout_nominal_z/2;
c14_body_z1 = c14_center_z + c14_cutout_nominal_z/2;

// Current placement leaves ~35.5 mm vertical clearance above the 14 mm rod
// sleeve and ~5.4 mm between the snap-relief edge and upper connector pad.
// The validator recomputes these relationships from the live geometry.

// Inner faces and axial lengths for the integrated rod retainers/sleeves.
// The capped portion stops the rod at X=10/246. From that point inward, the
// support becomes a hollow sleeve and continues exactly to the nearest barrel.
left_side_inner_x = -side_panel_clearance;
right_side_inner_x = module_w + side_panel_clearance;
left_rail_end_stop_len = hinge_rail_start_x - left_side_inner_x;
right_rail_end_stop_len = right_side_inner_x - hinge_rail_end_x;
left_side_rod_support_len = hinge_left_barrel_start - left_side_inner_x;
right_side_rod_support_len = right_side_inner_x - hinge_right_barrel_end;
left_side_rod_sleeve_len = hinge_left_barrel_start - hinge_rail_start_x;
right_side_rod_sleeve_len = hinge_rail_end_x - hinge_right_barrel_end;

side_connector_overlap = 0.4;
side_connector_bridge = side_panel_clearance + backplane_edge_inset;
side_connector_pin_len =
    connector_pin_len + side_connector_bridge + side_connector_overlap;

// Backplane/side alignment connector. The upper seam key is still useful for
// keeping adjacent removable backplanes/end plates aligned, but the old long
// Y/Z ramped "arms" are no longer needed now that the backplane prints side-on.
// Keep only a compact 10 mm-high local reinforcement around the final seated
// tab/slot position. Across X, each reinforcement tapers from native wall
// thickness to full connector depth so the late-print right edge grows
// gradually instead of appearing as an unsupported shelf.
top_connector_y = 71;
top_connector_release_travel = 15;
top_connector_slot_lower_span = 20;
top_connector_slot_bottom_y = top_connector_y - top_connector_slot_lower_span;
top_connector_slot_top_y =
    backplane_ramp_start_y + top_connector_release_travel + 0.2;

top_connector_overlap = 0.4;
top_connector_tab_len = connector_pin_len + top_connector_overlap;
top_connector_tab_root_len = 0.8;
top_connector_tab_h = 8;
top_connector_tab_t = 3.6;
top_connector_tab_slice_h = 1.0;

top_connector_pad_w = 8;
top_connector_pad_depth = 6.5;
top_connector_pad_inner_depth = equipment_backplane_t;
// Keep full connector depth across the actual 3 mm X-axis release slot plus
// 1 mm of structural continuation before tapering back to the native rear wall.
// This prevents the cavity-side lip around the left slot becoming a detached
// printable island after the slot is subtracted.
top_connector_pad_seam_w = connector_socket_depth + 1.0;
top_connector_pad_y_margin = 2;
top_connector_pad_y0 =
    top_connector_y - top_connector_tab_h/2 - top_connector_pad_y_margin;
top_connector_pad_y1 = backplane_ramp_start_y;
top_connector_pad_slice_w = 1.0;

// Centre the tab/slot through the compact reinforcement. This keeps material
// on both the cavity and rear sides of the 4.7 mm release slot.
top_connector_z =
    universal_deep_rear_z - top_connector_pad_depth/2;

top_side_pin_len = connector_pin_len + side_connector_overlap;
top_connector_support_margin = 0.8;
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
hinge_support_base_h =
    min(base_seat_y,base_panel_clearance_y)-service_base_y;
hinge_support_base_z = hinge_guard_front_z;
hinge_support_base_t = hinge_guard_t;

// Reinforce each removable-backplane U-channel without changing the slot itself.
// At the front, extend the existing 16 mm-high hidden-junction support forward
// until it overlaps the stationary hinge plate/guard. At the rear, add a side-
// view triangular buttress: 10 mm extra depth at the rail base tapering back to
// the native rail rear face at the top of the 40 mm guide.
side_guide_front_tie_z0 = hinge_guard_front_z;
side_guide_front_tie_h = junction_pad_h;
side_guide_rear_buttress_depth = 10;
side_guide_rear_buttress_slice_h = 1.0;
side_guide_rear_buttress_overlap = 0.4;

// Broad front-side floor gussets carry the vertical guide load into the base.
// Their triangular Y/Z section uses the available floor ahead of the guide;
// the upper tip overlaps the guide's front lip without entering its slot.
side_guide_floor_gusset_footprint = 26;
side_guide_floor_gusset_h = side_guide_h * 0.75;
side_guide_floor_gusset_overlap = 0.4;

// Use one rear reinforcement plane across the side-guide buttresses, the low
// stationary rear rail and the three removable backplane ribs. This gives the
// assembled rear edge a flush appearance without changing the backplane slot.
rear_reinforcement_flush_z =
    side_guide_rear_z + side_guide_rear_buttress_depth;
rear_guardrail_lip_front_z = side_guide_slot_back_z;
rear_guardrail_lip_rear_z = side_guide_rear_z;
rear_guardrail_shelf_front_z = rear_guardrail_lip_front_z;
rear_guardrail_shelf_rear_z = rear_reinforcement_flush_z;
rear_guardrail_y0 = service_base_y;
rear_guardrail_y1 = base_seat_y + side_guide_clearance;
rear_guardrail_shelf_top_y = equipment_backplane_y0 - 0.2;

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

        // Continue that same 16 mm-high support surface forward until it ties
        // directly into the stationary hinge plate/guard. This turns the guide
        // root and hinge plate into one continuous side load path instead of
        // leaving the junction pad cantilevered behind the hinge structure.
        translate([
            x0,
            side_guide_y0,
            side_guide_front_tie_z0
        ])
            cube([
                side_guide_w,
                side_guide_front_tie_h,
                junction_pad_front_z-side_guide_front_tie_z0+0.2
            ]);

        // Broad triangular support under the front of each vertical slider.
        // Its 26 mm floor footprint tapers to 75% of guide height and overlaps
        // the guide front lip by 0.4 mm. The whole wedge stays ahead of the
        // backplane slot; mirrored placement is supplied by x0 above.
        translate([
            x0,
            side_guide_y0,
            side_guide_front_z+side_guide_floor_gusset_overlap
        ])
            rotate([0,90,0])
                linear_extrude(height=side_guide_w)
                    polygon(points=[
                        [0,0],
                        [side_guide_floor_gusset_footprint+
                            side_guide_floor_gusset_overlap,0],
                        [0,side_guide_floor_gusset_h]
                    ]);

        // Rearward 10 mm triangular gusset in side view. The lower rail root
        // receives the full extra depth while the gusset tapers to the native
        // rear face at the guide top. The U-channel slot dimensions are
        // untouched because all added material is behind side_guide_rear_z.
        hull() {
            translate([
                x0,
                side_guide_y0,
                side_guide_rear_z-side_guide_rear_buttress_overlap
            ])
                cube([
                    side_guide_w,
                    side_guide_rear_buttress_slice_h,
                    side_guide_rear_buttress_depth+
                        side_guide_rear_buttress_overlap
                ]);

            translate([
                x0,
                side_guide_y1-side_guide_rear_buttress_slice_h,
                side_guide_rear_z-side_guide_rear_buttress_overlap
            ])
                cube([
                    side_guide_w,
                    side_guide_rear_buttress_slice_h,
                    side_guide_rear_buttress_overlap
                ]);
        }
    }
}

module rear_guardrail_shelf() {
    // Full-width low shelf extends the stationary base to the common rear plane
    // while staying below the seated lower edge of the removable backplane.
    translate([
        service_x,
        rear_guardrail_y0,
        rear_guardrail_shelf_front_z
    ])
        cube([
            service_w,
            rear_guardrail_shelf_top_y-rear_guardrail_y0,
            rear_guardrail_shelf_rear_z-rear_guardrail_shelf_front_z
        ]);

}

module rear_guardrail_rails() {
    // Continue the left/right side-guide rear lips inward until each reaches
    // the nearest outer rib tab. These remain behind the 0.6 mm tongue running
    // clearance, so they strengthen the base without narrowing the slide path.
    translate([
        rear_guardrail_left_x0,
        rear_guardrail_y0,
        rear_guardrail_lip_front_z
    ])
        cube([
            rear_guardrail_left_x1-rear_guardrail_left_x0,
            rear_guardrail_y1-rear_guardrail_y0,
            rear_guardrail_lip_rear_z-rear_guardrail_lip_front_z
        ]);

    translate([
        rear_guardrail_right_x0,
        rear_guardrail_y0,
        rear_guardrail_lip_front_z
    ])
        cube([
            rear_guardrail_right_x1-rear_guardrail_right_x0,
            rear_guardrail_y1-rear_guardrail_y0,
            rear_guardrail_lip_rear_z-rear_guardrail_lip_front_z
        ]);

    // Three narrow upright tabs rise into the printable flat centre of each
    // rib channel. The two outer tabs overlap the longer side rails by 0.4 mm;
    // the centre tab remains isolated so the centre span stays open.
    for (xc=transition_rib_centres)
        translate([
            xc-rear_guardrail_tab_w/2,
            rear_guardrail_y0,
            rear_guardrail_lip_front_z
        ])
            cube([
                rear_guardrail_tab_w,
                rear_guardrail_y1-rear_guardrail_y0,
                rear_guardrail_lip_rear_z-rear_guardrail_lip_front_z
            ]);

    // Short low spurs root the centre tab into the shelf on both sides of the
    // centre-rib socket without closing the full centre span.
    translate([
        rear_guardrail_center_left_x0,
        rear_guardrail_y0,
        rear_guardrail_lip_front_z
    ])
        cube([
            rear_guardrail_center_left_x1-rear_guardrail_center_left_x0,
            rear_guardrail_center_root_y1-rear_guardrail_y0,
            rear_guardrail_lip_rear_z-rear_guardrail_lip_front_z
        ]);

    translate([
        rear_guardrail_center_right_x0,
        rear_guardrail_y0,
        rear_guardrail_lip_front_z
    ])
        cube([
            rear_guardrail_center_right_x1-rear_guardrail_center_right_x0,
            rear_guardrail_center_root_y1-rear_guardrail_y0,
            rear_guardrail_lip_rear_z-rear_guardrail_lip_front_z
        ]);
}

module rear_guardrail() {
    union() {
        rear_guardrail_shelf();
        rear_guardrail_rails();
    }
}

module rear_rib_ground_clearance_cutters() {
    // Remove a vertical socket through the low rear shelf AND the complete
    // rear base-floor/seat band under each 24 mm continuous rib. Preserve the
    // #170 guardrail rails/tabs inside that socket; the rib's carved front/side
    // slots receive the complete retained guardrail shape during insertion.
    difference() {
        union() {
            for (xc=transition_rib_centres)
                translate([
                    xc-rear_rib_ground_pocket_w/2,
                    service_base_y-0.1,
                    rear_rib_ground_pocket_front_z
                ])
                    cube([
                        rear_rib_ground_pocket_w,
                        rear_rib_ground_pocket_y1-service_base_y+0.1,
                        rear_reinforcement_flush_z-rear_rib_ground_pocket_front_z+0.2
                    ]);
        }

        rear_guardrail_rails();
    }
}

module base_structural_body() {
    difference() {
        union() {
            // Low unobstructed structural floor.
            translate([service_x,service_base_y,base_floor_front_z])
                cube([
                    service_w,
                    base_seat_y-service_base_y,
                    base_floor_rear_z-base_floor_front_z
                ]);

            rear_guardrail();
            stationary_hinge_supports();
            stationary_hinge_barrels();
            lower_hinge_guard();

            // True U-channel side rails. The backplane engages inside both
            // channels for the first 50 mm of installed height.
            side_guide_channel("left");
            side_guide_channel("right");

            // Follow-up to #175: continue both guide lips toward the centre
            // until the first rib socket on each side, leaving that socket open
            // for the removable backplane's continuous reinforcement rib.
            side_guide_inward_extensions();

        }

        // Open three rear shelf pockets so the removable floor-reaching rib
        // spines can descend behind the #170 guardrails without collision.
        rear_rib_ground_clearance_cutters();

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
        if (base_panel_clearance_y < base_seat_y-0.01)
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

module top_backplane_connector_pad(side="left") {
    pad_h = top_connector_pad_y1-top_connector_pad_y0;
    seam_x0 = side == "left"
        ? service_x
        : service_x + service_w - top_connector_pad_seam_w;
    taper_full_x = side == "left"
        ? service_x + top_connector_pad_seam_w - top_connector_pad_slice_w
        : service_x + service_w - top_connector_pad_seam_w;
    taper_native_x = side == "left"
        ? service_x + top_connector_pad_w - top_connector_pad_slice_w
        : service_x + service_w - top_connector_pad_w;

    union() {
        // Full-depth local land around the seam. On the slotted left edge this
        // continues beyond the complete X depth of the release slot, keeping
        // both slot lips tied into the structural boss.
        translate([
            seam_x0,
            top_connector_pad_y0,
            universal_deep_rear_z-top_connector_pad_depth
        ])
            cube([
                top_connector_pad_seam_w,
                pad_h,
                top_connector_pad_depth
            ]);

        // Then taper back to the native 3 mm wall over the remaining edge
        // width. In the side-on manufacturing orientation this taper grows
        // progressively with print Z and avoids a new horizontal cantilever.
        hull() {
            translate([
                taper_full_x,
                top_connector_pad_y0,
                universal_deep_rear_z-top_connector_pad_depth
            ])
                cube([
                    top_connector_pad_slice_w,
                    pad_h,
                    top_connector_pad_depth
                ]);

            translate([
                taper_native_x,
                top_connector_pad_y0,
                universal_deep_rear_z-top_connector_pad_inner_depth
            ])
                cube([
                    top_connector_pad_slice_w,
                    pad_h,
                    top_connector_pad_inner_depth
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
        // Stepped vertical lower section. For the first 40 mm the plate is
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

// Replace the native shell above the guide section with one constant-width
// universal profile. The only reduced-width region is the lower insertion
// tongue that remains in backplane_shell_solid().
module universal_native_backplane_opening() {
    translate([
        service_x,
        universal_deep_y0-0.2,
        -1
    ])
        cube([
            service_w,
            enclosure_top_y-universal_deep_y0+0.4,
            universal_deep_rear_z+2
        ]);
}

module universal_deep_rear_shell() {
    slice_h = 1.0;

    // Full-width shoulder immediately ABOVE the guide tops. It bridges the
    // shallow insertion wall to the deep rear wall without intruding into the
    // 40 mm U-channel insertion envelope below universal_deep_y0.
    translate([
        universal_deep_x0,
        universal_deep_y0,
        equipment_backplane_front_z
    ])
        cube([
            universal_deep_w,
            universal_guide_shoulder_t,
            universal_deep_rear_z-equipment_backplane_front_z
        ]);

    // Full-width 54 mm equipment wall.
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

    // Full-width return ramp, repeated identically across X.
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

    // Final 11.5 mm closure wall remains flat/parallel to the LED panel.
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

module universal_backplane_shell_solid() {
    union() {
        difference() {
            backplane_shell_solid();
            universal_native_backplane_opening();
        }
        universal_deep_rear_shell();
    }
}

module horizontal_rounded_vent_cutter(x0,y0) {
    // Rounded slot ends avoid sharp stress raisers and make the openings read
    // as deliberate ventilation rather than large rectangular access holes.
    translate([
        x0 + vent_slot_len/2,
        y0 + vent_slot_y_h/2,
        equipment_backplane_top_front_z-2
    ])
        linear_extrude(
            height=universal_deep_rear_z-equipment_backplane_top_front_z+4
        )
            rounded_slot_2d(vent_slot_len,vent_slot_y_h);
}

module ramp_ventilation_cutters() {
    // Three rows of seven narrow rounded slots cross the reinforced lower
    // shoulder and four matching rows cross the restored 12 mm upper return
    // ramp. The full-depth rear mounting wall and final closure wall remain
    // unperforated.
    for (i=[0:vent_slot_count-1]) {
        xx = vent_slot_x0 + i*(vent_slot_len+vent_slot_gap);
        for (yy=bottom_ramp_vent_y)
            horizontal_rounded_vent_cutter(xx,yy);
        for (yy=top_ramp_vent_y)
            horizontal_rounded_vent_cutter(xx,yy);
    }
}


// ---------- Rear transition reinforcement ----------
// Three rear-only tapered ribs stiffen the fragile tongue-to-deep-shell
// transition without changing the slide-facing/front surface. Because installed
// X is the print Z axis, each rib grows and shrinks gradually across X so it
// never appears as an abrupt unsupported shelf during the side-on print.
transition_rib_centres = [64,128,192];
transition_rib_half_w = 12;
transition_rib_slice_w = 1.0;
transition_rib_depth =
    rear_reinforcement_flush_z-equipment_backplane_rear_z;
// Issue #182 physical assembly showed the ribs stopping about 1 mm above the stationary
// base even though their nominal CAD floor matched service_base_y. Compensate
// on the removable backplane only: extend the rib feet 1 mm below the nominal
// floor so they land on the real base when the fitted backplane sits ~1 mm high.
transition_rib_floor_extension = 1.0;
transition_rib_y0 = service_base_y - transition_rib_floor_extension;
transition_rib_y1 = universal_deep_y0 + universal_guide_shoulder_t;

// Functional slot between the 3 mm sliding tongue and each rear rib.
// The tongue already has 0.6 mm clearance before the slot begins; inside the
// slot the 1.2 mm stationary tab keeps another 0.6 mm to the rear rib wall.
transition_rib_channel_w = 18;
transition_rib_channel_flat_w = 12;
transition_rib_channel_taper_w =
    (transition_rib_channel_w-transition_rib_channel_flat_w)/2;
transition_rib_channel_front_z = side_guide_slot_back_z;
transition_rib_channel_depth =
    side_guide_wall_t + side_guide_clearance;
transition_rib_channel_rear_z =
    transition_rib_channel_front_z + transition_rib_channel_depth;
transition_rib_channel_y1 = universal_deep_y0 + 0.8;

// The three transition ribs are continuous solids from the reinforced shoulder
// down to the actual enclosure floor. The guardrail interface is a channel
// carved through the front of each rib rather than a separate lower spine.
// Matching rear-shelf pockets clear the complete rib footprint while preserving
// the #170 outer guardrails and centre/outer tabs in front of the pockets.
rear_rib_ground_pocket_w =
    2*transition_rib_half_w + 2*side_guide_clearance;
rear_rib_ground_pocket_front_z =
    equipment_backplane_rear_z - 0.4;
rear_rib_ground_pocket_y1 =
    rear_guardrail_y1 + 0.2;

// Extend the two outer stationary guardrails from the side guides to the
// nearest outer rib channel. Keep the middle span open; the existing three
// rib tabs remain the only raised guardrail features through the centre.
// A small overlap into each outer tab makes the side-to-rib load path manifold.
rear_guardrail_tab_w =
    transition_rib_channel_flat_w - 2*side_guide_clearance;
rear_guardrail_join_overlap = 0.4;
rear_guardrail_left_x0 = service_x;
rear_guardrail_left_x1 =
    transition_rib_centres[0] - rear_guardrail_tab_w/2
    + rear_guardrail_join_overlap;
rear_guardrail_right_x0 =
    transition_rib_centres[2] + rear_guardrail_tab_w/2
    - rear_guardrail_join_overlap;
rear_guardrail_right_x1 = service_x + service_w;

// Extend the two 40 mm side-guide capture lips inward as backup support for
// the removable backplane. Each extension intentionally stops at the OUTER
// edge of the nearest continuous-rib socket, so the first rib gap on each side
// stays completely open. A small overlap keeps the extension manifold with the
// existing 5 mm-wide side guide without changing the 3 mm + 0.6 mm slot fit.
side_guide_inward_extension_overlap = 0.4;
side_guide_left_extension_x0 =
    service_x + side_guide_w - side_guide_inward_extension_overlap;
side_guide_left_extension_x1 =
    transition_rib_centres[0] - rear_rib_ground_pocket_w/2;
side_guide_right_extension_x0 =
    transition_rib_centres[2] + rear_rib_ground_pocket_w/2;
side_guide_right_extension_x1 =
    service_x + service_w - side_guide_w
    + side_guide_inward_extension_overlap;

module side_guide_inward_extensions() {
    for (span=[
        [side_guide_left_extension_x0,side_guide_left_extension_x1],
        [side_guide_right_extension_x0,side_guide_right_extension_x1]
    ]) {
        // Front capture lip.
        translate([span[0],side_guide_y0,side_guide_front_z])
            cube([
                span[1]-span[0],
                side_guide_h,
                side_guide_wall_t
            ]);

        // Rear capture lip. The open Z gap between these two lips remains the
        // original backplane slot, including its 0.6 mm running clearance.
        translate([span[0],side_guide_y0,side_guide_slot_back_z])
            cube([
                span[1]-span[0],
                side_guide_h,
                side_guide_wall_t
            ]);
    }
}

// The centre guardrail tab needs a manifold root after the continuous-rib
// socket removes the shelf around it. Keep two short LOW spurs local to the
// centre rib only; they overlap the surrounding shelf by 0.4 mm and remain
// below the removable tongue.
rear_guardrail_center_root_overlap = 0.4;
rear_guardrail_center_root_y1 = rear_guardrail_shelf_top_y;
rear_guardrail_center_left_x0 =
    transition_rib_centres[1] - rear_rib_ground_pocket_w/2
    - rear_guardrail_center_root_overlap;
rear_guardrail_center_left_x1 =
    transition_rib_centres[1] - rear_guardrail_tab_w/2
    + rear_guardrail_center_root_overlap;
rear_guardrail_center_right_x0 =
    transition_rib_centres[1] + rear_guardrail_tab_w/2
    - rear_guardrail_center_root_overlap;
rear_guardrail_center_right_x1 =
    transition_rib_centres[1] + rear_rib_ground_pocket_w/2
    + rear_guardrail_center_root_overlap;

module transition_rear_rib(xc) {
    z0 = equipment_backplane_rear_z - 0.3;
    z1 = min(
        rear_reinforcement_flush_z,
        universal_deep_front_z
    );
    yh = transition_rib_y1-transition_rib_y0;
    shallow_d = 0.8;

    union() {
        hull() {
            translate([
                xc-transition_rib_half_w,
                transition_rib_y0,
                z0
            ])
                cube([
                    transition_rib_slice_w,
                    yh,
                    shallow_d
                ]);
            translate([
                xc-transition_rib_slice_w/2,
                transition_rib_y0,
                z0
            ])
                cube([
                    transition_rib_slice_w,
                    yh,
                    z1-z0
                ]);
        }

        hull() {
            translate([
                xc-transition_rib_slice_w/2,
                transition_rib_y0,
                z0
            ])
                cube([
                    transition_rib_slice_w,
                    yh,
                    z1-z0
                ]);
            translate([
                xc+transition_rib_half_w-transition_rib_slice_w,
                transition_rib_y0,
                z0
            ])
                cube([
                    transition_rib_slice_w,
                    yh,
                    shallow_d
                ]);
        }
    }
}

module transition_rear_ribs() {
    for (xc=transition_rib_centres)
        transition_rear_rib(xc);
}

module tapered_rib_guardrail_channel_cutter(xc) {
    // Installed X is print Z. Open the 2.4 mm-deep channel progressively over
    // 3 mm on each side, then keep a 12 mm flat centre. This avoids asking the
    // side-on print to create the complete rear-wall overhang in one layer.
    edge_slice_w = 0.5;
    tiny_depth = 0.1;
    // Issue #182: extend the rib-foot guardrail relief below the nominal floor. Carry the
    // stationary-guardrail relief through that complete extension so the last
    // millimetre of top-down insertion remains collision-free.
    y0 = transition_rib_y0-0.2;
    yh = transition_rib_channel_y1-y0+0.2;
    x0 = xc-transition_rib_channel_w/2;
    x1 = xc-transition_rib_channel_flat_w/2;
    x2 = xc+transition_rib_channel_flat_w/2;
    x3 = xc+transition_rib_channel_w/2;

    union() {
        hull() {
            translate([x0,y0,transition_rib_channel_front_z])
                cube([edge_slice_w,yh,tiny_depth]);
            translate([x1-edge_slice_w,y0,transition_rib_channel_front_z])
                cube([edge_slice_w,yh,transition_rib_channel_depth]);
        }

        translate([x1-edge_slice_w,y0,transition_rib_channel_front_z])
            cube([
                x2-x1+2*edge_slice_w,
                yh,
                transition_rib_channel_depth
            ]);

        hull() {
            translate([x2,y0,transition_rib_channel_front_z])
                cube([edge_slice_w,yh,transition_rib_channel_depth]);
            translate([x3-edge_slice_w,y0,transition_rib_channel_front_z])
                cube([edge_slice_w,yh,tiny_depth]);
        }
    }
}

module outer_guardrail_entry_cutter(
    xc,
    side="left",
    y1=rear_guardrail_y1
) {
    // Open the lower guardrail-height band from the selected rib edge into the
    // existing central channel. Each rib needs matching left/right entry relief
    // so the stationary base tab cannot catch on a closed half of the rib foot
    // during top-down insertion; the rest of the 24 mm rib stays continuous.
    x0 = side == "left"
        ? xc-transition_rib_half_w-0.2
        : xc+transition_rib_channel_flat_w/2-0.2;
    x1 = side == "left"
        ? xc-transition_rib_channel_flat_w/2+0.2
        : xc+transition_rib_half_w+0.2;

    y0 = transition_rib_y0-0.2;

    translate([
        x0,
        y0,
        rear_guardrail_lip_front_z-0.1
    ])
        cube([
            x1-x0,
            y1-y0+0.2,
            rear_guardrail_lip_rear_z-rear_guardrail_lip_front_z+
                side_guide_clearance+0.2
        ]);
}

module transition_rib_guardrail_channel_cutters() {
    for (xc=transition_rib_centres)
        tapered_rib_guardrail_channel_cutter(xc);

    // The stationary tabs are centred in the common rib channels. Keep both
    // low side entries open on the two outer ribs as well as the centre rib so
    // all three feet present the same unobstructed base-fitting slot.
    for (xc=[transition_rib_centres[0],transition_rib_centres[2]]) {
        outer_guardrail_entry_cutter(xc,"left");
        outer_guardrail_entry_cutter(xc,"right");
    }

    // Local low entries for the centre-tab root spurs.
    outer_guardrail_entry_cutter(
        transition_rib_centres[1],
        "left",
        rear_guardrail_center_root_y1+0.2
    );
    outer_guardrail_entry_cutter(
        transition_rib_centres[1],
        "right",
        rear_guardrail_center_root_y1+0.2
    );
}

module universal_equipment_backplane() {
    difference() {
        union() {
            universal_backplane_shell_solid();
            transition_rear_ribs();

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

        // Three shallow, tapered guardrail channels preserve the original
        // sliding tongue while allowing the stationary rear tabs to engage.
        transition_rib_guardrail_channel_cutters();

        // Three aligned top-row clearance holes let longer panel screws clamp
        // the moving panel/template to the stationary enclosure when closed.
        // These screws must be removed/loosened before opening the hinge.
        panel_closure_hole_cutters();

        // No rear cable/ribbon through-slots. Internal module seams remain
        // open for HUB75 and power cabling.
    }
}

// ---------- Backplane print orientation: 256 mm length vertical ----------
//
// Print the backplane on its left end so installed +X becomes print +Z.
// Because the shell above the guide section has one constant Y/Z profile
// across X, the return ramp is reproduced layer-by-layer. The narrowed lower
// insertion tongue starts above the bed and is intentionally left CLEAN in the
// STL; removable slicer-generated support is used instead of fused CAD support.
//
// Rotation [0,-90,0] maps installed +X -> print +Z and installed +Z -> print -X.
backplane_print_shift_x = universal_deep_rear_z + 1;
backplane_print_shift_y = -equipment_backplane_y0;
backplane_print_shift_z = -service_x;

module universal_equipment_backplane_print() {
    translate([
        backplane_print_shift_x,
        backplane_print_shift_y,
        backplane_print_shift_z
    ])
        rotate([0,-90,0])
            universal_equipment_backplane();
}

// ---------- Detachable side/end pieces ----------

module rounded_rect_x_cutter(
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
                        cylinder(r=corner_r,h=x_len);
}

module left_c14_panel_cutout() {
    rounded_rect_x_cutter(
        c14_left_outer_x-0.2,
        c14_side_material_depth+0.4,
        c14_center_y,
        c14_center_z,
        c14_cutout_y,
        c14_cutout_z,
        c14_cutout_corner_r
    );
}

module left_c14_snap_relief() {
    rounded_rect_x_cutter(
        c14_left_outer_x+c14_snap_panel_t-0.01,
        c14_side_material_depth-c14_snap_panel_t+0.21,
        c14_center_y,
        c14_center_z,
        c14_relief_y,
        c14_relief_z,
        c14_relief_corner_r
    );
}

module left_c14_body_envelope() {
    translate([
        c14_body_x0,
        c14_body_y0,
        c14_body_z0
    ])
        cube([
            c14_body_depth,
            c14_cutout_nominal_y,
            c14_cutout_nominal_z
        ]);
}

module side_upper_profile_solid(x0,x_len) {
    // Exact upper enclosure Y/Z profile, parameterised by X depth so the same
    // source drives both the 3 mm exterior end plate and the 10 mm inward return.
    union() {
        translate([
            x0,
            universal_deep_y0,
            enclosure_front_z
        ])
            cube([
                x_len,
                universal_deep_y1-universal_deep_y0,
                universal_deep_rear_z-enclosure_front_z
            ]);

        hull() {
            translate([
                x0,
                universal_deep_y1-1,
                enclosure_front_z
            ])
                cube([
                    x_len,
                    1,
                    universal_deep_rear_z-enclosure_front_z
                ]);

            translate([
                x0,
                universal_deep_ramp_end_y-backplane_top_band,
                enclosure_front_z
            ])
                cube([
                    x_len,
                    backplane_top_band,
                    equipment_backplane_top_rear_z-enclosure_front_z
                ]);
        }

        translate([
            x0,
            universal_deep_ramp_end_y-backplane_top_band,
            enclosure_front_z
        ])
            cube([
                x_len,
                enclosure_top_y-universal_deep_ramp_end_y+backplane_top_band,
                equipment_backplane_top_rear_z-enclosure_front_z
            ]);
    }
}

module base_side_profile_plate(side="right") {
    // Sample the ACTUAL base edge and stretch only that thin X slice to the
    // 3 mm detachable-side thickness. This makes the end cap follow future base
    // floor/gusset/guardrail changes automatically.
    source_x = side == "left"
        ? service_x
        : service_x + service_w - base_side_profile_slice_w;
    target_x = side == "left"
        ? -side_t - side_panel_clearance
        : module_w + side_panel_clearance;

    translate([target_x,0,0])
        scale([side_t/base_side_profile_slice_w,1,1])
            translate([-source_x,0,0])
                intersection() {
                    base_structural_body();
                    translate([
                        source_x,
                        service_base_y-1,
                        base_floor_front_z-20
                    ])
                        cube([
                            base_side_profile_slice_w,
                            enclosure_top_y-service_base_y+2,
                            rear_reinforcement_flush_z-base_floor_front_z+40
                        ]);
                }
}

module side_upper_connector_keepout(side="right") {
    // Preserve the existing top module-to-module connector and its vertical
    // release travel. The outer 3 mm end plate remains; only the 10 mm return
    // is removed from this rear connector zone.
    x0 = side == "left"
        ? left_side_inner_x-side_upper_core_clearance_x
        : right_side_inner_x-side_upper_intrusion_depth
            -side_upper_core_clearance_x;

    translate([
        x0,
        top_connector_slot_bottom_y-side_upper_connector_keepout_margin_y,
        universal_deep_rear_z-top_connector_pad_depth
            -side_upper_connector_keepout_margin_z
    ])
        cube([
            side_upper_intrusion_depth+2*side_upper_core_clearance_x,
            top_connector_slot_top_y-top_connector_slot_bottom_y
                +2*side_upper_connector_keepout_margin_y,
            top_connector_pad_depth+2*side_upper_connector_keepout_margin_z
        ]);
}

module side_upper_core_keepout() {
    // Only the universal upper shell can intersect this return. Use that live
    // shell directly instead of subtracting the complete base/backplane
    // assembly; connector geometry has its own larger keep-out below.
    for (dx=[
        -side_upper_core_clearance_x,
        0,
        side_upper_core_clearance_x
    ])
        translate([dx,0,0])
            universal_deep_rear_shell();
}

module side_upper_intrusion(side="right") {
    x0 = side == "left"
        ? left_side_inner_x
        : right_side_inner_x-side_upper_intrusion_depth;

    difference() {
        side_upper_profile_solid(x0,side_upper_intrusion_depth);
        side_upper_core_keepout();
        side_upper_connector_keepout(side);
    }
}

module side_wall_body(side="right") {
    x0 = side == "right"
        ? module_w + side_panel_clearance
        : -side_t - side_panel_clearance;

    union() {
        // Lower portion follows the current base edge profile exactly.
        base_side_profile_plate(side);

        // Upper exterior cover follows the enclosure profile.
        side_upper_profile_solid(x0,side_t);

        // Upper return reaches 10 mm past the actual enclosure edge while
        // avoiding the live module shell and connector/release geometry. The
        // canonical left/right side STLs are regenerated from this same source.
        side_upper_intrusion(side);
    }
}

module side_rod_retainer_sleeve(side="right") {
    // The outer support runs continuously from the detachable side wall to the
    // nearest hinge barrel. Only the segment overlapping the physical rod is
    // bored out; the short outer segment remains capped so the rod is retained
    // axially while still rotating freely inside the 7.2 mm clearance bore.
    if (side == "left") {
        difference() {
            translate([left_side_inner_x,hinge_axis_y,hinge_axis_z])
                rotate([0,90,0])
                    cylinder(
                        d=side_rod_sleeve_outer_d,
                        h=left_side_rod_support_len
                    );

            translate([
                hinge_rail_start_x-0.1,
                hinge_axis_y,
                hinge_axis_z
            ])
                rotate([0,90,0])
                    cylinder(
                        d=side_rod_sleeve_bore_d,
                        h=left_side_rod_sleeve_len+0.2
                    );
        }
    } else {
        difference() {
            translate([right_side_inner_x,hinge_axis_y,hinge_axis_z])
                rotate([0,-90,0])
                    cylinder(
                        d=side_rod_sleeve_outer_d,
                        h=right_side_rod_support_len
                    );

            translate([
                hinge_rail_end_x+0.1,
                hinge_axis_y,
                hinge_axis_z
            ])
                rotate([0,-90,0])
                    cylinder(
                        d=side_rod_sleeve_bore_d,
                        h=right_side_rod_sleeve_len+0.2
                    );
        }
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
            side_rod_retainer_sleeve(side);
            if (side == "right")
                right_side_pins();
            else
                left_side_pins();
        }

        if (side == "right")
            right_side_sockets();
        else {
            left_side_sockets();
            left_c14_panel_cutout();
            left_c14_snap_relief();
        }
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
