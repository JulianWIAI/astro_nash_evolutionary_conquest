"""
SpriteRenderer.py — Loads static species images and applies data-driven visual effects.

Three archetypes map to three PNG files in assets/characters/:
    predator.png   — dominant aggression trait
    gatherer.png   — dominant metabolism trait
    technician.png — dominant speed trait

Visual effects applied each frame:
    Fitness     → smoothscale the sprite (base 50×50) up or down.
    Aggression  → red colour tint via BLEND_RGB_MULT.
    Speed       → slight rotation lean in the direction of orbital movement.
    Always      → smooth Y-axis bobbing via math.sin so sprites feel alive.
"""

import os
import math
import numpy as np
import pygame
import pygame.surfarray as surfarray


class SpriteRenderer:
    """
    Manages image loading, caching, and per-frame visual effect rendering.

    Images are loaded once on first use and stored in a cache so pygame does
    not re-read the file every frame. Transforms (scale, tint, rotate) are
    computed fresh each frame from live DNA values so the visuals update
    whenever the player or evolution loop mutates a species.

    Attributes:
        BASE_SIZE  : Pixel size (width = height) of the base sprite before
                     fitness scaling is applied. Default: 50.
        asset_dir  : Absolute path to the directory containing the PNG files.
        _raw_cache : Dict mapping archetype name → base pygame.Surface.
    """

    BASE_SIZE = 50

    # How many pixels the bob travels above/below the orbit centre.
    _BOB_AMPLITUDE = 7
    # Angular frequency of the bob (radians per second).
    _BOB_SPEED = 2.2

    def __init__(self, asset_dir: str):
        """
        Initialise the renderer with the path to the character images.

        Args:
            asset_dir : Absolute or relative path to assets/characters/.
        """
        self.asset_dir = asset_dir
        self._raw_cache: dict[str, pygame.Surface] = {}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _remove_background(self, img: pygame.Surface) -> pygame.Surface:
        """
        Make the flat gray background of a character PNG transparent.

        Algorithm:
          1. Sample the top-left corner pixel as the background colour.
          2. Compute per-pixel Euclidean distance (in RGB space) from that colour
             using numpy, which keeps this O(1) in Python regardless of image size.
          3. Pixels below the hard threshold → alpha = 0 (fully transparent).
          4. Pixels in the soft band → alpha fades linearly (smooth edge / anti-alias).
          5. Pixels above the band → alpha unchanged (belongs to the character).

        The soft band handles anti-aliased edges and the drop-shadow under each
        character so they blend naturally into the game background.

        Args:
            img : Source surface with alpha channel (convert_alpha already applied).

        Returns:
            The same surface with background pixels zeroed out in the alpha channel.
        """
        w, h = img.get_size()

        # Sample all four corners; the background is the most common corner colour.
        candidates = [img.get_at((0, 0)), img.get_at((w - 1, 0)),
                      img.get_at((0, h - 1)), img.get_at((w - 1, h - 1))]
        bg = max(candidates, key=lambda c: candidates.count(c))
        bg_rgb = np.array([bg.r, bg.g, bg.b], dtype=np.float32)

        # Get direct-access numpy views of the surface pixel data.
        # pixels3d shape: (w, h, 3) — note pygame uses (x, y) not (row, col)
        rgb   = surfarray.pixels3d(img).astype(np.float32)   # (w, h, 3)
        alpha = surfarray.pixels_alpha(img)                   # (w, h), dtype uint8

        # Per-pixel Euclidean distance from the background colour.
        dist = np.sqrt(np.sum((rgb - bg_rgb) ** 2, axis=2))  # (w, h)

        # Hard threshold: clearly background → fully transparent.
        HARD = 38.0
        # Soft band upper edge: anti-aliased edge pixels fade to full opacity.
        SOFT = 72.0

        alpha[dist < HARD] = 0
        soft_mask = (dist >= HARD) & (dist < SOFT)
        # Remap [HARD, SOFT] → [0, 1] and multiply existing alpha.
        fade = ((dist[soft_mask] - HARD) / (SOFT - HARD)).astype(np.float32)
        alpha[soft_mask] = (alpha[soft_mask] * fade).astype(np.uint8)

        # Delete views before the surface is used elsewhere (pygame requirement).
        del rgb, alpha
        return img

    def _load_base(self, archetype: str) -> pygame.Surface:
        """
        Load, strip the background from, and cache a species image.

        Background removal is done on the full-resolution source before
        downscaling so colour edges are sharp in the original image.
        smoothscale then produces high-quality results at BASE_SIZE.

        Args:
            archetype : One of 'predator', 'gatherer', 'technician'.

        Returns:
            pygame.Surface with alpha channel, scaled to BASE_SIZE.
        """
        if archetype in self._raw_cache:
            return self._raw_cache[archetype]

        path = os.path.join(self.asset_dir, f"{archetype}.png")
        try:
            img = pygame.image.load(path).convert_alpha()
            img = self._remove_background(img)
            img = pygame.transform.smoothscale(img, (self.BASE_SIZE, self.BASE_SIZE))
        except (pygame.error, FileNotFoundError):
            # Fallback: solid coloured square so missing assets don't crash.
            img = pygame.Surface((self.BASE_SIZE, self.BASE_SIZE), pygame.SRCALPHA)
            fallback = {
                "predator":   (220, 60,  60),
                "gatherer":   (60,  200, 80),
                "technician": (60,  120, 220),
            }
            img.fill(fallback.get(archetype, (160, 160, 160)))

        self._raw_cache[archetype] = img
        return img

    def _apply_tint(self, img: pygame.Surface, aggression: float) -> pygame.Surface:
        """
        Multiply each pixel's green and blue channels down based on aggression.

        At aggression=0 the tint is (255,255,255) — no change.
        At aggression=1 the tint is (255, 50, 50) — strongly red.

        BLEND_RGB_MULT maps  result = src_pixel × tint / 255  per channel,
        leaving alpha untouched.

        Args:
            img        : Source surface (will be modified in-place on a copy).
            aggression : Species dna['aggression'] in [0.0, 1.0].

        Returns:
            Tinted pygame.Surface.
        """
        tinted = img.copy()
        gb = int(255 * (1.0 - aggression * 0.82))  # 255 → 46 as aggression rises
        tinted.fill((255, gb, gb), special_flags=pygame.BLEND_RGB_MULT)
        return tinted

    def _apply_scale(self, img: pygame.Surface, fitness: float) -> pygame.Surface:
        """
        Resize the sprite proportionally to the species' fitness score.

        Fitness typically falls in [0, 5].  We map that range to a visual
        scale of [0.5×, 1.75×] relative to BASE_SIZE, so a thriving species
        is noticeably larger and a struggling one visibly smaller.

        Args:
            img     : Source surface.
            fitness : Species.fitness value (result of calculate_fitness()).

        Returns:
            Rescaled pygame.Surface using smoothscale for quality.
        """
        scale = max(0.5, min(1.75, fitness / 2.8))
        new_size = max(12, int(self.BASE_SIZE * scale))
        return pygame.transform.smoothscale(img, (new_size, new_size))

    def _apply_lean(self, img: pygame.Surface, speed: float, orbit_angle: float) -> pygame.Surface:
        """
        Rotate the sprite slightly to lean in its direction of orbital movement.

        For a counterclockwise orbit, the tangential velocity has a horizontal
        component of  -sin(orbit_angle).  We tilt the sprite by up to ±8°
        (scaled by the speed trait) in that direction, giving the impression
        the species is pressing forward.

        pygame.transform.rotate uses counterclockwise-positive convention.

        Args:
            img          : Source surface.
            speed        : Species dna['speed'] in [0.0, 1.0].
            orbit_angle  : Current angle in radians on the orbit ellipse.

        Returns:
            Rotated pygame.Surface (bounding box grows to contain corners).
        """
        lean = math.sin(orbit_angle) * speed * 8.0
        if abs(lean) < 0.5:
            return img  # Skip trivially small rotations
        return pygame.transform.rotate(img, lean)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(
        self,
        surface: pygame.Surface,
        species,
        position: tuple,
        tick: float,
        orbit_angle: float = 0.0,
    ) -> pygame.Rect:
        """
        Draw a species sprite onto surface with all data-driven effects applied.

        Effect pipeline (order matters — scale before tint keeps colour accuracy):
          1. Load/cache base image.
          2. Fitness → scale.
          3. Aggression → red tint (BLEND_RGB_MULT).
          4. Speed → lean rotation.
          5. Bob: sinusoidal Y offset unique to this species.
          6. Blit centred on the bobbed position.

        Args:
            surface      : Target pygame.Surface to draw onto.
            species      : Species instance whose DNA and fitness drive effects.
            position     : (x, y) orbit centre position in pixels.
            tick         : Elapsed time in seconds (drives the bob oscillation).
            orbit_angle  : Radians along the orbit path (drives lean direction).

        Returns:
            pygame.Rect: The final blit rectangle (use .bottom for label placement).
        """
        species.calculate_fitness()

        # Step 1 — base image
        img = self._load_base(species.sprite_type)

        # Step 2 — fitness scaling
        img = self._apply_scale(img, species.fitness)

        # Step 3 — aggression tint
        img = self._apply_tint(img, species.dna.get("aggression", 0.5))

        # Step 4 — speed lean
        img = self._apply_lean(img, species.dna.get("speed", 0.5), orbit_angle)

        # Step 5 — unique bobbing phase derived from species name
        phase = (hash(species.name) % 628) * 0.01   # spread 0 → ~2π
        bob_y = math.sin(tick * self._BOB_SPEED + phase) * self._BOB_AMPLITUDE

        x, y = position
        rect = img.get_rect(center=(int(x), int(y + bob_y)))

        # Step 6 — blit
        surface.blit(img, rect)
        return rect
