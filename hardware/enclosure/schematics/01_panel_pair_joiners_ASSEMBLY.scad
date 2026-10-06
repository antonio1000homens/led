// Four-panel closed assembly with one removable seam joiner per panel pair.
include <../panel_pair_joiner.scad>;

complete_direct_mount_assembly(open_angle=0);

color([0.95,0.45,0.10])
    all_panel_pair_joiners_installed();
