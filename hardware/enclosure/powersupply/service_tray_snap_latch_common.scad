// Issue #177: enclosure-centred PSU service tray with integral pull-release tab.
// Local axes: tray/dock insertion is +X, vertical grid is Y, dock thickness Z.
include <psu_mount_common.scad>;
include <../psu_adapter_interface.scad>;

tray_w = 114;
tray_h = 79;
tray_t = 2.8;
dock_w = 118;
dock_h = 79;
fit_envelope_h = 80;
slide_z_clearance = 0.25;
tray_assembled_z = plate_t + slide_z_clearance;
psu_support_height = 2.0;
psu_support_plane_z = tray_t + psu_support_height;
psu_support_bar_overlap = 0.4;

// Keep the screw-land ring and internal runner webs around the open centre.
dock_relief_core_w = 80;
dock_relief_core_h = 26;

// Captive internal dovetails. The open-ended tray grooves allow insertion from
// -X; the dock's +X wall remains the independent hard insertion stop.
dovetail_y = [-25,25];
dovetail_base_w = 2.4;
dovetail_top_w = 4.0;
dovetail_h = 1.8;
dovetail_skin = 0.4;
dovetail_clearance = 0.3;
dovetail_groove_depth = 1.9;
dovetail_rail_x0 = -dock_w/2 + 2;
dovetail_rail_x1 = tray_w/2 - 18; // +39: 10 mm shorter than the former +49
// Extend the cutter beyond the leading +X edge so no closed tray lip blocks entry.
dovetail_groove_x0 = -tray_w/2 - 0.2;
dovetail_groove_x1 = tray_w/2 + 0.5;
dovetail_rail_len = dovetail_rail_x1-dovetail_rail_x0;
dovetail_groove_len = dovetail_groove_x1-dovetail_groove_x0;
dovetail_groove_bottom_w = dovetail_base_w + 2*dovetail_clearance;
dovetail_groove_top_w = dovetail_top_w + 2*dovetail_clearance;

// Integral PETG flexure, dimensioned in the seated dock coordinate frame.
detent_beam_free_len_y = 30;
detent_beam_width_x = 5;
detent_beam_thickness_z = 1.2;
detent_beam_x0 = -61;
detent_beam_x1 = detent_beam_x0 + detent_beam_width_x;
detent_beam_z0 = -1.5;
detent_beam_z1 = detent_beam_z0 + detent_beam_thickness_z;
detent_peak_z = 0.5;
detent_groove_depth = 0.8;
detent_nominal_engagement = detent_peak_z;
detent_groove_clearance = detent_groove_depth-detent_peak_z;
m3_button_head_max_d = 5.7;
m3_button_head_max_h = 1.65;
m3_head_recessed_protrusion = m3_button_head_max_h-adapter_screw_head_depth;
m3_psu_support_clearance = psu_support_plane_z-
    (plate_t+m3_head_recessed_protrusion);
detent_groove_x0 = -58.3;
detent_groove_x1 = -55.7;
detent_groove_y0 = -3.3;
detent_groove_y1 = 3.3;
detent_anchor_x0 = -61;
detent_anchor_x1 = -59.4;
detent_anchor_y0 = detent_beam_free_len_y-2.5;
detent_anchor_y1 = detent_beam_free_len_y+2.5;
detent_anchor_roof_z0 = plate_t;
detent_anchor_roof_z1 = tray_assembled_z+0.55;
detent_anchor_link_x0 = -61;
detent_anchor_link_x1 = -56.5;
detent_anchor_link_y0 = detent_beam_free_len_y;
detent_anchor_link_y1 = detent_beam_free_len_y+3.5;
detent_anchor_link_z0 = plate_t;
detent_anchor_link_z1 = tray_assembled_z+0.55;

psu_pilot_edge_margin =
    tray_h/2 - (abs(psu_rear_mount_points[0][1]) + psu_mount_pilot_d/2);
assert(dock_h == 79 && tray_h == 79 && fit_envelope_h == 80,
       "PSU dock and tray must preserve the measured 79 mm fit envelope");
