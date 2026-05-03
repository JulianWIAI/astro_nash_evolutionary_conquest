"""
TimeController.py — Global time-scale controller for the simulation.

Every dt-dependent operation in Simulation._tick_planet() is multiplied
by time_scale before use, so Pause / Normal / Fast Forward affect the
entire simulation uniformly without touching individual subsystems.

Keyboard bindings (wired in main.py):
  P — toggle pause / resume
  F — toggle fast-forward / normal
  N — force-return to normal speed
"""


class TimeController:
    """
    Manages the simulation time scale with three preset speeds.

    Class constants
    ---------------
    PAUSE  : 0.0 — simulation frozen; no dt advances.
    NORMAL : 1.0 — real-time, one game-second per wall-second.
    FAST   : 2.0 — double speed, useful for watching evolution unfold.

    Attributes:
        time_scale : Current multiplier applied to every raw dt value.
    """

    PAUSE  = 0.0
    NORMAL = 1.0
    FAST   = 2.0

    def __init__(self):
        self.time_scale = self.NORMAL
        self._pre_pause = self.NORMAL   # last non-zero scale, restored on resume

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def set_pause(self):
        """Freeze the simulation, remembering the current speed for resume."""
        if self.time_scale != self.PAUSE:
            self._pre_pause = self.time_scale
            self.time_scale = self.PAUSE

    def set_normal(self):
        """Return to 1× real-time speed."""
        self.time_scale = self.NORMAL
        self._pre_pause = self.NORMAL

    def set_fast(self):
        """Run the simulation at 2× speed."""
        self.time_scale = self.FAST
        self._pre_pause = self.FAST

    def toggle_pause(self):
        """
        Pause if currently running; resume at the pre-pause speed if paused.
        Bound to the P key in the main loop.
        """
        if self.is_paused:
            self.time_scale = self._pre_pause if self._pre_pause else self.NORMAL
        else:
            self.set_pause()

    def toggle_fast(self):
        """
        Switch between FAST and NORMAL (ignores paused state).
        Bound to the F key in the main loop.
        """
        if self.time_scale == self.FAST:
            self.set_normal()
        else:
            self.set_fast()

    # ------------------------------------------------------------------
    # Read-only helpers
    # ------------------------------------------------------------------

    @property
    def is_paused(self) -> bool:
        """True when the simulation is completely frozen."""
        return self.time_scale == self.PAUSE

    @property
    def label(self) -> str:
        """Short human-readable label for the HUD indicator."""
        if self.time_scale == self.PAUSE:
            return "PAUSED"
        if self.time_scale == self.FAST:
            return "FAST ×2"
        return "NORMAL ×1"
