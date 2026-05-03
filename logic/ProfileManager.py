"""
ProfileManager.py — Persistent cross-session player profiles.

Saved to global_profiles.json alongside the game binary.  Survives
New Game restarts and is never touched by the save/load system.

Profile schema (global_profiles.json)
--------------------------------------
{
  "profiles": {
    "profile_1": {
      "username":        "Player 1",
      "avatar_path":     "",
      "unlocked_badges": [],
      "unlocked_tracks": ["map_theme.mp3"],
      "lifetime_stats":  {
        "planets_conquered": 0,
        "time_played":       0.0,
        "games_played":      0
      }
    }
  },
  "active_profile": "profile_1"
}
"""

import json
import os


class ProfileManager:
    """
    Manages global player profiles independent of individual save files.

    A default "Player 1" profile is created automatically on first run.
    Call save() is called internally after every mutation.
    """

    def __init__(self, data_path: str):
        """
        Args:
            data_path : Absolute path to global_profiles.json.
        """
        self._path = data_path
        self._data: dict = {"profiles": {}, "active_profile": None}
        self._load()
        if not self._data["profiles"]:
            self.create_profile("Player 1")

    # ------------------------------------------------------------------
    # Profile CRUD
    # ------------------------------------------------------------------

    def create_profile(self, username: str) -> str:
        """Create a new profile and return its generated ID."""
        pid = f"profile_{len(self._data['profiles']) + 1}"
        self._data["profiles"][pid] = {
            "username":        username,
            "avatar_path":     "",
            "unlocked_badges": [],
            "unlocked_tracks": ["map_theme.mp3"],
            "lifetime_stats":  {
                "planets_conquered": 0,
                "time_played":       0.0,
                "games_played":      0,
            },
        }
        if self._data["active_profile"] is None:
            self._data["active_profile"] = pid
        self.save()
        return pid

    def list_profiles(self) -> list:
        """Return [(profile_id, username), …] for all profiles."""
        return [(pid, p["username"])
                for pid, p in self._data["profiles"].items()]

    def get_active_id(self) -> str:
        return self._data.get("active_profile") or ""

    def get_active_profile(self) -> dict:
        pid = self._data.get("active_profile")
        return self._data["profiles"].get(pid, {})

    def set_active_profile(self, profile_id: str):
        if profile_id in self._data["profiles"]:
            self._data["active_profile"] = profile_id
            self.save()

    def set_avatar(self, path: str):
        p = self.get_active_profile()
        if p:
            p["avatar_path"] = path
            self.save()

    # ------------------------------------------------------------------
    # Unlock helpers
    # ------------------------------------------------------------------

    def unlock_badge(self, badge_id: str) -> bool:
        """Unlock a badge.  Returns True if it was newly unlocked."""
        p = self.get_active_profile()
        if not p or badge_id in p["unlocked_badges"]:
            return False
        p["unlocked_badges"].append(badge_id)
        self.save()
        return True

    def unlock_track(self, filename: str) -> bool:
        """Unlock a music track.  Returns True if newly unlocked."""
        p = self.get_active_profile()
        if not p or filename in p["unlocked_tracks"]:
            return False
        p["unlocked_tracks"].append(filename)
        self.save()
        return True

    def add_stat(self, planets_conquered: int, time_played: float,
                 increment_games: bool = True):
        """Add to lifetime stats for the active profile."""
        p = self.get_active_profile()
        if not p:
            return
        s = p["lifetime_stats"]
        s["planets_conquered"] += planets_conquered
        s["time_played"]       += time_played
        if increment_games:
            s["games_played"]  += 1
        self.save()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self):
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, ensure_ascii=True)

    def _load(self):
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, encoding="utf-8") as fh:
                self._data.update(json.load(fh))
        except (json.JSONDecodeError, OSError):
            pass
