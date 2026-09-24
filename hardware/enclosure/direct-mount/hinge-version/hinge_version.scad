// Experimental 6 mm rail hinge variant for the direct-mount LED enclosure.
//
// This variant deliberately lives outside the production direct-mount part set.
// It reuses the *same* corrected panel mounting/locator coordinates as
// direct_mount_enclosure.scad, but changes the mechanical concept:
//
// 1. A thin fixed frame derived from the validated 08 mounting template stays
//    bolted to the LED panel.
// 2. Alternating printed hinge knuckles sit inside the panel footprint on the
//    lower template band; the hinge no longer extends below the enclosure.
// 3. A 6 mm metal rail/bar passes through 7.2 mm bores and becomes the hinge pin.
// 4. A complementary equipment tray/backplane swings down around that rail.
// 5. The moving tray has a deeper rear foot at the bottom so the closed display
//    gains a wider desk base.
// 6. The moving tray has a universal slot grid for PSU/controller/wiring mounts.
//
// The dimensions below are prototype defaults. The panel boss/locator positions
// are NOT duplicated here; they come directly from the validated main source.

part = "__library__";
include <../direct_mount_enclosure.scad>;

$fn = 48;

// ---------- Shared hinge geometry ----------

hinge_rail_d = 6;
hinge_bore_d = 7.2;         // same 0.6 mm radial clearance as the production rod bores
hinge_outer_d = 13;
hinge_axis_y = 16;          // fully inside the 0..128 mm panel/enclosure footprint
hinge_axis_z = 8;

// Keep the fixed knuckles away from the x=7.9/128/248.1 panel fastener columns.
// Moving knuckles alternate between them with ~2 mm axial clearance.
fixed_knuckles = [
    [20,28],
    [90,28],
    [160,28]
];

