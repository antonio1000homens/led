// Visual comparison of the four issue #166 PSU mount prototypes.
//
// This file is for geometry inspection only.  Export the individual numbered
// SCAD files when testing a specific option.

use <01_adapter_plate.scad>;
use <02_slide_cradle.scad>;
use <03_service_tray.scad>;
use <04_hybrid_mount.scad>;

spacing_x = 145;
spacing_y = 105;

translate([-spacing_x/2, spacing_y/2, 0])
    psu_adapter_plate();

translate([ spacing_x/2, spacing_y/2, 0])
    slide_cradle();

translate([-spacing_x/2,-spacing_y/2, 0])
    assembled_service_tray();

translate([ spacing_x/2,-spacing_y/2, 0])
    hybrid_mount();
