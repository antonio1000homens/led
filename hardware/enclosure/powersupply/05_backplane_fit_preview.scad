// Issue #166 - assembled fit preview against the current backplane boss grid.
//
// The solid plate is the common dock/backplane interface geometry.
// Transparent geometry is the simulated current universal backplane interface.
// The six 7 mm bosses should enter the six shallow locating pockets in the
// adapter underside. This is the easiest file to inspect when checking alignment.

include <psu_mount_common.scad>;


base_adapter_plate(); // shared enclosure-interface test geometry

backplane_interface_preview();
