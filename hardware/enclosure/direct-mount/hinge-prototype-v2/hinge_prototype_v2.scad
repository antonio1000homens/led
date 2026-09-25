// Print-first 6 mm rod hinge prototype for the verified direct-mount backplane.
//
// Goals:
// - reuse the production backplane geometry without copying its LED mount pattern;
// - keep the closed bottom flush: the hinge never projects below y=0.5 mm;
// - use simple rectangular hinge lugs, not horizontal round barrels, so slicers
//   do not see cantilevered/floating barrel regions;
// - keep the fixed base/tongue structurally attached to the production backplane;
// - print the moving enclosure rear-face-down so every major wall grows from bed.

part = "__library__";
include <../direct_mount_enclosure.scad>;

$fn = 48;

hinge_rod_d = 6;
hinge_bore_d = 7.2;
hinge_lug_size = 14;
hinge_r = hinge_lug_size/2;
hinge_clearance = 1.2;
hinge_axial_gap = 1.2;

// Bottom of every hinge lug is exactly y=0.5, the same as the verified
// production backplane. The 0.8 mm rear gap keeps moving lugs off the 16 mm
// production backplane even while a square lug rotates; the fixed tongue
// bridges that larger gap structurally.
hinge_axis_y = backplane_edge_inset + hinge_r;       // 7.5 mm
hinge_axis_z = depth + hinge_r*sqrt(2) + 1.0;        // 26.9 mm
hinge_y0 = hinge_axis_y - hinge_r;                   // 0.5 mm
hinge_z0 = hinge_axis_z - hinge_r;                   // 19.9 mm
hinge_z1 = hinge_axis_z + hinge_r;                   // 33.9 mm
hinge_sweep_r = hinge_r*sqrt(2) + hinge_clearance;   // square-lug rotation envelope

base_tongue_h = hinge_lug_size;
fixed_tongue_z0 = depth - 0.5;                       // overlap backplane by 0.5 mm
fixed_tongue_z1 = hinge_z1;                          // tongue supports full hinge depth

// Keep all lugs away from the measured lower screw/locator columns.
fixed_lugs = [
    [34, 24],
    [92, 24],
    [166, 28],
    [222, 18]
];

moving_lugs = [
    [60, 28],
    [120, 42],
    [196, 22]
];

module lug_block(x0, len) {
    translate([x0, hinge_y0, hinge_z0])
        cube([len, hinge_lug_size, hinge_lug_size]);
}

module lug_sweep_clearance(x0, len, radial_extra=0) {
    translate([x0-hinge_axial_gap/2, hinge_axis_y, hinge_axis_z])
        rotate([0,90,0])
            cylinder(
                r=hinge_sweep_r + radial_extra,
                h=len + hinge_axial_gap
            );
}

module continuous_rod_clearance() {
    translate([-0.5, hinge_axis_y, hinge_axis_z])
        rotate([0,90,0])
            cylinder(d=hinge_bore_d, h=module_w+1);
}

module lower_screw_tool_clearance() {
    for (x=panel_mount_x)
        translate([x, panel_mount_y[0], depth-0.6])
            cylinder(
                d=panel_mount_head_recess_d + 2,
                h=fixed_tongue_z1-depth+1.2
            );
}

module fixed_base_tongue() {
    difference() {
        translate([
            backplane_edge_inset,
            backplane_edge_inset,
            fixed_tongue_z0
        ])
            cube([
                backplane_w,
                base_tongue_h,
                fixed_tongue_z1-fixed_tongue_z0
            ]);

        lower_screw_tool_clearance();

        // Moving square lugs rotate in these circular sweep pockets. Because
        // the lugs alternate along X, the fixed tongue can remain continuous
        // everywhere else and still provide a broad flat base.
        for (segment=moving_lugs)
            lug_sweep_clearance(segment[0], segment[1]);

        // The moving enclosure has 3 mm side walls at the extreme left/right.
        // Remove only those narrow strips from the fixed tongue so the walls
        // can rotate through 90 degrees without clipping the otherwise flush
        // base. The remaining ~249 mm of tongue still forms the desk/base line.
        side_sweep_w = enclosure_wall_t + 0.8;
        translate([backplane_edge_inset-0.1, backplane_edge_inset-0.1, fixed_tongue_z0-0.1])
            cube([side_sweep_w, base_tongue_h+0.2, fixed_tongue_z1-fixed_tongue_z0+0.2]);
        translate([module_w-backplane_edge_inset-side_sweep_w, backplane_edge_inset-0.1, fixed_tongue_z0-0.1])
            cube([side_sweep_w+0.1, base_tongue_h+0.2, fixed_tongue_z1-fixed_tongue_z0+0.2]);

        continuous_rod_clearance();
    }
}