assert(abs(dovetail_rail_len-96)<0.01,
       "Dock dovetail rails must be shortened to 96 mm");
assert(dovetail_groove_x1 > tray_w/2,
       "Tray dovetail grooves must open through the leading +X edge");
assert(psu_pilot_edge_margin >= 1.0,
       "Measured PSU pilot holes need at least 1 mm of tray edge material");
assert(abs(psu_pilot_edge_margin-1.1)<0.01 &&
       psu_w == 110 && psu_h == 80 && psu_d == 37 &&
       psu_rear_mount_points == [[-52,-37],[52,37]],
       "PSU envelope, measured pilots, or tray edge material drifted");
assert(dovetail_groove_depth < tray_t-0.6,
       "Dovetail groove leaves too little tray roof thickness");
assert(abs(psu_support_plane_z-4.8)<0.01,
       "PSU bars and mounting bosses must use the 4.8 mm support plane");
assert(abs(detent_groove_clearance-0.3)<0.01 &&
       abs(detent_nominal_engagement-0.5)<0.01,
       "Integral detent engagement/clearance contract drifted");
assert(m3_button_head_max_d <= adapter_screw_head_d &&
       m3_psu_support_clearance >= 0.7,
       "Selected M3 button-head screw envelope must clear the PSU support plane");
assert(detent_anchor_x1 < -dock_w/2,
       "Flexure anchor must clear the dock's -X edge");

module dovetail_groove_cutter(yc) {
    hull() {
        translate([dovetail_groove_x0,
                   yc-dovetail_groove_bottom_w/2,-0.2])
            cube([dovetail_groove_len,dovetail_groove_bottom_w,dovetail_skin]);
        translate([dovetail_groove_x0,
                   yc-dovetail_groove_top_w/2,
                   dovetail_groove_depth-dovetail_skin])
            cube([dovetail_groove_len,dovetail_groove_top_w,
                  dovetail_skin+0.2]);
    }
}

module clipped_psu_mount_bosses() {
    intersection() {
        raised_psu_mount_bosses(base_z=tray_t,h=psu_support_height);
        translate([-tray_w/2,-tray_h/2,tray_t-0.5])
            cube([tray_w,tray_h,psu_support_height+1]);
    }
}

module snap_tray_plate() {
    difference() {
        rounded_plate(w=tray_w,h=tray_h,t=tray_t,r=2.5);
        for (pt=psu_rear_mount_points)
            translate([pt[0],pt[1],-0.2])
                cylinder(d=psu_mount_pilot_d,h=tray_t+0.4);
        for (yy=dovetail_y) dovetail_groove_cutter(yy);
        // The dock hard stop enters below the upper portion of this PSU lip.
        translate([dock_w/2-2,-tray_h/2-0.2,-0.1])
            cube([3.0,tray_h+0.4,dovetail_h+0.8+0.1]);
    }

    // The rails and PSU bosses share the same top plane at Z=4.8.
    for (xx=[-support_rail_x,support_rail_x])
        translate([xx-support_rail_w/2,-(psu_h-14)/2,
                   tray_t-psu_support_bar_overlap])
            cube([support_rail_w,psu_h-14,
                  psu_support_height+psu_support_bar_overlap]);
    clipped_psu_mount_bosses();
    translate([psu_w/2+psu_xy_clearance,-tray_h/2,tray_t-0.2])
        cube([2.2,tray_h,5.2]);
}

