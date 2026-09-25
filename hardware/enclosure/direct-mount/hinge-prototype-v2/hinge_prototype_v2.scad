// Minimal support-free 6 mm hinge prototype for the verified direct-mount LED template.
//
// Mechanical intent for v2:
// - The EQUIPMENT ENCLOSURE remains stationary and vertical.
// - The LED panel + mounting template is the moving leaf and opens forward/down
//   like an oven door.
// - The stationary enclosure has a floor-standing base that projects 25 mm in
//   front of the LED plane.
// - In the closed position the LED/template bottom edge is 20 mm above the
//   ground; it is supported by the enclosure/base rather than by a template lip.
// - The moving template has only LOCAL hinge-root reinforcement. There is no
//   full-width lower tongue/lip to foul the opening sweep.

part = "__library__";
include <../direct_mount_enclosure.scad>;

$fn = 48;

// ---------- Shared hinge geometry ----------

hinge_pin_d = 6;
hinge_bore_d = 7.2;
hinge_outer_d = 14;
hinge_r = hinge_outer_d/2;
axial_gap = 1.0;

// Closed installed geometry.
//
// y=0 is the ground plane.
// The real panel/template begins 20 mm above ground.
// A 14 mm barrel then puts its centre 7 mm above that lower panel edge.
ground_clearance = 20;
hinge_axis_y = ground_clearance + hinge_r; // 27 mm above ground

// z=0 is the LED/template front plane; +Z is behind the LED board.
// A 14 mm barrel centred at z=9 occupies z=2..16 mm, entirely behind the
// normal 2 mm template sheet while remaining close to the panel.
hinge_axis_z = 9;

// Alternate the two knuckle sets and preserve the same critical X clearances
// used by the earlier prototype. In particular, x=118..136 stays open around
// the centre lower panel fastener/tool-access column.
template_knuckles = [
    [34,26],   // x=34..60
    [92,26],   // x=92..118
    [166,28]   // x=166..194
];

enclosure_knuckles = [
    [62,28],   // x=62..90
    [136,28],  // x=136..164
    [196,24]   // x=196..220
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
    // LOCAL reinforcement only. The root starts inside the existing 20 mm
    // lower template band and grows into the matching barrel segment.
    //
    // There is deliberately NO full-width tongue below the template. This
    // leaves the complete front/down opening arc clear.
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
            // Reuse the physically verified production template unchanged,
            // simply positioned at its real closed height above the ground.
            translate([0,ground_clearance,0])
                mount_pattern_template();

            for (segment=template_knuckles)
                moving_template_root(segment[0],segment[1]);
        }

        // One cutter keeps every moving knuckle exactly coaxial.
        translate([-0.2,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_bore_d,h=module_w+0.4);
    }
}

module moving_panel_template_print() {
    // Remove only the assembly ground offset for printing. The verified
    // template face therefore remains flat on Z=0 and its lower edge is Y=0.
    translate([0,-ground_clearance,0])
        moving_panel_template_installed();
}

// ---------- Stationary half: enclosure + floor base ----------

box_x = backplane_edge_inset;
box_w = backplane_w;

// Closed enclosure follows the panel height, but its base separately reaches
// the floor. The LED itself remains 15 mm above ground.
box_y = ground_clearance;
box_top_y = ground_clearance + backplane_h;
box_h = box_top_y-box_y;

box_front_z = 2.8;   // 0.8 mm behind the 2 mm template
box_depth = 24;
box_rear_z = box_front_z + box_depth;
box_wall = 3;
box_rear_t = 3;

// Floor-standing base.
// 25 mm projects in front of the LED/template plane, meeting the user's
// requested 2–3 cm forward support footprint.
base_front_extension = 25;
base_front_z = -base_front_extension;
base_rear_z = box_rear_z;
base_thickness_y = 5;

// Keep the stationary lower enclosure wall behind the barrel sweep. This
// leaves the front/lower quadrant clear for the moving panel/template.
lower_rear_wall_front_z = hinge_axis_z + hinge_r + 0.8;

