"""
Building.py — Modular building structures that apply passive planet buffs.

Each subclass overrides one or more hook methods:
    on_construct(game_theory)          called once when the building is placed.
    on_tick(dt, planet, game_theory)   called every simulation frame.
    on_disaster(base_damage) -> int    called on disaster; returns filtered damage.

Available buildings
-------------------
  Church        (3 EP)  Floors coop_weight at 1.5, making Cooperate more
                         attractive and reducing strategy switching.
  MilitaryBase  (4 EP)  Floors every species' population at 15, preventing
                         extinction from disasters or resource scarcity.
  AirDefense    (5 EP)  Halves all disaster damage via the on_disaster hook.
"""


class Building:
    """Base class — all hooks are no-ops; subclasses override as needed."""

    name: str = "Building"
    cost: int = 0

    def __init__(self):
        self.is_constructed = False

    def on_construct(self, game_theory):
        """One-time effect applied immediately when the building is placed."""

    def on_tick(self, dt: float, planet, game_theory):
        """Passive effect applied once per simulation frame."""

    def on_disaster(self, base_damage: int) -> int:
        """Filter incoming disaster damage; return the (possibly reduced) amount."""
        return base_damage


class Church(Building):
    """
    Church — promotes cooperation by maintaining a coop_weight floor.

    While constructed, the Nash cooperation weight can never fall below
    COOP_FLOOR (1.5), which tilts the payoff matrix toward mutualism and
    reduces the chance of species switching from Cooperate to Compete.
    """

    name      = "Church"
    cost      = 2
    COOP_FLOOR = 1.5

    def on_tick(self, dt: float, planet, game_theory):
        if game_theory.coop_weight < self.COOP_FLOOR:
            game_theory.coop_weight = self.COOP_FLOOR


class MilitaryBase(Building):
    """
    Military Base — sustains species through disasters and starvation.

    While constructed, no species on this planet can fall below
    POPULATION_FLOOR (15) individuals, preventing extinction cascades.
    """

    name             = "MilitaryBase"
    cost             = 3
    POPULATION_FLOOR = 15

    def on_tick(self, dt: float, planet, game_theory):
        for sp in planet.species_list:
            if sp.population < self.POPULATION_FLOOR:
                sp.population = self.POPULATION_FLOOR


class AirDefense(Building):
    """
    Air Defense — orbital interceptors that absorb half of all disaster damage.

    on_disaster uses ceiling division so damage is always reduced but never
    reaches zero (the planet is still meaningfully hurt).
    """

    name = "AirDefense"
    cost = 4

    def on_disaster(self, base_damage: int) -> int:
        return (base_damage + 1) // 2   # ceiling division → always > 0
