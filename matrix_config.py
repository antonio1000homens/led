"""Non-user-tunable timing limits for the four-panel MatrixPortal S3."""

# The RGBMatrix scan timing is hardware-managed. These values limit how often
# CircuitPython replaces a complete displayio frame, which prevents the app
# from requesting a rate the board cannot compose or present reliably.
# One bit per RGB channel gives eight colours. It materially improves scan
# headroom across four chained panels while retaining the white, amber, red,
# green, blue, cyan, magenta, and black colours used by the board.
MATRIX_BIT_DEPTH = 1
MATRIX_REFRESH_FPS = 7
TODOIST_MARQUEE_SPEED = 4.0
TODOIST_MARQUEE_PAUSE_SECONDS = 1.5
