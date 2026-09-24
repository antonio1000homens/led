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
// 7. No integrated top latch is included in this print-first hinge prototype;
//    closure will be a separate support-free part after hinge fit is confirmed.
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
// Fully internal concealed edge hinge:
// - y=11.5 puts the 13 mm barrel envelope at y=5..18 mm, leaving a full
//   4.5 mm of enclosure/base material between the barrel and the y=0.5 outer
//   edge. The rail and both sets of knuckles therefore sit completely inside
//   the closed enclosure footprint rather than defining its bottom silhouette.
// - z=10.5 keeps the complete barrel behind the 2 mm fixed template.
// The moving front rim still begins at the pivot for opening clearance. A
// continuous lower apron runs to the normal y=0.5 enclosure edge, with only an
// internal front-quadrant sweep relief around the pivot.
hinge_axis_y = 11.5;
hinge_axis_z = 10.5;
hinge_radius = hinge_outer_d/2;
hinge_pocket_clearance = 0.6;
hinge_axial_clearance = 0.8;

// Keep BOTH fixed and moving knuckles away from the lower panel fastener and
// locator columns. Critical lower X positions are 7.9 / 26.704 / 128 /
// 229.296 / 248.1 mm. The centre screw therefore has a deliberately wider
// clear zone from x=118..136 mm for screw-head/tool access.
fixed_knuckles = [
    [36,24],   // x=36..60
    [92,26],   // x=92..118
    [166,28]   // x=166..194
];

