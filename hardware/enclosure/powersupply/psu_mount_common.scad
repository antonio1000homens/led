// Shared geometry for issue #166 PSU mounting experiments.
//
// This file models the PSU adapter in a LOCAL coordinate system centred on the
// six accessory bosses selected from the current universal backplane.
//
// Current master interface (PR #164):
//   absolute X = 80 / 176 mm
//   absolute Y = 62.5 / 86.5 / 110.5 mm
//
// Local adapter coordinates:
//   X = -48 / +48 mm
//   Y = -24 / 0 / +24 mm
//
// The backplane bosses are 7 mm OD x 4 mm high with 3.4 mm blind holes.
// The adapter uses shallow underside pockets around the boss bodies so that the
// plate positively registers on the boss grid instead of being positioned only
// by loose screw clearance.
//
// IMPORTANT: the PSU mounting-hole coordinates below remain placeholders until
// the real PSU has been measured.

$fn = 48;

// Documented PSU outer envelope.
psu_w = 110;
psu_h = 80;
psu_d = 37;

// Fit allowances.
psu_xy_clearance = 0.6;
plate_t = 3.2;
support_gap = 2.0;
wall_t = 2.4;
rail_h = 7.0;
lip_t = 1.6;
lip_inset = 1.8;

// Current six-boss accessory interface, local to its centre.
backplane_mount_x = [-48, 48];
backplane_mount_y = [-24, 0, 24];

backplane_boss_d = 7.0;
backplane_boss_h = 4.0;
backplane_boss_hole_d = 3.4;

// Adapter-side registration and screw clearance.
// 7.5 mm gives 0.25 mm radial clearance around the 7 mm PETG boss.
boss_pocket_d = 7.5;
boss_pocket_depth = 1.2;
adapter_screw_clearance_d = 3.6;

// Recess the M3 head/washer slightly on the equipment-facing side. Apart from
// making the fixing points obvious in the model, this keeps the screw head out
// of the PSU support plane.
adapter_screw_head_d = 7.0;
adapter_screw_head_depth = 0.8;

// Experimental PSU underside/back mounting points.
// Replace after measuring the real PSU.
psu_rear_mount_points = [
    [-42, -27],
    [ 42,  27]
];
psu_mount_pilot_d = 2.8;
locating_pin_d = 3.0;
locating_pin_h = 3.0;

// Adapter footprint. 118 x 82 mm contains the 110 x 80 mm PSU envelope while
// fitting around the current 96 x 48 mm six-boss grid.
adapter_w = 118;
adapter_h = 82;
corner_r = 3;

module rounded_plate(w=adapter_w, h=adapter_h, t=plate_t, r=corner_r) {
    linear_extrude(height=t)
        offset(r=r)
            square([w-2*r, h-2*r], center=true);
}

module backplane_interface_cutters(t=plate_t, extra=0.6) {
    for (xx = backplane_mount_x)
        for (yy = backplane_mount_y) {
            // M3 screw clearance through the adapter.
            translate([xx, yy, -extra/2])
                cylinder(d=adapter_screw_clearance_d, h=t+extra);

            // Visible equipment-side recess for the M3 screw head/washer.
            translate([xx, yy, t-adapter_screw_head_depth])
                cylinder(
                    d=adapter_screw_head_d,
                    h=adapter_screw_head_depth+extra/2
                );

            // Shallow socket on the BACK face of the adapter. The 7 mm boss
            // enters this pocket and provides positive X/Y registration.
            translate([xx, yy, -0.1])
                cylinder(d=boss_pocket_d, h=boss_pocket_depth+0.1);
        }
}

// Compatibility name retained for the experimental service tray.
module backplane_hole_cutters(t=plate_t, extra=0.6) {
    backplane_interface_cutters(t=t, extra=extra);
}

module psu_mount_pilot_cutters(t=plate_t, extra=0.6) {
    for (pt = psu_rear_mount_points)
        translate([pt[0], pt[1], -extra/2])
            cylinder(d=psu_mount_pilot_d, h=t+extra);
}

