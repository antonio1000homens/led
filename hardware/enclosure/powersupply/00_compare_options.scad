// Visual comparison of the remaining issue #166 PSU mount concepts.
//
// The service tray is the selected direction. The simple adapter remains as a
// useful geometry/reference baseline.

use <01_adapter_plate.scad>;
use <03_service_tray.scad>;

spacing_x = 145;

translate([-spacing_x/2, 0, 0])
    psu_adapter_plate();

translate([ spacing_x/2, 0, 0])
    assembled_service_tray();
