"""
Visuals.py — Parallax starfield for ambient background animation.

Three independent depth layers scroll downward at different speeds to
produce the illusion of three-dimensional space depth.  Stars that drift
past the bottom edge are recycled at the top with a randomised x-position,
creating a seamless infinite loop.

The class is self-timing via pygame.time so draw() can be called from any
context — the main game loop, blocking sub-screens, or one-off renders —
without an external dt feed.  Each draw() advances by the real elapsed
milliseconds since the previous call, clamped to 100 ms to avoid large
position jumps after focus loss or an unusually slow frame.

Integration
-----------
  Replace make_stars / the static star list with:

      stars = ParallaxStarfield(SCREEN_W, SCREEN_H)

  draw_stars() in UI_Elements duck-types on the presence of a .draw()
  method, so every existing draw function (draw_menu, draw_galactic_map,
  etc.) and every blocking sub-screen (ProfileUI, CreditsUI …) will
  automatically use the parallax renderer without any signature change.
"""

import random
import pygame


# Layer spec: (star_count, size_lo, size_hi, base_brightness, drift_px_s)
_LAYERS = [
    (160, 1, 1,  80,  14.0),   # deep  — dim, slow
    ( 80, 1, 2, 160,  30.0),   # mid
    ( 30, 2, 3, 210,  62.0),   # near  — bright, fast
]


class ParallaxStarfield:
    """
    Three-layer scrolling starfield renderer.

    Calling draw(surface) advances the internal simulation clock, moves
    every star by the elapsed time, and blits the result directly onto
    the given surface.  No separate update() call is required.
    """

    def __init__(self, width: int, height: int):
        self._w = width
        self._h = height
        self._layers: list[list[dict]] = []

        for count, sz_lo, sz_hi, brightness, speed in _LAYERS:
            layer = [
                {
                    "x":     float(random.randint(0, width)),
                    "y":     float(random.randint(0, height)),
                    "size":  random.randint(sz_lo, sz_hi),
                    # Slight per-star colour variation for visual richness
                    "r":     max(0, min(255, brightness + random.randint(-20, 20))),
                    "g":     max(0, min(255, brightness + random.randint(-10, 10))),
                    "b":     max(0, min(255, brightness + random.randint(0,  40))),
                    "speed": speed + random.uniform(-6.0, 6.0),
                }
                for _ in range(count)
            ]
            self._layers.append(layer)

        # Wall-clock time reference for self-timing
        self._last_ms: int = pygame.time.get_ticks()

    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface):
        """
        Advance simulation by wall-clock elapsed time and blit all layers.

        The 100 ms clamp on dt prevents large position jumps after the window
        loses focus or the host machine experiences a momentary stall.
        """
        now           = pygame.time.get_ticks()
        dt            = min((now - self._last_ms) / 1000.0, 0.1)
        self._last_ms = now

        for layer in self._layers:
            for star in layer:
                star["y"] += star["speed"] * dt
                if star["y"] > self._h:
                    star["y"] = 0.0
                    star["x"] = float(random.randint(0, self._w))
                pygame.draw.circle(
                    surface,
                    (star["r"], star["g"], star["b"]),
                    (int(star["x"]), int(star["y"])),
                    star["size"],
                )