module stationary_enclosure_shell() {
    union() {
        // Full-width floor base: this is what supports the closed display.
        translate([box_x,0,base_front_z])
            cube([
                box_w,
                base_thickness_y,
                base_rear_z-base_front_z
            ]);

        // Rear equipment plate continues down to the base so the enclosure is
        // structurally one floor-standing part.
        translate([
            box_x,
            base_thickness_y-0.5,
            box_rear_z-box_rear_t
        ])
            cube([
                box_w,
                box_top_y-(base_thickness_y-0.5),
                box_rear_t
            ]);

        // Side walls and top wall form the stationary vertical enclosure.
        translate([box_x,base_thickness_y-0.5,box_front_z])
            cube([
                box_wall,
                box_top_y-(base_thickness_y-0.5),
                box_depth
            ]);

        translate([
            box_x+box_w-box_wall,
            base_thickness_y-0.5,
            box_front_z
        ])
            cube([
                box_wall,
                box_top_y-(base_thickness_y-0.5),
                box_depth
            ]);

        translate([
            box_x,
            box_top_y-box_wall,
            box_front_z
        ])
            cube([box_w,box_wall,box_depth]);

        // The lower shelf starts BEHIND the hinge sweep. It anchors the
        // stationary knuckle roots without placing a lip in front of the pivot.
        translate([
            box_x,
            box_y,
            lower_rear_wall_front_z
        ])
            cube([
                box_w,
                box_wall+5,
                box_rear_z-lower_rear_wall_front_z
            ]);
    }
}

module stationary_enclosure_root(x0,len) {
    // The root grows from the supported rear lower shelf toward the hinge.
    // In the rear-face-down print orientation this remains continuously
    // connected to already-supported enclosure material.
    hull() {
        translate([
            x0,
            box_y,
            lower_rear_wall_front_z
        ])
            cube([len,box_wall+5,1]);

        translate([x0,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_outer_d,h=len);
    }
}

module stationary_enclosure_installed() {
    difference() {
        union() {
            stationary_enclosure_shell();

            for (segment=enclosure_knuckles)
                stationary_enclosure_root(segment[0],segment[1]);
        }

        // Continuous coaxial rail passage. Only the stationary knuckle/root
        // material intersecting this cutter is removed.
        translate([-0.2,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_bore_d,h=module_w+0.4);
    }
}

module stationary_enclosure_print() {
    // Large rear plate lies on the bed. The 25 mm front base extension becomes
    // a vertical, bed-connected wall in this orientation rather than a floating
    // horizontal cantilever.
    translate([0,0,box_rear_z])
        rotate([0,180,0])
            mirror([1,0,0])
                stationary_enclosure_installed();
}

// ---------- Assembly previews ----------

module hinge_pin_preview() {
    color("silver")
        translate([10,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_pin_d,h=236);
}

module ground_preview() {
    color([0.75,0.75,0.75,0.22])
        translate([-10,-0.6,-150])
            cube([module_w+20,0.5,220]);
}

module hinge_version_assembly(open_angle=0) {
    ground_preview();

    // Stationary enclosure/base never rotates.
    color([0.18,0.18,0.20])
        stationary_enclosure_installed();

    hinge_pin_preview();

    // The LED/template is the moving leaf. Negative X rotation sends the top
    // edge forward/down (toward -Z) like an oven door.
    color([0.75,0.75,0.78])
        translate([0,hinge_axis_y,hinge_axis_z])
            rotate([-open_angle,0,0])
                translate([0,-hinge_axis_y,-hinge_axis_z])
                    moving_panel_template_installed();
}

if (!is_undef(hinge_test_part)) {
    if (hinge_test_part == "moving_template")
        moving_panel_template_print();
    else if (hinge_test_part == "stationary_enclosure")
        stationary_enclosure_print();
    else if (hinge_test_part == "assembly")
        hinge_version_assembly(0);
    else if (hinge_test_part == "assembly_open")
        hinge_version_assembly(90);
    else
        assert(false,str("Unknown hinge_test_part: ",hinge_test_part));
}
