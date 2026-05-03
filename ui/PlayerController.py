"""
PlayerController.py — Handles all player-facing actions and UI state.

The player does not control a species directly. Instead, they act as a
'galactic god' who can:
  - Select planets on the galactic map.
  - Trigger environmental disasters or resource spawns via the side-panel.
  - Spend evolution points to mutate a species' DNA via the Evolution Menu.
  - Adjust the Nash payoff weights to influence species diplomacy.

This class bridges UI events (mouse clicks, button presses) to Planet and
GameTheory method calls, keeping main.py free of game logic.
"""


class PlayerController:
    """
    Mediates between player input events and the game simulation objects.

    Attributes:
        selected_planet   : The Planet currently shown in the detail view.
        evolution_points  : Points the player has accumulated to spend.
        active_menu       : String tag for the currently open overlay
                            ('none', 'evolution', 'disaster').
    """

    def __init__(self):
        """Initialise the controller with no planet selected and zero points."""
        self.selected_planet = None
        self.evolution_points = 10
        self.active_menu = "none"

    def select_planet(self, planet):
        """
        Set a planet as the active detail view target.

        Args:
            planet : The Planet instance clicked by the player.
        """
        self.selected_planet = planet

    def trigger_disaster(self, damage: int = 200):
        """
        Apply an environmental disaster to the selected planet.

        Calls Planet.apply_disaster() which reduces resources and
        shrinks all species populations on that planet.

        Args:
            damage : Severity of the disaster in resource/population units.
        """
        if self.selected_planet:
            self.selected_planet.apply_disaster(damage)

    def spawn_resources(self, bonus: int = 300, evo_gain: int = 1):
        """
        Inject bonus resources into the selected planet.

        Args:
            bonus    : Resource units to inject.
            evo_gain : Evolution points awarded (scaled by DifficultyManager).
        """
        if self.selected_planet:
            self.selected_planet.spawn_resources(bonus)
            self.evolution_points += evo_gain

    def spend_evolution_point(self, species, trait: str, delta: float = 0.1):
        """
        Spend one evolution point to manually buff a species trait.

        Args:
            species : The Species whose DNA will be modified.
            trait   : DNA key to boost ('speed', 'aggression', 'metabolism').
            delta   : Amount to add to the trait (clamped to [0, 1]).

        Returns:
            bool: True if the point was spent, False if insufficient points.
        """
        if self.evolution_points <= 0:
            return False
        if trait not in species.dna:
            return False
        species.dna[trait] = min(1.0, species.dna[trait] + delta)
        self.evolution_points -= 1
        return True

    def adjust_coop_weight(self, game_theory, delta: float = 0.2) -> bool:
        """
        Spend 1 EP to shift the cooperation reward weight in the Nash payoff matrix.

        A higher coop_weight makes Cooperate more attractive for both species,
        nudging the Nash Equilibrium toward mutualism.

        Args:
            game_theory : The GameTheory instance to modify.
            delta       : Amount to add to coop_weight (minimum 0.2).

        Returns:
            bool: True if the point was spent, False if insufficient points.
        """
        if self.evolution_points < 1:
            return False
        self.evolution_points -= 1
        game_theory.coop_weight = max(0.2, game_theory.coop_weight + delta)
        return True

    def open_menu(self, menu_name: str):
        """
        Toggle a named overlay menu open or closed.

        Args:
            menu_name : 'evolution' or 'disaster'.
        """
        if self.active_menu == menu_name:
            self.active_menu = "none"
        else:
            self.active_menu = menu_name
