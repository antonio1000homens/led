// Issue #166 - exact current accessory-boss test coupon.
//
// Print this small coupon before committing to heat-set inserts in the real
// enclosure. It reproduces one current backplane boss:
//   7 mm OD x 4 mm high
//   3.4 mm blind hole
//   3 mm rear wall with 1.2 mm unbroken outer skin
//
// The coupon is for retention experiments only; it is not an enclosure part.

$fn = 48;

wall_t = 3.0;
outer_skin = 1.2;
boss_d = 7.0;
boss_h = 4.0;
hole_d = 3.4;
hole_depth = boss_h + wall_t - outer_skin;

coupon_w = 20;
coupon_h = 20;

difference() {
    union() {
        translate([-coupon_w/2,-coupon_h/2,0])
            cube([coupon_w,coupon_h,wall_t]);
        translate([0,0,wall_t-0.2])
            cylinder(d=boss_d,h=boss_h+0.2);
    }

    translate([0,0,wall_t+boss_h-hole_depth])
        cylinder(d=hole_d,h=hole_depth+0.1);
}
