suppress_complete_assembly = true;
include <00_complete_enclosure_ASSEMBLY.scad>;

// 2D front elevation: Panel 1 remains on the left, matching the illuminated face.
projection(cut=false)
    complete_enclosure_projection_mesh();
