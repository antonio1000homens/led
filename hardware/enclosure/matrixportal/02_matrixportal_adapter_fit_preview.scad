// Context view of adapter, MatrixPortal reference and actual enclosure shell.
// Start fully open for visibility; override panel_angle to inspect intermediate
// positions. The canonical enclosure validator checks the complete angle sweep.
panel_angle = 90;
include <../direct_mount_enclosure.scad>;
include <matrixportal_adapter_common.scad>;

color([0.16,0.2,0.24,0.28]) universal_equipment_backplane();
color([0.2,0.24,0.28,0.6]) equipment_side("right");
color([0.72,0.4,0.12,0.9]) matrixportal_adapter_installed();

// Overlay real #177 dock/tray/PSU geometry in the same enclosure coordinates.
include <../powersupply/service_tray_snap_latch_common.scad>;
translate([128,90.5,51.3]) rotate([180,0,0]) {
    color([0.82,0.48,0.14,0.65]) snap_dock();
    color([0.7,0.72,0.76,0.4])
        translate([0,0,tray_assembled_z]) snap_tray_with_detent();
    %translate([-psu_w/2,-psu_h/2,psu_support_plane_z])
        cube([psu_w,psu_h,psu_d]);
}

// Faint closed panel check; the canonical module supplies the full moving leaf.
%color([0.1,0.2,0.8,0.12]) moving_panel_at_angle(panel_angle);
