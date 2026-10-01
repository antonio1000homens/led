// Visual comparison of issue #166 PSU mount concepts.
//
// The service tray remains the selected direction. Option 07 adds a replaceable
// snap latch so it can be compared with the screw-lock tray.

use <01_adapter_plate.scad>;
use <03_service_tray.scad>;
use <07_service_tray_snap_latch.scad>;

spacing_x = 145;
spacing_y = 110;

translate([-spacing_x/2, spacing_y/2, 0])
    psu_adapter_plate();

translate([ spacing_x/2, spacing_y/2, 0])
    assembled_service_tray();

translate([0, -spacing_y/2, 0])
    assembled_snap_service_tray();
