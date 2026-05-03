"""
PlanetRenderer.py — Loads planet PNG images, removes the #00FF00 chroma key
background, caches the result, and draws planets on both the galactic map and
the planet detail view.

Chroma key removal uses a numpy-based Euclidean distance approach so that
anti-aliased edge pixels (where the green background blends into the planet's
glow) fade out smoothly rather than leaving a harsh green fringe.
"""

import os
import numpy as np
import pygame
import pygame.surfarray as surfarray


class PlanetRenderer:
    """
    Handles loading, chroma-key removal, caching, and rendering of planet images.

    Two draw methods cover the two views:
        draw_on_map()    — small sprite at the planet's galactic-map position.
        draw_in_detail() — large sprite centred in the planet detail view.

    Images are loaded once per filename and stored as cleaned SRCALPHA surfaces.
    Scaled variants are cached by (filename, pixel_size) so smoothscale is only
    called when the requested size is new.

    Attributes:
        asset_dir     : Path to the folder containing the planet PNG files.
        _raw_cache    : filename → full-resolution SRCALPHA surface.
        _scaled_cache : (filename, size) → pre-scaled SRCALPHA surface.
    """

    # Chroma key colour that marks the transparent background in each planet PNG.
    CHROMA_KEY = (0, 255, 0)

    # Greenness score = G - max(R, B).  Pure #00FF00 scores 255.
    # Pixels above HARD are definitely background; below SOFT are definitely planet.
    _HARD_GREEN = 175
    _SOFT_GREEN = 45

    def __init__(self, asset_dir: str):
        """
        Initialise the renderer with the path to the planet image directory.

        Args:
            asset_dir : Absolute path to assets/planets/.
        """
        self.asset_dir = asset_dir
        self._raw_cache: dict[str, pygame.Surface] = {}
        self._scaled_cache: dict[tuple, pygame.Surface] = {}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _remove_chroma_key(self, img: pygame.Surface) -> pygame.Surface:
        """
        Remove the #00FF00 green-screen background using a greenness-score metric.

        Why greenness score instead of L2 distance from (0,255,0):
          L2 distance fails on planets with coloured glow halos.  For example,
          Kharenos has an orange-yellow edge that blends with the green background,
          producing pixels like (100, 200, 20).  Their L2 distance from pure green
          is ~116, beyond the soft threshold, so they survive as opaque green residue.
          The greenness score  G − max(R, B)  measures how *dominantly* green a
          pixel is, independent of its brightness, which is exactly what video
          chroma-keying uses.

        Algorithm:
          1. Compute greenness = G − max(R, B) for every pixel (float array).
          2. greenness > HARD_GREEN  →  t = 0  (background, fully transparent).
          3. greenness < SOFT_GREEN  →  t = 1  (planet interior, fully opaque).
          4. Between the two        →  t fades linearly (smooth edge).
          5. Apply t to both alpha AND rgb channels.  Zeroing the rgb of background
             pixels prevents pygame.transform.smoothscale from blending the green
             colour into neighbouring pixels during downscaling (green fringe fix).

        Args:
            img : Surface already converted with convert_alpha().

        Returns:
            The same surface with background pixels made transparent and their
            RGB zeroed so scaling stays clean.
        """
        # Take a float COPY for calculations, then release the surface lock.
        _lock = surfarray.pixels3d(img)
        rgb_float = _lock.astype(np.float32)   # shape (w, h, 3)
        del _lock

        # Greenness score: how much more green than red or blue.
        # Range: −255 (no green) … 255 (pure #00FF00).
        greenness = rgb_float[:, :, 1] - np.maximum(rgb_float[:, :, 0],
                                                     rgb_float[:, :, 2])

        # Build per-pixel fade factor t  (0 = transparent, 1 = opaque).
        t = np.ones(greenness.shape, dtype=np.float32)
        hard = greenness > self._HARD_GREEN
        soft = (greenness >= self._SOFT_GREEN) & (greenness <= self._HARD_GREEN)
        t[hard] = 0.0
        band = float(self._HARD_GREEN - self._SOFT_GREEN)
        t[soft] = (self._HARD_GREEN - greenness[soft]) / band   # 1 at SOFT, 0 at HARD

        # --- Apply to alpha (sequential locks, never held simultaneously) ---
        alpha = surfarray.pixels_alpha(img)
        alpha[:] = np.clip(alpha.astype(np.float32) * t, 0, 255).astype(np.uint8)
        del alpha

        # --- Apply to RGB: zero background, fade edges toward black ---
        # This prevents smoothscale from leaking green into planet edge pixels.
        rgb_view = surfarray.pixels3d(img)
        rgb_view[:] = np.clip(
            rgb_float * t[:, :, np.newaxis], 0, 255
        ).astype(np.uint8)
        del rgb_view

        return img

    def _load(self, filename: str) -> pygame.Surface:
        """
        Load a planet image, strip its chroma key, and cache the result.

        Args:
            filename : Basename of the PNG file (e.g. 'ignaros.png').

        Returns:
            Full-resolution SRCALPHA surface with the green background removed.
            Falls back to a coloured placeholder circle if the file is missing.
        """
        if filename in self._raw_cache:
            return self._raw_cache[filename]

        path = os.path.join(self.asset_dir, filename)
        try:
            img = pygame.image.load(path).convert_alpha()
            img = self._remove_chroma_key(img)
        except (pygame.error, FileNotFoundError):
            # Placeholder: semi-transparent grey circle so the game still runs.
            img = pygame.Surface((200, 200), pygame.SRCALPHA)
            pygame.draw.circle(img, (120, 120, 140, 200), (100, 100), 100)

        self._raw_cache[filename] = img
        return img

    def _get_scaled(self, filename: str, pixel_size: int) -> pygame.Surface:
        """
        Return a cached copy of the planet image scaled to pixel_size × pixel_size.

        Uses smoothscale (bilinear) for quality downscaling from large originals.

        Args:
            filename   : Planet image filename.
            pixel_size : Side length in pixels for the square output surface.

        Returns:
            Scaled SRCALPHA surface.
        """
        key = (filename, pixel_size)
        if key not in self._scaled_cache:
            raw = self._load(filename)
            self._scaled_cache[key] = pygame.transform.smoothscale(
                raw, (pixel_size, pixel_size)
            )
        return self._scaled_cache[key]

    # ------------------------------------------------------------------
    # Public draw API
    # ------------------------------------------------------------------

    def draw_on_map(
        self,
        surface: pygame.Surface,
        planet,
        mouse_pos: tuple,
        name_font: pygame.font.Font,
        badge_font: pygame.font.Font,
    ):
        """
        Draw a planet sprite on the galactic map, replacing the plain circle.

        The sprite is sized to match planet.radius * 2 so click detection
        (which is still based on radius) stays accurate.  A cyan ring appears
        on hover, and the planet name / species badge are drawn below the image.

        Args:
            surface    : The galactic-map pygame surface.
            planet     : Planet instance (must have .image_file, .position, .radius).
            mouse_pos  : Current mouse position for hover detection.
            name_font  : Font for the planet name label.
            badge_font : Font for the '×N species' badge.
        """
        WHITE      = (255, 255, 255)
        ACCENT_CYAN = (0, 200, 255)
        ACCENT_GOLD = (255, 200, 50)
        DIM_WHITE  = (180, 180, 180)

        px, py = planet.position
        hovered = planet.is_clicked(mouse_pos)
        display_size = planet.radius * 2

        if planet.image_file:
            sprite = self._get_scaled(planet.image_file, display_size)
            rect = sprite.get_rect(center=(px, py))

            if hovered:
                # Cyan glow ring slightly outside the sprite bounding box.
                pygame.draw.circle(surface, ACCENT_CYAN, (px, py),
                                   planet.radius + 9, 2)
            surface.blit(sprite, rect)
        else:
            # Fallback: coloured circle for planets without an image.
            if hovered:
                pygame.draw.circle(surface, ACCENT_CYAN, (px, py),
                                   planet.radius + 8, 2)
            pygame.draw.circle(surface, planet.color, (px, py), planet.radius)
            pygame.draw.circle(surface, WHITE, (px, py), planet.radius, 1)

        label_color = ACCENT_GOLD if hovered else DIM_WHITE
        label = name_font.render(planet.name, True, label_color)
        surface.blit(label, (px - label.get_width() // 2,
                             py + planet.radius + 6))

        badge = badge_font.render(f"×{len(planet.species_list)}", True, ACCENT_CYAN)
        surface.blit(badge, (px + planet.radius - 4,
                             py - planet.radius - 4))

    def draw_in_detail(
        self,
        surface: pygame.Surface,
        planet,
        center: tuple,
        display_radius: int,
    ):
        """
        Draw a large planet image centred in the planet detail view.

        Args:
            surface        : The detail-view pygame surface.
            planet         : Planet instance.
            center         : (cx, cy) centre pixel for the planet image.
            display_radius : Half the desired display diameter in pixels.
        """
        WHITE = (255, 255, 255)
        display_size = display_radius * 2
        cx, cy = center

        if planet.image_file:
            sprite = self._get_scaled(planet.image_file, display_size)
            rect = sprite.get_rect(center=(cx, cy))
            surface.blit(sprite, rect)
        else:
            pygame.draw.circle(surface, planet.color, (cx, cy), display_radius)
            pygame.draw.circle(surface, WHITE, (cx, cy), display_radius, 2)
