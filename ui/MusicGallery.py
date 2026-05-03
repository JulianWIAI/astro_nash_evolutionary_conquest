"""
MusicGallery.py — Music Album reward screen.

Four tracks are gated behind achievement badges.  Once unlocked, the player
can listen to each track and see its local file path (the "Download" reveal).

Lock table
----------
  map_theme.mp3      Always available.
  coop_theme.mp3     Requires badge_diplomat   (first Cooperate equilibrium).
  war_theme.mp3      Requires badge_arms_race  (10 Compete interactions).
  disaster_theme.mp3 Requires badge_disaster   (first disaster triggered).
"""

import os

import pygame

from ui.UI_Elements import (
    SCREEN_W, SCREEN_H, DEEP_SPACE, ACCENT_CYAN, ACCENT_GOLD,
    DIM_WHITE, WHITE, BTN_DARK, BTN_HOVER, draw_stars,
)
from logic.BadgeEngine import BADGE_DEFINITIONS

_TRACKS = [
    {
        "filename":    "map_theme.mp3",
        "title":       "Galactic Overture",
        "badge_req":   None,
        "description": "The main theme. Plays on the galactic map.",
    },
    {
        "filename":    "coop_theme.mp3",
        "title":       "Harmony Protocol",
        "badge_req":   "badge_diplomat",
        "description": "Plays when both species choose to Cooperate.",
    },
    {
        "filename":    "war_theme.mp3",
        "title":       "Nash Breakdown",
        "badge_req":   "badge_arms_race",
        "description": "Plays during competitive Nash interactions.",
    },
    {
        "filename":    "disaster_theme.mp3",
        "title":       "Extinction Event",
        "badge_req":   "badge_disaster",
        "description": "Plays while a disaster ravages the planet.",
    },
]

_LIST_X  = 60
_LIST_Y  = 130
_ITEM_H  = 72
_PANEL_X = 510


