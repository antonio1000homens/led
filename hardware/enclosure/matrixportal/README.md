# MatrixPortal S3 right-side adapter

Issue #178 adds a screw-on adapter to the right-hand area of the universal
backplane. `matrixportal_adapter_common.scad` holds the shared prototype
geometry. The print wrapper produces the plate/standoffs as one part; the fit
preview shows the actual enclosure, detachable right side, PSU dock/tray and
reference PSU envelope. The reference PCB itself is approximate: verify it
with the real board before treating the fit as accepted.

The 66 × 60 × 3.2 mm adapter spans enclosure X=189–255 and Y=60.5–120.5,
registers on the three X=224 bosses at Y=71.5/90.5/109.5, and leaves 2 mm
nominal plate clearance to the PSU dock edge at X=187. The landscape PCB is
rotated 180° in plane so USB-C/buttons face the right side. For service, open
the panel and remove that side. The side edge is only 2 mm from the nominal PCB
edge, so check the actual USB connector housing and plug clearance physically.

## Print and overlay

Generate the printable adapter from its SCAD wrapper:

```sh
openscad -o hardware/enclosure/stl/08_matrixportal_adapter_PRINT_1.stl \
  hardware/enclosure/matrixportal/01_matrixportal_adapter_PRINT_1.scad
```

Export the 1:1 hole overlay as SVG and print at Actual Size (100%):

```sh
openscad -o /tmp/matrixportal-hole-overlay.svg \
  hardware/enclosure/matrixportal/03_matrixportal_hole_overlay_1_TO_1.scad
```

The overlay has a 20 mm scale bar. Verify all four holes against the real board
before printing the full adapter. Automated mesh and preview checks are run by
`hardware/enclosure/scripts/validate_matrixportal_adapter.py`.

## Prototype hardware

- 3 × enclosure fasteners, nominal M3 size; determine length and engagement
  after confirming whether the Ø3.4 blind holes are tapped or need another
  retention method.
- 4 × M2.5 screws and 4 × M2.5 hex nuts for PCB retention. The adapter uses
  side-loaded, nominal 5 mm across-flats nut pockets.
- Choose screw lengths after measuring the actual PCB, washer/head and nut
  stack. Keep screw tips clear of the board and surrounding enclosure.

The 8 mm standoffs and captive-nut pockets are prototype dimensions. Measure
board underside components, USB/button hardware, HUB75 and power connectors,
cables, panel closure and side-wall clearance. CAD/slicer validation does not
replace a 1:1 overlay or physical assembly test.
