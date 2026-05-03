"""
DifficultyManager.py — Three-tier difficulty scaling.

Profiles
--------
  EASY   : Generous resources, rare auto-disasters, +2 EP per resource spawn,
           slow species mutation.
  MEDIUM : Balanced default.
  HARD   : Scarce resources, frequent auto-disasters, no EP from spawning,
           fast mutation.

Usage
-----
  Instantiate once before _new_game_objects() and pass it in:

      difficulty = DifficultyManager()          # default MEDIUM
      sim = SimulationManager(difficulty)

  The instance persists across New Game restarts so the player's chosen
  difficulty is remembered between sessions.  Cycle with ← / → on the menu.
"""

_PROFILES = {
    "EASY": {
        "resource_drain_rate":  0.5,    # divides regen rate  → lower = more regen
        "disaster_frequency":   0.002,  # probability per effective second of auto-disaster
        "evolution_point_gain": 2,      # EP awarded when player triggers resource spawn
        "mutation_rate":        0.05,   # magnitude passed to Species.mutate()
        # Cooperation tuning ------------------------------------------------
        "starting_coop_weight": 2.5,    # species cooperate ~75% at game start
        "stability_duration":   12.0,   # seconds of cooperation to unlock next planet
    },
    "MEDIUM": {
        "resource_drain_rate":  1.0,
        "disaster_frequency":   0.005,
        "evolution_point_gain": 1,
        "mutation_rate":        0.1,
        "starting_coop_weight": 1.5,    # species need a little nudging
        "stability_duration":   20.0,
    },
    "HARD": {
        "resource_drain_rate":  2.0,
        "disaster_frequency":   0.01,
        "evolution_point_gain": 0,
        "mutation_rate":        0.15,
        "starting_coop_weight": 1.0,    # default — player must earn cooperation
        "stability_duration":   30.0,
    },
}

_ORDER = ["EASY", "MEDIUM", "HARD"]


class DifficultyManager:
    """
    Cycles between EASY / MEDIUM / HARD and exposes the active profile values
    as plain attributes so callers need no knowledge of the profile dict.

    Attributes:
        resource_drain_rate  : Divisor on resource regeneration (higher = harder).
        disaster_frequency   : Auto-disaster probability per effective second.
        evolution_point_gain : EP rewarded per player resource-spawn action.
        mutation_rate        : Passed to Species.mutate() each evolution tick.
    """

    def __init__(self, default: str = "MEDIUM"):
        self._index = _ORDER.index(default)
        self._apply()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def label(self) -> str:
        """Current difficulty name: 'EASY', 'MEDIUM', or 'HARD'."""
        return _ORDER[self._index]

    def cycle_next(self):
        """Advance to the next (harder) difficulty, wrapping at the end."""
        self._index = (self._index + 1) % len(_ORDER)
        self._apply()

    def cycle_prev(self):
        """Step back to the previous (easier) difficulty, wrapping at start."""
        self._index = (self._index - 1) % len(_ORDER)
        self._apply()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _apply(self):
        """Copy the active profile values into public instance attributes."""
        p = _PROFILES[_ORDER[self._index]]
        self.resource_drain_rate  = p["resource_drain_rate"]
        self.disaster_frequency   = p["disaster_frequency"]
        self.evolution_point_gain = p["evolution_point_gain"]
        self.mutation_rate        = p["mutation_rate"]
        self.starting_coop_weight = p["starting_coop_weight"]
        self.stability_duration   = p["stability_duration"]
