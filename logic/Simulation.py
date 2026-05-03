"""
Simulation.py — Orchestrates the per-frame game simulation.

Wraps GameTheory, AIEngine, BuildingManager, and Planet/Species setup into a
single SimulationManager that main.py ticks each frame.  All mutable
simulation state lives here; main.py only handles input routing and draw calls.
"""
import copy
import random

from logic.Species         import Species
from logic.Planet          import Planet
from logic.GameTheory      import GameTheory
from logic.AIEngine        import AIEngine
from logic.BuildingManager import BuildingManager

EVOLUTION_INTERVAL = 60.0   # seconds between automatic evolution ticks
_NASH_INTERVAL     = 2.0    # seconds between Nash interactions
_DISASTER_DURATION = 15.0   # seconds the disaster music theme plays

_BASE_EP_RATE    = 0.2    # EP per second of active simulation
_NASH_COOP_BONUS = 0.25   # fractional EP-rate bonus during mutual cooperate
_POP_MILESTONE   = 150    # population level that fires a one-time +50 EP grant
_MILESTONE_EP    = 50     # lump EP for disaster-survived and population milestones


def create_planets() -> list:
    """
    Build the initial set of planets with two species each.

    Returns:
        list of Planet instances ready for the galactic map.
    """
    PLANET_IMAGES = {
        "Ignaros":   "ignaros.png",
        "Kharenos":  "kharenos.png",
        "Venomara":  "venomara.png",
        "Crystalis": "crystalis.png",
        "Terranova": "terranova.png",
        "Glacius":   "glacius.png",
    }
    planet_data = [
        ("Ignaros",   (320, 200), (255,  80,  30), "Ignaros"),
        ("Kharenos",  (650, 160), (200, 150,  60), "Kharenos"),
        ("Venomara",  (900, 300), (120, 180,  40), "Venomara"),
        ("Crystalis", (200, 480), ( 60, 180, 220), "Crystalis"),
        ("Terranova", (550, 420), ( 60, 140, 220), "Terranova"),
        ("Glacius",   (820, 520), (180, 220, 255), "Glacius"),
    ]
    dna_templates = [
        {"speed": 0.7, "aggression": 0.3, "metabolism": 0.6},
        {"speed": 0.4, "aggression": 0.8, "metabolism": 0.4},
        {"speed": 0.5, "aggression": 0.5, "metabolism": 0.5},
        {"speed": 0.9, "aggression": 0.2, "metabolism": 0.7},
    ]
    species_colors = [
        (255, 100, 100), (100, 255, 100), (100, 100, 255),
        (255, 255, 100), (255, 100, 255), (100, 255, 255),
        (200, 150,  50), ( 50, 200, 150),
    ]
    species_names = [
        "Zorgon", "Kreel", "Veldari", "Nexari",
        "Omrath", "Sylari", "Dusken",  "Primos",
    ]

    planets = []
    sp_idx = 0
    for name, pos, color, img_key in planet_data:
        planet = Planet(name, pos, color, image_file=PLANET_IMAGES.get(img_key, ""))
        for _ in range(2):
            dna = copy.deepcopy(dna_templates[sp_idx % len(dna_templates)])
            for key in dna:
                dna[key] = max(0.0, min(1.0, dna[key] + random.uniform(-0.15, 0.15)))
            sp = Species(
                species_names[sp_idx % len(species_names)],
                dna,
                species_colors[sp_idx % len(species_colors)],
            )
            planet.add_species(sp)
            sp_idx += 1
        planets.append(planet)
    return planets


