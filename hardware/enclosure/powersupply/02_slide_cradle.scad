// Option 2 - slide-in printed cradle for issue #166.
//
// The PSU slides in horizontally from the left. Side rails and shallow upper
// lips constrain Y/Z movement; a closed stop constrains +X. After insertion,
// fit one M3 screw with an 8 mm OD washer in the front lock boss. The printed
// boss remains clear during insertion; the washer overlaps the PSU edge and
// prevents the PSU sliding back out.
//
// This option intentionally does not depend on the PSU's unknown mounting-hole
// coordinates, making it useful as an early fit/serviceability experiment.

include <psu_mount_common.scad>;

insertion_side = "left";

module slide_cradle() {
    union() {
        base_adapter_plate();
        integrated_support_rails();
        side_capture_rails(open_side=insertion_side);

        // Printed boss clears the PSU body; fit the washer only after insertion.
        lock_offset =
            psu_w/2 + psu_xy_clearance + lock_boss_d/2 + lock_edge_clearance;
        lock_x = insertion_side == "left" ? -lock_offset : lock_offset;

        assert(
            lock_washer_d/2 > lock_boss_d/2 + lock_edge_clearance,
            "Lock washer does not overlap the PSU edge"
        );

        screw_stop_boss(lock_x, 0, h=5, d=lock_boss_d);
    }
}

slide_cradle();
backplane_boss_preview();
