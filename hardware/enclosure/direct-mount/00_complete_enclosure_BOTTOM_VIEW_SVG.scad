suppress_complete_assembly = true;
include <00_complete_enclosure_ASSEMBLY.scad>;

// 2D bottom elevation: enclosure width is horizontal, rear depth is vertical.
projection(cut=false)
    rotate([-90,0,0])
        complete_enclosure_assembly(false);
