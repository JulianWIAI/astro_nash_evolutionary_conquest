"""
GalaxyManager.py — Planet unlock progression driven by cooperative stability.

A planet is unlocked when the species on the previously unlocked planet
maintain mutual cooperation for STABILITY_DURATION (60 s) of consecutive
game-time.  Ignaros is always unlocked at the start; each successive planet
in PLANET_ORDER is gated behind the one before it.

Stability drains at half the build-up rate when cooperation breaks, so
brief interruptions are forgiving but sustained competing resets progress.
"""

_STABILITY_DURATION    = 30.0   # seconds of cooperation needed to unlock next (was 60)
_DRAIN_RATE            = 0.5    # multiplier on dt when stability is draining
_NOTIFICATION_DURATION = 4.0    # seconds to display the unlock banner
_BUILDING_ACCEL        = 1.5    # stability speed multiplier when Church or MilBase is built
_UNLOCK_EP_BONUS       = 50     # EP granted to the player when a new planet is unlocked

# Must match the planet names defined in Simulation.create_planets()
_PLANET_ORDER = ["Ignaros", "Kharenos", "Venomara", "Crystalis", "Terranova", "Glacius"]


class GalaxyManager:
    """
    Manages planet lock/unlock state and cooperative-stability timers.

    Stability is advanced only while the player is viewing that planet in
    SIMULATION state and both species chose Cooperate last Nash tick.

    Attributes:
        notification_text  : Text for the current unlock banner (empty = none).
        notification_timer : Seconds remaining for the banner (<=0 = hidden).
    """

    def __init__(self, planets: list, stability_duration: float = _STABILITY_DURATION):
        """
        Lock all planets except Ignaros and store planet references.

        Args:
            planets            : All Planet instances from SimulationManager.
            stability_duration : Seconds of cooperation required to unlock the
                                 next planet.  Passed from DifficultyManager so
                                 EASY/MEDIUM/HARD each feel appropriately paced.
        """
        self._planet_map: dict       = {p.name: p for p in planets}
        self._stability:  dict       = {name: 0.0 for name in _PLANET_ORDER}
        self._stability_duration     = stability_duration

        self.notification_text  = ""
        self.notification_timer = 0.0
        self.milestone_ep       = 0   # set to _UNLOCK_EP_BONUS on unlock; main.py reads & resets

        for planet in planets:
            planet.is_locked = (planet.name != _PLANET_ORDER[0])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tick(self, dt: float, selected_planet, last_interaction,
             building_manager=None):
        """
        Advance stability timers for the planet currently being viewed.

        Args:
            dt               : Effective delta time (already time-scaled).
            selected_planet  : Planet in the detail view, or None.
            last_interaction : (act_a, act_b, …) tuple from SimulationManager,
                               or None when no interaction has resolved yet.
            building_manager : Optional BuildingManager — if present and the
                               planet has a Church or MilitaryBase, stability
                               accumulates at _BUILDING_ACCEL speed.
        """
        if self.notification_timer > 0:
            self.notification_timer -= dt

        if not selected_planet or selected_planet.is_locked:
            return

        name = selected_planet.name
        if name not in self._stability:
            return

        both_cooperate = (
            last_interaction is not None
            and last_interaction[0] == "cooperate"
            and last_interaction[1] == "cooperate"
        )

        if both_cooperate:
            effective_dt = dt
            if building_manager:
                built = {b.name for b in building_manager.get_buildings(name)}
                if "Church" in built or "MilitaryBase" in built:
                    effective_dt = dt * _BUILDING_ACCEL

            self._stability[name] = min(self._stability_duration,
                                        self._stability[name] + effective_dt)
            if self._stability[name] >= self._stability_duration:
                self._unlock_next(name)
                self._stability[name] = 0.0   # reset so trigger fires only once
        else:
            self._stability[name] = max(
                0.0, self._stability[name] - dt * _DRAIN_RATE
            )

    def stability_progress(self, planet_name: str) -> float:
        """Return a 0.0–1.0 fraction representing unlock-stability progress."""
        t = self._stability.get(planet_name, 0.0)
        return min(1.0, t / self._stability_duration)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _unlock_next(self, planet_name: str):
        """Unlock the planet immediately after planet_name in the order list."""
        if planet_name not in _PLANET_ORDER:
            return
        idx      = _PLANET_ORDER.index(planet_name)
        next_idx = idx + 1
        if next_idx >= len(_PLANET_ORDER):
            return
        next_name   = _PLANET_ORDER[next_idx]
        next_planet = self._planet_map.get(next_name)
        if next_planet and next_planet.is_locked:
            next_planet.is_locked      = False
            self.notification_text     = f"{next_name}  UNLOCKED"
            self.notification_timer    = _NOTIFICATION_DURATION
            self.milestone_ep          = _UNLOCK_EP_BONUS
