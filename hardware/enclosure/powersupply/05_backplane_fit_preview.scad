// Actual enclosure/boss fit and three tray travel states for issue #177.
// Docks sit on the measured 80/176 mm columns, centred at Y=90.5. The 3.7 mm
// boss projection and 1.2 mm registration-pocket engagement are included.
hinge_part = undef;
include <../direct_mount_enclosure.scad>;
include <service_tray_snap_latch_common.scad>;

module psu_fit_snapshot(dx=0,tray_x=0,show_tray=true) {
    translate([dx,0,0]) {
        color([0.16,0.2,0.24,0.75]) universal_equipment_backplane();
        // Local dock +Z maps into the cavity (-global Z); local Y is symmetric.
        translate([128,90.5,51.3]) rotate([180,0,0]) {
            color([0.8,0.42,0.12]) snap_dock();
            if (show_tray) {
                color([0.82,0.82,0.86,0.42])
                    translate([tray_x,0,tray_assembled_z]) snap_tray_with_detent();
                %translate([tray_x-psu_w/2,-psu_h/2,psu_support_plane_z])
                    cube([psu_w,psu_h,psu_d]);
            }
        }
    }
}

// Independent full-backplane assemblies expose all universal bosses and the
// selected six dock fixings at seated, partly inserted and withdrawn positions.
psu_fit_snapshot(0,0);
psu_fit_snapshot(280,-20);
psu_fit_snapshot(560,100);

// Local cutaway of the seated dock/tray detent, isolated from the backplane.
translate([0,-165,0])
    intersection() {
        union() {
            snap_dock();
            translate([0,0,tray_assembled_z]) snap_tray_with_detent();
        }
        translate([-63,-5,-2]) cube([12,12,8]);
    }
