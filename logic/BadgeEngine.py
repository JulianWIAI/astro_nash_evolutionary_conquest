"""
BadgeEngine.py — Badge unlock logic and in-session interaction tracking.

Pure Python — no pygame dependency — so it can be tested independently.
All badge image loading lives in ui/ProfileUI.py.

Badge rows
----------
  Row 1  Planet Badges  : one per planet, awarded on first conquest.
  Row 2  Special Badges : awarded by specific gameplay triggers.

Track unlock table
------------------
  badge_diplomat  → coop_theme.mp3
  badge_disaster  → disaster_theme.mp3
  badge_arms_race → war_theme.mp3
  badge_conqueror → (map_theme already default; re-confirms it)
"""

# badge_id → display metadata used by ProfileUI for rendering
BADGE_DEFINITIONS: dict = {
    # ── Row 1: Planet badges ──────────────────────────────────────────
    "badge_ignaros":   {"name": "Ignaros Tamer",    "desc": "Conquer Ignaros",               "file": "badge_ignaros.png",   "row": 1, "color": (230,  50,  30)},
    "badge_kharenos":  {"name": "Kharenos Pioneer",  "desc": "Conquer Kharenos",              "file": "badge_kharenos.png",  "row": 1, "color": (200, 160,  60)},
    "badge_venomara":  {"name": "Venomara Warden",   "desc": "Conquer Venomara",              "file": "badge_venomara.png",  "row": 1, "color": (120, 220,  80)},
    "badge_crystalis": {"name": "Crystalis Scholar", "desc": "Conquer Crystalis",             "file": "badge_crystalis.png", "row": 1, "color": ( 60, 200, 230)},
    "badge_terranova": {"name": "Terranova Sage",    "desc": "Conquer Terranova",             "file": "badge_terranova.png", "row": 1, "color": ( 40, 100, 200)},
    "badge_glacius":   {"name": "Glacius Master",    "desc": "Conquer Glacius",               "file": "badge_glacius.png",   "row": 1, "color": (180, 220, 255)},
    # ── Row 2: Special badges ─────────────────────────────────────────
    "badge_diplomat":  {"name": "Diplomat",          "desc": "Achieve first COOPERATE",       "file": "badge_diplomat.png",  "row": 2, "color": ( 80, 200, 120)},
    "badge_disaster":  {"name": "Disaster Bringer",  "desc": "Trigger your first disaster",   "file": "badge_disaster.png",  "row": 2, "color": (220,  60,  60)},
    "badge_builder":   {"name": "Architect",         "desc": "Construct your first building", "file": "badge_builder.png",   "row": 2, "color": (200, 160,  40)},
    "badge_arms_race": {"name": "Arms Race",         "desc": "10 COMPETE interactions",       "file": "badge_arms_race.png", "row": 2, "color": (180,  40,  40)},
    "badge_hard_mode": {"name": "Iron Will",         "desc": "Win the game on HARD",          "file": "badge_hard_mode.png", "row": 2, "color": (160,  60, 220)},
    "badge_conqueror": {"name": "Conqueror",         "desc": "Conquer all 6 planets",         "file": "badge_conqueror.png", "row": 2, "color": (255, 200,  50)},
}

# Planet name → badge ID
PLANET_TO_BADGE: dict[str, str] = {
    "Ignaros":   "badge_ignaros",
    "Kharenos":  "badge_kharenos",
    "Venomara":  "badge_venomara",
    "Crystalis": "badge_crystalis",
    "Terranova": "badge_terranova",
    "Glacius":   "badge_glacius",
}

# Badge → music track unlocked alongside it
_BADGE_TO_TRACK: dict[str, str] = {
    "badge_diplomat":  "coop_theme.mp3",
    "badge_disaster":  "disaster_theme.mp3",
    "badge_arms_race": "war_theme.mp3",
    "badge_conqueror": "map_theme.mp3",
}


class BadgeEngine:
    """
    Stateful tracker for in-session badge triggers.

    Call reset_session() at the start of each new game so per-session
    counters (compete_count etc.) are cleared.
    """

    def __init__(self):
        self._compete_count  = 0
        self._last_processed = None   # last interaction tuple — identity check

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def on_planet_conquered(self, planet_name: str, profile_manager) -> str | None:
        """
        Award the planet badge and check for the all-planets Conqueror badge.

        Returns the badge_id that was newly unlocked, or None if already owned.
        """
        badge_id = PLANET_TO_BADGE.get(planet_name)
        newly    = False
        if badge_id:
            newly = profile_manager.unlock_badge(badge_id)

        # All-planet conqueror check
        owned = set(profile_manager.get_active_profile().get("unlocked_badges", []))
        if all(bid in owned for bid in PLANET_TO_BADGE.values()):
            self.unlock_special("badge_conqueror", profile_manager)

        return badge_id if newly else None

    def unlock_special(self, badge_id: str, profile_manager):
        """Unlock a special badge and its linked music track (if any)."""
        profile_manager.unlock_badge(badge_id)
        track = _BADGE_TO_TRACK.get(badge_id)
        if track:
            profile_manager.unlock_track(track)

    def on_interaction(self, interaction, profile_manager):
        """
        Process the latest Nash interaction tuple for badge triggers.

        Uses identity comparison (is) so calling this every frame is safe —
        the tuple reference only changes when a new Nash tick fires.

        Args:
            interaction : (act_a, act_b, …) tuple from SimulationManager, or None.
        """
        if interaction is None or interaction is self._last_processed:
            return
        self._last_processed = interaction

        act_a, act_b = interaction[0], interaction[1]

        if act_a == "cooperate" and act_b == "cooperate":
            self.unlock_special("badge_diplomat", profile_manager)

        if "compete" in (act_a, act_b):
            self._compete_count += 1
            if self._compete_count >= 10:
                self.unlock_special("badge_arms_race", profile_manager)

    def reset_session(self):
        """Reset per-session counters.  Call this on every New Game."""
        self._compete_count  = 0
        self._last_processed = None

    # ------------------------------------------------------------------
    # Static helpers used by ProfileUI
    # ------------------------------------------------------------------

    @staticmethod
    def get_row(row: int) -> list:
        """Return badge IDs for row 1 (planets) or row 2 (specials)."""
        return [bid for bid, d in BADGE_DEFINITIONS.items() if d["row"] == row]
