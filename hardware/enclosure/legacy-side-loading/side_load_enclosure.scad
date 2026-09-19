// LED matrix side-loading enclosure v2
// Concept fit model for 4 x 256x128 mm LED modules, 2 x 1000mm x 8mm steel reinforcement bars.
// All dimensions in mm.
// IMPORTANT: panel thickness and edge clearances are assumptions until measured on the real LED module.

$fn = 48;
part = "frame";

// ---- primary dimensions ----
module_pitch = 256;          // one printed structural module per LED panel
panel_w = 256;
panel_h = 128;
panel_edge_t = 16.0;        // ASSUMPTION: maximum edge/backing thickness in guide region
panel_z_clear = 0.8;
panel_y_clear = 0.8;

outer_h = 155;
depth = 32;
rail_h = (outer_h - (panel_h + panel_y_clear))/2; // 13.1 mm
stile_w = 8;
back_stile_z = 19.5;        // stiles live behind slide path

// panel slide path / lips
panel_z0 = 1.8;
panel_z1 = panel_z0 + panel_edge_t + panel_z_clear;
lip_inset_y = 1.8;
lip_z = 1.8;
rear_lip_z = 2.4;

// 8 mm bar channel
rod_d = 8.0;
rod_channel_d = 8.8;        // 0.8 mm diametral clearance (0.4 mm radial)
rod_r = rod_channel_d/2;
rod_center_z = depth - rod_r + 0.25; // opens slightly to rear for drop-in assembly
rod_center_y_bottom = rail_h/2;
rod_center_y_top = outer_h - rail_h/2;

// module interlock tabs on rear stiles
join_len = 5.0;
join_clear = 0.35;
join_w_y = 16;
join_h_z = 7;
join_y1 = 27;
join_y2 = outer_h - 27 - join_w_y;
join_z = depth - join_h_z;

// fasteners
m3_clear = 3.4;
m3_pilot = 2.6;
m4_clear = 4.4;

// utility
module cyl_x(len, d) {
    rotate([0,90,0]) cylinder(h=len, d=d, center=false);
}

// Main printable module. Pitch remains exactly 256 mm when joined.
module frame_module() {
    difference() {
        union() {
            cube([module_pitch, rail_h, depth]);
            translate([0, outer_h-rail_h, 0]) cube([module_pitch, rail_h, depth]);

            translate([0, rail_h, back_stile_z])
                cube([stile_w, outer_h-2*rail_h, depth-back_stile_z]);
            translate([module_pitch-stile_w, rail_h, back_stile_z])
                cube([stile_w, outer_h-2*rail_h, depth-back_stile_z]);

            translate([0, rail_h-2.0, back_stile_z]) cube([module_pitch, 2.0, depth-back_stile_z]);
            translate([0, outer_h-rail_h, back_stile_z]) cube([module_pitch, 2.0, depth-back_stile_z]);

            translate([0, rail_h-lip_inset_y, 0]) cube([module_pitch, lip_inset_y, lip_z]);
            translate([0, outer_h-rail_h, 0]) cube([module_pitch, lip_inset_y, lip_z]);

            translate([0, rail_h-lip_inset_y, panel_z1]) cube([module_pitch, lip_inset_y, rear_lip_z]);
            translate([0, outer_h-rail_h, panel_z1]) cube([module_pitch, lip_inset_y, rear_lip_z]);

            for (yy=[join_y1, join_y2])
                translate([module_pitch, yy, join_z])
                    cube([join_len, join_w_y, join_h_z]);
        }

        translate([-0.1, rod_center_y_bottom, rod_center_z]) cyl_x(module_pitch+0.2, rod_channel_d);
        translate([-0.1, rod_center_y_top, rod_center_z]) cyl_x(module_pitch+0.2, rod_channel_d);

        for (yy=[join_y1-join_clear/2, join_y2-join_clear/2])
            translate([-0.1, yy, join_z-join_clear/2])
                cube([join_len+join_clear+0.1, join_w_y+join_clear, join_h_z+join_clear]);

        for (xx=[4, module_pitch-4])
            translate([xx, outer_h/2, depth-7]) cylinder(h=8, d=m3_pilot);

        for (yy=[rod_center_y_bottom, rod_center_y_top]) {
            for (xx=[module_pitch/2-8, module_pitch/2+8])
                translate([xx, yy, depth-7]) cylinder(h=8, d=m3_pilot);
        }

        for (xx=[48, 80, 176, 208])
            for (yy=[outer_h/2-24, outer_h/2+24])
                translate([xx, yy, depth-7]) cylinder(h=8, d=m3_pilot);

        for (yy=[rod_center_y_bottom, rod_center_y_top]) {
            translate([-0.1, yy, 10]) rotate([0,90,0]) cylinder(h=10.2,d=m3_pilot);
            translate([module_pitch-10.1, yy, 10]) rotate([0,90,0]) cylinder(h=10.2,d=m3_pilot);
        }
    }
}

module left_end_cap() {
    cap_t = 5;
    band_h = rail_h + 5;
    spine_z = 4;
    difference() {
        union() {
            cube([cap_t, band_h, depth]);
            translate([0, outer_h-band_h, 0]) cube([cap_t, band_h, depth]);
            cube([cap_t, outer_h, spine_z]);
            for (yy=[rod_center_y_bottom, rod_center_y_top])
                translate([cap_t-0.5, yy, rod_center_z]) cyl_x(12.5, 7.6);
        }
        for (yy=[rod_center_y_bottom, rod_center_y_top])
            translate([-0.1,yy,10]) rotate([0,90,0]) cylinder(h=cap_t+0.2,d=m3_clear);
    }
}

