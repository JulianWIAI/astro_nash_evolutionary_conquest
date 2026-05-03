"""
Leaderboard.py — Global high-score tracking and top-10 screen.

Scores are stored in leaderboard.json next to the game binary and persist
across all profiles and sessions.

Score formula
-------------
  score = (planets_conquered * 1000) / max(time_played_seconds, 1)

A higher score means more planets conquered in less time.  Difficulty is
displayed but does not affect the raw score — players on HARD with fewer
planets can still rank below a thorough EASY run.

Usage
-----
  leaderboard = Leaderboard(path)
  leaderboard.submit("Alice", 6, 540.0, "HARD")
  leaderboard.run_screen(screen, clock, ...)    # blocking
"""

import json
import os
from datetime import datetime

import pygame

from ui.UI_Elements import (
    SCREEN_W, SCREEN_H, DEEP_SPACE, ACCENT_CYAN, ACCENT_GOLD,
    DIM_WHITE, draw_stars,
)

_MAX_STORED = 50


class Leaderboard:
    """
    Persists run data and renders the top-10 leaderboard screen.

    The run_screen() method enters its own pygame event loop and returns
    when ESC is pressed, keeping main.py free of leaderboard draw code.
    """

    def __init__(self, data_path: str):
        self._path    = data_path
        self._entries: list = []
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, username: str, planets: int, time_s: float,
               difficulty: str):
        """Add a completed run and immediately persist it."""
        entry = {
            "username":          username,
            "planets_conquered": planets,
            "time_played":       round(time_s, 1),
            "difficulty":        difficulty,
            "score":             round(self._score(planets, time_s), 2),
            "timestamp":         datetime.now().isoformat(),
        }
        self._entries.append(entry)
        self._entries.sort(key=lambda e: e["score"], reverse=True)
        self._entries = self._entries[:_MAX_STORED]
        self._save()

    def get_top_10(self) -> list:
        return self._entries[:10]

    def run_screen(self, screen: pygame.Surface, clock: pygame.time.Clock,
                   font_title, font_ui, font_small, stars: list):
        """Blocking leaderboard view.  Returns when ESC is pressed."""
        tick = 0.0
        while True:
            dt    = clock.tick(60) / 1000.0
            tick += dt
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return
            self._draw(screen, tick, font_title, font_ui, font_small, stars)
            pygame.display.flip()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score(planets: int, time_s: float) -> float:
        return (planets * 1000) / max(time_s, 1.0)

    def _draw(self, surface, tick, font_title, font_ui, font_small, stars):
        surface.fill(DEEP_SPACE)
        draw_stars(surface, stars, tick)

        cx = SCREEN_W // 2

        title = font_title.render("LEADERBOARD", True, ACCENT_GOLD)
        surface.blit(title, title.get_rect(centerx=cx, top=18))
        pygame.draw.line(surface, ACCENT_GOLD,
                         (cx - 360, 92), (cx + 360, 92), 1)

        # Column headers
        cols = ["RANK", "PLAYER",     "PLANETS",  "TIME",     "DIFF", "SCORE"]
        xs   = [cx-410,  cx-310,       cx-100,     cx+10,      cx+175, cx+290]
        for hdr, x in zip(cols, xs):
            surface.blit(font_small.render(hdr, True, ACCENT_CYAN), (x, 104))
        pygame.draw.line(surface, ACCENT_CYAN,
                         (cx - 420, 122), (cx + 380, 122), 1)

        entries = self.get_top_10()
        if not entries:
            msg = font_ui.render("No runs recorded yet — finish a game first.",
                                 True, (80, 80, 120))
            surface.blit(msg, msg.get_rect(center=(cx, 320)))
        else:
            for i, e in enumerate(entries):
                row_y  = 132 + i * 46
                colors = [ACCENT_GOLD, (200, 200, 200), (160, 160, 160)]
                color  = colors[min(i, 2)]
                medals = ["1st", "2nd", "3rd"]
                rank   = medals[i] if i < 3 else f"#{i+1}"
                mins, secs = divmod(int(e["time_played"]), 60)
                cells  = [
                    rank,
                    e["username"][:14],
                    str(e["planets_conquered"]),
                    f"{mins}m {secs:02d}s",
                    e["difficulty"][:3],
                    f"{e['score']:.1f}",
                ]
                for val, x in zip(cells, xs):
                    surface.blit(font_small.render(val, True, color), (x, row_y))

        pygame.draw.line(surface, ACCENT_GOLD,
                         (cx - 360, SCREEN_H - 58), (cx + 360, SCREEN_H - 58), 1)
        formula = font_small.render(
            "Score = (Planets x 1000) / Time (seconds)", True, (70, 70, 100))
        surface.blit(formula, formula.get_rect(centerx=cx, top=SCREEN_H - 46))
        esc = font_ui.render("[ ESC  —  BACK TO MENU ]", True, ACCENT_CYAN)
        surface.blit(esc, esc.get_rect(centerx=cx, top=SCREEN_H - 26))

    def _save(self):
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump({"entries": self._entries}, fh, indent=2, ensure_ascii=True)

    def _load(self):
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, encoding="utf-8") as fh:
                self._entries = json.load(fh).get("entries", [])
        except (json.JSONDecodeError, OSError):
            pass
