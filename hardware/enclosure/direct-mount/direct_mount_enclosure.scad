// Modular direct-mount enclosure/backplane for four 256 x 128 mm P4 HUB75 panels.
// Issue #53 - antonio1000homens/led
//
// Design intent:
// - Print four identical backplane modules and bolt each LED PCB directly to one module.
// - All printed structure remains BEHIND the LED PCB. Nothing projects into the 256 x 128 mm front face.
// - Two 1000 x 8 mm round reinforcement bars pass through all four modules.
// - Neighbouring modules align with tongue/socket keys and are locked with rear M3 joiner plates.
// - Rear electronics carriers mount to blind M3 heat-set-insert pockets, so screws cannot protrude into the LED face.
//
// IMPORTANT: The physical AliExpress panel mounting-hole pattern is not yet measured.
// The LED mounting cross-slots are deliberately provisional. Print/verify one module before printing all four.

$fn = 48;
part = "backplane";

module_w = 256;
module_h = 128;
depth = 16;
frame = 16;

pad_size = 32;
pad_center_offset = 24;
slot_len = 22;
slot_w = 4.6;

rod_d = 8.6;
rod_z = depth/2;
rod_y_bottom = frame/2;
rod_y_top = module_h-frame/2;

joint_len = 6;
joint_w = 11.5;
joint_h = 8;
joint_z = 4;
joint_clear = 0.35;
joint_y1 = 37;
joint_y2 = 79;

joiner_insert_x = 8;
joiner_insert_y1 = 50;
joiner_insert_y2 = 78;
insert_d = 4.7;
insert_depth = 6.2;

accessory_insert_y1 = 30;
accessory_insert_y2 = 98;

module slot2d(len=22, w=4.6) {
    hull() {
        translate([-(len-w)/2,0]) circle(d=w);
        translate([(len-w)/2,0]) circle(d=w);
    }
}

module cross_slot(x,y) {
    translate([x,y,-0.5]) linear_extrude(height=depth+1) {
        union() {
            slot2d(slot_len, slot_w);
            rotate(90) slot2d(slot_len, slot_w);
        }
    }
}

module blind_insert_pocket(x,y,d=insert_d,dep=insert_depth) {
    translate([x,y,depth-dep]) cylinder(d=d,h=dep+0.25);
}

module backplane_body() {
    union() {
        cube([module_w,frame,depth]);
        translate([0,module_h-frame,0]) cube([module_w,frame,depth]);
        translate([0,frame,0]) cube([frame,module_h-2*frame,depth]);
        translate([module_w-frame,frame,0]) cube([frame,module_h-2*frame,depth]);

        for (x=[pad_center_offset,module_w-pad_center_offset])
            for (y=[pad_center_offset,module_h-pad_center_offset])
                translate([x-pad_size/2,y-pad_size/2,0]) cube([pad_size,pad_size,depth]);

        translate([frame,pad_center_offset-5,0]) cube([pad_center_offset-frame,10,depth]);
        translate([frame,module_h-pad_center_offset-5,0]) cube([pad_center_offset-frame,10,depth]);
        translate([module_w-pad_center_offset,pad_center_offset-5,0]) cube([pad_center_offset-frame,10,depth]);
        translate([module_w-pad_center_offset,module_h-pad_center_offset-5,0]) cube([pad_center_offset-frame,10,depth]);

        for (yy=[joint_y1,joint_y2])
            translate([module_w-0.6,yy,joint_z]) cube([joint_len+0.6,joint_w,joint_h]);
    }
}

module backplane() {
    difference() {
        backplane_body();

        for (yy=[rod_y_bottom,rod_y_top])
            translate([-0.5,yy,rod_z]) rotate([0,90,0]) cylinder(d=rod_d,h=module_w+7);

        for (x=[pad_center_offset,module_w-pad_center_offset])
            for (y=[pad_center_offset,module_h-pad_center_offset]) cross_slot(x,y);

        for (yy=[joint_y1,joint_y2])
            translate([-0.1,yy-joint_clear/2,joint_z-joint_clear/2])
                cube([joint_len+0.2,joint_w+joint_clear,joint_h+joint_clear]);

        for (xx=[joiner_insert_x,module_w-joiner_insert_x])
            for (yy=[joiner_insert_y1,joiner_insert_y2]) blind_insert_pocket(xx,yy);

        for (xx=[joiner_insert_x,module_w-joiner_insert_x])
            for (yy=[accessory_insert_y1,accessory_insert_y2]) blind_insert_pocket(xx,yy);
    }
}

