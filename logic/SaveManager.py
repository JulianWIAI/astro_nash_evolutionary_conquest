"""
SaveManager.py — Secure save/load system with SHA-256 data integrity.

Save format  (savegame.json)
----------------------------
{
    "checksum": "<sha-256 hex digest of the canonical save_data string>",
    "save_data": {
        "timestamp":         "ISO-8601 string",
        "conquered_planets": ["Ignaros", ...],
        "evolution_points":  10,
        "coop_weight":       1.0,
        "planets": {
            "Ignaros": {
                "resources": 450.0,
                "species": [
                    {"name": "Zorgon", "population": 83, "dna": {...}},
                    ...
                ]
            },
            ...
        }
    }
}

Integrity model
---------------
On save  : The save_data dict is serialised with sorted keys and no
           whitespace to produce a canonical byte string.  Its SHA-256
           hash is stored in the same file alongside the data.

On load  : The loaded save_data is re-serialised with the same parameters
           and re-hashed.  If the new hash differs from the stored hash the
           file was externally edited — loading is refused and an error is
           printed to the console.  This demonstrates tamper-evidence as
           required for the Business Informatics data-integrity presentation.
"""

import hashlib
import json
import os
from datetime import datetime

_DEFAULT_PATH = "savegame.json"


class SaveManager:
    """
    Handles secure serialisation and deserialisation of the game state.

    Attributes:
        save_path : Filesystem path for the save file (default savegame.json).
    """

    def __init__(self, save_path: str = _DEFAULT_PATH):
        self.save_path = save_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, gsm, controller, sim):
        """
        Serialise the current game state and write it with a SHA-256 checksum.

        Args:
            gsm        : GameStateManager — supplies conquered_planets.
            controller : PlayerController — supplies evolution_points.
            sim        : SimulationManager — supplies planets, species, coop_weight.
        """
        save_data = {
            "timestamp":         datetime.now().isoformat(),
            "conquered_planets": list(gsm.conquered_planets),
            "evolution_points":  controller.evolution_points,
            "coop_weight":       sim.game_theory.coop_weight,
            "planets":           self._serialise_planets(sim.planets),
        }

        checksum = self._hash(save_data)
        payload  = {"checksum": checksum, "save_data": save_data}

        with open(self.save_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=True)

        print(f"[SaveManager] Game saved.  Checksum: {checksum[:20]}…")

    def load(self, gsm, controller, sim) -> bool:
        """
        Load and integrity-validate a save file, then restore game state.

        Prints a console error and returns False if the file is missing,
        malformed, or tampered with.

        Args:
            gsm        : GameStateManager to restore conquered_planets into.
            controller : PlayerController to restore evolution_points into.
            sim        : SimulationManager to restore planets/species into.

        Returns:
            bool: True on successful, verified load; False otherwise.
        """
        if not os.path.exists(self.save_path):
            print("[SaveManager] No save file found.")
            return False

        try:
            with open(self.save_path, encoding="utf-8") as fh:
                payload = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[SaveManager] Could not read save file: {exc}")
            return False

        stored_checksum = payload.get("checksum", "")
        save_data       = payload.get("save_data", {})
        actual_checksum = self._hash(save_data)

        if actual_checksum != stored_checksum:
            print("=" * 62)
            print("!! DATA INTEGRITY VIOLATION: Save File Manipulated !!")
            print(f"   Stored   hash : {stored_checksum}")
            print(f"   Computed hash : {actual_checksum}")
            print("   Loading aborted — save data cannot be trusted.")
            print("=" * 62)
            return False

        self._restore(gsm, controller, sim, save_data)
        print("[SaveManager] Game loaded.  Integrity verified OK")
        return True

    @property
    def save_exists(self) -> bool:
        """True when a save file is present on disk."""
        return os.path.exists(self.save_path)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _hash(self, data: dict) -> str:
        """
        Produce a deterministic SHA-256 hex digest of a dict.

        json.dumps with sort_keys=True and no separators beyond the
        defaults guarantees the same canonical byte string regardless
        of Python's dict-insertion order or locale settings, making
        the hash reproducible across sessions and machines.
        """
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=True,
                               separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _serialise_planets(self, planets) -> dict:
        """Capture resource levels and full species DNA/population per planet."""
        result = {}
        for planet in planets:
            result[planet.name] = {
                "resources": planet.resources,
                "species": [
                    {
                        "name":       sp.name,
                        "population": sp.population,
                        "dna":        dict(sp.dna),
                    }
                    for sp in planet.species_list
                ],
            }
        return result

    def _restore(self, gsm, controller, sim, save_data: dict):
        """Apply validated save_data to the live game objects."""
        gsm.conquered_planets         = save_data.get("conquered_planets", [])
        controller.evolution_points   = save_data.get("evolution_points", 10)
        sim.game_theory.coop_weight   = save_data.get("coop_weight", 1.0)

        saved_planets = save_data.get("planets", {})
        for planet in sim.planets:
            if planet.name not in saved_planets:
                continue
            p_data = saved_planets[planet.name]
            planet.resources = p_data.get("resources", planet.resources)
            for sp, sp_data in zip(planet.species_list, p_data.get("species", [])):
                sp.population = sp_data.get("population", sp.population)
                sp.dna.update(sp_data.get("dna", {}))
