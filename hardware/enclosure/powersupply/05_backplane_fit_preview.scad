// Issue #166 - actual selected dock against the current backplane boss grid.
//
// Solid geometry is the production snap-latch dock. Transparent geometry is the
// universal backplane wall + six accessory bosses. Use this view to confirm
// that the widened 89 mm dock still sits inside the available full-depth zone
// and that all six locating pockets align with the backplane bosses.

include <service_tray_snap_latch_common.scad>;

snap_dock();
backplane_interface_preview();
