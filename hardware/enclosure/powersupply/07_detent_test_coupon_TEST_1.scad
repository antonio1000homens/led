// Issue #177 PETG detent test coupon.
// Render coupon_part=0 for the tray flexure and coupon_part=1 for its matching
// dock groove. They are separate prints so the fit can be tested by hand.
include <service_tray_snap_latch_common.scad>;

coupon_part = is_undef(coupon_part) ? 0 : coupon_part;

// A small handle replaces the full tray. The flexure itself is the production
// geometry, kept in its seated dock coordinate system and the same edge-on
// print pose as the production tray.
module flexure_coupon() {
    translate([0,0,tray_h/2])
        rotate([-90,0,0])
            union() {
                // Handle and anchor land. Its +Y edge is the print-bed contact.
                translate([-72,27,0]) cube([20,tray_h/2-27,tray_t]);
                translate([0,0,-tray_assembled_z])
                    integral_tray_detent_dock_frame();
            }
}

// Keep the real dock's outside edge, underside groove and wall thickness; the
// crop removes unrelated plate features to make a small mating test piece.
module groove_coupon() {
    intersection() {
        snap_dock();
        translate([-62,-10,-0.1]) cube([15,20,plate_t+0.2]);
    }
}

assert(coupon_part == 0 || coupon_part == 1,
       "coupon_part must be 0 (flexure) or 1 (dock groove)");
if (coupon_part == 0)
    flexure_coupon();
else
    groove_coupon();
