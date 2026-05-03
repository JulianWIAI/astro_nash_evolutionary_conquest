"""
PauseMenu.py — In-game pause overlay.

Renders a semitransparent panel over a frozen snapshot of the last rendered
frame and presents a compact action list.  The game simulation is effectively
paused while the overlay blocks the main event loop.

Keyboard shortcuts
------------------
  ESC / P    Resume.
  UP / DOWN  Navigate.
  ENTER      Confirm the highlighted item.

Return values
-------------
  'RESUME'       Continue the active game session.
  'HOW_TO_PLAY'  Caller should open the How-to-Play screen.
  'PROFILE'      Caller should open the Profile screen.
  'MENU'         Caller should transition back to the main menu.
"""

import pygame

from ui.UI_Elements import (
    SCREEN_W, SCREEN_H, ACCENT_CYAN, ACCENT_GOLD,
    DIM_WHITE, WHITE, BTN_DARK, BTN_HOVER,
)

_OPTIONS = [
    ("RESUME",      "Resume"),
    ("HOW_TO_PLAY", "How to Play"),
    ("PROFILE",     "View Profile"),
    ("MENU",        "Quit to Menu"),
]

_ITEM_H  = 50
_PANEL_W = 360
_PANEL_H = len(_OPTIONS) * (_ITEM_H + 8) + 80
_BTN_W   = _PANEL_W - 40


def _item_rect(i: int, px: int, py: int) -> pygame.Rect:
    """Return the bounding rect for option button at list index i."""
    return pygame.Rect(px + 20, py + 64 + i * (_ITEM_H + 8), _BTN_W, _ITEM_H)


class PauseMenu:
    """
    Self-contained pause overlay.

    Call run() with the current screen snapshot; it blocks until the player
    makes a choice and returns an action string for the caller to handle.
    """

    def run(self, screen: pygame.Surface, clock: pygame.time.Clock,
            font_title, font_ui,
            snapshot: pygame.Surface) -> str:
        """
        Args:
            snapshot : pygame.Surface copy captured just before pausing.
                       Displayed frozen behind the overlay so the player can
                       see their game state while navigating the menu.

        Returns:
            One of 'RESUME', 'HOW_TO_PLAY', 'PROFILE', 'MENU'.
        """
        selected = 0
        px = (SCREEN_W - _PANEL_W) // 2
        py = (SCREEN_H - _PANEL_H) // 2

        while True:
            clock.tick(60)
            mx, my = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit

                if event.type == pygame.KEYDOWN:
                    k = event.key
                    if k in (pygame.K_ESCAPE, pygame.K_p):
                        return "RESUME"
                    elif k == pygame.K_UP:
                        selected = (selected - 1) % len(_OPTIONS)
                    elif k == pygame.K_DOWN:
                        selected = (selected + 1) % len(_OPTIONS)
                    elif k == pygame.K_RETURN:
                        return _OPTIONS[selected][0]

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i in range(len(_OPTIONS)):
                        if _item_rect(i, px, py).collidepoint(mx, my):
                            return _OPTIONS[i][0]

            # Frozen game frame + translucent dimming layer
            screen.blit(snapshot, (0, 0))
            dim = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 148))
            screen.blit(dim, (0, 0))

            # Panel background with cyan border
            panel = pygame.Surface((_PANEL_W, _PANEL_H), pygame.SRCALPHA)
            panel.fill((7, 7, 28, 222))
            screen.blit(panel, (px, py))
            pygame.draw.rect(screen, ACCENT_CYAN,
                             (px, py, _PANEL_W, _PANEL_H), 2, border_radius=8)

            t = font_title.render("PAUSED", True, ACCENT_GOLD)
            screen.blit(t, t.get_rect(centerx=px + _PANEL_W // 2, top=py + 12))

            for i, (_, label) in enumerate(_OPTIONS):
                rect    = _item_rect(i, px, py)
                hovered = rect.collidepoint(mx, my) or i == selected
                pygame.draw.rect(screen, BTN_HOVER if hovered else BTN_DARK,
                                 rect, border_radius=6)
                pygame.draw.rect(screen, ACCENT_CYAN, rect, 1, border_radius=6)
                lbl = font_ui.render(label, True,
                                     ACCENT_GOLD if hovered else DIM_WHITE)
                screen.blit(lbl, lbl.get_rect(center=rect.center))

            pygame.display.flip()
