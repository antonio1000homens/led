# Bambu Studio hinge-v2 slice

Open `03_left_controller_end_enclosure_HINGE_TEST_H2D_020_STANDARD.3mf` in Bambu Studio for the left controller end enclosure. This project contains the regenerated SCAD geometry and its sliced toolpath.

Validated with Bambu Studio 02.08.02.61, Bambu Lab H2D, 0.4 mm nozzle, `0.20 mm Standard @BBL H2D`, and Bambu PLA Basic. Tree supports are enabled and restricted to the build plate (`support_on_build_plate_only=1`). With that setup, Bambu reports no `FLOATING_REGION` category for this part. The standard profile with supports disabled still reports a floating cantilever for the STL, so open this project rather than re-slicing the STL with supports off.

The other three regenerated hinge-v2 STLs slice with supports disabled and no warning categories under the same machine, process, and filament profile. The moving-template sweep validator is collision-free at 0, 15, 30, 45, 60, 75, and 90 degrees.