module base_adapter_plate(include_psu_pilots=false, w=adapter_w, h=adapter_h) {
    difference() {
        rounded_plate(w=w, h=h);
        backplane_interface_cutters(t=plate_t);
        if (include_psu_pilots)
            psu_mount_pilot_cutters();
    }
}

support_rail_x = 34;
support_rail_w = 5;

module integrated_support_rails(length=psu_h-12) {
    // Keep the support rails well inboard of the X=+/-48 enclosure fixing
    // columns. The earlier +/-45 rail position partially refilled all six
    // screw holes after the plate was cut.
    assert(
        support_rail_x + support_rail_w/2 <
            abs(backplane_mount_x[0]) - adapter_screw_head_d/2 - 0.5,
        "PSU support rails overlap enclosure screw access"
    );

    for (xx = [-support_rail_x, support_rail_x])
        translate([xx-support_rail_w/2, -length/2, plate_t-0.2])
            cube([support_rail_w, length, support_gap+0.2]);
}

module locating_pins() {
    for (pt = psu_rear_mount_points)
        translate([pt[0], pt[1], plate_t-0.2])
            cylinder(d=locating_pin_d, h=support_gap+locating_pin_h+0.2);
}

module backplane_interface_preview() {
    // In the assembled position the boss tip enters the adapter by
    // boss_pocket_depth, so the backplane wall sits this far behind z=0.
    wall_z = -(backplane_boss_h - boss_pocket_depth);

    // Small transparent patch of the actual backplane mounting surface.
    %translate([-adapter_w/2, -adapter_h/2, wall_z-3])
        cube([adapter_w, adapter_h, 3]);

    // All six bosses are shown at the current master spacing.
    for (xx = backplane_mount_x)
        for (yy = backplane_mount_y)
            %translate([xx, yy, wall_z])
                difference() {
                    cylinder(d=backplane_boss_d, h=backplane_boss_h);
                    translate([0,0,-0.1])
                        cylinder(d=backplane_boss_hole_d,
                                 h=backplane_boss_h+0.2);
                }
}

// Backwards-compatible preview name used by the initial option files.
module backplane_boss_preview() {
    backplane_interface_preview();
}

module screw_stop_boss(x, y, h=6, d=8, pilot_d=2.8) {
    difference() {
        translate([x, y, plate_t-0.2])
            cylinder(d=d, h=h+0.2);
        translate([x, y, plate_t-0.4])
            cylinder(d=pilot_d, h=h+0.6);
    }
}

module side_capture_rails(open_side="left") {
    side_y = psu_h/2 + psu_xy_clearance + wall_t/2;
    rail_len = psu_w + 2*psu_xy_clearance + 8;
    x0 = -rail_len/2;

    for (sy = [-1, 1]) {
        y0 = sy*side_y - wall_t/2;
        translate([x0, y0, plate_t-0.2])
            cube([rail_len, wall_t, rail_h+0.2]);

        lip_y = sy > 0
            ? side_y - wall_t/2 - lip_inset
            : -side_y - wall_t/2;
        translate([x0, lip_y, plate_t+rail_h-lip_t-0.1])
            cube([rail_len, wall_t+lip_inset, lip_t+0.1]);
    }

    stop_x = open_side == "left"
        ? psu_w/2 + psu_xy_clearance
        : -psu_w/2 - psu_xy_clearance - wall_t;
    translate([stop_x, -psu_h/2-psu_xy_clearance, plate_t-0.2])
        cube([wall_t, psu_h+2*psu_xy_clearance, rail_h+0.2]);
}

module corner_locators(h=5, arm=10, t=2.2) {
    for (sx=[-1,1], sy=[-1,1]) {
        x = sx*(psu_w/2 + psu_xy_clearance);
        y = sy*(psu_h/2 + psu_xy_clearance);

        translate([
            x - (sx < 0 ? t : 0),
            y - (sy < 0 ? arm : 0),
            plate_t-0.2
        ])
            cube([t, arm,h+0.2]);

        translate([
            x - (sx < 0 ? arm : 0),
            y - (sy < 0 ? t : 0),
            plate_t-0.2
        ])
            cube([arm,t,h+0.2]);
    }
}
