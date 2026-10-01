// Option 4 — hybrid adapter/cradle for issue #166.
//
// Preferred prototype:
// - screws to the existing enclosure boss grid;
// - integral support rails provide an airflow gap;
// - two configurable locating pins use the PSU's rear/bottom mounting holes;
// - low corner guides constrain the envelope;
// - one accessible M3 stop screw provides positive anti-slide retention.
//
// The locating-pin coordinates are placeholders until the real PSU is measured.

include <psu_mount_common.scad>;

show_psu = true;
insertion_side = "left";

module hybrid_mount() {
    union() {
        base_adapter_plate();
        integrated_support_rails();
        locating_pins();
        corner_locators(h=4.5, arm=8);

        lock_x = insertion_side == "left"
            ? -psu_w/2 - psu_xy_clearance - 4
            :  psu_w/2 + psu_xy_clearance + 4;
        screw_stop_boss(lock_x, 0, h=5.5);
    }
}

hybrid_mount();
if (show_psu) {
    psu_preview();
    backplane_boss_preview();
}
