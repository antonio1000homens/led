// Option 1 - simple printed adapter plate for issue #166.
//
// Intended experiment:
// - plate screws to the current six-boss universal backplane interface;
// - integral rails create a 2 mm gap below the PSU;
// - two raised PSU screw bosses finish level with the 2 mm support rails;
// - low corner locators make positioning repeatable.
//
// Measure psu_rear_mount_points in psu_mount_common.scad before treating these
// holes as production geometry.

include <psu_mount_common.scad>;


module psu_adapter_plate() {
    union() {
        base_adapter_plate(include_psu_pilots=true);
        integrated_support_rails();
        raised_psu_mount_bosses();
        corner_locators();
    }
}

psu_adapter_plate();
backplane_boss_preview();