moving_knuckles = [
    [62,28],   // x=62..90
    [136,28],  // x=136..164
    [196,24]   // x=196..220
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
fixed_hinge_root_y = hinge_axis_y-hinge_radius;
fixed_hinge_root_h = hinge_outer_d; // root follows the fully internal barrel envelope
fixed_hinge_root_t = 8;

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
// Outer/base edge matches the validated rear backplane lower edge.
service_base_y = backplane_edge_inset;

// The LED-facing/front wall begins on the hinge axis so opening motion still
// carries it away from the fixed template. A rear skirt added below extends to
// service_base_y, hiding the hinge inside the closed enclosure.
service_y = hinge_axis_y;
service_top_y = backplane_edge_inset + backplane_h;
service_w = backplane_w;
service_h = service_top_y - service_y;

// The lower apron reaches the normal outer/base edge. The front/lower quadrant
// around the internal pivot is relieved separately so the moving half can swing
// without the hinge or its clearance pocket protruding below the enclosure.
hinge_shroud_overlap_y = 0.8;
hinge_sweep_relief_back_z = hinge_axis_z + 0.6;

// The front rim closes almost flush against the 2 mm fixed template: 0.6 mm
// clearance avoids printed faces rubbing while keeping the hinge hidden inside.
service_close_clearance = 0.6;
service_front_z = fixed_template_t + service_close_clearance;

// Bottom stays deep enough for PSU/wiring; upper enclosure becomes much
// shallower/lighter. The rear equipment surface slopes between these depths.
service_back_z_bottom = 42;
service_back_z_top = 28;
service_plate_t = 3;
service_wall = 16;

// Additional rearward base extension at the lower edge. In the closed position
// this gives a ~60 mm maximum rear depth and a much wider desk footprint.
// The upper enclosure is intentionally much shallower than this lower/base zone.
base_rear_z = 60;
base_beam_t = 6;
base_y_h = 18;
base_rib_w = 8;

// Middle-enclosure shape and cable routing.
//
// Keep the lower portion full-width because this is where inter-panel wiring
// now runs. Above the wiring zone the enclosure tapers inward on both sides,
// leaving more clearance between neighbouring enclosures.
lower_wiring_zone_h = 46;
upper_side_inset = 8;
depth_taper_start_y = service_y + lower_wiring_zone_h;

function service_back_at_y(y) =
    y <= depth_taper_start_y
        ? service_back_z_bottom
        : service_back_z_bottom
          + (service_back_z_top-service_back_z_bottom)
            * (y-depth_taper_start_y)
            / (service_top_y-depth_taper_start_y);

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

// Dedicated ventilation is restricted to the tapered upper region. There are
// deliberately NO ventilation slots in the lower wiring/base area.
upper_vent_slot_len = 24;
upper_vent_slot_w = 5;
upper_vent_x = [48,88,128,168,208];
upper_vent_y = [84,101,118];

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

module service_depth_envelope() {
    // Lower equipment/base zone keeps full depth.
    translate([
        service_x-2,
        service_y,
        service_front_z
    ])
        cube([
            service_w+4,
            lower_wiring_zone_h+0.5,
            service_back_z_bottom+service_plate_t-service_front_z
        ]);

    // Upper envelope tapers continuously from the deep lower zone to the
    // shallower top. This trims both side walls and top wall.
    hull() {
        translate([
            service_x-2,
            depth_taper_start_y-0.5,
            service_front_z
        ])
            cube([
                service_w+4,
                1,
                service_back_z_bottom+service_plate_t-service_front_z
            ]);

        translate([
            service_x-2,
            service_top_y-1,
            service_front_z
        ])
            cube([
                service_w+4,
                1,
                service_back_z_top+service_plate_t-service_front_z
            ]);
    }
}

module tapered_rear_equipment_plate() {
    // Flat/deep lower plate for PSU/power hardware.
    translate([
        service_x,
        service_y,
        service_back_z_bottom
    ])
        cube([
            service_w,
            lower_wiring_zone_h+0.5,
            service_plate_t
        ]);

    // Sloped upper equipment/ventilation plate. Width and depth both reduce
    // toward the top, lowering weight and rear protrusion.
    hull() {
        translate([
            service_x,
            depth_taper_start_y-0.5,
            service_back_z_bottom
        ])
            cube([
                service_w,
                1,
                service_plate_t
            ]);

        translate([
            service_x+upper_side_inset,
            service_top_y-1,
            service_back_z_top
        ])
            cube([
                service_w-2*upper_side_inset,
                1,
                service_plate_t
            ]);
    }
}

module fixed_knuckle_clearance_pockets() {
    // The fixed-template knuckles sit INSIDE the moving enclosure when closed.
    // Open each pocket toward the LED-facing side so the two printed halves can
    // be interleaved and the 6 mm rail inserted afterwards.
    pocket_d = hinge_outer_d + 2*hinge_pocket_clearance;

    for (segment=fixed_knuckles) {
        x0 = segment[0]-hinge_axial_clearance/2;
        len = segment[1]+hinge_axial_clearance;

        // Cylindrical running clearance around the fixed barrel.
        translate([x0,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=pocket_d,h=len);

        // Front-entry mouth also clears the local fixed root pad.
        translate([
            x0,
            0,
            service_front_z-0.6
        ])
            cube([
                len,
                hinge_axis_y+hinge_radius+hinge_pocket_clearance,
                fixed_hinge_root_t-service_front_z+1.2
            ]);
    }
}

module moving_hinge_barrels() {
    for (segment=moving_knuckles)
        // The rear half of each barrel keys directly into the lower apron.
        // The alternating fixed knuckles sit in pockets removed from the shell.
        rail_hinge_barrel(segment[0],segment[1]);
}

module moving_hinge_bores() {
    // The moving barrel is merged into the lower apron, so cut the rail bore
    // again after the union. Without this, overlapping apron material could
    // partially fill the nominal 7.2 mm passage.
    for (segment=moving_knuckles)
        translate([segment[0]-0.2,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_bore_d,h=segment[1]+0.4);
}

module hinge_front_sweep_relief() {
    // Concealed-hinge opening relief. Only the LED-facing/front-lower quadrant
    // of the apron is removed. The rear/bottom exterior remains continuous all
    // the way to service_base_y, so the closed enclosure has a flush base while
    // the 13 mm barrels remain entirely inside that outer envelope.
    translate([
        service_x-1,
        service_base_y-1,
        service_front_z-1
    ])
        cube([
            service_w+2,
            hinge_axis_y+hinge_radius+hinge_pocket_clearance-service_base_y+2,
            hinge_sweep_relief_back_z-service_front_z+1
        ]);
}

module lower_flush_hinge_shroud() {
    // Full-depth lower apron from the validated y=0.5 rear-enclosure edge to
    // just past the pivot line. The internal sweep relief is cut later from the
    // LED-facing side, so no hinge barrel or special boss protrudes below it.
    translate([
        service_x,
        service_base_y,
        service_front_z
    ])
        cube([
            service_w,
            service_y-service_base_y+hinge_shroud_overlap_y,
            service_back_z_bottom+service_plate_t-service_front_z
        ]);
}

module service_tray_shell_body() {
    // Open face is at service_front_z. The lower shell stays deep for PSU and
    // wiring; the top is trimmed to the shallower service_back_z_top envelope.
    union() {
        tapered_rear_equipment_plate();
        lower_flush_hinge_shroud();

        intersection() {
            translate([0,0,service_front_z])
                linear_extrude(
                    height=service_back_z_bottom
                           +service_plate_t-service_front_z
                )
                    service_wall_ring_2d();

            service_depth_envelope();
        }

        // Full-width rear foot beam.
        translate([
            service_x,
            service_base_y,
            base_rear_z-base_beam_t
        ])
            cube([
                service_w,
                base_y_h + (service_y-service_base_y),
                base_beam_t
            ]);

        // Four diagonal ribs connect the deep lower plate to the rear foot beam.
        for (xx=[
            service_x,
            service_x+80,
            service_x+160,
            service_x+service_w-base_rib_w
        ])
            hull() {
                translate([
                    xx,
                    service_y-0.5,
                    service_back_z_bottom
                ])
                    cube([base_rib_w,base_y_h+0.5,service_plate_t]);
                translate([
                    xx,
                    service_base_y,
                    base_rear_z-base_beam_t
                ])
                    cube([
                        base_rib_w,
                        base_y_h + (service_y-service_base_y),
                        base_beam_t
                    ]);
            }
    }
}

module hinged_equipment_enclosure() {
    difference() {
        union() {
            difference() {
                service_tray_shell_body();

                // Keep the enclosure/base outer edge flush while removing only
                // the internal front quadrant needed for hinge rotation.
                hinge_front_sweep_relief();

                // Recess the fixed hinge half inside the closed enclosure.
                fixed_knuckle_clearance_pockets();

            // Universal M3 / cable-tie slot grid. Use a long cutter so slots
            // pass through both the deep lower plate and the shallower sloped
            // upper plate.
            for (xx=equipment_slot_x)
                for (yy=equipment_slot_y)
                    translate([xx,yy,service_back_z_top-1])
                        linear_extrude(
                            height=service_back_z_bottom
                                   -service_back_z_top
                                   +service_plate_t+2
                        )
                            equipment_slot_2d();

            // Rounded ventilation slots only in the shallow tapered upper area.
            // No dedicated ventilation holes are cut in the lower/base zone.
            for (xx=upper_vent_x)
                for (yy=upper_vent_y)
                    translate([xx,yy,service_back_z_top-1])
                        linear_extrude(
                            height=service_back_z_bottom
                                   -service_back_z_top
                                   +service_plate_t+2
                        )
                            equipment_slot_2d(
                                upper_vent_slot_len,
                                upper_vent_slot_w
                            );

            // Larger wiring/ribbon slots remain in the deep lower wiring zone.
            for (xx=[54,184])
                translate([
                    xx,
                    service_y+40,
                    service_back_z_bottom-0.5
                ])
                    cube([18,6,service_plate_t+1]);

            // Matching U-shaped notches on both lower sides let fixed panel-to-
            // panel power/data cables remain in place while the enclosure opens.
            side_cable_notch(service_x-1);
                side_cable_notch(service_x+service_w-service_wall-1);

            }

            // Moving knuckles are integral to the moving shell. Only the FIXED
            // knuckle positions are pocketed above.
            moving_hinge_barrels();
        }

        // Preserve a clear 7.2 mm rail passage through apron/barrel overlaps.
        moving_hinge_bores();
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
