// Minimal support-free 6 mm hinge prototype for the verified direct-mount LED template.
//
// Mechanical intent:
// CI must keep both the 0-90 degree sweep-clearance test and the upright
// floating-layer proxy green for this hinge geometry.
// - The EQUIPMENT ENCLOSURE remains stationary and vertical.
// - The LED panel + mounting template is the moving leaf and opens forward/down.
// - Three stationary enclosure variants are provided:
//     * LEFT/controller end: outer closure wall with a MatrixPortal service
//       opening and integrated PCB standoffs;
//     * MIDDLE: both side planes stay open for hinge sweep and inter-panel cable;
//     * RIGHT/power end: solid outer closure wall plus rear grommet cable entry.
// - All outer walls sit primarily OUTSIDE the LED/template X footprint so they
//   do not obstruct the moving panel's hinge sweep.
// - The stationary enclosure stays orthogonal at 40 mm depth for the first
//   60 mm above the floor, then tapers to 10 mm depth at the top.
// - A self-supporting top roof links forward to the rear of the closed
//   LED-panel template.
// - The lower 60 mm equipment cavity is completely solid.
// - Rear ventilation exists only in the upper tapered section and uses very
//   narrow vertical slits for a fine mesh-like appearance.
// - The enclosure has a floor-standing base projecting 25 mm in front.
// - The LED/template lower edge is 20 mm above the floor when closed.
// - The moving template has only local hinge-root reinforcement; no lower lip.
// - The hinge axis is offset 19 mm behind the plate front, giving 10 mm radial
//   clearance between the closed plate back and the stationary barrel.
// - Stationary hinge roots approach the barrel from the rear, leaving the
//   forward/downward plate sweep corridor unobstructed.
// - A thin full-width stationary guard plate runs behind the hinge line on every
//   enclosure variant, shielding the lower opening when the LED/template closes.

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
//
// The previous 9 mm axis offset put the front of the 14 mm stationary barrel
// directly against the 2 mm moving plate. That left no practical sweep
// clearance and the stationary knuckle/root could block the plate as it opened.
//
// The earlier 7 mm gap was too tight around the stationary hinge block, but a
// 15 mm experiment moved the pivot so far rearward that the moving plate hit the
// 5 mm floor/base around 50 degrees. With the existing 20 mm closed floor
// clearance and 27 mm pivot height, 10 mm is the larger safe stand-off that
// still leaves clearance through the full 0-90 degree service arc.
//
// A 10 mm air gap between the back of the 2 mm moving plate and the front-most
// surface of the 14 mm hinge barrel places the hinge axis 19 mm behind the
// LED/template front plane. The lower plate edge remains roughly 1.75 mm above
// the top of the 5 mm floor/base at the lowest point of its rotation.
moving_plate_t = 2;
hinge_plate_clearance = 10;
hinge_axis_z = moving_plate_t + hinge_r + hinge_plate_clearance; // 19 mm

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
            cube([len,7,moving_plate_t]);

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

// ---------- Outer/end enclosure details ----------
//
// End walls are intentionally placed primarily OUTSIDE the 0..256 LED/template
// footprint. A small 0.4 mm overlap ties them into the base/rear/top enclosure
// geometry without recreating the side-wall hinge obstruction that was removed
// from the middle variant.
end_wall_t = 3;
end_wall_overlap = 0.4;
left_end_wall_x = box_x-end_wall_t+end_wall_overlap;
right_end_wall_x = box_x+box_w-end_wall_overlap;

// MatrixPortal S3 controller-end integration.
//
// Reuse the measured/validated PCB dimensions and hole offsets from
// direct_mount_enclosure.scad, but place the PCB entirely in the orthogonal
// lower cavity so all four standoffs terminate on the flat lower rear wall.
// The PCB stays parallel to the LED plane and its short USB/button edge
// protrudes through the LEFT outer service opening.
controller_pcb_x = -10.0;
controller_pcb_y = 8.0;
controller_pcb_rear_z = 31.5;
controller_pcb_t = 1.6;
controller_post_d = 8;
controller_post_h = (rear_z_bottom-box_rear_t)-controller_pcb_rear_z+0.3;
controller_hole_d = matrixportal_hole_d;

controller_mount_points = [
    [controller_pcb_x + matrixportal_hole_x1,
     controller_pcb_y + matrixportal_hole_y1],
    [controller_pcb_x + matrixportal_hole_x2,
     controller_pcb_y + matrixportal_hole_y1],
    [controller_pcb_x + matrixportal_hole_x1,
     controller_pcb_y + matrixportal_hole_y2],
    [controller_pcb_x + matrixportal_hole_x2,
     controller_pcb_y + matrixportal_hole_y2]
];

controller_service_y_margin = 4;
controller_service_z_min = controller_pcb_rear_z-controller_pcb_t-5;
controller_service_z_max = controller_pcb_rear_z+4;

// Rear mains/power-cable entry on the RIGHT end enclosure.
//
// 14 mm is a prototype default only. Match this to the PANEL CUT-OUT specified
// by the actual snap grommet before final printing.
power_grommet_hole_d = 14;
power_grommet_x = box_x+box_w-28;
power_grommet_y = 30;

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

