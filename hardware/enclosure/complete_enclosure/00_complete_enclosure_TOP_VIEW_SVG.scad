suppress_complete_assembly = true;
include <00_complete_enclosure_ASSEMBLY.scad>;

// 2D top elevation: enclosure width is horizontal, rear depth is vertical.
translate([0,40,0])
    projection(cut=false)
        rotate([90,0,0])
            complete_enclosure_assembly(false);
