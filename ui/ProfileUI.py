"""
ProfileUI.py — Pokemon-style "Trainer Card" profile screen.

Layout
------
  Left panel  (0 – 400 px)    Avatar, username, lifetime stats, controls.
  Right panel (420 – 1260 px) Badge grid — row 1 planet badges, row 2 specials.

Controls
--------
  [U]    Upload profile picture via OS file-dialog (tkinter).
  [N]    Create a new profile (in-game text prompt).
  [G]    Open Music Gallery.
  [←/→]  Cycle between existing profiles.
  [ESC]  Return to menu.

Badge rendering
---------------
  If assets/badges/<filename>.png exists it is loaded and scaled to 76×76.
  Otherwise a colored-circle placeholder is drawn.
  Locked badges get a dark translucent overlay.
  Hovering a badge shows a tooltip with name, description, and lock state.
"""

import os

import numpy as np
import pygame
import pygame.surfarray as surfarray

from ui.UI_Elements import (
    SCREEN_W, SCREEN_H, DEEP_SPACE, ACCENT_CYAN, ACCENT_GOLD,
    DIM_WHITE, WHITE, BTN_DARK, draw_stars,
)
from logic.BadgeEngine import BADGE_DEFINITIONS, BadgeEngine

_BADGE_W      = 76
_BADGE_H      = 76
_BADGE_GAP    = 12
_ROW1_Y       = 168
_ROW2_Y       = 296
_BADGE_START_X = 440
_BADGE_SIZE   = (_BADGE_W, _BADGE_H)

_AVATAR_W = 152
_AVATAR_H = 152


