// Minimal support-free 6 mm hinge prototype for the verified direct-mount LED template.
// Keeps the validated panel mounting pattern unchanged and isolates the hinge mechanics
// from the full equipment-enclosure design.

part = "__library__";
include <../direct_mount_enclosure.scad>;

$fn = 48;

hinge_pin_d = 6;
hinge_bore_d = 7.2;
hinge_outer_d = 14;
hinge_r = hinge_outer_d/2;
hinge_axis_y = 12;
hinge_axis_z = 9;

// Full-width bottom tongue/sole on the fixed template. Its lowest edge remains
// y=0, so the hinge barrel is recessed inside the base silhouette instead of
// becoming the lowest point when the assembly is closed.
fixed_tongue_h = 8;
fixed_tongue_t = 18;
fixed_template_t = 2;

// Interleaved knuckles, kept clear of the verified panel fastener/locator columns.
fixed_knuckles = [ [34,28], [94,24], [166,28] ];
moving_knuckles = [ [64,28], [120,44], [196,26] ];
axial_gap = 1.0;

// Deliberately simple constant-depth moving enclosure. This prototype validates
// the hinge and flush base before PSU/controller details are reintroduced.
box_x = 0.5;
box_y = 18;
box_w = 255;
box_h = 109.5;
box_depth = 24;
box_wall = 3;
box_rear_t = 3;
box_front_z = 2.8;
box_rear_z = box_front_z + box_depth;

module hinge_barrel(x0,len) {
    translate([x0,hinge_axis_y,hinge_axis_z])
        rotate([0,90,0])
            difference() {
                cylinder(d=hinge_outer_d,h=len);
                translate([0,0,-0.2]) cylinder(d=hinge_bore_d,h=len+0.4);
            }
}

module fixed_tongue_body() {
    // Flat, full-width tongue below the hinge. It overlaps the lower part of the
    // barrel envelope so no barrel begins as a tangent/floating cantilever.
    cube([module_w,fixed_tongue_h,fixed_tongue_t]);

    for (s=fixed_knuckles)
        hull() {
            translate([s[0],fixed_tongue_h-0.5,0])
                cube([s[1],1,fixed_tongue_t]);
            translate([s[0],hinge_axis_y,hinge_axis_z])
                rotate([0,90,0]) cylinder(d=hinge_outer_d,h=s[1]);
        }
}

module fixed_hinge_template() {
    difference() {
        union() {
            // Reuse the verified production template unchanged.
            mount_pattern_template();
            fixed_tongue_body();
        }

        // Restore the verified lower-row holes through the thicker tongue.
        for (x=panel_mount_x)
            for (y=panel_mount_y)
                if (y < 20)
                    translate([x,y,-0.5])
                        cylinder(d=panel_mount_hole_d,h=fixed_tongue_t+1);

        for (x=panel_locator_x)
            for (y=panel_locator_y)
                if (y < 20)
                    translate([x,y,-0.5])
                        cylinder(d=panel_locator_clearance_d,h=fixed_tongue_t+1);

        // One continuous cutter keeps every knuckle coaxial.
        translate([-0.2,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_bore_d,h=module_w+0.4);

        // Moving-knuckle windows open from the rear/top. They are recesses in
        // the flat print, not enclosed voids or isolated start regions.
        for (s=moving_knuckles)
            translate([
                s[0]-axial_gap/2,
                hinge_axis_y-hinge_r-0.7,
                hinge_axis_z-hinge_r-0.7
            ])
                cube([
                    s[1]+axial_gap,
                    2*hinge_r+1.4,
                    fixed_tongue_t-(hinge_axis_z-hinge_r)+1
                ]);
    }
}

module moving_box_shell() {
    // Rear plate + perimeter walls. The print wrapper flips the part so the
    // large rear plate lies directly on the build plate.
    union() {
        translate([box_x,box_y,box_rear_z-box_rear_t])
            cube([box_w,box_h,box_rear_t]);

        translate([box_x,box_y,box_front_z])
            cube([box_wall,box_h,box_depth]);

        translate([box_x+box_w-box_wall,box_y,box_front_z])
            cube([box_wall,box_h,box_depth]);

        translate([box_x,box_y+box_h-box_wall,box_front_z])
            cube([box_w,box_wall,box_depth]);

        // Continuous lower wall is the structural root for moving knuckles.
        translate([box_x,box_y,box_front_z])
            cube([box_w,box_wall+4,box_depth]);
    }
}

module moving_hinge_root(x0,len) {
    // Hull the lower wall into each barrel. This avoids the unsupported
    // horizontal-cylinder start that slicers often report as a floating
    // cantilever.
    hull() {
        translate([x0,box_y,box_front_z])
            cube([len,box_wall+4,box_depth]);

        translate([x0,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_outer_d,h=len);
    }
}

module moving_hinge_enclosure() {
    difference() {
        union() {
            moving_box_shell();
            for (s=moving_knuckles)
                moving_hinge_root(s[0],s[1]);
        }

        // One coaxial bore across all moving knuckles.
        translate([-0.2,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_bore_d,h=module_w+0.4);

        // Fixed-knuckle pockets are open toward the LED-panel side.
        for (s=fixed_knuckles)
            translate([
                s[0]-axial_gap/2,
                hinge_axis_y-hinge_r-0.7,
                box_front_z-1
            ])
                cube([
                    s[1]+axial_gap,
                    2*hinge_r+1.4,
                    hinge_axis_z+hinge_r-box_front_z+1.5
                ]);

        // Front/lower sweep relief only. Material behind the pivot stays
        // continuous to the rear plate.
        translate([box_x-1,-0.5,box_front_z-0.2])
            cube([
                box_w+2,
                hinge_axis_y+0.5,
                hinge_axis_z-box_front_z+0.2
            ]);
    }
}

module moving_hinge_enclosure_print() {
    // Rear-face-down print orientation. The moving part is about 24.8 mm tall
    // instead of standing the 255 mm enclosure on edge.
    translate([0,0,box_rear_z])
        rotate([0,180,0])
            mirror([1,0,0])
                moving_hinge_enclosure();
}

module hinge_pin_preview() {
    color("silver")
        translate([10,hinge_axis_y,hinge_axis_z])
            rotate([0,90,0])
                cylinder(d=hinge_pin_d,h=236);
}

module assembly(open_angle=0) {
    color([0.75,0.75,0.78])
        fixed_hinge_template();

    hinge_pin_preview();

    color([0.18,0.18,0.20])
        translate([0,hinge_axis_y,hinge_axis_z])
            rotate([open_angle,0,0])
                translate([0,-hinge_axis_y,-hinge_axis_z])
                    moving_hinge_enclosure();
}

if (!is_undef(hinge_test_part)) {
    if (hinge_test_part == "fixed_template")
        fixed_hinge_template();
    else if (hinge_test_part == "moving_enclosure")
        moving_hinge_enclosure_print();
    else if (hinge_test_part == "assembly")
        assembly(0);
    else if (hinge_test_part == "assembly_open")
        assembly(70);
    else
        assert(false,str("Unknown hinge_test_part: ",hinge_test_part));
}
