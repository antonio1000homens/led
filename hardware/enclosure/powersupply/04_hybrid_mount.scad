// Option 4 - hybrid adapter/cradle for issue #166.
//
// Preferred prototype:
// - screws to the current six-boss enclosure boss grid;
// - integral support rails provide an airflow gap;
// - side capture rails provide positive vertical/lateral retention;
// - two configurable locating pins can additionally use the PSU's rear/bottom holes;
// - one accessible M3 screw + 8 mm washer provides positive anti-slide retention.
//
// The locating-pin coordinates are placeholders until the real PSU is measured.

include <psu_mount_common.scad>;

insertion_side = "left";

module hybrid_mount() {
    union() {
        base_adapter_plate();
        integrated_support_rails();
        side_capture_rails(open_side=insertion_side);
        locating_pins();

        lock_offset =
            psu_w/2 + psu_xy_clearance + lock_boss_d/2 + lock_edge_clearance;
        lock_x = insertion_side == "left" ? -lock_offset : lock_offset;

        assert(
            lock_washer_d/2 > lock_boss_d/2 + lock_edge_clearance,
            "Hybrid lock washer does not overlap the PSU edge"
        );

        screw_stop_boss(lock_x, 0, h=5.5, d=lock_boss_d);
    }
}

hybrid_mount();
backplane_boss_preview();
