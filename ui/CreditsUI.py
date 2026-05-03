"""
CreditsUI.py — Auto-scrolling credits screen.

Attributes this project as a Staatlich gepruefter Wirtschaftsinformatiker
programming exam project and credits the AI-assisted development workflow.

Controls
--------
  ESC / SPACE  Exit.
  UP / DOWN    Scrub the scroll position manually.
"""

import pygame

from ui.UI_Elements import (
    SCREEN_W, SCREEN_H, DEEP_SPACE, ACCENT_CYAN, ACCENT_GOLD,
    DIM_WHITE, draw_stars,
)

# (kind, text)  — kind drives font selection and colour
_LINES = [
    ("gap",    ""),
    ("gap",    ""),
    ("title",  "ASTRO-NASH"),
    ("title",  "EVOLUTIONARY CONQUEST"),
    ("gap",    ""),
    ("sub",    "A Programming Exam Project"),
    ("text",   "Wirtschaftsinformatik  —  Staatlich gepruefter Wirtschaftsinformatiker"),
    ("gap",    ""),
    ("sep",    ""),
    ("gap",    ""),
    ("header", "DEVELOPMENT"),
    ("text",   "Game Design & Programming     Julian Gast"),
    ("text",   "AI-Assisted Development       Claude Code  (Anthropic)"),
    ("text",   "Music Generation              AI-Assisted"),
    ("gap",    ""),
    ("header", "TECHNOLOGY STACK"),
    ("text",   "Python 3.x  /  Pygame 2.x"),
    ("text",   "SHA-256 Data Integrity  (SaveManager)"),
    ("text",   "Nash Equilibrium Game Theory  (GameTheory)"),
    ("text",   "NEAT-Inspired Neural Evolution  (AIEngine)"),
    ("text",   "Difficulty Scaling Engine  (DifficultyManager)"),
    ("text",   "Modular Building System  (BuildingManager)"),
    ("text",   "Global Badge & Profile Persistence  (ProfileManager)"),
    ("gap",    ""),
    ("header", "AI WORKFLOW NOTE"),
    ("body",   "This project was built in direct collaboration with"),
    ("body",   "Claude Code (claude.ai/code), an AI coding assistant"),
    ("body",   "developed by Anthropic."),
    ("body",   ""),
    ("body",   "Architecture decisions, creative direction, and all"),
    ("body",   "final code were authored by the student developer."),
    ("body",   "The AI served as a technical implementation partner,"),
    ("body",   "accelerating complex module development."),
    ("gap",    ""),
    ("sep",    ""),
    ("gap",    ""),
    ("header", "ACKNOWLEDGEMENTS"),
    ("text",   "Course Supervisor  —  Project Guidance"),
    ("text",   "Pygame Community   —  Open Source Framework"),
    ("text",   "Anthropic          —  AI Development Platform"),
    ("gap",    ""),
    ("sep",    ""),
    ("gap",    ""),
    ("sub",    "Built with purpose. Played with curiosity."),
    ("gap",    ""),
    ("gap",    ""),
    ("gap",    ""),
    ("gap",    ""),
]

_LINE_H = {
    "title": 68, "sub": 32, "header": 30,
    "text":  24, "body": 22, "gap": 16, "sep": 6,
}
_TOTAL_SCROLL = sum(_LINE_H[k] + 4 for k, _ in _LINES) + SCREEN_H


class CreditsUI:
    """
    Auto-scrolling credits.  Loops back to the top when fully scrolled past.
    Call run() to enter the blocking event loop.
    """

    def run(self, screen: pygame.Surface, clock: pygame.time.Clock,
            font_title, font_ui, font_small, stars: list):
        tick     = 0.0
        scroll_y = float(SCREEN_H)
        speed    = 42.0   # pixels per second

        while True:
            dt       = clock.tick(60) / 1000.0
            tick    += dt
            scroll_y -= speed * dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_SPACE):
                        return
                    elif event.key == pygame.K_UP:
                        scroll_y += 80
                    elif event.key == pygame.K_DOWN:
                        scroll_y -= 80

            if scroll_y < -_TOTAL_SCROLL:
                scroll_y = float(SCREEN_H)

            screen.fill(DEEP_SPACE)
            draw_stars(screen, stars, tick)

            cx     = SCREEN_W // 2
            draw_y = int(scroll_y)

            for kind, text in _LINES:
                h = _LINE_H[kind] + 4

                # Skip off-screen lines for performance
                if draw_y > SCREEN_H + 10:
                    draw_y += h
                    continue
                if draw_y < -(h + 10):
                    draw_y += h
                    continue

                if kind == "sep":
                    pygame.draw.line(screen, ACCENT_CYAN,
                                     (cx - 280, draw_y + 3),
                                     (cx + 280, draw_y + 3), 1)
                elif kind == "gap":
                    pass
                elif kind == "title":
                    s = font_title.render(text, True, ACCENT_GOLD)
                    screen.blit(s, s.get_rect(centerx=cx, top=draw_y))
                elif kind == "sub":
                    s = font_ui.render(text, True, ACCENT_CYAN)
                    screen.blit(s, s.get_rect(centerx=cx, top=draw_y))
                elif kind == "header":
                    s = font_ui.render(text, True, ACCENT_GOLD)
                    screen.blit(s, s.get_rect(centerx=cx, top=draw_y))
                elif kind == "text":
                    s = font_small.render(text, True, DIM_WHITE)
                    screen.blit(s, s.get_rect(centerx=cx, top=draw_y))
                elif kind == "body":
                    s = font_small.render(text, True, (160, 178, 196))
                    screen.blit(s, s.get_rect(centerx=cx, top=draw_y))

                draw_y += h

            hint = font_small.render(
                "[ ESC / SPACE  —  BACK TO MENU ]   [ UP/DOWN  —  SCRUB ]",
                True, (60, 60, 90))
            screen.blit(hint, hint.get_rect(centerx=cx, top=6))

            pygame.display.flip()
