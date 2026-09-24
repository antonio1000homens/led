// Experimental 6 mm rail hinge variant for the direct-mount LED enclosure.
//
// This variant deliberately lives outside the production direct-mount part set.
// It reuses the *same* corrected panel mounting/locator coordinates as
// direct_mount_enclosure.scad, but changes the mechanical concept:
//
// 1. A thin fixed frame derived from the validated 08 mounting template stays
//    bolted to the LED panel.
// 2. Alternating printed hinge knuckles are integrated below that frame.
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
hinge_axis_y = -5.8;        // below nominal 0 mm panel edge; 0.7 mm barrel overlap into frame
hinge_axis_z = 8;

// Keep enough empty space at the ends for a 1000 mm rail across four 256 mm
// modules. A 1 m rail placed at global x ~= 12..1012 covers all knuckles.
fixed_knuckles = [
    [16,32],
    [96,32],
    [176,32]
];

moving_knuckles = [
    [50,44],
    [130,44],
    [210,30]
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
fixed_hinge_spine_h = 6;
fixed_hinge_spine_t = 8;

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

            // Full-width lower spine transfers hinge load into the template
            // without thickening the screw-bearing centre at y=7.9 mm.
            cube([module_w,fixed_hinge_spine_h,fixed_hinge_spine_t]);

            for (segment=fixed_knuckles)
                rail_hinge_barrel(segment[0],segment[1]);
        }

        // Reuse the physically validated six panel-boss centres directly.
        for (x=panel_mount_x)
            for (y=panel_mount_y)
                translate([x,y,-0.5])
                    cylinder(d=panel_mount_hole_d,h=fixed_hinge_spine_t+1);

        // Reuse the current conservative moulded-locator clearances directly.
        for (x=panel_locator_x)
            for (y=panel_locator_y)
                translate([x,y,-0.5])
                    cylinder(d=panel_locator_clearance_d,h=fixed_hinge_spine_t+1);
    }
}

// ---------- Moving half: equipment enclosure / service tray ----------

// Closed-position coordinates: this tray sits behind the LED panel. The tray is
// open toward the LED board; its solid equipment plate is at the rear.
service_x = backplane_edge_inset;
// Raise the moving tray 1 mm above the nominal rear-frame bottom edge.
// The fixed hinge barrels reach y ~= 0.7 mm; y=1.5 gives ~0.8 mm closed
// clearance over those fixed knuckle sections while preserving top y=127.5.
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

// Middle-enclosure cable passages. This specific moving tray is intended for a
// module between two neighbours, so wiring must be able to continue through
// both the left and right side walls. Keep the dimensions parametric for easy
// adjustment after the first physical cable-fit test.
side_cable_gap_y = 44;
side_cable_gap_z = 20;
side_cable_gap_corner_r = 4;
side_cable_gap_center_y = service_y + service_h/2;
side_cable_gap_center_z = service_front_z + 15;

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

module side_cable_passage(x0) {
    assert(side_cable_gap_y > 2*side_cable_gap_corner_r);
    assert(side_cable_gap_z > 2*side_cable_gap_corner_r);

    // Rounded rectangular opening extruded through one side wall. Retaining a
    // frame around the opening preserves considerably more rigidity than
    // removing the side wall completely and avoids sharp cable-contact corners.
    hull()
        for (yy=[
            side_cable_gap_center_y-(side_cable_gap_y/2-side_cable_gap_corner_r),
            side_cable_gap_center_y+(side_cable_gap_y/2-side_cable_gap_corner_r)
        ])
            for (zz=[
                side_cable_gap_center_z-(side_cable_gap_z/2-side_cable_gap_corner_r),
                side_cable_gap_center_z+(side_cable_gap_z/2-side_cable_gap_corner_r)
            ])
                translate([x0,yy,zz])
                    rotate([0,90,0])
                        cylinder(r=side_cable_gap_corner_r,h=service_wall+2);
}

module moving_hinge_barrels() {
    for (segment=moving_knuckles) {
        rail_hinge_barrel(segment[0],segment[1]);

        // Give every moving knuckle a positive-volume root into the tray wall.
        // The root starts at z=9 mm: 1 mm behind the fixed spine (ends at z=8)
        // but low enough to overlap the circular barrel before it rises into
        // the moving tray wall at z=12 mm.
        translate([segment[0],-1.0,9.0])
            cube([segment[1],6.0,8.0]);
    }
}

module service_tray_shell() {
    // The open face is at service_front_z. Equipment mounts to the inner face
    // of the rear plate at service_back_z.
    union() {
        // Rear equipment plate.
        translate([service_x,service_y,service_back_z])
            cube([service_w,service_h,service_plate_t]);

        // Perimeter walls.
        translate([service_x,service_y,service_front_z])
            cube([service_w,service_wall,service_back_z-service_front_z]);
        translate([
            service_x,
            service_y+service_h-service_wall,
            service_front_z
        ])
            cube([service_w,service_wall,service_back_z-service_front_z]);
        translate([
            service_x,
            service_y+service_wall,
            service_front_z
        ])
            cube([
                service_wall,
                service_h-2*service_wall,
                service_back_z-service_front_z
            ]);
        translate([
            service_x+service_w-service_wall,
            service_y+service_wall,
            service_front_z
        ])
            cube([
                service_wall,
                service_h-2*service_wall,
                service_back_z-service_front_z
            ]);

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

        // Two larger cable-pass slots near the top of the mounting plate.
        for (xx=[54,184])
            translate([xx,service_h-17,service_back_z-0.5])
                cube([18,6,service_plate_t+1]);

        // This part is the middle enclosure: provide the same rounded cable
        // passage on both sides so power/data wiring can enter from either
        // neighbour and continue across the display.
        side_cable_passage(service_x-1);
        side_cable_passage(service_x+service_w-service_wall-1);
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
