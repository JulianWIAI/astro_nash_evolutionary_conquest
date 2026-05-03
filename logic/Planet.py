"""
Planet.py — Defines the Planet class that acts as the arena for species simulations.

Each planet hosts one or two species and holds the resource pool that species
compete over. The Planet class also stores the display position on the galactic map.
"""

from logic.Species import Species


class Planet:
    """
    A selectable planet on the galactic map that contains a species simulation.

    Attributes:
        name        : Display name shown on the galactic map.
        position    : (x, y) pixel coordinates on the galactic map.
        radius      : Visual radius in pixels used for click-detection.
        color       : (R, G, B) base colour for the planet sprite.
        resources   : Current resource units available to all species.
        max_resources: Upper cap on resources (regrows toward this value).
        species_list: List of Species currently inhabiting this planet.
    """

    def __init__(self, name: str, position: tuple, color: tuple,
                 radius: int = 40, image_file: str = ""):
        """
        Initialise a planet with a map position and visual properties.

        Args:
            name       : Unique planet name (e.g. 'Ignaros').
            position   : (x, y) pixel coordinates on the 1280x720 galactic map.
            color      : (R, G, B) fallback colour when no image_file is set.
            radius     : Hit-box / display radius in pixels (default 40).
            image_file : PNG filename in assets/planets/ (empty = circle fallback).
        """
        self.name = name
        self.position = position
        self.radius = radius
        self.color = color
        self.image_file = image_file
        self.resources = 500
        self.max_resources = 1000
        self.species_list: list[Species] = []
        self.is_locked = False

    def add_species(self, species: Species):
        """
        Add a species to this planet (max 2 species per planet for Nash logic).

        Args:
            species : The Species instance to add.

        Raises:
            ValueError: If the planet already has 2 species.
        """
        if len(self.species_list) >= 2:
            raise ValueError(f"Planet '{self.name}' is already at capacity (2 species).")
        self.species_list.append(species)

    def regenerate_resources(self, rate: float = 5.0):
        """
        Grow resources each simulation tick up to max_resources.

        Args:
            rate : Resource units added per tick (default 5.0).
        """
        self.resources = min(self.max_resources, self.resources + rate)

    def apply_disaster(self, damage: int = 200):
        """
        Reduce resources and shrink all species populations (environmental disaster).

        Args:
            damage : Resource units removed and population penalty per species.
        """
        self.resources = max(0, self.resources - damage)
        for species in self.species_list:
            species.population = max(0, species.population - damage // 2)

    def spawn_resources(self, bonus: int = 300):
        """
        Instantly add bonus resources (triggered from the side-panel).

        Args:
            bonus : Resource units to add (capped at max_resources).
        """
        self.resources = min(self.max_resources, self.resources + bonus)

    def is_clicked(self, mouse_pos: tuple) -> bool:
        """
        Return True if a mouse click falls within this planet's hit-box.

        Args:
            mouse_pos : (mx, my) pixel position of the mouse click.

        Returns:
            bool: True when the click is inside the planet circle.
        """
        dx = mouse_pos[0] - self.position[0]
        dy = mouse_pos[1] - self.position[1]
        return (dx * dx + dy * dy) <= (self.radius * self.radius)

    def __repr__(self):
        return f"Planet('{self.name}', resources={self.resources}, species={len(self.species_list)})"