// Full-width lower hinge guard.
//
// The LED/template lower edge sits 20 mm above the floor and the hinge barrel
// is centred at y=27 mm. Without a guard, the low front opening behind the
// closed panel remains exposed between the floor base and hinge line.
//
// Keep this plate on the STATIONARY enclosure, immediately behind the complete
// hinge-barrel envelope. It spans the full enclosure width on every variant,
// rises from the base to the hinge centreline, and stays 0.8 mm behind the
// moving/fixed barrel envelope so the LED/template can rotate forward freely.
// Small bridge pads at the stationary knuckle segments tie the guard directly
// into each stationary hinge without intruding into the alternating moving
// knuckle segments.
hinge_guard_t = 2;
hinge_guard_clearance = 0.8;
hinge_guard_front_z = hinge_axis_z + hinge_r + hinge_guard_clearance;
hinge_guard_start_y = base_thickness_y - 0.5;
hinge_guard_top_y = hinge_axis_y;
hinge_guard_bridge_overlap = 0.5;
hinge_guard_bridge_h = 2.0;

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

module lower_hinge_guard() {
    // Thin continuous shield across the full module width. In the closed state
    // this blocks direct access through the low opening behind the LED/template.
    // It is deliberately rearward of the complete 14 mm hinge barrel so the
    // alternating moving knuckles and the moving template never rub on it.
    union() {
        translate([
            box_x,
            hinge_guard_start_y,
            hinge_guard_front_z
        ])
            cube([
                box_w,
                hinge_guard_top_y-hinge_guard_start_y,
                hinge_guard_t
            ]);

        // Tie the continuous plate directly into each STATIONARY knuckle at the
        // rear-most part of its barrel. There are no bridge pads in the moving
        // knuckle X ranges, preserving the alternating hinge sweep clearance.
        for (segment=enclosure_knuckles)
            translate([
                segment[0],
                hinge_axis_y-hinge_guard_bridge_h,
                hinge_axis_z+hinge_r-hinge_guard_bridge_overlap
            ])
                cube([
                    segment[1],
                    hinge_guard_bridge_h,
                    hinge_guard_clearance
                        + hinge_guard_t
                        + hinge_guard_bridge_overlap
                ]);
    }
}

module outer_end_wall(side="left", controller_service=false) {
    x0 = side == "left" ? left_end_wall_x : right_end_wall_x;

    difference() {
        union() {
            // Orthogonal/full-depth lower wall, bed-connected through the base.
            translate([x0,0,box_front_z])
                cube([
                    end_wall_t,
                    taper_start_y,
                    rear_z_bottom-box_front_z
                ]);

            // Upper side follows the same 40 -> 10 mm taper as the rear
            // enclosure and terminates at the top landing.
            hull() {
                translate([
                    x0,
                    taper_start_y-1,
                    box_front_z
                ])
                    cube([
                        end_wall_t,
                        2,
                        rear_z_bottom-box_front_z
                    ]);

                translate([
                    x0,
                    box_top_y-top_link_cap_h,
                    top_link_front_z
                ])
                    cube([
                        end_wall_t,
                        top_link_cap_h,
                        rear_z_top-top_link_front_z
                    ]);
            }
        }

        // Continuous 6 mm hinge rail exits through both outer walls.
        translate([
            x0-0.5,
            hinge_axis_y,
            hinge_axis_z
        ])
            rotate([0,90,0])
                cylinder(d=hinge_bore_d,h=end_wall_t+1.0);

        if (controller_service)
            // Expose the complete short MatrixPortal service edge rather than
            // attempting individual button/USB cut-outs. This leaves tolerance
            // for the real board/connectors and guarantees finger access.
            translate([
                x0-0.5,
                controller_pcb_y-controller_service_y_margin,
                controller_service_z_min
            ])
                cube([
                    end_wall_t+1.0,
                    matrixportal_pcb_h+2*controller_service_y_margin,
                    controller_service_z_max-controller_service_z_min
                ]);
    }
}

module controller_mount_standoffs() {
    // Four M2.5 clearance standoffs grow forward from the lower rear wall.
    // The LED/template opens forward (towards -Z), while the board remains
    // well behind it inside the stationary enclosure.
    difference() {
        union() {
            for (point=controller_mount_points)
                translate([
                    point[0],
                    point[1],
                    controller_pcb_rear_z
                ])
                    cylinder(d=controller_post_d,h=controller_post_h);
        }

        for (point=controller_mount_points)
            translate([
                point[0],
                point[1],
                controller_pcb_rear_z-0.5
            ])
                cylinder(
                    d=controller_hole_d,
                    h=controller_post_h+1.0
                );
    }
}

module controller_pcb_preview() {
    // Reference-only board slab; not part of printable geometry.
    color([0.10,0.45,0.20,0.75])
        translate([
            controller_pcb_x,
            controller_pcb_y,
            controller_pcb_rear_z-controller_pcb_t
        ])
            cube([
                matrixportal_pcb_w,
                matrixportal_pcb_h,
                controller_pcb_t
            ]);
}

