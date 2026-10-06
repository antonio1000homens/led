include <../direct_mount_enclosure.scad>;
include <../matrixportal/matrixportal_s3_mount.scad>;

boss_tip_z = universal_deep_front_z-adapter_boss_h+adapter_boss_overlap;

color([0.12,0.12,0.14]) hinged_equipment_base();
color([0.18,0.22,0.25]) universal_equipment_backplane();
color([0.30,0.30,0.34]) equipment_side("left");
color([0.30,0.30,0.34]) matrixportal_right_equipment_side();
color([0.70,0.45,0.15]) matrixportal_s3_adapter_installed(boss_tip_z);
matrixportal_s3_reference_installed(boss_tip_z,true);
