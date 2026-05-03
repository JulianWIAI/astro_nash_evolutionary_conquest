"""
AIEngine.py — NEAT-inspired neural network that drives species behavior.

Each species carries a small feed-forward network whose weights are derived
from its DNA traits. The network takes environmental inputs (resource level,
threat level, population) and outputs a movement/action decision.

The evolution loop calls AIEngine.evolve_population() every 60 seconds to
replace the weakest species with mutated offspring of the survivors.
"""

import random
import math


class NeuralNet:
    """
    A tiny 3→4→2 feed-forward neural network for a single species.

    Inputs  (3): normalised resource level, threat level, own population ratio.
    Hidden  (4): fully connected, tanh activation.
    Outputs (2): [move_toward_resource, hide_from_threat] probability scores.

    Weights are seeded from the species DNA so that the phenotype (behaviour)
    is a direct expression of the genotype (DNA traits).
    """

    def __init__(self, dna: dict):
        """
        Build weight matrices from the species DNA.

        Args:
            dna : Dict with keys 'speed', 'aggression', 'metabolism'.
        """
        seed_value = int(
            dna["speed"] * 1000
            + dna["aggression"] * 100
            + dna["metabolism"] * 10
        )
        rng = random.Random(seed_value)

        # Input→Hidden weights: shape (4, 3)
        self.w1 = [
            [rng.uniform(-1, 1) for _ in range(3)]
            for _ in range(4)
        ]
        # Hidden→Output weights: shape (2, 4)
        self.w2 = [
            [rng.uniform(-1, 1) for _ in range(4)]
            for _ in range(2)
        ]

        # Bias influenced by aggression (aggressive species are bolder)
        self.bias = dna["aggression"] - 0.5

    def _tanh(self, x: float) -> float:
        """Element-wise tanh activation (avoids numpy dependency)."""
        return math.tanh(x)

    def forward(self, inputs: list) -> list:
        """
        Run a forward pass through the network.

        Args:
            inputs : List of 3 floats — [resource_ratio, threat_ratio, pop_ratio].

        Returns:
            list: Two output floats — [move_score, hide_score], each in (-1, 1).
        """
        # Hidden layer
        hidden = []
        for weights in self.w1:
            total = self.bias + sum(w * x for w, x in zip(weights, inputs))
            hidden.append(self._tanh(total))

        # Output layer
        outputs = []
        for weights in self.w2:
            total = sum(w * h for w, h in zip(weights, hidden))
            outputs.append(self._tanh(total))

        return outputs


class AIEngine:
    """
    Manages the evolution loop for all species across all planets.

    Responsibilities:
      - Wrap each species in a NeuralNet keyed by species name.
      - Run tick-level AI decisions (movement, resource targeting).
      - Execute the 60-second fitness check: cull losers, mutate survivors.
    """

    def __init__(self):
        """Initialise an empty map from species name → NeuralNet."""
        self.networks: dict[str, NeuralNet] = {}

    def register_species(self, species):
        """
        Create and store a NeuralNet for a newly added species.

        Args:
            species : A Species instance to register.
        """
        self.networks[species.name] = NeuralNet(species.dna)

    def decide_action(self, species, planet) -> str:
        """
        Ask the species' neural network what to do this tick.

        Inputs are derived from the planet's current state relative to
        the species' own population, so the same DNA behaves differently
        on a resource-rich planet versus a barren one.

        Args:
            species : The Species making the decision.
            planet  : The Planet the species currently inhabits.

        Returns:
            str: One of 'forage', 'hide', or 'idle'.
        """
        if species.name not in self.networks:
            self.register_species(species)

        resource_ratio = planet.resources / max(planet.max_resources, 1)
        threat_ratio = len(planet.species_list) / 2.0  # 0.5 if alone, 1.0 with rival
        pop_ratio = species.population / 100.0

        outputs = self.networks[species.name].forward(
            [resource_ratio, threat_ratio, pop_ratio]
        )

        move_score, hide_score = outputs
        if move_score > hide_score and move_score > 0:
            return "forage"
        elif hide_score > 0:
            return "hide"
        return "idle"

    def evolve_population(self, planet, mutation_rate: float = 0.1):
        """
        Perform the 60-second evolution tick for all species on a planet.

        Algorithm:
          1. Calculate fitness for every species.
          2. Sort by fitness (ascending = weakest first).
          3. Remove species with population ≤ 0.
          4. Mutate survivors at the given rate and rebuild their networks.

        Args:
            planet         : The Planet whose species_list will be evolved.
            mutation_rate  : Passed directly to Species.mutate() — scaled by
                             DifficultyManager so harder modes evolve faster.
        """
        if not planet.species_list:
            return

        for sp in planet.species_list:
            sp.calculate_fitness()

        planet.species_list.sort(key=lambda s: s.fitness)
        planet.species_list = [s for s in planet.species_list if s.population > 0]

        for sp in planet.species_list:
            sp.mutate(mutation_rate)
            self.networks[sp.name] = NeuralNet(sp.dna)