module module_joiner() {
    difference() {
        cube([32,48,4]);
        for (xx=[8,24])
            for (yy=[10,38])
                translate([xx,yy,-0.5]) cylinder(d=3.5,h=5);
    }
}

module rod_end_plug() {
    union() {
        cylinder(h=2.5,d=13);
        translate([0,0,2.5]) cylinder(h=10.5,d1=8.45,d2=8.20);
    }
}

carrier_w = 244;
carrier_h = 80;
carrier_t = 4;
carrier_hole_x = 2;
carrier_hole_y = 6;

module carrier_frame() {
    difference() {
        union() {
            cube([carrier_w,12,carrier_t]);
            translate([0,carrier_h-12,0]) cube([carrier_w,12,carrier_t]);
            cube([12,carrier_h,carrier_t]);
            translate([carrier_w-12,0,0]) cube([12,carrier_h,carrier_t]);
        }
        for (xx=[carrier_hole_x,carrier_w-carrier_hole_x])
            for (yy=[carrier_hole_y,carrier_h-carrier_hole_y])
                translate([xx,yy,-0.5]) cylinder(d=3.5,h=carrier_t+1);
    }
}

module elongated_hole(len=12,d=3.2,h=10) {
    hull() {
        translate([-len/2+d/2,0,0]) cylinder(d=d,h=h);
        translate([ len/2-d/2,0,0]) cylinder(d=d,h=h);
    }
}

module matrixportal_mount() {
    difference() {
        union() {
            carrier_frame();
            translate([(carrier_w-100)/2,10,0]) cube([100,60,carrier_t]);
            for (xx=[carrier_w/2-38,carrier_w/2+38])
                for (yy=[carrier_h/2-17,carrier_h/2+17])
                    translate([xx,yy,carrier_t]) cylinder(d=8,h=6);
        }
        for (xx=[carrier_w/2-38,carrier_w/2+38])
            for (yy=[carrier_h/2-17,carrier_h/2+17])
                translate([xx,yy,-0.5]) rotate([0,0,90]) elongated_hole(10,2.8,carrier_t+7);
        translate([carrier_w/2-22,carrier_h/2-6,-0.5]) cube([44,12,carrier_t+1]);
    }
}

module power_distribution_mount() {
    difference() {
        union() {
            carrier_frame();
            translate([(carrier_w-126)/2,(carrier_h-56)/2,0]) cube([126,56,carrier_t]);
        }
        for (xx=[carrier_w/2-48,carrier_w/2+48])
            for (yy=[carrier_h/2-18,carrier_h/2+18])
                translate([xx,yy,-0.5]) elongated_hole(20,4.2,carrier_t+1);
        for (yy=[carrier_h/2-12,carrier_h/2+12])
            translate([carrier_w/2+56,yy,-0.5]) cube([3.5,12,carrier_t+1]);
    }
}

module cable_clip() {
    difference() {
        union() {
            cube([24,14,4]);
            translate([12,14,6]) rotate([90,0,0]) cylinder(d=12,h=14);
        }
        translate([12,15,6]) rotate([90,0,0]) cylinder(d=7,h=16);
        translate([10.5,-1,8]) cube([3,16,6]);
        translate([4,7,-0.5]) cylinder(d=3.5,h=5);
    }
}

module mounting_slot_coupon() {
    difference() {
        cube([42,42,6]);
        translate([21,21,-0.5]) linear_extrude(height=7) {
            union() {
                slot2d(slot_len,slot_w);
                rotate(90) slot2d(slot_len,slot_w);
            }
        }
        translate([7,7,-0.5]) cylinder(d=insert_d,h=6.7);
    }
}

if (part == "backplane") backplane();
else if (part == "joiner") module_joiner();
else if (part == "rod_plug") rod_end_plug();
else if (part == "matrixportal_mount") matrixportal_mount();
else if (part == "power_mount") power_distribution_mount();
else if (part == "cable_clip") cable_clip();
else if (part == "slot_coupon") mounting_slot_coupon();
else assert(false, str("Unknown part: ",part));
