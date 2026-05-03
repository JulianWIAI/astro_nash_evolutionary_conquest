"""
GameStateManager.py — Top-level game state, win/loss logic, and planet conquest.

States
------
  MENU        : Title screen.
  MAP         : Galactic map — planet selection.
  SIMULATION  : Planet detail simulation view.
  HOW_TO_PLAY : Instruction overlay.
  WIN_SCREEN  : Victory — all planets conquered.
  LOSS_SCREEN : Defeat — total species extinction.
"""


class GameStateManager:
    """
    Tracks the active game state and evaluates win/loss conditions each frame.

    Win condition  — all planets in the galaxy have been conquered (both
                     species chose Cooperate in the same Nash tick).
    Loss condition — the total population of every species across every
                     active planet reaches zero (extinction).

    Attributes:
        current_state      : Active state string (one of VALID_STATES).
        conquered_planets  : Names of planets that have achieved equilibrium.
    """

    VALID_STATES = frozenset({
        "MENU", "MAP", "SIMULATION", "HOW_TO_PLAY", "WIN_SCREEN", "LOSS_SCREEN",
    })

    def __init__(self, total_planets: int):
        """
        Args:
            total_planets : Fixed count of planets in the galaxy (set at game start).
        """
        self.current_state         = "MENU"
        self.conquered_planets: list[str] = []
        self._total_planets        = total_planets

    # ------------------------------------------------------------------
    # Win / Loss checks
    # ------------------------------------------------------------------

    def check_win(self) -> bool:
        """
        Return True when every planet in the galaxy has been conquered.

        Win condition: len(conquered_planets) >= total_planets.
        """
        return len(self.conquered_planets) >= self._total_planets

    def check_loss(self, planets: list) -> bool:
        """
        Return True when all species across all active planets are extinct.

        Loss condition: the sum of every species' population across every
        planet is zero, and at least one planet has species (so an empty
        galaxy at startup doesn't trigger a loss).

        Args:
            planets : Full list of Planet objects to evaluate.
        """
        has_any_species = any(planet.species_list for planet in planets)
        if not has_any_species:
            return False
        total_population = sum(
            sp.population
            for planet in planets
            for sp in planet.species_list
        )
        return total_population == 0

    # ------------------------------------------------------------------
    # Conquest
    # ------------------------------------------------------------------

    def try_conquer(self, planet_name: str) -> bool:
        """
        Add planet_name to conquered_planets if not already present.

        Args:
            planet_name : Identifier of the planet that achieved equilibrium.

        Returns:
            bool: True if newly conquered, False if already in the list.
        """
        if planet_name not in self.conquered_planets:
            self.conquered_planets.append(planet_name)
            return True
        return False

    @property
    def conquest_progress(self) -> tuple:
        """Return (conquered_count, total_count) for HUD display."""
        return len(self.conquered_planets), self._total_planets

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def transition(self, new_state: str):
        """
        Move to a new game state.

        Args:
            new_state : Must be one of VALID_STATES.

        Raises:
            ValueError: If new_state is not recognised.
        """
        if new_state not in self.VALID_STATES:
            raise ValueError(f"Unknown game state: {new_state!r}")
        self.current_state = new_state

    def update(self, planets: list) -> str | None:
        """
        Evaluate win/loss conditions and return the target state to transition
        to, or None if no automatic transition is needed.

        Only active during MAP and SIMULATION states — menus and end-screens
        are not re-evaluated.

        Args:
            planets : List of all Planet objects to check.

        Returns:
            'WIN_SCREEN', 'LOSS_SCREEN', or None.
        """
        if self.current_state not in ("MAP", "SIMULATION"):
            return None
        if self.check_win():
            return "WIN_SCREEN"
        if self.check_loss(planets):
            return "LOSS_SCREEN"
        return None
