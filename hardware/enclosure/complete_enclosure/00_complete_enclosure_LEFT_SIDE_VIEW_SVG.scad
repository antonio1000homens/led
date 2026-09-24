suppress_complete_assembly = true;
include <00_complete_enclosure_ASSEMBLY.scad>;

// 2D left-side elevation: depth is horizontal, enclosure height is vertical.
translate([40,0,0])
    projection(cut=false)
        rotate([0,-90,0])
            complete_enclosure_assembly(false);
