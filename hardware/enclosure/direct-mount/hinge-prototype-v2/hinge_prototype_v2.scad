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
// - Rear ventilation uses narrow vertical slots so the upright print only
//   needs to bridge short slot widths rather than long horizontal gaps.
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

// Rear ventilation slots.
// Narrow vertical openings are deliberately used so each slot only presents
// a short printable bridge at its top edge in the upright orientation.
vent_side_margin = 16;
vent_slot_w = 9;
vent_pitch = 22;
lower_vent_y = 16;
lower_vent_h = 32;
upper_vent_y = 72;
upper_vent_h = 48;

// Floor base supports the stationary enclosure.
base_front_extension = 25;
base_front_z = -base_front_extension;
base_rear_z = rear_z_bottom;
base_thickness_y = 5;

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
// A 12 mm vertical drop over the 10 mm enclosure depth creates a self-supporting
// ramp in the upright print instead of a flat 10 mm top cantilever.
template_back_z = 2.0;
top_template_clearance = 0.8;
top_link_front_z = template_back_z + top_template_clearance; // 2.8 mm
top_link_drop = 12;
top_link_front_h = 3;
top_link_rear_h = 3;

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
    // Cut fully through the rear wall/taper depth. Two vertically separated
    // slot zones leave a strong horizontal structural band around the 60 mm
    // transition where the rear wall changes from orthogonal to tapered.
    for (x=[
        box_x+vent_side_margin :
        vent_pitch :
        box_x+box_w-vent_side_margin-vent_slot_w
    ]) {
        translate([
            x,
            lower_vent_y,
            rear_z_top-box_rear_t-2
        ])
            cube([
                vent_slot_w,
                lower_vent_h,
                rear_z_bottom-rear_z_top+box_rear_t+4
            ]);

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
    // Full-width ramp/roof joining the 10 mm-deep top of the tapered rear
    // enclosure to the rear of the moving LED template.
    //
    // Both LEFT and RIGHT sides remain open below this roof.
    hull() {
        // Front landing: sits just behind the closed template's upper band.
        translate([
            box_x,
            box_top_y-top_link_drop,
            top_link_front_z
        ])
            cube([box_w,top_link_front_h,1.8]);

        // Rear landing: merges directly into the top of the sloping rear plate.
        translate([
            box_x,
            box_top_y-top_link_rear_h,
            rear_z_top-box_rear_t
        ])
            cube([box_w,top_link_rear_h,box_rear_t]);
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
    // while the vertical 40 mm lower rear wall and the upper 40 -> 10 mm
    // taper rise directly from the base and remain self-supporting.
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
