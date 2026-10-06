# MatrixPortal S3 enclosure mount

This accessory mounts an Adafruit MatrixPortal S3 to the universal equipment
backplane without adding controller-specific holes to the enclosure itself.

## Mechanical source

The dimensions come from Adafruit's official Eagle board file in
`adafruit/Adafruit-MatrixPortal-S3-PCB`:

- PCB: **63.50 × 44.45 mm**;
- PCB thickness model: **1.60 mm**;
- four plated mounting holes: **2.50 mm**;
- native hole centres: X = **7.62 / 48.26 mm**, Y = **15.875 / 35.56 mm**;
- USB-C and Reset/Up/Down are on the same short edge;
- HUB75 connectors are on the opposite short edge.

The board is rotated 180° in the enclosure so the USB/button edge faces the
**outer right side** and HUB75 faces inward.

## Printable parts

- `../parts/08_matrixportal_s3_adapter_PRINT_1.scad` — flat detachable adapter
  plate with four M3 backplane holes and four MatrixPortal standoffs;
- `../parts/09_right_equipment_side_matrixportal_PRINT_1.scad` — replacement
  for the generic right end cap, adding the USB/button service opening.

Do **not** fit both the generic `05_right_equipment_side_PRINT_1` and the
MatrixPortal-specific `09_...` right side. The MatrixPortal side is a drop-in
replacement on the controller end of the complete four-module enclosure.

## Backplane attachment

The adapter uses four existing universal blind M3 bosses:

- X = **176 / 224 mm**;
- Y = **62.5 / 102.5 mm**.

Use four M3 screws sized for the existing blind boss depth. The adapter recesses
the screw heads below the board envelope.

## Board attachment

The four board standoffs are **6 mm** high. They provide 2.8 mm screw passages
and top-loading captive hex pockets sized for typical M2.5 nuts. Fit the nuts
before placing the MatrixPortal, then secure the PCB with M2.5 screws through
its official 2.5 mm plated holes.

## Service access

The MatrixPortal service edge sits at X = **254.5 mm**, immediately inside the
right end cap. The MatrixPortal-specific side removes a rounded **50 × 20 mm**
Y/Z service window around USB-C and the three right-angle buttons. The cut stays
forward of the enclosure's compact rear connector reinforcement.

## Preview

Open `../schematics/01_matrixportal_mount_ASSEMBLY.scad` to inspect the
backplane, adapter, PCB reference and MatrixPortal-specific right side together.
The PCB model is mechanical reference geometry only; connector bodies are
clearance approximations rather than manufacturing STEP geometry.
