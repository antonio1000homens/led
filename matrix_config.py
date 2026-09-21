"""Non-user-tunable timing limits for the four-panel MatrixPortal S3."""

# Issue #70 presentation experiment.
#
# Change only these three values between hardware runs:
#
#   MATRIX_PRESENTATION_MODE = "target_fps"   # Mode A: current behaviour
#   MATRIX_PRESENTATION_MODE = "immediate"    # Mode B: refresh(None) + app pacing
#   MATRIX_PRESENTATION_MODE = "auto_refresh" # Mode C: CircuitPython owns refresh
#
# MATRIX_REFRESH_FPS is the manual refresh target in Mode A. In Modes B/C it
# is the application animation-update cadence. Keep TODOIST_MARQUEE_SPEED equal
# to it for the 7/7, 8/8 and 10/10 comparison so moving frames advance by
# approximately one logical pixel per animation tick.
MATRIX_PRESENTATION_MODE = "target_fps"
MATRIX_BIT_DEPTH = 1
MATRIX_REFRESH_FPS = 7
TODOIST_MARQUEE_SPEED = 7.0
TODOIST_MARQUEE_PAUSE_SECONDS = 1.5

# Aggregate serial summaries are deliberately infrequent so measurement does
# not materially change MatrixPortal timing.
MATRIX_STATS_INTERVAL_SECONDS = 20.0
