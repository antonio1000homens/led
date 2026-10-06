// Removable seam joiner for the four-panel enclosure.
//
// Each joiner spans one adjacent pair of 256 mm LED/enclosure modules and
// reuses the existing top-row panel/enclosure closure screws nearest the seam.
// No new holes are introduced in either the LED panel or enclosure.

hinge_part = undef;
include <direct_mount_enclosure.scad>;

panel_pair_joiner_t = 3.0;
panel_pair_joiner_outer_d = 13.0;
panel_pair_joiner_hole_d = panel_mount_hole_d;
panel_pair_joiner_print_gap = 8.0;

panel_pair_joiner_left_edge_offset =
    module_w - panel_mount_x[len(panel_mount_x)-1];
panel_pair_joiner_right_edge_offset = panel_mount_x[0];
panel_pair_joiner_hole_spacing =
    panel_pair_joiner_left_edge_offset + panel_pair_joiner_right_edge_offset;
panel_pair_joiner_length =
    panel_pair_joiner_hole_spacing + panel_pair_joiner_outer_d;

assert(
    abs(panel_pair_joiner_hole_spacing-15.8) < 0.01,
    "panel-pair joiner must track the measured 15.8 mm seam hole spacing"
);
assert(
    abs(panel_pair_joiner_hole_d-4.5) < 0.01,
    "panel-pair joiner must reuse the 4.5 mm closure-hole clearance"
);

module panel_pair_joiner() {
    r = panel_pair_joiner_outer_d/2;
    left_x = r;
    right_x = r + panel_pair_joiner_hole_spacing;
    yc = r;

    difference() {
        hull() {
            translate([left_x,yc,0])
                cylinder(d=panel_pair_joiner_outer_d,h=panel_pair_joiner_t,$fn=32);
            translate([right_x,yc,0])
                cylinder(d=panel_pair_joiner_outer_d,h=panel_pair_joiner_t,$fn=32);
        }

        for (xx=[left_x,right_x])
            translate([xx,yc,-0.2])
                cylinder(d=panel_pair_joiner_hole_d,h=panel_pair_joiner_t+0.4,$fn=24);
    }
}

module panel_pair_joiners_print(count=3) {
    assert(count >= 1);

    for (i=[0:count-1])
        translate([
            i*(panel_pair_joiner_length+panel_pair_joiner_print_gap),
            0,
            0
        ])
            panel_pair_joiner();
}

module panel_pair_joiner_installed(seam_x) {
    // Place the joiner on the accessible rear face of the shallow top wall.
    // Its two holes land exactly on the right-most closure hole of the module
    // to the left and the left-most closure hole of the module to the right.
    translate([
        seam_x-panel_pair_joiner_left_edge_offset-panel_pair_joiner_outer_d/2,
        panel_closure_y-panel_pair_joiner_outer_d/2,
        equipment_backplane_top_rear_z
    ])
        panel_pair_joiner();
}

module all_panel_pair_joiners_installed() {
    for (seam=[1:3])
        panel_pair_joiner_installed(seam*module_w);
}
