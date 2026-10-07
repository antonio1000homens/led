# MatrixPortal S3 click dock

This accessory mounts an Adafruit MatrixPortal S3 from the **detachable left
equipment side**, keeping controller-specific attachment off the universal
backplane.

The controller uses a **side-carried two-part service dock**:

1. the fixed dock snaps into two keyed PETG receiver channels built into the
   MatrixPortal-specific CAD-left / **front-view-right** side;
2. the dock has **no backplane screws, boss sockets, locating pockets or other
   capturing features**;
3. its solid rear face runs **0.40 mm clear of the universal backplane boss
   tips**, so the side can withdraw laterally without catching them;
4. the MatrixPortal stays attached to a raised removable carrier;
5. the carrier still slides on captive dovetails for separate bench servicing.

The complete **side + dock + carrier + MatrixPortal** is therefore one removable
service assembly. Pulling the front-right side outward brings the controller
with it and exposes the USB-C, buttons and HUB75 connectors without opening the
main enclosure.

## Mechanical source

The board dimensions come from Adafruit's official Eagle board file in
`adafruit/Adafruit-MatrixPortal-S3-PCB`:

- PCB: **63.50 × 44.45 mm**;
- PCB thickness model: **1.60 mm**;
- four plated mounting holes: **2.50 mm**;
- native hole centres: X = **7.62 / 48.26 mm**, Y = **15.875 / 35.56 mm**;
- USB-C and Reset/Up/Down are on the same short edge;
- HUB75 connectors are on the opposite short edge.

The board uses its native XY orientation so the USB/button edge faces the
**outer left side** and HUB75 faces inward.

The Eagle source confirms a mirrored HUB75 connector on the underside, but does
not provide a reliable mechanical component height. The CAD therefore uses a
conservative **9 mm underside connector envelope** and the carrier raises the
PCB by **11.5 mm**, leaving **2.5 mm nominal clearance**. If the physical
connector proves taller, tune `mp_underside_connector_h` rather than moving the
official mounting-hole pattern.

## Printable parts

- `../parts/08_matrixportal_s3_dock_PRINT_1.scad` — fixed side-carried dock
  with two keyed snap tabs, a solid backplane-facing surface, two captive
  dovetail rails, click detent and seated stop;
- `../parts/09_left_equipment_side_matrixportal_PRINT_1.scad` — replacement
  left end cap with the enlarged carrier/service opening plus the two matching
  inward-facing dock receiver channels;
- `../parts/10_matrixportal_s3_carrier_PRINT_1.scad` — removable raised
  controller carrier with four 11.5 mm standoffs, integrated locating/locking
  pins and a low-profile pull tab;
- `../parts/11_matrixportal_s3_keeper_PRINT_1.scad` — tool-free slide-lock
  keeper bar. **Print two copies**, one for each mounting-hole column.

Do **not** fit both the generic `04_left_equipment_side_PRINT_1` and the
MatrixPortal-specific `09_...` left side.

## Side-carried dock attachment

The MatrixPortal-specific CAD-left / **front-view-right** side is the dock's
**only structural attachment**. Two receiver channels sit just outside the
52 mm-high service aperture: one below and one above. Matching tabs on the dock
slide into these channels from the enclosure interior and click into place.

The dock deliberately has **no geometry that wraps around, screws into or keys
against the backplane**. Its rear face is solid and the installed dock plane is
offset **0.40 mm toward the LED panel** from the universal boss-tip plane. This
provides running clearance when the side is pulled outward.

The boss grid therefore remains completely independent of MatrixPortal service.
If the long dock flexes unusually far, the boss tips can act only as
non-capturing bump stops after the 0.40 mm gap is consumed; they are not part of
normal retention.

### Side-removal service sequence

1. disconnect any external cable that would prevent the side moving outward;
2. release the detachable front-right side from the enclosure;
3. pull the side outward — the fixed dock, carrier and MatrixPortal move with it;
4. the USB-C, Reset/Up/Down and HUB75 connections are then accessible without
   opening the hinged enclosure;
5. if required on the bench, pull the carrier from its dovetails separately.

## Carrier / click interface

The carrier inserts from **left to right**:

- two captive dovetails guide and retain it in Z;
- **0.30 mm** dovetail running clearance is built into the grooves;
- one rail has a shallow ramped detent with **0.25 mm nominal click
  interference**;
- the matching carrier roof pocket lets the detent relax once fully seated;
- a fixed stop behind the carrier leading edge prevents over-insertion;
- a 3 mm low-profile pull tab sits inside the left service opening for removal.

The detent is intentionally a modest PETG interference rather than a rigid
latch. It should click positively while still releasing with a deliberate pull.
Physical fit testing should tune `mp_detent_extra_h` or
`mp_dovetail_clearance` in small increments if needed.

## Tool-free board attachment and underside clearance

The carrier now needs **no MatrixPortal screws or nuts**.

Each 11.5 mm standoff has a fixed **2.20 mm printed locating pin**. The official
PCB holes are 2.50 mm, leaving 0.30 mm diametral installation clearance. Place
the MatrixPortal straight down over the four pins until the PCB rests on the
standoff shoulders.

Each pin then continues above the PCB to a reduced **1.60 mm locking neck** and
a full-diameter tip. Lock the board with **two printed keeper bars**:

1. place one keeper over each X column of two pins using the round entry holes;
2. slide the keeper approximately **2 mm** toward the board's lower-Y edge;
3. both pin necks pass a slightly undersized PETG throat and click into the
   terminal pockets;
4. the full-diameter pin tips prevent the locked keeper lifting off.

The keeper has local feet only around the mounting-hole keepouts. Its bridge
sits **4.5 mm above the PCB top surface**, avoiding the known USB/button
components and staying left of the modelled HUB75 connector envelope. To remove
the board, slide both keepers back through their click throats, lift them off,
then lift the PCB straight off the four locating pins.

The **11.5 mm** standoff height continues to clear the conservative 9 mm
underside connector envelope by 2.5 mm.

## Service opening

The MatrixPortal service edge remains at X = **1.5 mm**. The MatrixPortal side
now has a rounded **52 × 31 mm** Y/Z opening so the complete carrier + raised PCB
can pass through the left end while keeping USB-C and the three right-angle
buttons accessible.

## Printing

The dock, carrier and keeper have been validated with:

- Bambu Lab H2D 0.4 nozzle;
- 0.20 mm Standard;
- Bambu PETG Basic;
- Textured PEI Plate;
- supports **off**.

All three slice without a floating-region warning. The MatrixPortal-specific side
retains the enclosure side part's existing support/floating-region behaviour.

## Preview

Open `../schematics/01_matrixportal_mount_ASSEMBLY.scad` to inspect the
side-mounted fixed dock, the two side receiver channels, passive backplane-boss
registration, raised carrier, locked keeper bars, PCB reference and conservative
underside connector envelope together.