module power_grommet_cutter() {
    // Round rear-wall cut-out for a snap grommet. Axis is normal to the
    // orthogonal lower rear wall.
    translate([
        power_grommet_x,
        power_grommet_y,
        rear_z_bottom-box_rear_t-0.5
    ])
        cylinder(
            d=power_grommet_hole_d,
            h=box_rear_t+1.0
        );
}

module stationary_middle_enclosure_root(x0,len) {
    // Keep the stationary knuckle, but do NOT fill the volume directly below
    // the hinge axis. The moving plate sweeps through that region on its way
    // toward the service-open position.
    //
    // The support web begins at the BOTTOM tangent of the stationary barrel,
    // then slopes strongly rearward into the floor/base. Starting at the bottom
    // tangent means the first printed barrel layers are already connected to
    // material below instead of appearing as a floating island. Sweeping the
    // web rearward keeps the moving plate's forward/downward rotation corridor
    // clear.
    union() {
        hinge_barrel(x0,len);

        hull() {
            // Narrow overlap around the barrel's bottom tangent. The 3 mm
            // installed-Y height provides layer-to-layer support as the circular
            // barrel begins to grow.
            translate([
                x0,
                hinge_axis_y-hinge_r-1.0,
                hinge_axis_z-1.0
            ])
                cube([len,3,2]);

            // Bed-connected anchor near the rear of the 40 mm-deep base. This
            // large rearward offset keeps the diagonal web out of the plate
            // sweep while remaining support-free in the upright print.
            translate([
                x0,
                base_thickness_y-0.5,
                rear_z_bottom-box_rear_t
            ])
                cube([len,2,2]);
        }
    }
}

module stationary_middle_enclosure_installed() {
    difference() {
        union() {
            middle_floor_base();
            lower_hinge_guard();
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

module stationary_left_controller_enclosure_installed(show_pcb=false) {
    union() {
        stationary_middle_enclosure_installed();
        outer_end_wall("left",true);
        controller_mount_standoffs();

        if (show_pcb)
            controller_pcb_preview();
    }
}

module stationary_left_controller_enclosure_print() {
    rotate([90,0,0])
        stationary_left_controller_enclosure_installed(false);
}

module stationary_right_power_enclosure_installed() {
    difference() {
        union() {
            stationary_middle_enclosure_installed();
            outer_end_wall("right",false);
        }

        power_grommet_cutter();
    }
}

module stationary_right_power_enclosure_print() {
    rotate([90,0,0])
        stationary_right_power_enclosure_installed();
}

// CI checks the moving leaf against the stationary middle enclosure throughout
// the 0-90 degree service arc, so changes here must preserve both print support
// and rotational clearance.

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

module one_variant_model(
    variant="middle",
    open_angle=0,
    x_offset=0,
    show_pin=false
) {
    translate([x_offset,0,0]) {
        color([0.18,0.18,0.20])
            if (variant == "left_controller")
                stationary_left_controller_enclosure_installed(false);
            else if (variant == "right_power")
                stationary_right_power_enclosure_installed();
            else
                stationary_middle_enclosure_installed();

        if (variant == "left_controller")
            controller_pcb_preview();

        if (show_pin)
            hinge_pin_preview();

        color([0.75,0.75,0.78])
            translate([0,hinge_axis_y,hinge_axis_z])
                rotate([-open_angle,0,0])
                    translate([0,-hinge_axis_y,-hinge_axis_z])
                        moving_panel_template_installed();
    }
}

module four_panel_assembly_model(open_angle=0) {
    ground_preview(4*module_w);

    one_variant_model("left_controller",open_angle,0,false);
    one_variant_model("middle",open_angle,module_w,false);
    one_variant_model("middle",open_angle,2*module_w,false);
    one_variant_model("right_power",open_angle,3*module_w,false);

    // One continuous 6 mm hinge rail across all four modules.
    hinge_pin_preview(4*module_w-20,10);
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

module assembly_presentation(
    open_angle=0,
    two_middle=false,
    four_panel=false
) {
    rotate([90,0,0]) {
        if (four_panel)
            four_panel_assembly_model(open_angle);
        else if (two_middle)
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
    else if (hinge_test_part == "left_controller_enclosure")
        stationary_left_controller_enclosure_print();
    else if (hinge_test_part == "right_power_enclosure")
        stationary_right_power_enclosure_print();
    else if (hinge_test_part == "assembly")
        assembly_presentation(0,false);
    else if (hinge_test_part == "assembly_open")
        assembly_presentation(90,false);
    else if (hinge_test_part == "two_middle_assembly")
        assembly_presentation(0,true);
    else if (hinge_test_part == "two_middle_assembly_open")
        assembly_presentation(75,true);
    else if (hinge_test_part == "four_panel_assembly")
        assembly_presentation(0,false,true);
    else if (hinge_test_part == "four_panel_assembly_open")
        assembly_presentation(75,false,true);
    else
        assert(false,str("Unknown hinge_test_part: ",hinge_test_part));
}
