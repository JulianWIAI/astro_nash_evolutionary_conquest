"""
GameTheory.py — Implements Nash Equilibrium logic for two-species interactions.

When two species share a planet, they choose to either Cooperate or Compete.
A 2×2 payoff matrix is evaluated each game tick. The outcome is a Nash
Equilibrium when neither species can improve its payoff by switching strategy
unilaterally. The player can shift payoff weights via the Evolution Menu.
"""

import random


# Default payoff matrix weights (player can tune these via Evolution Menu).
# Format: {(row_action, col_action): (row_payoff, col_payoff)}
DEFAULT_PAYOFF = {
    ("cooperate", "cooperate"): (3, 3),   # Mutualism — both benefit
    ("cooperate", "compete"):   (0, 5),   # Exploitation — row loses
    ("compete",   "cooperate"): (5, 0),   # Exploitation — col loses
    ("compete",   "compete"):   (1, 1),   # War — both suffer
}


class GameTheory:
    """
    Resolves resource-sharing decisions between two species on the same planet.

    The core algorithm:
      1. Each species independently decides whether to Cooperate or Compete,
         weighted by its aggression DNA trait.
      2. The payoff matrix maps the joint decision to resource rewards.
      3. The Nash Equilibrium check warns if neither species would want to
         switch — useful for the school presentation demo.

    Attributes:
        payoff_matrix : Dict mapping (action_A, action_B) → (payoff_A, payoff_B).
        coop_weight   : Global multiplier on the Cooperate payoffs (player tunable).
    """

    def __init__(self, payoff_matrix: dict = None):
        """
        Initialise with an optional custom payoff matrix.

        Args:
            payoff_matrix : Override DEFAULT_PAYOFF with a custom dict if provided.
        """
        self.payoff_matrix = payoff_matrix or dict(DEFAULT_PAYOFF)
        self.coop_weight = 1.0  # Player can increase this to encourage cooperation

    def choose_action(self, species) -> str:
        """
        Decide whether a species will Cooperate or Compete this tick.

        Effective aggression is divided by coop_weight so that the player's
        +CoopWeight button directly lowers the probability of competing.
        At coop_weight 1.0 the formula is unchanged; at 2.0 a species with
        aggression 0.8 has only a 40% chance to compete instead of 80%.

        Args:
            species : A Species instance whose dna['aggression'] drives the choice.

        Returns:
            str: 'cooperate' or 'compete'.
        """
        effective_aggression = species.dna["aggression"] / max(1.0, self.coop_weight)
        compete_probability  = max(0.0, min(1.0, effective_aggression))
        return "compete" if random.random() < compete_probability else "cooperate"

    def resolve_interaction(self, species_a, species_b, available_resources: float) -> tuple:
        """
        Run one interaction tick between two species sharing a planet.

        Steps:
          1. Each species chooses an action.
          2. Payoffs are looked up from the matrix.
          3. Resources are distributed proportionally to payoff scores,
             scaled by coop_weight for cooperative outcomes.
          4. Populations are updated based on net resource gain.

        Args:
            species_a          : First Species instance.
            species_b          : Second Species instance.
            available_resources: Total resource units on the planet this tick.

        Returns:
            tuple: (action_a, action_b, gain_a, gain_b) describing what happened.
        """
        action_a = self.choose_action(species_a)
        action_b = self.choose_action(species_b)

        raw_a, raw_b = self.payoff_matrix[(action_a, action_b)]

        # Boost cooperative payoffs if the player has raised coop_weight
        if action_a == "cooperate":
            raw_a = int(raw_a * self.coop_weight)
        if action_b == "cooperate":
            raw_b = int(raw_b * self.coop_weight)

        total_score = raw_a + raw_b or 1  # Avoid division by zero
        gain_a = (raw_a / total_score) * available_resources * 0.1
        gain_b = (raw_b / total_score) * available_resources * 0.1

        # Translate resource gain into population change
        species_a.population = max(0, int(species_a.population + gain_a - 2))
        species_b.population = max(0, int(species_b.population + gain_b - 2))

        return action_a, action_b, gain_a, gain_b

    def is_nash_equilibrium(self, action_a: str, action_b: str) -> bool:
        """
        Check whether the current joint action is a Nash Equilibrium.

        Payoffs are evaluated with coop_weight applied — the same scaling
        used in resolve_interaction — so that COOPERATE/COOPERATE becomes
        a Nash Equilibrium once the player has raised coop_weight above the
        defection threshold (coop_weight > 5/3 ≈ 1.67 with default matrix).
        This lets the player *create* the Nash Equilibrium through gameplay.

        Args:
            action_a : Current action of species A ('cooperate' or 'compete').
            action_b : Current action of species B ('cooperate' or 'compete').

        Returns:
            bool: True if the joint action is a Nash Equilibrium.
        """
        def _weighted(row_act, col_act):
            pa, pb = self.payoff_matrix[(row_act, col_act)]
            if row_act == "cooperate":
                pa = int(pa * self.coop_weight)
            if col_act == "cooperate":
                pb = int(pb * self.coop_weight)
            return pa, pb

        alt_a = "compete" if action_a == "cooperate" else "cooperate"
        alt_b = "compete" if action_b == "cooperate" else "cooperate"

        current_pa, current_pb = _weighted(action_a, action_b)
        deviate_pa, _          = _weighted(alt_a,    action_b)
        _,          deviate_pb = _weighted(action_a,  alt_b)

        return deviate_pa <= current_pa and deviate_pb <= current_pb

    def update_payoff(self, key: tuple, new_values: tuple):
        """
        Allow the player to modify a payoff matrix entry via the Evolution Menu.

        Args:
            key        : Tuple key like ('cooperate', 'compete').
            new_values : New (payoff_a, payoff_b) tuple to assign.
        """
        if key in self.payoff_matrix:
            self.payoff_matrix[key] = new_values