class SimulationManager:
    """
    Owns all mutable simulation state and drives per-frame updates.

    Attributes:
        planets           : All Planet instances on the galactic map.
        game_theory       : GameTheory instance (tunable by PlayerController).
        ai_engine         : AIEngine driving species evolution.
        building_manager  : BuildingManager for per-planet buildings.
        disaster_timer    : Seconds remaining in the active disaster event.
        nash_status       : 'cooperate', 'compete', or 'idle' — drives music.
        last_interaction  : Most recent (action_a, action_b, gain_a, gain_b).
    """

    def __init__(self, difficulty_manager=None):
        """
        Args:
            difficulty_manager : DifficultyManager instance, or None for defaults.
        """
        self._difficulty      = difficulty_manager
        self.planets          = create_planets()
        self.game_theory      = GameTheory()
        self.ai_engine        = AIEngine()
        self.building_manager = BuildingManager()

        # Apply difficulty's starting cooperation weight immediately
        if difficulty_manager:
            self.game_theory.coop_weight = difficulty_manager.starting_coop_weight

        self._evolution_timer   = 0.0
        self._interaction_timer = 0.0
        self.disaster_timer     = 0.0
        self.nash_status        = "idle"
        self.last_interaction   = None

        self._ep_accumulator        = 0.0
        self.ep_gained_this_tick    = 0   # main.py reads this each frame
        self._pop_milestones: set   = set()   # (planet_name, species_name)
        self._last_disaster_planet  = ""

        for planet in self.planets:
            for sp in planet.species_list:
                self.ai_engine.register_species(sp)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_disaster_active(self) -> bool:
        """True while the disaster music timer is running."""
        return self.disaster_timer > 0.0

    def trigger_disaster(self, planet, damage: int = 200):
        """
        Apply an environmental disaster, routing damage through building filters.

        Args:
            planet : The Planet to damage.
            damage : Base resource/population impact before any mitigation.
        """
        actual = self.building_manager.apply_disaster(planet.name, damage)
        planet.apply_disaster(actual)
        self.disaster_timer = _DISASTER_DURATION
        self._last_disaster_planet = planet.name

    def reset_selected_planet(self):
        """Call whenever the player selects a new planet to clear stale state."""
        self.last_interaction   = None
        self._interaction_timer = 0.0

    def tick(self, dt: float, selected_planet, game_state: str,
             time_scale: float = 1.0):
        """
        Advance simulation by one frame.

        Args:
            dt              : Raw elapsed seconds since the last frame.
            selected_planet : Planet currently in the detail view, or None.
            game_state      : Active view string — controls which logic runs.
            time_scale      : Multiplier from TimeController (0 = pause, 2 = fast).
        """
        self.ep_gained_this_tick = 0
        effective_dt = dt * time_scale

        _was_disaster = self.disaster_timer > 0.0

        if game_state == "SIMULATION" and selected_planet:
            self._tick_planet(effective_dt, selected_planet)

        self.disaster_timer = max(0.0, self.disaster_timer - effective_dt)

        # Disaster survived: timer just hit zero and the planet still has life
        if _was_disaster and self.disaster_timer == 0.0 and self._last_disaster_planet:
            for p in self.planets:
                if p.name == self._last_disaster_planet:
                    if any(sp.population > 0 for sp in p.species_list):
                        self.ep_gained_this_tick += _MILESTONE_EP
                    break
            self._last_disaster_planet = ""

        if self.last_interaction and game_state == "SIMULATION":
            act_a, act_b = self.last_interaction[0], self.last_interaction[1]
            self.nash_status = "compete" if "compete" in (act_a, act_b) else "cooperate"
        elif game_state != "SIMULATION":
            self.nash_status = "idle"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _tick_planet(self, dt: float, planet):
        """Resource regen, buildings, Nash interaction, evolution, auto-disaster."""
        drain = self._difficulty.resource_drain_rate if self._difficulty else 1.0
        planet.regenerate_resources(rate=3.0 * dt * 60 / drain)

        self.building_manager.tick(dt, planet, self.game_theory)

        self._interaction_timer += dt
        if self._interaction_timer >= _NASH_INTERVAL and len(planet.species_list) == 2:
            self._interaction_timer = 0.0
            self.last_interaction = self.game_theory.resolve_interaction(
                planet.species_list[0], planet.species_list[1], planet.resources
            )

        self._evolution_timer += dt
        if self._evolution_timer >= EVOLUTION_INTERVAL:
            self._evolution_timer = 0.0
            rate = self._difficulty.mutation_rate if self._difficulty else 0.1
            self.ai_engine.evolve_population(planet, mutation_rate=rate)

        if self._difficulty:
            if random.random() < self._difficulty.disaster_frequency * dt:
                self.trigger_disaster(planet)

        # Passive EP income — +25% bonus during mutual cooperation
        cooperating = (
            self.last_interaction is not None
            and self.last_interaction[0] == "cooperate"
            and self.last_interaction[1] == "cooperate"
        )
        ep_rate = _BASE_EP_RATE * (1.0 + _NASH_COOP_BONUS if cooperating else 1.0)
        self._ep_accumulator += ep_rate * dt
        while self._ep_accumulator >= 1.0:
            self._ep_accumulator -= 1.0
            self.ep_gained_this_tick += 1

        # Population milestone — one-time +50 EP per species reaching _POP_MILESTONE
        for sp in planet.species_list:
            key = (planet.name, sp.name)
            if sp.population >= _POP_MILESTONE and key not in self._pop_milestones:
                self._pop_milestones.add(key)
                self.ep_gained_this_tick += _MILESTONE_EP