module integral_tray_detent_dock_frame() {
    // Cantilever and raised nose. The nose ramps down toward the free -Y end
    // and toward the +X insertion/withdrawal faces to cam under axial force.
    union() {
        translate([detent_beam_x0,0,detent_beam_z0])
            cube([detent_beam_width_x,detent_beam_free_len_y,
                  detent_beam_thickness_z]);
        hull() {
            translate([detent_groove_x0,0,detent_beam_z1-0.05])
                cube([0.6,3,0.1]);
            translate([detent_groove_x1-0.6,0,detent_peak_z-0.1])
                cube([0.6,3,0.1]);
        }
        // Fixed wrap-over anchor and roof link join the beam to the tray while
        // staying outside the dock edge until the link clears the top surface.
        translate([detent_anchor_x0,detent_anchor_y0,detent_beam_z0])
            cube([detent_anchor_x1-detent_anchor_x0,
                  detent_anchor_y1-detent_anchor_y0,
                  detent_anchor_roof_z1-detent_beam_z0]);
        hull() {
            translate([detent_anchor_link_x0,detent_anchor_link_y0,
                       detent_anchor_link_z0])
                cube([0.3,detent_anchor_link_y1-detent_anchor_link_y0,
                      detent_anchor_link_z1-detent_anchor_link_z0]);
            translate([detent_anchor_link_x1-0.3,
                       detent_anchor_link_y1-0.3,
                       detent_anchor_link_z0])
                cube([0.3,0.3,detent_anchor_link_z1-detent_anchor_link_z0]);
        }
    }
}

module snap_tray_with_detent() {
    union() {
        snap_tray_plate();
        translate([0,0,-tray_assembled_z])
            integral_tray_detent_dock_frame();
    }
}

module dovetail_rail(yc) {
    hull() {
        translate([dovetail_rail_x0,yc-dovetail_base_w/2,plate_t-0.2])
            cube([dovetail_rail_len,dovetail_base_w,dovetail_skin]);
        translate([dovetail_rail_x0,yc-dovetail_top_w/2,
                   plate_t+dovetail_h-dovetail_skin])
            cube([dovetail_rail_len,dovetail_top_w,dovetail_skin]);
    }
}

module backplane_mount_cutters(t=plate_t,extra=0.6) {
    local_mount_x = [
        psu_adapter_selected_columns[0]-128,
        psu_adapter_selected_columns[1]-128
    ];
    local_mount_y = psu_adapter_mount_row_offsets;
    for (xx=local_mount_x)
        for (yy=local_mount_y) {
            translate([xx,yy,-extra/2]) cylinder(d=adapter_screw_clearance_d,h=t+extra);
            translate([xx,yy,t-adapter_screw_head_depth])
                cylinder(d=adapter_screw_head_d,
                         h=adapter_screw_head_depth+extra/2);
            translate([xx,yy,-0.1])
                cylinder(d=boss_pocket_d,h=boss_pocket_depth+0.1);
        }
    // The unused X=128 upper/lower enclosure bosses intersect the dock. Relieve
    // their exposed tips while retaining every universal accessory boss.
    for (yy=[psu_adapter_mount_row_offsets[0],psu_adapter_mount_row_offsets[2]])
        translate([0,yy,-0.1])
            cylinder(d=boss_pocket_d,h=boss_pocket_depth+0.1);
}

module detent_groove_cutter() {
    // Blind groove from the underside of the dock; 0.3 mm remains above nose.
    translate([detent_groove_x0,detent_groove_y0,-0.1])
        cube([detent_groove_x1-detent_groove_x0,
              detent_groove_y1-detent_groove_y0,
              detent_groove_depth+0.1]);
}

module snap_dock() {
    difference() {
        union() {
            difference() {
                rounded_plate(w=dock_w,h=dock_h,t=plate_t,r=corner_r);
                backplane_mount_cutters();
                translate([0,0,-0.2]) linear_extrude(height=plate_t+0.4)
                    offset(r=2)
                        square([dock_relief_core_w,dock_relief_core_h],center=true);
            }
            for (yy=dovetail_y) dovetail_rail(yy);
            translate([dock_w/2-2,-tray_h/2,plate_t-0.2])
                cube([2,tray_h,dovetail_h+0.8]);
        }
        detent_groove_cutter();
    }
}

module assembled_psu_mount(tray_offset_x=0,show_psu=true) {
    snap_dock();
    translate([tray_offset_x,0,tray_assembled_z]) snap_tray_with_detent();
    if (show_psu)
        %translate([tray_offset_x-psu_w/2,-psu_h/2,psu_support_plane_z])
            cube([psu_w,psu_h,psu_d]);
}
