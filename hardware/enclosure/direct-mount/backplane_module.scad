// LED Matrix Backplane Module v1
// Designed for one nominal 256 x 128 mm P4 LED panel.
// Four identical modules form a 1024 x 128 mm backplane.
// The LED panel sits entirely in FRONT of this backplane; no printed feature
// projects over the 256 x 128 mm LED face.
//
// IMPORTANT: panel mounting-hole pattern was not supplied. The four corner
// cross-slots provide adjustment, but verify against the actual panel before
// printing all four modules.

$fn = 72;

// ---------- Parameters ----------
module_w = 256;
module_h = 128;
depth = 16;

frame = 16;                 // perimeter beam width
rod_d = 8.6;                // clearance for nominal 8 mm round bar
rod_z = depth/2;
rod_y_bottom = frame/2;
rod_y_top = module_h - frame/2;

pad_size = 32;
pad_thick = depth;
pad_center_offset = 24;     // nominal mounting zone centre from panel edges
slot_len = 22;
slot_w = 4.6;               // M4-ish universal clearance; also works with M3 washer

joint_len = 6;
joint_w = 11.5;
joint_h = 8;
joint_z = 4;
joint_clear = 0.35;
joint_y1 = 37;
joint_y2 = 79;

// ---------- Helpers ----------
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

module frame_body() {
    union() {
        // Top and bottom structural beams
        cube([module_w, frame, depth]);
        translate([0,module_h-frame,0]) cube([module_w, frame, depth]);

        // Side rails
        translate([0,frame,0]) cube([frame,module_h-2*frame,depth]);
        translate([module_w-frame,frame,0]) cube([frame,module_h-2*frame,depth]);

        // Four reinforced mounting pads, fully behind the panel
        for (x=[pad_center_offset, module_w-pad_center_offset])
            for (y=[pad_center_offset, module_h-pad_center_offset])
                translate([x-pad_size/2,y-pad_size/2,0])
                    cube([pad_size,pad_size,pad_thick]);

        // Short ribs tying pads to perimeter. These stay behind the PCB.
        // Left pair
        translate([frame, pad_center_offset-5, 0]) cube([pad_center_offset-frame,10,depth]);
        translate([frame, module_h-pad_center_offset-5, 0]) cube([pad_center_offset-frame,10,depth]);
        // Right pair
        translate([module_w-pad_center_offset, pad_center_offset-5, 0]) cube([pad_center_offset-frame,10,depth]);
        translate([module_w-pad_center_offset, module_h-pad_center_offset-5, 0]) cube([pad_center_offset-frame,10,depth]);

        // Right-side alignment tongues. These disappear into the next module,
        // so the assembled pitch remains exactly 256 mm per panel.
        for (yy=[joint_y1,joint_y2])
            translate([module_w-0.6,yy,joint_z])
                cube([joint_len+0.6,joint_w,joint_h]);
    }
}

module backplane_module() {
    difference() {
        frame_body();

        // Continuous 8 mm reinforcement-bar bores
        for (yy=[rod_y_bottom,rod_y_top])
            translate([-0.5,yy,rod_z])
                rotate([0,90,0]) cylinder(d=rod_d,h=module_w+7);

        // Universal mounting cross-slots
        for (x=[pad_center_offset,module_w-pad_center_offset])
            for (y=[pad_center_offset,module_h-pad_center_offset])
                cross_slot(x,y);

        // Left-side sockets for the previous module's tongues
        for (yy=[joint_y1,joint_y2])
            translate([-0.1, yy-joint_clear/2, joint_z-joint_clear/2])
                cube([joint_len+0.2,
                      joint_w+joint_clear,
                      joint_h+joint_clear]);
    }
}

backplane_module();