moving_knuckles = [
    [50,38],
    [120,38],
    [190,38]
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

// ---------- Fixed half: corrected 08 template + hinge ----------

fixed_template_t = 2;
fixed_band_h = 20;
fixed_side_w = 8;
fixed_hinge_root_y = hinge_axis_y - 6;
fixed_hinge_root_h = 12;
fixed_hinge_root_t = 8;

// Internal snap-latch prototype. The template carries the flexible tongue and
// rounded detent; the moving enclosure has a shallow catch pocket behind its
// front lip. Keep it away from the top centre panel fastener.
latch_x = 96;
latch_w = 12;
latch_root_y = module_h - fixed_band_h + 2;
latch_riser_y = 4;
latch_beam_len = 14;
latch_beam_z = 9.5;
latch_beam_t = 2.2;
latch_detent_r = 1.4;
latch_catch_clearance = 0.5;

module template_snap_latch() {
    // Riser lifts the latch beam from the 2 mm template into the enclosure.
    translate([
        latch_x-latch_w/2,
        latch_root_y,
        fixed_template_t
    ])
        cube([
            latch_w,
            latch_riser_y,
            latch_beam_z+latch_beam_t-fixed_template_t
        ]);

    // PETG cantilever beam. It flexes toward the panel (negative z) as the
    // enclosure's front lip passes over the rounded detent.
    translate([
        latch_x-latch_w/2,
        latch_root_y+latch_riser_y/2,
        latch_beam_z
    ])
        cube([
            latch_w,
            latch_beam_len,
            latch_beam_t
        ]);

    // Rounded detent at the free end reduces insertion force and snaps into the
    // enclosure catch pocket.
    translate([
        latch_x-latch_w/2,
        latch_root_y+latch_riser_y/2+latch_beam_len-latch_detent_r,
        latch_beam_z+latch_beam_t
    ])
        rotate([0,90,0])
            cylinder(r=latch_detent_r,h=latch_w);
}

module hinge_mount_pattern_template() {
    difference() {
        union() {
            // Exact same template envelope as production 08.
            cube([module_w,fixed_band_h,fixed_template_t]);
            translate([0,module_h-fixed_band_h,0])
                cube([module_w,fixed_band_h,fixed_template_t]);
            cube([fixed_side_w,module_h,fixed_template_t]);
            translate([module_w-fixed_side_w,0,0])
                cube([fixed_side_w,module_h,fixed_template_t]);

            // Each fixed knuckle is rooted into a local pad sitting on the
            // lower template band. Nothing projects below y=0.
            for (segment=fixed_knuckles) {
                translate([segment[0],fixed_hinge_root_y,0])
                    cube([segment[1],fixed_hinge_root_h,fixed_hinge_root_t]);
                rail_hinge_barrel(segment[0],segment[1]);
            }

            template_snap_latch();
        }

        // Reuse the physically validated six panel-boss centres directly.
        for (x=panel_mount_x)
            for (y=panel_mount_y)
                translate([x,y,-0.5])
                    cylinder(d=panel_mount_hole_d,h=fixed_hinge_root_t+1);

        // Reuse the current conservative moulded-locator clearances directly.
        for (x=panel_locator_x)
            for (y=panel_locator_y)
                translate([x,y,-0.5])
                    cylinder(d=panel_locator_clearance_d,h=fixed_hinge_root_t+1);
    }
}

// ---------- Moving half: equipment enclosure / service tray ----------

// Closed-position coordinates: this tray sits behind the LED panel. The tray is
// open toward the LED board; its solid equipment plate is at the rear.
service_x = backplane_edge_inset;
// Keep the moving tray entirely within the nominal panel footprint. The hinge
// itself is now internal at y=16 mm rather than hanging below the panel.
service_y = backplane_edge_inset + 1.0;
service_w = backplane_w;
service_h = backplane_h - 1.0;

service_front_z = 12;       // front lip of tray, near the LED board
service_back_z = 42;        // inside face of equipment mounting plate
service_plate_t = 3;
service_wall = 16;

// Additional rearward base extension at the lower edge. In the closed position
// this gives a ~60 mm maximum rear depth and a much wider desk footprint.
base_rear_z = 60;
base_beam_t = 6;
base_y_h = 18;
base_rib_w = 8;

// Middle-enclosure shape and cable routing.
//
// Keep the lower portion full-width because this is where inter-panel wiring
// now runs. Above the wiring zone the enclosure tapers inward on both sides,
// leaving more clearance between neighbouring enclosures.
lower_wiring_zone_h = 52;
upper_side_inset = 8;

// Panel-to-panel cables must not be captured by the moving enclosure. Each
// lower side therefore has a U-shaped notch that is OPEN toward the LED panel
// (service_front_z). When the tray swings down, it moves away from the fixed
// cable rather than dragging the cable through a closed hole.
side_cable_notch_y = 30;
side_cable_notch_depth = 22;
side_cable_notch_corner_r = 4;
side_cable_notch_center_y = service_y + service_wall + side_cable_notch_y/2;

// Universal equipment slots through the rear mounting plate.
equipment_slot_len = 16;
equipment_slot_w = 4.2;
equipment_slot_x = [28,64,100,136,172,208,236];
equipment_slot_y = [30,54,78,102];

module equipment_slot_2d(len=equipment_slot_len,w=equipment_slot_w) {
    hull() {
        translate([-(len-w)/2,0]) circle(d=w);
        translate([(len-w)/2,0]) circle(d=w);
    }
}

module service_outline_2d() {
    // Full-width through the lower wiring zone, then continuously narrower
    // toward the top. A taper avoids a sharp external shoulder between modules.
    polygon(points=[
        [service_x, service_y],
        [service_x+service_w, service_y],
        [service_x+service_w, service_y+lower_wiring_zone_h],
        [service_x+service_w-upper_side_inset, service_y+service_h],
        [service_x+upper_side_inset, service_y+service_h],
        [service_x, service_y+lower_wiring_zone_h]
    ]);
}

module service_wall_ring_2d() {
    difference() {
        service_outline_2d();
        offset(delta=-service_wall)
            service_outline_2d();
    }
}

module side_cable_notch(x0) {
    assert(side_cable_notch_y > 2*side_cable_notch_corner_r);
    assert(side_cable_notch_depth > side_cable_notch_corner_r);

    // Open U-notch in the Y/Z side-wall plane. The mouth deliberately extends
    // beyond the front edge (toward the LED panel), while the two rear corners
    // are rounded to reduce cable abrasion and stress concentration.
    union() {
        translate([
            x0,
            side_cable_notch_center_y-side_cable_notch_y/2,
            service_front_z-1
        ])
            cube([
                service_wall+2,
                side_cable_notch_y,
                side_cable_notch_depth-side_cable_notch_corner_r+1
            ]);

        hull()
            for (yy=[
                side_cable_notch_center_y-(side_cable_notch_y/2-side_cable_notch_corner_r),
                side_cable_notch_center_y+(side_cable_notch_y/2-side_cable_notch_corner_r)
            ])
                translate([
                    x0,
                    yy,
                    service_front_z+side_cable_notch_depth-side_cable_notch_corner_r
                ])
                    rotate([0,90,0])
                        cylinder(r=side_cable_notch_corner_r,h=service_wall+2);
    }
}

module moving_hinge_barrels() {
    for (segment=moving_knuckles)
        // At y=16 the barrel overlaps the lower perimeter wall directly, so the
        // hinge is internal and needs no external/root extension below y=0.
        rail_hinge_barrel(segment[0],segment[1]);
}

module enclosure_latch_catch() {
    // Leave a shallow front lip (z=12..13.4) for the rounded detent to snap
    // behind. The pocket is internal and does not alter the external envelope.
    translate([
        latch_x-latch_w/2-latch_catch_clearance,
        latch_root_y+latch_riser_y/2+latch_beam_len-2*latch_detent_r-latch_catch_clearance,
        service_front_z+1.4
    ])
        cube([
            latch_w+2*latch_catch_clearance,
            2*latch_detent_r+2*latch_catch_clearance,
            5
        ]);
}

module service_tray_shell() {
    // The open face is at service_front_z. Equipment mounts to the inner face
    // of the rear plate at service_back_z.
    union() {
        // Rear equipment plate follows the tapered outline.
        translate([0,0,service_back_z])
            linear_extrude(height=service_plate_t)
                service_outline_2d();

        // Perimeter wall ring follows the same outline. The lower section stays
        // full-width for wiring; the upper side walls taper inward.
        translate([0,0,service_front_z])
            linear_extrude(height=service_back_z-service_front_z)
                service_wall_ring_2d();

        // Full-width rear foot beam.
        translate([
            service_x,
            service_y,
            base_rear_z-base_beam_t
        ])
            cube([service_w,base_y_h,base_beam_t]);

        // Four diagonal ribs connect the tray rear plate to the rear foot beam.
        for (xx=[
            service_x,
            service_x+80,
            service_x+160,
            service_x+service_w-base_rib_w
        ])
            hull() {
                translate([xx,service_y,service_back_z])
                    cube([base_rib_w,base_y_h,service_plate_t]);
                translate([xx,service_y,base_rear_z-base_beam_t])
                    cube([base_rib_w,base_y_h,base_beam_t]);
            }

        // Complementary hinge knuckles share the exact fixed-half axis.
        moving_hinge_barrels();
    }
}

module hinged_equipment_enclosure() {
    difference() {
        service_tray_shell();

        // Universal M3 / cable-tie slot grid. This deliberately avoids baking a
        // particular PSU size into the first physical prototype.
        for (xx=equipment_slot_x)
            for (yy=equipment_slot_y)
                translate([xx,yy,service_back_z-0.5])
                    linear_extrude(height=service_plate_t+1)
                        equipment_slot_2d();

        // Keep the larger equipment-plate cable slots in the same lower wiring
        // zone as the side notches rather than routing wiring back to the top.
        for (xx=[54,184])
            translate([xx,service_y+42,service_back_z-0.5])
                cube([18,6,service_plate_t+1]);

        // This part is the middle enclosure: matching U-shaped notches on both
        // lower sides let fixed panel-to-panel power/data cables remain in place
        // while the enclosure swings away from them.
        side_cable_notch(service_x-1);
        side_cable_notch(service_x+service_w-service_wall-1);

        // Internal catch pocket for the template-mounted snap latch.
        enclosure_latch_catch();
    }
}

// Rotate the moving enclosure around the real 6 mm rail for assembly previews.
// angle=0 is closed; positive angles swing the tray downward.
module hinged_equipment_enclosure_at_angle(angle=0) {
    translate([0,hinge_axis_y,hinge_axis_z])
        rotate([angle,0,0])
            translate([0,-hinge_axis_y,-hinge_axis_z])
                hinged_equipment_enclosure();
}

module hinge_rail_preview(length=232) {
    translate([12,hinge_axis_y,hinge_axis_z])
        rotate([0,90,0])
            cylinder(d=hinge_rail_d,h=length);
}

module hinge_version_assembly(open_angle=72) {
    color([0.25,0.25,0.28])
        hinge_mount_pattern_template();

    color([0.62,0.62,0.66])
        hinge_rail_preview();

    color([0.12,0.12,0.14])
        hinged_equipment_enclosure_at_angle(open_angle);
}

if (!is_undef(hinge_part)) {
    if (hinge_part == "fixed_template")
        hinge_mount_pattern_template();
    else if (hinge_part == "equipment_enclosure")
        hinged_equipment_enclosure();
    else if (hinge_part == "assembly")
        hinge_version_assembly();
    else
        assert(false,str("Unknown hinge_part: ",hinge_part));
}
