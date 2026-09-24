// Rear lid/backplane alignment schematic.
//
// The lid and backplane deliberately share the same nominal panel XY coordinate
// system. Socket centres and lid snap-peg centres are both:
//   x = 64 / 192 mm
//   y = 8 / 120 mm
//
// Green cylinders mark the four common centres. The lid is shown in its
// installed orientation (snap pegs pointing toward the backplane).
part = "__library__";
include <../direct_mount_enclosure.scad>;

color("dimgray",0.75)
    backplane(false);

color("lightgray",0.55)
    rear_lid_installed();

for (xx=lid_lock_x)
    for (yy=lid_lock_y)
        color("green",0.9)
            translate([xx,yy,depth-0.5])
                cylinder(d=3,h=22,$fn=24);

// Outline guide for the physical rear backplane footprint.
color("red",0.25)
    translate([backplane_edge_inset,backplane_edge_inset,depth+0.2])
        linear_extrude(height=0.3)
            difference() {
                square([backplane_w,backplane_h]);
                translate([0.6,0.6])
                    square([backplane_w-1.2,backplane_h-1.2]);
            }
