suppress_complete_assembly = true;
include <00_complete_enclosure_ASSEMBLY.scad>;

// 2D right-side elevation: depth is horizontal, enclosure height is vertical.
projection(cut=false)
    rotate([0,90,0])
        complete_enclosure_assembly(false);