module right_end_cap() {
    cap_t = 5;
    band_h = rail_h + 5;
    spine_z = 4;
    difference() {
        union() {
            cube([cap_t, band_h, depth]);
            translate([0, outer_h-band_h, 0]) cube([cap_t, band_h, depth]);
            cube([cap_t, outer_h, spine_z]);
            for (yy=[rod_center_y_bottom, rod_center_y_top])
                translate([-12, yy, rod_center_z]) cyl_x(12.5, 7.6);
        }
        for (yy=[rod_center_y_bottom, rod_center_y_top])
            translate([-0.1,yy,10]) rotate([0,90,0]) cylinder(h=cap_t+0.2,d=m3_clear);
    }
}

module rod_retainer_clip() {
    clip_x = 24;
    clip_y = 12;
    clip_z = 3;
    difference() {
        cube([clip_x, clip_y, clip_z]);
        translate([clip_x/2, clip_y/2, -1.2]) cylinder(h=2.4, d=8.6);
        for (xx=[4, clip_x-4])
            translate([xx, clip_y/2, -0.1]) cylinder(h=clip_z+0.2, d=m3_clear);
    }
}

module seam_lock() {
    w=34; h=28; t=4; finger_w=1.2; finger_h=12; finger_d=8;
    difference() {
        union() {
            cube([w,h,t]);
            translate([w/2-finger_w/2, h/2-finger_h/2, -finger_d]) cube([finger_w,finger_h,finger_d]);
        }
        for (xx=[13,w-13])
            translate([xx,h/2,-0.1]) cylinder(h=t+0.2,d=m3_clear);
    }
}

module controller_tray() {
    w=98; h=62; t=3; boss=7; boss_h=5;
    difference() {
        union() {
            cube([w,h,t]);
            for (x=[8,w-8]) for (y=[8,h-8])
                translate([x,y,t]) cylinder(h=boss_h,d=boss);
        }
        for (x=[6,w-6]) for (y=[6,h-6])
            translate([x,y,-0.1]) cylinder(h=t+boss_h+0.2,d=m3_clear);
        for (x=[24,w-24]) for (y=[18,h-18])
            hull() {
                translate([x-3,y,-0.1]) cylinder(h=t+boss_h+0.2,d=3.0);
                translate([x+3,y,-0.1]) cylinder(h=t+boss_h+0.2,d=3.0);
            }
        translate([w/2-24,h/2-12,-0.1]) cube([48,24,t+0.2]);
    }
}

module power_tray() {
    w=112; h=68; t=3; rim=3;
    difference() {
        union() {
            cube([w,h,t]);
            cube([w,rim,8]);
            translate([0,h-rim,0]) cube([w,rim,8]);
            cube([rim,h,8]);
            translate([w-rim,0,0]) cube([rim,h,8]);
        }
        for (x=[7,w-7]) for (y=[7,h-7])
            translate([x,y,-0.1]) cylinder(h=8.2,d=m3_clear);
        for (x=[28,56,84])
            hull() {
                translate([x-5,h/2,-0.1]) cylinder(h=t+0.2,d=3.5);
                translate([x+5,h/2,-0.1]) cylinder(h=t+0.2,d=3.5);
            }
        translate([w-22,h/2-8,-0.1]) cube([16,16,t+0.2]);
    }
}

module cable_clip() {
    w=16; h=10; t=5;
    difference() {
        cube([w,h,t]);
        translate([w/2,h/2,t]) rotate([90,0,0]) cylinder(h=h+0.2,d=5.2,center=true);
        translate([3,h/2,-0.1]) cylinder(h=t+0.2,d=m3_clear);
    }
}

module thickness_gauge() {
    base_w=100; base_h=28; base_t=8;
    vals=[10,12,14,16,18];
    difference() {
        cube([base_w,base_h,base_t]);
        for(i=[0:4]) {
            x=4+i*19;
            translate([x,10,-0.1]) cube([vals[i]+0.6,18.2,base_t+0.2]);
        }
    }
}

module joint_coupon() {
    difference() {
        union() {
            cube([35,24,10]);
            translate([35,4,3]) cube([join_len,16,7]);
        }
        translate([-0.1,4-join_clear/2,3-join_clear/2]) cube([join_len+join_clear,16+join_clear,7+join_clear]);
    }
}

module assembly_reference(exploded=0) {
    for(i=[0:3])
        translate([i*module_pitch + i*exploded,0,0]) frame_module();
    translate([-5-exploded,0,0]) left_end_cap();
    translate([4*module_pitch+exploded*4,0,0]) right_end_cap();
    color("silver") {
        translate([12,rod_center_y_bottom,rod_center_z]) cyl_x(1000,rod_d);
        translate([12,rod_center_y_top,rod_center_z]) cyl_x(1000,rod_d);
    }
}

// ---- dispatch ----
if (part=="frame") frame_module();
else if (part=="left_cap") left_end_cap();
else if (part=="right_cap") right_end_cap();
else if (part=="rod_clip") rod_retainer_clip();
else if (part=="seam_lock") seam_lock();
else if (part=="controller_tray") controller_tray();
else if (part=="power_tray") power_tray();
else if (part=="cable_clip") cable_clip();
else if (part=="thickness_gauge") thickness_gauge();
else if (part=="joint_coupon") joint_coupon();
else if (part=="assembly") assembly_reference(0);
else if (part=="assembly_exploded") assembly_reference(12);
