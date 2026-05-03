"""
WinScreen.py — Cinematic "Galactic Peace" victory screen.

All six planet badge icons are displayed in a centred row.  Conquered badges
glow with a pulsing gold border; missing badges are dimmed with a translucent
overlay to show what the player did not earn in this run.

Stats displayed: planets conquered, session time.

Controls:  ESC → returns to caller (main.py then transitions to MENU).
"""

import math
import os

import numpy as np
import pygame
import pygame.surfarray as surfarray

from ui.UI_Elements import (
    SCREEN_W, SCREEN_H, ACCENT_CYAN, ACCENT_GOLD,
    DIM_WHITE, draw_stars,
)
from logic.BadgeEngine import BADGE_DEFINITIONS, BadgeEngine

_BADGE_W    = 80
_BADGE_H    = 80
_BADGE_GAP  = 24
_BADGE_ROW_Y = 370

_HARD_GREEN = 175
_SOFT_GREEN = 45


def _remove_chroma_key(img: pygame.Surface) -> pygame.Surface:
    """Greenness-score chroma key removal — same algorithm as PlanetRenderer."""
    _lock = surfarray.pixels3d(img)
    rgb_float = _lock.astype(np.float32)
    del _lock

    greenness = rgb_float[:, :, 1] - np.maximum(rgb_float[:, :, 0],
                                                  rgb_float[:, :, 2])
    t = np.ones(greenness.shape, dtype=np.float32)
    hard = greenness > _HARD_GREEN
    soft = (greenness >= _SOFT_GREEN) & (greenness <= _HARD_GREEN)
    t[hard] = 0.0
    band = float(_HARD_GREEN - _SOFT_GREEN)
    t[soft] = (_HARD_GREEN - greenness[soft]) / band

    alpha = surfarray.pixels_alpha(img)
    alpha[:] = np.clip(alpha.astype(np.float32) * t, 0, 255).astype(np.uint8)
    del alpha

    rgb_view = surfarray.pixels3d(img)
    rgb_view[:] = np.clip(rgb_float * t[:, :, np.newaxis], 0, 255).astype(np.uint8)
    del rgb_view

    return img


class WinScreen:
    """
    Self-contained victory screen.

    Call run() to enter the blocking event loop; it returns when the
    player presses ESC, at which point the caller transitions to MENU.
    """

    def run(self, screen: pygame.Surface, clock: pygame.time.Clock,
            font_title, font_ui, font_small, stars,
            conquered_planets: list, total_planets: int, session_time: float,
            profile_manager, badge_asset_dir: str):
        """
        Args:
            conquered_planets : Names of planets that reached Nash Equilibrium.
            total_planets     : Total planets in the galaxy this session.
            session_time      : Seconds elapsed during the winning run.
            profile_manager   : Used to read which badges the player owns.
            badge_asset_dir   : Absolute path to assets/badges/.
        """
        tick = 0.0

        # Preload planet badge surfaces (row 1) — fall back to placeholder circles
        badge_row  = BadgeEngine.get_row(1)
        badge_surfs: dict[str, pygame.Surface] = {}
        for bid in badge_row:
            info = BADGE_DEFINITIONS.get(bid, {})
            path = os.path.join(badge_asset_dir, info.get("file", ""))
            try:
                img = pygame.image.load(path).convert_alpha()
                img = _remove_chroma_key(img)
                badge_surfs[bid] = pygame.transform.smoothscale(img, (_BADGE_W, _BADGE_H))
            except Exception:
                surf = pygame.Surface((_BADGE_W, _BADGE_H), pygame.SRCALPHA)
                bx   = _BADGE_W // 2
                col  = info.get("color", (200, 180, 50))
                pygame.draw.circle(surf, (25, 25, 45), (bx, bx), bx - 4)
                pygame.draw.circle(surf, col, (bx, bx), bx - 4, 4)
                fnt = pygame.font.SysFont("consolas, courier new, menlo, monaco", 18, bold=True)
                t   = fnt.render(info.get("name", "??")[:2].upper(), True, col)
                surf.blit(t, (bx - t.get_width() // 2, bx - t.get_height() // 2))
                badge_surfs[bid] = surf

        total_w  = len(badge_row) * _BADGE_W + (len(badge_row) - 1) * _BADGE_GAP
        row_x    = (SCREEN_W - total_w) // 2

        while True:
            dt    = clock.tick(60) / 1000.0
            tick += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return

            # Gold-tinted starfield
            screen.fill((10, 8, 2))
            draw_stars(screen, stars, tick)

            cx   = SCREEN_W // 2
            glow = int(200 + 55 * math.sin(tick * 2.0))

            t1 = font_title.render("GALACTIC  PEACE", True, (glow, int(glow * 0.75), 0))
            t2 = font_title.render("ACHIEVED", True, ACCENT_GOLD)
            screen.blit(t1, t1.get_rect(centerx=cx, top=52))
            screen.blit(t2, t2.get_rect(centerx=cx, top=126))

            pygame.draw.line(screen, ACCENT_GOLD, (cx - 380, 206), (cx + 380, 206), 2)

            desc = font_ui.render(
                "All species have reached stable mutual cooperation.",
                True, (220, 200, 120))
            screen.blit(desc, desc.get_rect(centerx=cx, top=222))

            prog = font_ui.render(
                f"Conquered:  {len(conquered_planets)} / {total_planets}  Planets",
                True, ACCENT_GOLD)
            screen.blit(prog, prog.get_rect(centerx=cx, top=260))

            mins, secs = divmod(int(session_time), 60)
            hrs,  mins = divmod(mins, 60)
            time_surf  = font_ui.render(
                f"Time Played:  {hrs}h {mins:02d}m {secs:02d}s",
                True, DIM_WHITE)
            screen.blit(time_surf, time_surf.get_rect(centerx=cx, top=294))

            # Planet badge row
            lbl = font_small.render("PLANET  BADGES  EARNED", True, ACCENT_CYAN)
            screen.blit(lbl, lbl.get_rect(centerx=cx, top=_BADGE_ROW_Y - 30))

            owned = set(profile_manager.get_active_profile().get("unlocked_badges", []))
            for i, bid in enumerate(badge_row):
                bx  = row_x + i * (_BADGE_W + _BADGE_GAP)
                by  = _BADGE_ROW_Y
                img = badge_surfs.get(bid)
                if not img:
                    continue
                if bid in owned:
                    screen.blit(img, (bx, by))
                    # Pulsing gold border on earned badges
                    g_pulse = int(200 + 55 * math.sin(tick * 2.0 + i * 0.5))
                    pygame.draw.rect(
                        screen, (g_pulse, int(g_pulse * 0.75), 0),
                        (bx - 2, by - 2, _BADGE_W + 4, _BADGE_H + 4), 2,
                        border_radius=6)
                else:
                    # Dimmed overlay for badges not earned this run
                    dim_copy = img.copy()
                    ov = pygame.Surface((_BADGE_W, _BADGE_H), pygame.SRCALPHA)
                    ov.fill((10, 10, 30, 190))
                    dim_copy.blit(ov, (0, 0))
                    screen.blit(dim_copy, (bx, by))

            pygame.draw.line(screen, ACCENT_GOLD,
                             (cx - 380, SCREEN_H - 72), (cx + 380, SCREEN_H - 72), 1)
            esc = font_ui.render("[ ESC  —  RETURN TO MENU ]", True, ACCENT_GOLD)
            screen.blit(esc, esc.get_rect(centerx=cx, top=SCREEN_H - 56))

            pygame.display.flip()