class MusicGallery:
    """
    Self-contained music gallery.  Call run() to enter its blocking event loop.
    Returns when ESC is pressed (stops any playing track first).
    """

    def run(self, screen: pygame.Surface, clock: pygame.time.Clock,
            font_title, font_ui, font_small, stars: list,
            profile_manager, music_asset_dir: str):
        tick        = 0.0
        selected    = 0
        playing_idx = None

        def _unlocked(t: dict) -> bool:
            if t["badge_req"] is None:
                return True
            return t["filename"] in profile_manager.get_active_profile().get(
                "unlocked_tracks", [])

        def _play(idx: int):
            nonlocal playing_idx
            path = os.path.join(music_asset_dir, _TRACKS[idx]["filename"])
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(0.7)
                pygame.mixer.music.play(-1)
                playing_idx = idx
            except (pygame.error, FileNotFoundError, OSError):
                pass

        while True:
            dt     = clock.tick(60) / 1000.0
            tick  += dt
            mx, my = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.mixer.music.stop()
                    pygame.quit()
                    raise SystemExit

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.mixer.music.stop()
                        return
                    elif event.key == pygame.K_UP:
                        selected = (selected - 1) % len(_TRACKS)
                    elif event.key == pygame.K_DOWN:
                        selected = (selected + 1) % len(_TRACKS)
                    elif event.key == pygame.K_RETURN and _unlocked(_TRACKS[selected]):
                        _play(selected)

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i in range(len(_TRACKS)):
                        item_r = pygame.Rect(_LIST_X, _LIST_Y + i * _ITEM_H,
                                             390, _ITEM_H - 4)
                        if item_r.collidepoint(mx, my):
                            selected = i
                    play_r = pygame.Rect(_PANEL_X + 20, 360, 130, 42)
                    if play_r.collidepoint(mx, my) and _unlocked(_TRACKS[selected]):
                        _play(selected)

            # ---- Draw ----
            screen.fill(DEEP_SPACE)
            draw_stars(screen, stars, tick)

            title = font_title.render("MUSIC  GALLERY", True, ACCENT_CYAN)
            screen.blit(title, title.get_rect(centerx=SCREEN_W // 2, top=22))
            pygame.draw.line(screen, ACCENT_CYAN,
                             (SCREEN_W // 2 - 360, 90),
                             (SCREEN_W // 2 + 360, 90), 1)

            # Track list (left side)
            screen.blit(font_small.render("TRACKS", True, ACCENT_GOLD),
                        (_LIST_X, _LIST_Y - 24))
            for i, t in enumerate(_TRACKS):
                item_r   = pygame.Rect(_LIST_X, _LIST_Y + i * _ITEM_H,
                                       390, _ITEM_H - 4)
                unlocked = _unlocked(t)
                pygame.draw.rect(screen, BTN_HOVER if i == selected else BTN_DARK,
                                 item_r, border_radius=6)
                pygame.draw.rect(screen, ACCENT_CYAN, item_r, 1, border_radius=6)

                title_color = ACCENT_GOLD if unlocked else (60, 60, 80)
                lock_color  = (0, 200, 100) if unlocked else (180, 60, 60)
                now_play    = "  >" if i == playing_idx else ""
                screen.blit(font_small.render(t["title"] + now_play,
                                              True, title_color),
                            (item_r.x + 10, item_r.y + 8))
                screen.blit(font_small.render(
                    "UNLOCKED" if unlocked else "LOCKED", True, lock_color),
                    (item_r.x + 10, item_r.y + 32))

            # Detail panel (right side)
            t_sel    = _TRACKS[selected]
            unlocked = _unlocked(t_sel)
            panel    = pygame.Surface((710, 430), pygame.SRCALPHA)
            panel.fill((7, 7, 28, 215))
            screen.blit(panel, (_PANEL_X, 120))
            pygame.draw.rect(screen, ACCENT_CYAN,
                             (_PANEL_X, 120, 710, 430), 1, border_radius=6)

            px = _PANEL_X + 22
            color = ACCENT_GOLD if unlocked else (60, 60, 80)
            screen.blit(font_title.render(t_sel["title"], True, color),
                        (px, 138))
            screen.blit(font_small.render(t_sel["description"], True, DIM_WHITE),
                        (px, 218))
            screen.blit(font_small.render(t_sel["filename"], True, (70, 70, 100)),
                        (px, 242))

            if unlocked:
                play_r = pygame.Rect(px, 360, 130, 42)
                ph     = play_r.collidepoint(mx, my)
                pygame.draw.rect(screen, BTN_HOVER if ph else BTN_DARK,
                                 play_r, border_radius=8)
                pygame.draw.rect(screen, ACCENT_CYAN, play_r, 2, border_radius=8)
                p_lbl = font_ui.render("PLAY", True, WHITE)
                screen.blit(p_lbl, p_lbl.get_rect(center=play_r.center))

                if playing_idx == selected:
                    screen.blit(
                        font_small.render("NOW PLAYING  >", True, (0, 220, 120)),
                        (px + 144, 372))

                # "Download" reveal
                full_path = os.path.join(music_asset_dir, t_sel["filename"])
                screen.blit(font_small.render("File location:", True, ACCENT_CYAN),
                            (px, 418))
                screen.blit(font_small.render(full_path, True, (100, 210, 110)),
                            (px, 438))
                screen.blit(
                    font_small.render(
                        "(Navigate to this path to copy the file)",
                        True, (60, 60, 80)),
                    (px, 458))
            else:
                screen.blit(font_ui.render("LOCKED", True, (180, 60, 60)),
                            (px, 360))
                req  = t_sel.get("badge_req", "")
                name = BADGE_DEFINITIONS.get(req, {}).get("name", req)
                screen.blit(
                    font_small.render(f"Earn '{name}' badge to unlock.",
                                      True, DIM_WHITE),
                    (px, 406))

            pygame.draw.line(screen, ACCENT_CYAN,
                             (60, SCREEN_H - 36),
                             (SCREEN_W - 60, SCREEN_H - 36), 1)
            screen.blit(
                font_small.render(
                    "[ UP/DOWN ] Select   [ ENTER ] Play   [ ESC ] Back",
                    True, (60, 60, 90)),
                (60, SCREEN_H - 24))

            pygame.display.flip()
