# Mechanical reference views

The hinged direct-mount design is canonical.

Current assembly views:

- `00_hinged_enclosure_ASSEMBLY.scad` — single module, open service position;
- `00_hinged_enclosure_CLOSED_ASSEMBLY.scad` — single module, closed position;
- `00_complete_enclosure_OPEN_ASSEMBLY.scad` — complete four-module display,
  all panel leaves open to 90°;
- `00_complete_enclosure_CLOSED_ASSEMBLY.scad` — complete four-module display,
  all panel leaves closed;
- `matrixportal_s3_REFERENCE.scad` — non-printing MatrixPortal S3 mechanical
  reference retained for future detachable adapter work.

The old non-hinged complete assembly was removed when issue #133 committed the
repository to the hinged architecture. The two complete assembly views above
restore full-system visualisation using the current hinged modular geometry.