# ---------------------------------------------------------------------------
# File-dialog helper (gracefully skips if tkinter absent)
# ---------------------------------------------------------------------------
def _pick_file() -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(
            title="Select Profile Picture",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.bmp"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
        return path or ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Badge surface helpers
# ---------------------------------------------------------------------------
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


def _load_badge_surface(badge_id: str, asset_dir: str) -> pygame.Surface:
    info = BADGE_DEFINITIONS.get(badge_id, {})
    path = os.path.join(asset_dir, info.get("file", ""))
    try:
        img = pygame.image.load(path).convert_alpha()
        img = _remove_chroma_key(img)
        return pygame.transform.smoothscale(img, _BADGE_SIZE)
    except Exception:
        return _make_placeholder(info.get("color", (100, 100, 180)),
                                 info.get("name", "??")[:2].upper())


def _make_placeholder(color: tuple, initials: str) -> pygame.Surface:
    surf = pygame.Surface(_BADGE_SIZE, pygame.SRCALPHA)
    cx = cy = _BADGE_W // 2
    r  = cx - 4
    pygame.draw.circle(surf, (25, 25, 45), (cx, cy), r)
    pygame.draw.circle(surf, color,        (cx, cy), r, 4)
    font = pygame.font.SysFont("consolas, courier new, menlo, monaco", 18, bold=True)
    t    = font.render(initials, True, color)
    surf.blit(t, (cx - t.get_width() // 2, cy - t.get_height() // 2))
    return surf


def _locked_overlay(surf: pygame.Surface) -> pygame.Surface:
    copy = surf.copy()
    ov   = pygame.Surface(_BADGE_SIZE, pygame.SRCALPHA)
    ov.fill((10, 10, 30, 195))
    copy.blit(ov, (0, 0))
    return copy


def _scale_to_fit(img: pygame.Surface, target_w: int, target_h: int) -> pygame.Surface:
    """
    Halve the image repeatedly until within 4× of the target, then smoothscale.

    A direct smoothscale from 4K (8 MP) to 152 px touches every source pixel
    once — that's ~25 ms on slow hardware and causes a visible frame spike.
    Each halving pass costs O(pixels/4), so four fast passes replace one slow
    one.  We clamp each intermediate size so we never undershoot the target.
    """
    w, h = img.get_size()
    while w > target_w * 4 or h > target_h * 4:
        w = max(w // 2, target_w)
        h = max(h // 2, target_h)
        img = pygame.transform.scale(img, (w, h))
    return pygame.transform.smoothscale(img, (target_w, target_h))


def _load_avatar(path: str) -> pygame.Surface | None:
    if not path or not os.path.exists(path):
        return None
    try:
        raw = pygame.image.load(path)
        img = raw.convert_alpha() if raw.get_alpha() is not None else raw.convert()
        return _scale_to_fit(img, _AVATAR_W, _AVATAR_H)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------
class ProfileUI:
    """
    Self-contained Trainer Card screen.

    Call run() to enter the blocking event loop; returns when ESC is pressed.
    """

    def run(self, screen: pygame.Surface, clock: pygame.time.Clock,
            font_title, font_ui, font_small, stars: list,
            profile_manager, badge_asset_dir: str,
            music_gallery=None, music_asset_dir: str = ""):
        """
        Args:
            badge_asset_dir  : Absolute path to assets/badges/.
            music_gallery    : Optional MusicGallery instance; [G] opens it.
            music_asset_dir  : Absolute path to assets/music/ (passed to gallery).
        """
        tick          = 0.0
        _badge_cache: dict  = {}
        _avatar_cache: dict = {}   # path -> Surface | None; populated once per path
        _profile_ids  = [pid for pid, _ in profile_manager.list_profiles()]
        active_id     = profile_manager.get_active_id()
        _active_idx   = _profile_ids.index(active_id) if active_id in _profile_ids else 0
        _creating     = False
        _new_name     = ""
        hover_badge   = None

        def _get_surfs(badge_id):
            if badge_id not in _badge_cache:
                base   = _load_badge_surface(badge_id, badge_asset_dir)
                locked = _locked_overlay(base)
                _badge_cache[badge_id] = (base, locked)
            return _badge_cache[badge_id]

        def _badge_rect(idx: int, row: int) -> pygame.Rect:
            x = _BADGE_START_X + idx * (_BADGE_W + _BADGE_GAP)
            y = _ROW1_Y if row == 1 else _ROW2_Y
            return pygame.Rect(x, y, _BADGE_W, _BADGE_H)

        def _refresh_profiles():
            nonlocal _profile_ids, _active_idx
            _profile_ids = [pid for pid, _ in profile_manager.list_profiles()]
            aid = profile_manager.get_active_id()
            _active_idx = _profile_ids.index(aid) if aid in _profile_ids else 0
            _badge_cache.clear()
            _avatar_cache.clear()

        while True:
            dt     = clock.tick(60) / 1000.0
            tick  += dt
            mx, my = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit

                # ---- Text-input mode ----
                if _creating:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            _creating = False
                            _new_name = ""
                        elif event.key == pygame.K_RETURN and _new_name.strip():
                            profile_manager.create_profile(_new_name.strip())
                            _refresh_profiles()
                            _active_idx = len(_profile_ids) - 1
                            profile_manager.set_active_profile(
                                _profile_ids[_active_idx])
                            _creating = False
                            _new_name = ""
                        elif event.key == pygame.K_BACKSPACE:
                            _new_name = _new_name[:-1]
                        elif event.unicode.isprintable() and len(_new_name) < 20:
                            _new_name += event.unicode
                    continue

                # ---- Normal navigation ----
                if event.type == pygame.KEYDOWN:
                    k = event.key
                    if k == pygame.K_ESCAPE:
                        return
                    elif k == pygame.K_u:
                        path = _pick_file()
                        if path:
                            profile_manager.set_avatar(path)
                            _avatar_cache.clear()
                    elif k == pygame.K_n:
                        _creating = True
                    elif k == pygame.K_g and music_gallery is not None:
                        music_gallery.run(screen, clock,
                                          font_title, font_ui, font_small,
                                          stars, profile_manager, music_asset_dir)
                    elif k == pygame.K_LEFT and len(_profile_ids) > 1:
                        _active_idx = (_active_idx - 1) % len(_profile_ids)
                        profile_manager.set_active_profile(_profile_ids[_active_idx])
                        _badge_cache.clear()
                        _avatar_cache.clear()
                    elif k == pygame.K_RIGHT and len(_profile_ids) > 1:
                        _active_idx = (_active_idx + 1) % len(_profile_ids)
                        profile_manager.set_active_profile(_profile_ids[_active_idx])
                        _badge_cache.clear()
                        _avatar_cache.clear()

            # ---- Hover detection ----
            hover_badge = None
            for row in (1, 2):
                for idx, bid in enumerate(BadgeEngine.get_row(row)):
                    if _badge_rect(idx, row).collidepoint(mx, my):
                        hover_badge = bid

            # ================================================================
            # DRAW
            # ================================================================
            screen.fill(DEEP_SPACE)
            draw_stars(screen, stars, tick)

            profile = profile_manager.get_active_profile()
            stats   = profile.get("lifetime_stats", {})
            owned   = set(profile.get("unlocked_badges", []))

            # Vertical panel divider
            pygame.draw.line(screen, ACCENT_CYAN, (412, 0), (412, SCREEN_H), 1)

            # ── LEFT PANEL ──────────────────────────────────────────────
            # Avatar box — load once per path, cache for the rest of the session
            avatar_path = profile.get("avatar_path", "")
            if avatar_path not in _avatar_cache:
                _avatar_cache[avatar_path] = _load_avatar(avatar_path)
            av_surf = _avatar_cache[avatar_path]
            ax, ay  = 30, 70
            if av_surf:
                screen.blit(av_surf, (ax, ay))
                pygame.draw.rect(screen, ACCENT_GOLD,
                                 (ax - 2, ay - 2, 156, 156), 2)
            else:
                pygame.draw.rect(screen, (28, 28, 55), (ax, ay, 152, 152))
                pygame.draw.rect(screen, ACCENT_CYAN, (ax, ay, 152, 152), 2)
                ph = font_small.render("[ no photo ]", True, (70, 70, 100))
                screen.blit(ph, (ax + 76 - ph.get_width() // 2, ay + 68))

            # Username (large, gold) + profile index
            screen.blit(
                font_title.render(profile.get("username", "?"), True, ACCENT_GOLD),
                (20, 232))
            screen.blit(
                font_small.render(
                    f"Profile  {_active_idx + 1} / {len(_profile_ids)}",
                    True, (70, 70, 100)),
                (20, 282))

            # Lifetime stats
            mins, secs = divmod(int(stats.get("time_played", 0)), 60)
            hrs, mins  = divmod(mins, 60)
            for ly, text in [
                (312, f"Planets Conquered : {stats.get('planets_conquered', 0)}"),
                (334, f"Time Played       : {hrs}h {mins:02d}m {secs:02d}s"),
                (356, f"Games Played      : {stats.get('games_played', 0)}"),
                (378, f"Badges Earned     : {len(owned)} / {len(BADGE_DEFINITIONS)}"),
            ]:
                screen.blit(font_small.render(text, True, DIM_WHITE), (20, ly))

            # Controls hint
            for ly, text in [
                (SCREEN_H - 126, "[U]    Upload profile picture"),
                (SCREEN_H - 104, "[N]    Create new profile"),
                (SCREEN_H -  82, "[G]    Music Gallery"),
                (SCREEN_H -  60, "[</>]  Cycle profiles"),
                (SCREEN_H -  38, "[ESC]  Back to menu"),
            ]:
                screen.blit(font_small.render(text, True, (60, 60, 90)), (20, ly))

            # ── RIGHT PANEL ─────────────────────────────────────────────
            screen.blit(
                font_title.render("BADGES", True, ACCENT_CYAN), (440, 16))
            pygame.draw.line(screen, ACCENT_CYAN, (440, 64), (1260, 64), 1)

            for row, label, header_y, row_y in [
                (1, "PLANET BADGES",      _ROW1_Y - 26, _ROW1_Y),
                (2, "ACHIEVEMENT BADGES", _ROW2_Y - 26, _ROW2_Y),
            ]:
                screen.blit(font_small.render(label, True, ACCENT_GOLD),
                            (_BADGE_START_X, header_y))
                for idx, bid in enumerate(BadgeEngine.get_row(row)):
                    rect   = _badge_rect(idx, row)
                    is_own = bid in owned
                    base_s, lock_s = _get_surfs(bid)
                    screen.blit(base_s if is_own else lock_s, rect.topleft)
                    if is_own:
                        pygame.draw.rect(screen, ACCENT_GOLD, rect, 2,
                                         border_radius=6)

            # Hover tooltip
            if hover_badge:
                info   = BADGE_DEFINITIONS[hover_badge]
                is_own = hover_badge in owned
                color  = ACCENT_GOLD if is_own else (110, 110, 130)
                status = "UNLOCKED" if is_own else "LOCKED"
                tx     = min(mx + 14, SCREEN_W - 218)
                ty     = max(my - 62, 4)
                tp     = pygame.Surface((210, 62), pygame.SRCALPHA)
                tp.fill((8, 8, 28, 215))
                screen.blit(tp, (tx, ty))
                pygame.draw.rect(screen, color, (tx, ty, 210, 62), 1,
                                 border_radius=4)
                screen.blit(font_small.render(info["name"],     True, color),
                            (tx + 6, ty + 4))
                screen.blit(font_small.render(info["desc"],     True, DIM_WHITE),
                            (tx + 6, ty + 22))
                screen.blit(font_small.render(f"[ {status} ]", True, color),
                            (tx + 6, ty + 40))

            # ---- New-profile text-input overlay ----
            if _creating:
                ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                ov.fill((0, 0, 0, 165))
                screen.blit(ov, (0, 0))
                box = pygame.Rect(SCREEN_W // 2 - 230, SCREEN_H // 2 - 48, 460, 96)
                pygame.draw.rect(screen, (10, 10, 35), box, border_radius=8)
                pygame.draw.rect(screen, ACCENT_CYAN,  box, 2, border_radius=8)
                screen.blit(font_ui.render("Enter username:", True, ACCENT_CYAN),
                            (box.x + 14, box.y + 10))
                screen.blit(font_ui.render(_new_name + "_", True, WHITE),
                            (box.x + 14, box.y + 50))

            pygame.display.flip()
