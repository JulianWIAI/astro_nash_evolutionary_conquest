"""
BuildingManager.py — Per-planet building slot management.

Each planet can hold up to MAX_SLOTS buildings.  The manager mediates
construction (spending evolution points, enforcing slot limits) and routes
the three simulation hooks (tick, disaster, construct) to the appropriate
Building instances so Simulation.py stays clean.
"""

MAX_SLOTS = 3


class BuildingManager:
    """
    Manages all buildings across every planet.

    Internal state is a dict mapping planet_name → list[Building].
    The list is created on first access so planets require no pre-registration.
    """

    def __init__(self):
        self._slots: dict[str, list] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_buildings(self, planet_name: str) -> list:
        """Return the (possibly empty) list of buildings on the named planet."""
        return self._slots.get(planet_name, [])

    def construct(self, building, planet, game_theory, controller) -> bool:
        """
        Attempt to place a building on a planet.

        Checks (in order):
          1. Building type not already present on this planet.
          2. Planet has a free slot (< MAX_SLOTS).
          3. Player has enough evolution points (>= building.cost).

        Args:
            building    : A Building instance to place.
            planet      : The target Planet.
            game_theory : Passed to building.on_construct().
            controller  : PlayerController — evolution points are deducted here.

        Returns:
            bool: True if the building was successfully placed, False otherwise.
        """
        slots      = self._slots.setdefault(planet.name, [])
        built_names = {b.name for b in slots}

        if building.name in built_names:
            return False
        if len(slots) >= MAX_SLOTS:
            return False
        if controller.evolution_points < building.cost:
            return False

        controller.evolution_points -= building.cost
        building.is_constructed = True
        building.on_construct(game_theory)
        slots.append(building)
        return True

    def tick(self, dt: float, planet, game_theory):
        """
        Call on_tick for every building on the given planet.

        Args:
            dt          : Effective delta time (already time-scaled).
            planet      : The planet currently being simulated.
            game_theory : Passed to each building's on_tick hook.
        """
        for building in self._slots.get(planet.name, []):
            building.on_tick(dt, planet, game_theory)

    def apply_disaster(self, planet_name: str, base_damage: int) -> int:
        """
        Filter disaster damage through each building's on_disaster hook.

        Buildings are applied in construction order so later buildings
        reduce whatever damage the earlier ones let through.

        Args:
            planet_name : Name of the planet being hit.
            base_damage : Raw damage before any mitigation.

        Returns:
            int: Final damage after all building filters.
        """
        damage = base_damage
        for building in self._slots.get(planet_name, []):
            damage = building.on_disaster(damage)
        return damage
