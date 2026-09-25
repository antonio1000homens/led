// Minimal support-free 6 mm hinge prototype for the verified direct-mount LED template.
//
// Mechanical intent:
// - The EQUIPMENT ENCLOSURE remains stationary and vertical.
// - The LED panel + mounting template is the moving leaf and opens forward/down.
// - This prototype models a MIDDLE enclosure: both left/right sides stay open
//   so HUB75 and power cables can pass directly between neighbouring panels.
// - The stationary enclosure stays orthogonal at 40 mm depth for the first
//   60 mm above the floor, then tapers to 10 mm depth at the top.
// - A self-supporting top roof links forward to the rear of the closed
//   LED-panel template.
// - The lower 60 mm equipment cavity is completely solid.
// - Rear ventilation exists only in the upper tapered section and uses very
//   narrow vertical slits for a fine mesh-like appearance.
// - Middle enclosures have lower side cheeks from the base to the 60 mm taper
//   start. Each cheek carries the continuous 6 mm hinge rod through a 7.2 mm
//   clearance bore; the upper sides remain open for inter-panel cabling.
// - The enclosure has a floor-standing base projecting 25 mm in front.
// - The LED/template lower edge is 20 mm above the floor when closed.
// - The moving template has only local hinge-root reinforcement; no lower lip.

part = "__library__";
include <../direct_mount_enclosure.scad>;

$fn = 48;

// ---------- Shared hinge geometry ----------

hinge_pin_d = 6;
hinge_bore_d = 7.2;
hinge_outer_d = 14;
hinge_r = hinge_outer_d/2;
axial_gap = 1.0;

ground_clearance = 20;
hinge_axis_y = ground_clearance + hinge_r; // 27 mm above floor

// z=0 is the LED/template front plane; +Z is behind the LED.
hinge_axis_z = 9;

template_knuckles = [
    [34,26],
    [92,26],
    [166,28]
];

enclosure_knuckles = [
    [62,28],
    [136,28],
    [196,24]
];

module hinge_barrel(x0,len) {
    translate([x0,hinge_axis_y,hinge_axis_z])
        rotate([0,90,0])
            difference() {
                cylinder(d=hinge_outer_d,h=len);
                translate([0,0,-0.2])
                    cylinder(d=hinge_bore_d,h=len+0.4);
            }
}

// ---------- Moving half: verified panel template ----------

module moving_template_root(x0,len) {
    // Local reinforcement only: start within the existing lower template band
    // and grow into the matching knuckle. No full-width lip is added.
    hull() {
        translate([x0,ground_clearance,0])
            cube([len,7,2]);

        translate([x0,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_outer_d,h=len);
    }
}

module moving_panel_template_installed() {
    difference() {
        union() {
            translate([0,ground_clearance,0])
                mount_pattern_template();

            for (segment=template_knuckles)
                moving_template_root(segment[0],segment[1]);
        }

        translate([-0.2,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_bore_d,h=module_w+0.4);
    }
}

module moving_panel_template_print() {
    // Verified template face remains flat on the build plate.
    translate([0,-ground_clearance,0])
        moving_panel_template_installed();
}

// ---------- Stationary MIDDLE enclosure ----------

box_x = backplane_edge_inset;
box_w = backplane_w;
box_y = ground_clearance;
box_top_y = ground_clearance + backplane_h;
box_h = box_top_y-box_y;

box_front_z = 2.8; // just behind the 2 mm moving template

// User-requested profile for the two middle enclosures.
//
// The lower rear wall is orthogonal/vertical at the full 40 mm depth until
// 60 mm above the floor. Only above that point does it begin tapering toward
// the 10 mm top depth.
enclosure_bottom_depth = 40;
enclosure_top_depth = 10;
taper_start_y = 60;
rear_z_bottom = box_front_z + enclosure_bottom_depth; // 42.8 mm
rear_z_top = box_front_z + enclosure_top_depth;       // 12.8 mm
box_rear_t = 3;

// Lower side-cheek thickness. Their Y extent is defined after the floor-base
// dimensions so they can overlap the base slightly for a robust manifold union.
lower_side_wall_t = 3;

// Upper-only rear ventilation.
//
// Keep the complete lower 60 mm rectangular equipment cavity solid. The tapered
// upper section gets a fine slotted grille: 3 mm openings on an 8 mm pitch,
// leaving 5 mm solid ribs between neighbouring openings.
//
// This gives a mesh-like visual density without the fragile intersections and
// tiny unsupported cells of a true printed mesh.
vent_side_margin = 12;
vent_slot_w = 3;
vent_pitch = 8;
upper_vent_y = taper_start_y + 10;
upper_vent_h = 50;

// Floor base supports the stationary enclosure.
base_front_extension = 25;
base_front_z = -base_front_extension;
base_rear_z = rear_z_bottom;
base_thickness_y = 5;

lower_side_wall_y0 = base_thickness_y-0.5;
lower_side_wall_y1 = taper_start_y;

// Small rear-edge margin used only to give the sloping rear plate a printable,
// robust edge. It does NOT form a left/right side wall.
rear_plate_start_y = base_thickness_y-0.5;
rear_plate_top_band = 1.5;

// Top closure/landing.
//
// The verified moving template is ~2 mm thick at its upper band. Bring the
// stationary enclosure forward to 0.8 mm behind that rear surface so the two
// parts visually/structurally close together without binding during rotation.
//
// IMPORTANT PRINTING RULE:
// The roof must NOT begin at the front/template side. In the upright print that
// creates a detached first roof layer and Bambu Studio reports a floating
// cantilever.
//
// Instead, the roof starts as a small anchor overlapping the already-printed
// tapered rear wall, then widens forward on successive layers until it becomes
// a complete top cap at the template junction.
template_back_z = 2.0;
top_template_clearance = 0.8;
top_link_front_z = template_back_z + top_template_clearance; // 2.8 mm
top_link_start_y = box_top_y - 18;
top_link_anchor_h = 2;
top_link_cap_h = 3;

function tapered_rear_z_at_y(y) =
    rear_z_bottom +
    (rear_z_top-rear_z_bottom) *
    ((y-taper_start_y)/(box_top_y-taper_start_y));

module middle_rear_plate_solid() {
    union() {
        // Orthogonal lower section: full 40 mm depth from the floor/base region
        // up to exactly 60 mm above the floor.
        translate([
            box_x,
            rear_plate_start_y,
            rear_z_bottom-box_rear_t
        ])
            cube([
                box_w,
                taper_start_y-rear_plate_start_y,
                box_rear_t
            ]);

