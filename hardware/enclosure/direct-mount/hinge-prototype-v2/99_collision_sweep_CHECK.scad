include <hinge_prototype_v2.scad>;
angles = [5, 15, 30, 45, 60, 75, 90];
for (i=[0:len(angles)-1])
    translate([i*300, 0, 0])
        intersection() {
            fixed_backplane_hinge();
            moving_at_angle(angles[i]);
        }
