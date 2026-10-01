// Visual comparison of issue #166 service-tray concepts.
//
// Both options use the same enclosure-side six-boss dock interface.
// The difference is only the tray retention mechanism.

use <03_service_tray.scad>;
use <07_service_tray_snap_latch.scad>;

spacing_x = 145;

translate([-spacing_x/2, 0, 0])
    assembled_service_tray();

translate([ spacing_x/2, 0, 0])
    assembled_snap_service_tray();