        // Tapered upper section: begins only at 60 mm and reduces continuously
        // from 40 mm depth to the 10 mm top depth.
        hull() {
            translate([
                box_x,
                taper_start_y-1.0,
                rear_z_bottom-box_rear_t
            ])
                cube([box_w,2.0,box_rear_t]);

            translate([
                box_x,
                box_top_y-rear_plate_top_band,
                rear_z_top-box_rear_t
            ])
                cube([box_w,rear_plate_top_band,box_rear_t]);
        }
    }
}

module rear_ventilation_cutters() {
    // Cut only the tapered upper rear wall. Nothing below taper_start_y is
    // ventilated: the full 40 mm-deep lower equipment cavity remains solid.
    //
    // The 3 mm slits are intentionally much finer than the earlier 9 mm slots
    // while still being substantially more robust than a true lattice mesh.
    for (x=[
        box_x+vent_side_margin :
        vent_pitch :
        box_x+box_w-vent_side_margin-vent_slot_w
    ]) {
        translate([
            x,
            upper_vent_y,
            rear_z_top-box_rear_t-2
        ])
            cube([
                vent_slot_w,
                upper_vent_h,
                rear_z_bottom-rear_z_top+box_rear_t+4
            ]);
    }
}

module middle_rear_plate() {
    difference() {
        middle_rear_plate_solid();
        rear_ventilation_cutters();
    }
}

module middle_top_link() {
    // Full-width roof joining the tapered rear enclosure to the rear of the
    // closed LED template.
    //
    // Print sequence in the upright orientation:
    //   1. first roof layers overlap the existing tapered rear wall;
    //   2. each higher layer grows progressively forward;
    //   3. the final layers form a complete top cap from the template junction
    //      back to the 10 mm-deep rear edge.
    //
    // This avoids the old front-first geometry that Bambu Studio correctly
    // identified as a floating cantilever.
    anchor_rear_z = tapered_rear_z_at_y(top_link_start_y);

