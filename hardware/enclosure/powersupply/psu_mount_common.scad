// Measured PSU envelope and local hardware geometry for issue #177.
//
// This file models the PSU adapter in a LOCAL coordinate system centred on the
// six accessory bosses selected from the current universal backplane.
//
// The shared psu_adapter_interface.scad supplies local row offsets and selects
// the two enclosure columns at X=80/176. The enclosure derives absolute rows
// from the usable cavity above its reinforced shoulder.
//
// The backplane bosses are 7 mm OD x 4 mm high with 3.4 mm blind holes.
// The adapter uses shallow underside pockets around the boss bodies so that the
// plate positively registers on the boss grid instead of being positioned only
// by loose screw clearance.
//
// Measured PSU geometry:
//   outer envelope = 110 x 80 mm
//   two mounting holes = diagonally opposed, each centre 3 mm from its adjacent
//   long and short edges. This gives local centres at +/-52, +/-37 mm.
// The measured diagonal was approximately 125 mm; the edge-derived coordinates
// imply 127.64 mm centre-to-centre, which is within the stated hand-measurement
// tolerance and is more useful for locating the holes on the tray.

$fn = 48;

// Documented PSU outer envelope.
psu_w = 110;
psu_h = 80;
psu_d = 37;

// Fit allowances.
psu_xy_clearance = 0.6;
plate_t = 4.2; // +1 mm keeps recessed dock screw heads below the slide surface.
support_gap = 2.0;
wall_t = 2.4;
rail_h = 7.0;
lip_t = 1.6;
lip_inset = 1.8;

// Current six-boss accessory interface, local to its centre.
backplane_mount_x = [-48, 48];
backplane_mount_y = [-19, 0, 19];

backplane_boss_d = 7.0;
backplane_boss_h = 4.0;
backplane_boss_hole_d = 3.4;

// Adapter-side registration and screw clearance.
// 7.5 mm gives 0.25 mm radial clearance around the 7 mm PETG boss.
boss_pocket_d = 7.5;
boss_pocket_depth = 1.2;
adapter_screw_clearance_d = 3.6;

// Recess the M3 button head fully below the dock's tray-facing surface. The
// 4.2 mm dock thickness preserves the same 1.2 mm structural web above the
// 1.2 mm rear registration pocket while allowing a 1.65 mm head to sit 0.15 mm
// below flush.
adapter_screw_head_d = 7.0;
adapter_screw_head_depth = 1.8;

// PSU underside mounting points after physical fit correction. Keep the
// horizontal X inset at 3 mm, but bring both diagonal holes 1 mm inward in Y:
// landscape bottom-left moves up and top-right moves down. This yields
// (-52,-36) and (+52,+36) mm.
psu_hole_edge_inset_x = 3;
psu_hole_edge_inset_y = 4;
psu_rear_mount_points = [
    [-(psu_w/2-psu_hole_edge_inset_x), -(psu_h/2-psu_hole_edge_inset_y)],
    [ +(psu_w/2-psu_hole_edge_inset_x), +(psu_h/2-psu_hole_edge_inset_y)]
];
psu_mount_pilot_d = 2.8;
psu_mount_boss_d = 8.0;

// Shared interface footprint. Keep the Y envelope below the physical 80 mm
// enclosure opening so helper/previews cannot silently reintroduce the old
// over-width geometry.
adapter_w = 118;
adapter_h = 79;
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

module raised_psu_mount_bosses(base_z=plate_t, h=support_gap) {
    // Two integral screw bosses support the PSU at exactly the same Z height
    // as the airflow rails. This avoids pulling the PSU down toward the plate
    // when the mounting screws are tightened.
    for (pt = psu_rear_mount_points)
        difference() {
            translate([pt[0], pt[1], base_z-0.2])
                cylinder(d=psu_mount_boss_d, h=h+0.2);
            translate([pt[0], pt[1], base_z-0.4])
                cylinder(d=psu_mount_pilot_d, h=h+0.6);
        }
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
