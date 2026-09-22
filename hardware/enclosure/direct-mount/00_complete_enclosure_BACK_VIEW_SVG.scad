suppress_complete_assembly = true;
include <00_complete_enclosure_ASSEMBLY.scad>;

// 2D rear elevation. Looking from behind reverses left/right relative to the front.
translate([1024,0,0])
    mirror([1,0,0])
        projection(cut=false)
            complete_enclosure_assembly(false);
