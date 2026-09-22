// Complete nominal rear assembly preview for the four-panel LED enclosure.
// This is an assembly/view file, not a printable part.
//
// Front-view numbering:
//   Panel 1 | Panel 2 | Panel 3 | Panel 4
//
// When viewing this file from the rear, Panel 1 is still at global x=0;
// rotate the OpenSCAD camera as needed rather than renumbering the modules.

part = "__library__";
include <direct_mount_enclosure.scad>;
include <matrixportal_s3_REFERENCE.scad>;

panel_pitch = 256;
joiner_z = 11.8;
carrier_z = 16;

module complete_enclosure_assembly(show_guides=true) {
    // ---------- Backplanes ----------
    color([0.20,0.20,0.22])
        translate([0,0,0]) backplane(false);
    color([0.24,0.24,0.26])
        translate([panel_pitch,0,0]) backplane(false);
    color([0.20,0.20,0.22])
        translate([2*panel_pitch,0,0]) backplane(false);
    color([0.24,0.24,0.26])
        translate([3*panel_pitch,0,0]) backplane(true);

    // ---------- Recessed seam joiners ----------
    for (x=[240,496,752])
        color([0.55,0.55,0.58])
            translate([x,40,joiner_z]) module_joiner();

    // ---------- 1000 mm reinforcement rods ----------
    module rod_x(y) {
        color([0.70,0.70,0.72])
            translate([12,y,rod_z])
                rotate([0,90,0])
                    cylinder(d=8,h=1000,$fn=64);
    }
    rod_x(rod_y_bottom);
    rod_x(rod_y_top);

    // ---------- Electronics carriers ----------
    // Panel 1: MatrixPortal carrier / HUB75 input end.
    color([0.08,0.08,0.09])
        translate([6,28,carrier_z]) matrixportal_mount();

    // Simplified MatrixPortal board reference to show the left-side service overhang.
    translate([
        6 + matrixportal_pcb_x,
        28 + matrixportal_pcb_y,
        carrier_z + matrixportal_standoff_z + matrixportal_standoff_h
    ])
        matrixportal_s3_reference();

    // Panel 2: power-distribution carrier.
    color([0.10,0.13,0.16])
        translate([panel_pitch + 6,28,carrier_z]) power_distribution_mount();

    // ---------- Assembly guides ----------
    if (show_guides) {
        // Panel seam planes: these should remain exactly at 256, 512, and 768 mm.
        for (x=[256,512,768])
            color([0.95,0.20,0.20,0.20])
                translate([x-0.15,0,-1]) cube([0.3,module_h,24]);

        // Nominal 1024 mm overall printed-panel envelope.
        color([0.20,0.45,0.95,0.10])
            translate([0,0,-0.5]) cube([1024,module_h,0.5]);
    }

}

// Lightweight assembly for orthographic SVG projection.
//
// This deliberately imports the already-validated printable STL meshes rather
// than re-running every OpenSCAD boolean in direct_mount_enclosure.scad for
// each view. Placement constants are shared with the parametric assembly above.
module complete_enclosure_projection_mesh() {
    // Backplanes.
    translate([0,0,0])
        import("01_backplane_module_PRINT_3.stl", convexity=10);
    translate([panel_pitch,0,0])
        import("01_backplane_module_PRINT_3.stl", convexity=10);
    translate([2*panel_pitch,0,0])
        import("01_backplane_module_PRINT_3.stl", convexity=10);
    translate([3*panel_pitch,0,0])
        import("01b_backplane_right_end_PRINT_1.stl", convexity=10);

    // Recessed seam joiners.
    for (x=[240,496,752])
        translate([x,40,joiner_z])
            import("02_module_joiner_PRINT_3.stl", convexity=10);

    // Reinforcement rods.
    for (y=[rod_y_bottom,rod_y_top])
        translate([12,y,rod_z])
            rotate([0,90,0])
                cylinder(d=8,h=1000,$fn=48);

    // Panel 1 MatrixPortal carrier plus simplified PCB reference.
    translate([6,28,carrier_z])
        import("04_matrixportal_mount_PRINT_1.stl", convexity=10);
    translate([
        6 + matrixportal_pcb_x,
        28 + matrixportal_pcb_y,
        carrier_z + matrixportal_standoff_z + matrixportal_standoff_h
    ])
        matrixportal_s3_reference();

    // Panel 2 power-distribution carrier.
    translate([panel_pitch + 6,28,carrier_z])
        import("05_power_distribution_mount_PRINT_1.stl", convexity=10);
}

// Opening this file directly still shows the complete 3D assembly.
// Projection wrapper files set suppress_complete_assembly=true before include.
if (is_undef(suppress_complete_assembly) || !suppress_complete_assembly)
    complete_enclosure_assembly(true);
