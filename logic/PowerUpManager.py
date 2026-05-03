"""
PowerUpManager.py — Evolution Booster one-time powerup system.

Boosters are awarded when a planet reaches Nash Equilibrium (conquered).
Each booster can be spent once to apply an immediate +20 fitness surge to
the primary species on any active planet.

The gain is applied directly to the Species.fitness attribute rather than
to DNA, so it represents a transient selective pressure that the simulation
will naturally balance over subsequent ticks rather than a permanent
genetic modification.
"""

_BOOSTER_FITNESS_GAIN = 20
_MAX_INVENTORY        = 5    # cap prevents screen clutter and preserves challenge


class PowerUpManager:
    """
    Manages the player's Evolution Booster inventory.

    Attributes:
        inventory : Current count of available boosters (0 – _MAX_INVENTORY).
    """

    def __init__(self):
        self.inventory: int = 0

    def reset(self):
        """Clear the inventory for a fresh game session."""
        self.inventory = 0

    # ------------------------------------------------------------------

    def award(self):
        """
        Grant one booster upon planet conquest.

        Capped at _MAX_INVENTORY so surplus conquests do not overflow the HUD.
        """
        self.inventory = min(self.inventory + 1, _MAX_INVENTORY)

    def apply(self, planet) -> bool:
        """
        Spend one booster on the planet's primary species.

        Args:
            planet : Planet object; species_list[0] receives the fitness boost.

        Returns:
            True if a booster was spent, False if inventory is empty or the
            planet currently has no resident species.
        """
        if self.inventory <= 0 or not planet.species_list:
            return False
        planet.species_list[0].fitness += _BOOSTER_FITNESS_GAIN
        self.inventory -= 1
        return True

    @property
    def has_booster(self) -> bool:
        """True when at least one booster remains in the inventory."""
        return self.inventory > 0
