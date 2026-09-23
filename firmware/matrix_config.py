"""Non-user-tunable timing limits for the four-panel MatrixPortal S3."""

# Issue #70 hardware experiment.
#
# The local board agent only needs to change this ONE value between runs,
# upload the branch to CIRCUITPY, and capture serial output:
#
#   A7 / A8 / A10 = current target-FPS refresh control
#   B7 / B8 / B10 / B12 = immediate refresh + application-owned pacing
#   C7 / C8 / C10 = CircuitPython auto-refresh + application animation cadence
MATRIX_EXPERIMENT_PRESET = "B8"

_MATRIX_EXPERIMENT_PRESETS = {
    "A7": ("target_fps", 7, 7.0),
    "A8": ("target_fps", 8, 8.0),
    "A10": ("target_fps", 10, 10.0),
    "B7": ("immediate", 7, 7.0),
    "B8": ("immediate", 8, 8.0),
    "B10": ("immediate", 10, 10.0),
    # B12 intentionally increases animation cadence without increasing text
    # travel speed, isolating smoothness from readability/speed changes.
    "B12": ("immediate", 12, 8.0),
    "C7": ("auto_refresh", 7, 7.0),
    "C8": ("auto_refresh", 8, 8.0),
    "C10": ("auto_refresh", 10, 10.0),
}

try:
    (
        MATRIX_PRESENTATION_MODE,
        MATRIX_REFRESH_FPS,
        TODOIST_MARQUEE_SPEED,
    ) = _MATRIX_EXPERIMENT_PRESETS[MATRIX_EXPERIMENT_PRESET]
except KeyError:
    raise ValueError("Unknown MATRIX_EXPERIMENT_PRESET: {}".format(MATRIX_EXPERIMENT_PRESET))

# One bit per RGB channel keeps maximum refresh headroom across four chained
# panels while retaining the board's eight required colours.
MATRIX_BIT_DEPTH = 1
TODOIST_MARQUEE_PAUSE_SECONDS = 1.5

# Issue #91/#94 adaptive partial-scene cadence. These are animation update
# cadences, not framebuffer refresh modes; Mode B remains the presentation
# strategy and only changed persistent-scene state is presented.
TODOIST_MARQUEE_FPS = 8
TODOIST_PAGE_SLIDE_FPS = 12
HEADER_SLIDE_FPS = 12
DEPARTURES_CALLING_FPS = 12

# Keep the experiment profiles in one table so cadence comparisons cannot
# accidentally change animation speed or the lower-level presentation mode.
# ``baseline`` is the production control. The other profiles are opt-in board
# experiments for issue #94.
MATRIX_ANIMATION_PROFILES = {
    "baseline": {
        "todoist_marquee": MATRIX_REFRESH_FPS,
        "todoist_page_slide": MATRIX_REFRESH_FPS,
        "header_slide": MATRIX_REFRESH_FPS,
        "departures_calling": MATRIX_REFRESH_FPS,
    },
    "adaptive": {
        "todoist_marquee": TODOIST_MARQUEE_FPS,
        "todoist_page_slide": TODOIST_PAGE_SLIDE_FPS,
        "header_slide": HEADER_SLIDE_FPS,
        "departures_calling": DEPARTURES_CALLING_FPS,
    },
    "transition_15": {
        "todoist_marquee": TODOIST_MARQUEE_FPS,
        "todoist_page_slide": 15,
        "header_slide": 15,
        "departures_calling": DEPARTURES_CALLING_FPS,
    },
    "transition_20": {
        "todoist_marquee": TODOIST_MARQUEE_FPS,
        "todoist_page_slide": 20,
        "header_slide": 20,
        "departures_calling": DEPARTURES_CALLING_FPS,
    },
}

# Keep the pre-#91 fixed B8 scheduling model reproducible until a physical
# comparison demonstrates a clear visual improvement. A board-local
# settings_local.py may opt into "adaptive" for the P1 experiment.
MATRIX_ANIMATION_PROFILE = "baseline"
try:
    import settings_local as _animation_settings_local
    MATRIX_ANIMATION_PROFILE = getattr(
        _animation_settings_local,
        "MATRIX_ANIMATION_PROFILE",
        MATRIX_ANIMATION_PROFILE,
    )
except ImportError:
    pass
if MATRIX_ANIMATION_PROFILE not in MATRIX_ANIMATION_PROFILES:
    raise ValueError(
        "MATRIX_ANIMATION_PROFILE must be one of {}".format(
            ", ".join(sorted(MATRIX_ANIMATION_PROFILES))
        )
    )

# Aggregate serial summaries are deliberately infrequent so measurement does
# not materially change MatrixPortal timing.
MATRIX_STATS_INTERVAL_SECONDS = 20.0
