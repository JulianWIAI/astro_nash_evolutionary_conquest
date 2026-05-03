"""
LossScreen.py — "Civilization Collapse" defeat screen.

Presents the player's final statistics alongside two recovery options so
they are not forced back to the main menu after a single bad run.

Controls
--------
  R      Reload the last save file and continue from that checkpoint.
  ESC    Return to the main menu.

Return values
-------------
  'RELOAD'  Caller should invoke SaveManager.load() then transition to MAP.
  'MENU'    Caller should transition to MENU.
"""

import math
import pygame

from ui.UI_Elements import (
    SCREEN_W, SCREEN_H, ACCENT_GOLD, DIM_WHITE, WHITE,
    BTN_DARK, BTN_HOVER, draw_stars,
)

_RED     = (220,  40,  40)
_DIM_RED = (160,  80,  80)
_BTN_W   = 210
_BTN_H   = 50


class LossScreen:
    """
    Self-contained defeat screen.

    Call run() to enter the blocking event loop.  Returns an action string
    that the caller uses to decide the next game state transition.
    """

    def run(self, screen: pygame.Surface, clock: pygame.time.Clock,
            font_title, font_ui, font_small, stars,
            conquered_planets: list, total_planets: int) -> str:
        """
        Args:
            conquered_planets : Planets the player captured before extinction.
            total_planets     : Total planets in the galaxy this session.

        Returns:
            'RELOAD' or 'MENU'.
        """
        tick = 0.0
        cx   = SCREEN_W // 2

        # Two action buttons centred horizontally
        reload_r = pygame.Rect(cx - _BTN_W - 14, SCREEN_H - 122, _BTN_W, _BTN_H)
        menu_r   = pygame.Rect(cx + 14,           SCREEN_H - 122, _BTN_W, _BTN_H)

        while True:
            dt     = clock.tick(60) / 1000.0
            tick  += dt
            mx, my = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "MENU"
                    elif event.key == pygame.K_r:
                        return "RELOAD"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if reload_r.collidepoint(mx, my):
                        return "RELOAD"
                    if menu_r.collidepoint(mx, my):
                        return "MENU"

            # Red-tinted starfield
            screen.fill((8, 2, 2))
            draw_stars(screen, stars, tick)

            pulse = int(170 + 50 * math.sin(tick * 1.2))
            t1 = font_title.render("CIVILIZATION  COLLAPSE", True, (pulse, 20, 20))
            t2 = font_title.render("ALL  SPECIES  EXTINCT", True, _RED)
            screen.blit(t1, t1.get_rect(centerx=cx, top=52))
            screen.blit(t2, t2.get_rect(centerx=cx, top=126))

            pygame.draw.line(screen, _RED, (cx - 380, 206), (cx + 380, 206), 2)

            for i, line in enumerate([
                f"Planets Conquered:  {len(conquered_planets)} / {total_planets}",
                "No Nash Equilibrium was sustained across the galaxy.",
                "",
                "The silence of stars remains.",
            ]):
                s = font_ui.render(line, True, _DIM_RED)
                screen.blit(s, s.get_rect(centerx=cx, top=234 + i * 42))

            # Reload / Menu buttons
            for rect, label in [(reload_r, "[ R ]  Reload Save"),
                                 (menu_r,   "[ ESC ]  Main Menu")]:
                hov = rect.collidepoint(mx, my)
                pygame.draw.rect(screen, BTN_HOVER if hov else BTN_DARK,
                                 rect, border_radius=8)
                pygame.draw.rect(screen, _RED, rect, 2, border_radius=8)
                s = font_ui.render(label, True, WHITE if hov else _DIM_RED)
                screen.blit(s, s.get_rect(center=rect.center))

            pygame.display.flip()