module fixed_backplane_hinge() {
    difference() {
        union() {
            backplane(false);
            fixed_base_tongue();
            for (segment=fixed_lugs)
                lug_block(segment[0], segment[1]);
        }
        continuous_rod_clearance();
    }
}

// ---------- Moving prototype enclosure ----------

enclosure_front_gap = 0.6;
enclosure_front_z = depth + enclosure_front_gap;
enclosure_rear_z = 45;
enclosure_back_t = 2.5;
enclosure_wall_t = 3;
enclosure_x0 = backplane_edge_inset;
enclosure_w = backplane_w;
enclosure_top_y = module_h-backplane_edge_inset;
// The rear panel overlaps the top of each moving hinge beam by 0.5 mm, but does
// not extend to the base. This keeps the base/hinge mechanics local to the
// alternating moving-lug X segments instead of creating a full-width sweep.
enclosure_lower_y = hinge_axis_y + hinge_r + 1.0;   // 15.5 mm

module moving_hinge_beam(x0, len) {
    beam_h = enclosure_lower_y - hinge_y0 + 0.5;
    // A rectangular beam from the hinge lug all the way to the rear panel.
    // With the enclosure printed rear-face-down, this is a continuous support
    // path from the build plate to the hinge rather than a floating cantilever.
    translate([x0, hinge_y0, hinge_z0])
        cube([
            len,
            beam_h,
            enclosure_rear_z + enclosure_back_t - hinge_z0
        ]);
}

module moving_enclosure_shell() {
    union() {
        // Rear panel deliberately starts above the base/hinge sweep zone.
        translate([
            enclosure_x0,
            enclosure_lower_y,
            enclosure_rear_z
        ])
            cube([
                enclosure_w,
                enclosure_top_y-enclosure_lower_y,
                enclosure_back_t
            ]);

        // Left/right walls close 0.6 mm behind the production backplane.
        for (xx=[enclosure_x0, enclosure_x0+enclosure_w-enclosure_wall_t])
            translate([xx, enclosure_lower_y, enclosure_front_z])
                cube([
                    enclosure_wall_t,
                    enclosure_top_y-enclosure_lower_y,
                    enclosure_rear_z-enclosure_front_z
                ]);

        // Top wall.
        translate([
            enclosure_x0,
            enclosure_top_y-enclosure_wall_t,
            enclosure_front_z
        ])
            cube([
                enclosure_w,
                enclosure_wall_t,
                enclosure_rear_z-enclosure_front_z
            ]);

        for (segment=moving_lugs)
            moving_hinge_beam(segment[0], segment[1]);
    }
}

module moving_enclosure() {
    difference() {
        moving_enclosure_shell();
        continuous_rod_clearance();
    }
}

// Rear-face-down is the intended slicer orientation. The rear panel is the
// first 2.5 mm of the print, the side/top walls grow directly from it, and each
// hinge beam grows continuously from the rear panel to the 6 mm rod bore.
module moving_enclosure_print() {
    translate([
        enclosure_x0 + enclosure_w,
        -hinge_y0,
        enclosure_rear_z + enclosure_back_t
    ])
        rotate([0,180,0])
            moving_enclosure();
}

module moving_at_angle(angle=0) {
    translate([0, hinge_axis_y, hinge_axis_z])
        rotate([angle,0,0])
            translate([0,-hinge_axis_y,-hinge_axis_z])
                moving_enclosure();
}

module rod_preview() {
    color([0.65,0.65,0.68])
        translate([0,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_rod_d,h=module_w);
}

module closed_assembly() {
    color([0.22,0.22,0.24]) fixed_backplane_hinge();
    color([0.08,0.08,0.09]) moving_at_angle(0);
    rod_preview();
}

module open_assembly(angle=75) {
    color([0.22,0.22,0.24]) fixed_backplane_hinge();
    color([0.08,0.08,0.09]) moving_at_angle(angle);
    rod_preview();
}

// Tiny rod-fit coupon. Both pieces start on the build plate, so two separate
// shells are intentional here and cannot be interpreted as floating regions.
module hinge_fit_coupon() {
    coupon_w = 86;
    split = 40;
    gap = 2;
    difference() {
        union() {
            cube([split,18,14]);
            translate([split+gap,0,0]) cube([coupon_w-split-gap,18,14]);
        }
        translate([-0.5,hinge_axis_y,7])
            rotate([0,90,0])
                cylinder(d=hinge_bore_d,h=coupon_w+1);
    }
}

if (!is_undef(prototype_part)) {
    if (prototype_part == "fixed") fixed_backplane_hinge();
    else if (prototype_part == "moving") moving_enclosure_print();
    else if (prototype_part == "closed") closed_assembly();
    else if (prototype_part == "open") open_assembly();
    else if (prototype_part == "coupon") hinge_fit_coupon();
    else assert(false, str("Unknown prototype_part: ", prototype_part));
}
