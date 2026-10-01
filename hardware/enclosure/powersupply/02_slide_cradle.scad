// Option 2 - slide-in printed cradle for issue #166.
//
// The PSU slides in horizontally from the left. Side rails and shallow upper
// lips constrain Y/Z movement; a closed stop constrains +X. After insertion,
// fit one ordinary M3 screw in the front lock boss to prevent the PSU sliding
// back out.
//
// This option intentionally does not depend on the PSU's unknown mounting-hole
// coordinates, making it useful as an early fit/serviceability experiment.

include <psu_mount_common.scad>;

show_psu = true;
insertion_side = "left";

module slide_cradle() {
    union() {
        base_adapter_plate();
        integrated_support_rails();
        side_capture_rails(open_side=insertion_side);

        // Removable M3 screw head/washer acts as the anti-slide lock.
        lock_x = insertion_side == "left"
            ? -psu_w/2 - psu_xy_clearance - 4
            :  psu_w/2 + psu_xy_clearance + 4;
        screw_stop_boss(lock_x, 0, h=5);
    }
}

slide_cradle();
if (show_psu) {
    psu_preview();
    backplane_boss_preview();
}
