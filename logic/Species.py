"""
Species.py — Defines the Species class that represents an AI-controlled life form.

Each species has a DNA dictionary (speed, aggression, metabolism) that drives
its behavior in the simulation. DNA is used by the neural network in AIEngine
and by the Nash payoff matrix in GameTheory.
"""


class Species:
    """
    Represents a single AI species with evolvable traits (DNA).

    Attributes:
        name        : Human-readable identifier for the species.
        dna         : Dict of trait floats — speed, aggression, metabolism.
        fitness     : Accumulated fitness score used in the evolution loop.
        color       : RGB tuple used when rendering the species on a planet.
        population  : Current population count on the host planet.
    """

    def __init__(self, name: str, dna: dict, color: tuple):
        """
        Initialise a species with a name, DNA traits, and a display colour.

        Args:
            name  : Unique string identifier (e.g. 'Zorgon').
            dna   : Dict with keys 'speed', 'aggression', 'metabolism',
                    each a float in [0.0, 1.0].
            color : (R, G, B) used when drawing the species.
        """
        self.name = name
        self.dna = dna
        self.fitness = 0.0
        self.color = color
        self.population = 100

    def mutate(self, mutation_rate: float = 0.1):
        """
        Apply random mutations to the DNA traits.

        Each trait is shifted by a small random delta scaled by mutation_rate,
        then clamped to [0.0, 1.0] so values remain valid.

        Args:
            mutation_rate : Maximum ± change applied to each trait per cycle.
        """
        import random
        for key in self.dna:
            delta = random.uniform(-mutation_rate, mutation_rate)
            self.dna[key] = max(0.0, min(1.0, self.dna[key] + delta))

    def calculate_fitness(self):
        """
        Compute a fitness score from the current DNA and population.

        Higher metabolism and larger population reward fitness; aggression
        provides a smaller bonus because it helps compete for resources but
        also risks population loss in conflicts.

        Returns:
            float: The calculated fitness score (also stored in self.fitness).
        """
        self.fitness = (
            self.dna["metabolism"] * 2.0
            + self.dna["speed"] * 1.0
            + self.dna["aggression"] * 0.5
            + (self.population / 100.0) * 1.5
        )
        return self.fitness

    @property
    def sprite_type(self) -> str:
        """
        Return the archetype name that selects the character image file.

        The dominant DNA trait determines the archetype so the visual
        automatically reflects how the species has evolved:
            aggression  → 'predator'
            metabolism  → 'gatherer'
            speed       → 'technician'

        Returns:
            str: One of 'predator', 'gatherer', 'technician'.
        """
        archetype_map = {
            "aggression": "predator",
            "metabolism": "gatherer",
            "speed":      "technician",
        }
        dominant_trait = max(self.dna, key=self.dna.get)
        return archetype_map[dominant_trait]

    def __repr__(self):
        return f"Species('{self.name}', pop={self.population}, fitness={self.fitness:.2f})"
