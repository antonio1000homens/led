include <../direct_mount_enclosure.scad>;

intersection() {
    hinge_mount_pattern_template();

    translate([0,hinge_axis_y,hinge_axis_z])
        rotate([30,0,0])
            translate([0,-hinge_axis_y,-hinge_axis_z])
                hinged_equipment_base();
}
