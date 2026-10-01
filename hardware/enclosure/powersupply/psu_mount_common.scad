// Shared dimensions/helpers for issue #166 PSU mounting experiments.
//
// Coordinate system for all prototype mounts:
//   X = enclosure/backplane horizontal direction
//   Y = enclosure/backplane vertical direction
//   Z = away from the backplane into the equipment cavity
//
// The current enclosure provides a centred 96 x 64 mm rectangle of M3 bosses
// using X=80/176 and Y=60/124 from the canonical backplane coordinates.
// These prototype files translate that pattern to a local origin.
//
// IMPORTANT: the PSU mounting-hole coordinates below are deliberately marked as
// placeholders. The ~110 x 80 x 37 mm PSU envelope is documented in the
// enclosure README, but the PSU hole centres have not yet been measured.

$fn = 48;

// Measured/documented PSU outer envelope.
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

// Enclosure accessory-boss pattern, local to the centred adapter.
// Canonical absolute points are X=80/176 and Y=60/124.
backplane_mount_x = [-48, 48];
backplane_mount_y = [-32, 32];
backplane_hole_d = 3.6;  // M3 clearance in adapter

// Experimental PSU underside/back mounting points.
//
// Replace these two coordinates after measuring the real PSU. They are only
// defaults to make the prototypes immediately renderable and editable.
psu_rear_mount_points = [
    [-42, -27],
    [ 42,  27]
];
psu_mount_pilot_d = 2.8; // pilot for an M3 screw into printed plastic
locating_pin_d = 3.0;
locating_pin_h = 3.0;

// Adapter footprint. 118 x 82 mm remains centred on the 96 x 64 boss pattern
// and is close to the 84 mm usable height of the universal deep zone.
adapter_w = 118;
adapter_h = 82;
corner_r = 3;

module rounded_plate(w=adapter_w, h=adapter_h, t=plate_t, r=corner_r) {
    linear_extrude(height=t)
        offset(r=r)
            square([w-2*r, h-2*r], center=true);
}

module backplane_hole_cutters(t=plate_t, extra=0.6) {
    for (xx = backplane_mount_x)
        for (yy = backplane_mount_y)
            translate([xx, yy, -extra/2])
                cylinder(d=backplane_hole_d, h=t+extra);
}

module psu_mount_pilot_cutters(t=plate_t, extra=0.6) {
    for (pt = psu_rear_mount_points)
        translate([pt[0], pt[1], -extra/2])
            cylinder(d=psu_mount_pilot_d, h=t+extra);
}

module base_adapter_plate(include_psu_pilots=false, w=adapter_w, h=adapter_h) {
    difference() {
        rounded_plate(w=w, h=h);
        backplane_hole_cutters();
        if (include_psu_pilots)
            psu_mount_pilot_cutters();
    }
}

module integrated_support_rails(length=psu_h-12) {
    // Two low rails create an airflow/service gap without loose spacers.
    for (xx = [-psu_w/2+10, psu_w/2-10])
        translate([xx-2.5, -length/2, plate_t-0.2])
            cube([5, length, support_gap+0.2]);
}

module locating_pins() {
    for (pt = psu_rear_mount_points)
        translate([pt[0], pt[1], plate_t-0.2])
            cylinder(d=locating_pin_d, h=support_gap+locating_pin_h+0.2);
}

module psu_preview(z=plate_t+support_gap) {
    %translate([-psu_w/2, -psu_h/2, z])
        cube([psu_w, psu_h, psu_d]);
}

module backplane_boss_preview() {
    // Ghosted reference only; not part of exported geometry.
    for (xx = backplane_mount_x)
        for (yy = backplane_mount_y)
            %translate([xx, yy, -4])
                cylinder(d=7, h=4);
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
    // Rails run along X; PSU can slide in from left or right.
    // The small inward lip is intentionally shallow so it can bridge cleanly.
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

    // Closed-end stop opposite the insertion side.
    stop_x = open_side == "left"
        ? psu_w/2 + psu_xy_clearance
        : -psu_w/2 - psu_xy_clearance - wall_t;
    translate([stop_x, -psu_h/2-psu_xy_clearance, plate_t-0.2])
        cube([wall_t, psu_h+2*psu_xy_clearance, rail_h+0.2]);
}

module corner_locators(h=5, arm=10, t=2.2) {
    // Four low L-shaped guides centre the PSU ‰ÕĞ±•…Ù”µ½ÍĞÍ¥‘”Ù•¹Ñ¥±…Ñ¥½¸½Á•¸¸(€€€™½È€¡Íàõl´Ä°Åt°Íäõl´Ä°Åt¤ì(€€€€€€€à€ôÍà¨¡ÁÍÕ}Ü¼È€¬ÁÍÕ}áå}±•…É…¹”¤ì(€€€€€€€ä€ôÍä¨¡ÁÍÕ} ¼È€¬ÁÍÕ}áå}±•…É…¹”¤ì((€€€€€€€ÑÉ…¹Í±…Ñ”¡l(€€€€€€€€€€€à€´€¡Íà€ğ€À€üĞ€è€À¤°(€€€€€€€€€€€ä€´€¡Íä€ğ€À€ü…É´€è€À¤°(€€€€€€€€€€€Á±…Ñ•}Ğ´À¸È(€€€€€€€t¤(€€€€€€€€€€€Õ‰”¡mĞ°…É´± ¬À¸Ét¤ì((€€€€€€€ÑÉ…¹Í±…Ñ”¡l(€€€€€€€€€€€à€´€¡Íà€ğ€À€ü…É´€è€À¤°(€€€€€€€€€€€ä€´€¡Íä€ğ€À€üĞ€è€À¤°(€€€€€€€€€€€Á±…Ñ•}Ğ´À¸È(€€€€€€€t¤(€€€€€€€€€€€Õ‰”¡m…É´±Ğ± ¬À¸Ét¤ì(€€€ô)ô