include <../direct_mount_enclosure.scad>;
include <../matrixportal/matrixportal_s3_mount.scad>;

boss_tip_z = universal_deep_front_z-adapter_boss_h+adapter_boss_overlap;

color([0.12,0.12,0.14]) hinged_equipment_base();
color([0.18,0.22,0.25]) universal_equipment_backplane();
color([0.30,0.30,0.34]) matrixportal_left_equipment_side();
color([0.30,0.30,0.34]) equipment_side("right");
color([0.45,0.45,0.50]) matrixportal_s3_dock_installed(boss_tip_z);
color([0.70,0.45,0.15]) matrixportal_s3_carrier_installed(boss_tip_z);
matrixportal_s3_reference_installed(boss_tip_z,true);
color([0.85,0.75,0.20]) matrixportal_s3_keepers_installed(boss_tip_z,0,true);