    hull() {
        // Bed-connected/previous-layer-connected rear anchor.
        translate([
            box_x,
            top_link_start_y,
            anchor_rear_z-box_rear_t
        ])
            cube([
                box_w,
                top_link_anchor_h,
                box_rear_t
            ]);

        // Complete top cap. Because this is the HIGH end of the hull rather
        // than the LOW end, all of it has progressively grown material below.
        translate([
            box_x,
            box_top_y-top_link_cap_h,
            top_link_front_z
        ])
            cube([
                box_w,
                top_link_cap_h,
                rear_z_top-top_link_front_z
            ]);
    }
}

module middle_floor_base() {
    // Full-width base. Above this 5 mm floor thickness, BOTH enclosure sides
    // are open for inter-panel cables.
    translate([box_x,0,base_front_z])
        cube([
            box_w,
            base_thickness_y,
            base_rear_z-base_front_z
        ]);
}

module middle_lower_side_walls() {
    difference() {
        union() {
            // Left lower cheek.
            translate([
                box_x,
                lower_side_wall_y0,
                box_front_z
            ])
                cube([
                    lower_side_wall_t,
                    lower_side_wall_y1-lower_side_wall_y0,
                    rear_z_bottom-box_front_z
                ]);

            // Right lower cheek.
            translate([
                box_x+box_w-lower_side_wall_t,
                lower_side_wall_y0,
                box_front_z
            ])
                cube([
                    lower_side_wall_t,
                    lower_side_wall_y1-lower_side_wall_y0,
                    rear_z_bottom-box_front_z
                ]);
        }

        // One continuous clearance bore through both side cheeks, concentric
        // with the 6 mm hinge rod. The printed clearance matches the hinge
        // barrels at 7.2 mm.
        translate([
            box_x-0.5,
            hinge_axis_y,
            hinge_axis_z
        ])
            rotate([0,90,0])
                cylinder(
                    d=hinge_bore_d,
                    h=box_w+1.0
                );
    }
}

module stationary_middle_enclosure_root(x0,len) {
    // Each stationary hinge knuckle rises directly from the floor base under
    // the pivot. In the upright print this is a continuous bed-supported root,
    // and it does not require a solid side wall or a floating lower shelf.
    hull() {
        translate([
            x0,
            base_thickness_y-0.5,
            hinge_axis_z-hinge_r
        ])
            cube([len,2,2*hinge_r]);

        translate([x0,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_outer_d,h=len);
    }
}

module stationary_middle_enclosure_installed() {
    difference() {
        union() {
            middle_floor_base();
            middle_rear_plate();
            middle_top_link();
            middle_lower_side_walls();

            for (segment=enclosure_knuckles)
                stationary_middle_enclosure_root(segment[0],segment[1]);
        }

        translate([-0.2,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_bore_d,h=module_w+0.4);
    }
}

module stationary_middle_enclosure_print() {
    // Print upright on the real floor base.
    //
    // Map installed +Y (physical up) to print +Z. Installed +Z (rearward)
    // becomes print -Y. The base is therefore a broad flat Z=0 contact patch,
    // while the vertical 40 mm lower rear wall, lower side cheeks and the
    // upper 40 -> 10 mm taper rise directly from the base and remain
    // self-supporting.
    rotate([90,0,0])
        stationary_middle_enclosure_installed();
}

// ---------- Assembly model coordinates ----------

module hinge_pin_preview(length=236,x0=10) {
    color("silver")
        translate([x0,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_pin_d,h=length);
}

module ground_preview(width=module_w) {
    color([0.75,0.75,0.75,0.22])
        translate([-10,-0.6,-70])
            cube([width+20,0.5,140]);
}

module one_middle_model(open_angle=0, x_offset=0, show_pin=true) {
    translate([x_offset,0,0]) {
        color([0.18,0.18,0.20])
            stationary_middle_enclosure_installed();

        if (show_pin)
            hinge_pin_preview();

        color([0.75,0.75,0.78])
            translate([0,hinge_axis_y,hinge_axis_z])
                rotate([-open_angle,0,0])
                    translate([0,-hinge_axis_y,-hinge_axis_z])
                        moving_panel_template_installed();
    }
}

module single_middle_assembly_model(open_angle=0) {
    ground_preview(module_w);
    one_middle_model(open_angle,0,true);
}

module two_middle_assembly_model(open_angle=0) {
    // Represent the two centre modules of the final four-panel display.
    // Both stationary enclosures are the SAME printable middle part and sit
    // one 256 mm panel pitch apart.
    ground_preview(2*module_w);

    one_middle_model(open_angle,0,false);
    one_middle_model(open_angle,module_w,false);

    // Preview one continuous 6 mm rail through both adjacent hinge sets.
    hinge_pin_preview(2*module_w-20,10);
}

// ---------- Presentation coordinates ----------
//
// Internal enclosure geometry deliberately uses the production panel convention:
// X=width, Y=panel height, Z=depth.
//
// OpenSCAD naturally treats Z as "up", so raw assembly files can look as though
// the Y axis is inverted/sideways. Rotate ONLY the assembly presentation by
// +90 degrees around X so physical +Y becomes screen/world +Z.
// Printable part coordinates are not changed.

module assembly_presentation(open_angle=0,two_middle=false) {
    rotate([90,0,0]) {
        if (two_middle)
            two_middle_assembly_model(open_angle);
        else
            single_middle_assembly_model(open_angle);
    }
}

if (!is_undef(hinge_test_part)) {
    if (hinge_test_part == "moving_template")
        moving_panel_template_print();
    else if (hinge_test_part == "middle_enclosure")
        stationary_middle_enclosure_print();
    else if (hinge_test_part == "assembly")
        assembly_presentation(0,false);
    else if (hinge_test_part == "assembly_open")
        assembly_presentation(90,false);
    else if (hinge_test_part == "two_middle_assembly")
        assembly_presentation(0,true);
    else if (hinge_test_part == "two_middle_assembly_open")
        assembly_presentation(75,true);
    else
        assert(false,str("Unknown hinge_test_part: ",hinge_test_part));
}
