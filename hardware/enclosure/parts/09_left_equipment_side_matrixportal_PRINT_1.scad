include <../direct_mount_enclosure.scad>;
include <../matrixportal/matrixportal_s3_mount.scad>;

// MatrixPortal-specific replacement for the generic left end cap.
// Installed geometry is cut first, then rotated exactly like the standard
// left-side print wrapper.
rotate([0,-90,0])
    matrixportal_left_equipment_side();
