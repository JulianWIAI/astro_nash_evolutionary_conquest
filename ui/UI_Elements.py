"""
UI_Elements.py — Visual constants, Button widget, star-field helpers,
and every state-level draw routine including the How to Play overlay.

Draw functions are pure renderers: they receive all data they need as
arguments and never modify game state, making them easy to test and reuse.
"""
import math
import random

import pygame


# ---------------------------------------------------------------------------
# Layout & timing constants
# ---------------------------------------------------------------------------
SCREEN_W   = 1280
SCREEN_H   = 720
FPS        = 60
STAR_COUNT = 200

# Colour palette
WHITE        = (255, 255, 255)
DIM_WHITE    = (180, 180, 180)
DEEP_SPACE   = (  5,   5,  20)
ACCENT_CYAN  = (  0, 200, 255)
ACCENT_GOLD  = (255, 200,  50)
BTN_DARK     = ( 30,  30,  60)
BTN_HOVER    = ( 60,  60, 120)


# ---------------------------------------------------------------------------
# Floating text reward manager
# ---------------------------------------------------------------------------
class FloatingTextManager:
    """
    Lightweight manager for brief "+N EP!" reward texts that drift upward
    and fade from gold toward black over their lifetime.

    Usage:
        float_texts = FloatingTextManager()
        float_texts.add("+50 EP!", x, y)
        # each frame:
        float_texts.draw_and_update(screen, font_small, dt)
    """

    _DURATION = 2.0    # seconds each text lives
    _DRIFT    = 45     # pixels per second, upward

    def __init__(self):
        self._entries: list = []

    def add(self, text: str, x: int, y: int):
        """Spawn a new floating text at pixel position (x, y)."""
        self._entries.append({
            "text":  text,
            "x":     x,
            "y":     float(y),
            "timer": self._DURATION,
        })

    def draw_and_update(self, surface: pygame.Surface,
                        font: pygame.font.Font, dt: float):
        """Advance all active texts and render them; expired entries are removed."""
        kept = []
        for e in self._entries:
            e["timer"] -= dt
            if e["timer"] <= 0:
                continue
            e["y"] -= self._DRIFT * dt
            # Fade gold → black by scaling RGB with remaining lifetime fraction
            fade  = e["timer"] / self._DURATION     # 1.0 → 0.0
            r, g, b = ACCENT_GOLD
            color = (int(r * fade), int(g * fade), int(b * fade))
            surf  = font.render(e["text"], True, color)
            surface.blit(surf, (e["x"], int(e["y"])))
            kept.append(e)
        self._entries = kept

    def reset(self):
        """Clear all active texts (call on New Game)."""
        self._entries.clear()


# ---------------------------------------------------------------------------
# Button widget
# ---------------------------------------------------------------------------
class Button:
    """Rectangular button with hover highlight and single-click detection."""

    def __init__(self, x: int, y: int, w: int, h: int,
                 label: str, font: pygame.font.Font):
        self.rect  = pygame.Rect(x, y, w, h)
        self.label = label
        self.font  = font

    def draw(self, surface: pygame.Surface, mouse_pos: tuple):
        hovered = self.rect.collidepoint(mouse_pos)
        pygame.draw.rect(surface, BTN_HOVER if hovered else BTN_DARK,
                         self.rect, border_radius=8)
        pygame.draw.rect(surface, ACCENT_CYAN, self.rect, width=2, border_radius=8)
        text_surf = self.font.render(self.label, True,
                                     ACCENT_GOLD if hovered else WHITE)
        surface.blit(text_surf, text_surf.get_rect(center=self.rect.center))

    def is_clicked(self, event: pygame.event.Event) -> bool:
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


# ---------------------------------------------------------------------------
# Button factory functions
# ---------------------------------------------------------------------------
def create_menu_buttons(font_ui: pygame.font.Font) -> list:
    """
    Return the six main-menu buttons.

    Index map (used in main.py):
      0 NEW GAME   1 HOW TO PLAY   2 PROFILE
      3 LEADERBOARD               4 CREDITS     5 QUIT
    """
    cx, w, h, gap = SCREEN_W // 2, 280, 44, 8
    ys = [252 + i * (h + gap) for i in range(6)]
    return [
        Button(cx - w // 2, ys[0], w, h, "NEW GAME",     font_ui),
        Button(cx - w // 2, ys[1], w, h, "HOW TO PLAY",  font_ui),
        Button(cx - w // 2, ys[2], w, h, "PROFILE",      font_ui),
        Button(cx - w // 2, ys[3], w, h, "LEADERBOARD",  font_ui),
        Button(cx - w // 2, ys[4], w, h, "CREDITS",      font_ui),
        Button(cx - w // 2, ys[5], w, h, "QUIT",         font_ui),
    ]


def create_detail_buttons(font_ui: pygame.font.Font,
                          font_small: pygame.font.Font) -> dict:
    """
    Return the planet-detail side-panel action buttons keyed by name.

    'booster' and building labels are updated dynamically each frame by
    main.py so they reflect live inventory / build state.
    """
    return {
        "disaster":  Button( 910, 490, 170, 44, "DISASTER",      font_ui),
        "resources": Button(1090, 490, 170, 44, "RESOURCES",     font_ui),
        "evo_speed": Button( 910, 544, 110, 36, "+Speed",        font_small),
        "evo_agg":   Button(1030, 544, 130, 36, "+Aggression",   font_small),
        "evo_meta":  Button(1170, 544, 110, 36, "+Metabolism",   font_small),
        "coop_up":   Button( 910, 590, 150, 36, "+CoopWeight",   font_small),
        # Evolution Booster — label shows current inventory count
        "booster":   Button(1072, 590, 196, 36, "EvoBoost [0]",  font_small),
        # Buildings — labels updated dynamically from main.py each frame
        "church":    Button( 910, 654, 112, 26, "Church [2]",    font_small),
        "military":  Button(1026, 654, 112, 26, "MilBase [3]",   font_small),
        "airdef":    Button(1142, 654, 118, 26, "AirDef [4]",    font_small),
    }


# ---------------------------------------------------------------------------
# Star-field helpers
# ---------------------------------------------------------------------------
def make_stars(count: int, w: int, h: int) -> list:
    """Generate random star descriptors for the parallax background."""
    return [
        {
            "x":     random.randint(0, w),
            "y":     random.randint(0, h),
            "r":     random.choice([1, 1, 1, 2, 2, 3]),
            "base":  random.randint(120, 220),
            "phase": random.uniform(0, math.tau),
        }
        for _ in range(count)
    ]


def draw_stars(surface: pygame.Surface, stars, tick: float):
    """
    Render the star-field background.

    Accepts either the original star-dict list (twinkling static field) or a
    ParallaxStarfield instance (scrolling parallax).  The duck-type check on
    .draw keeps every existing draw function and blocking sub-screen compatible
    with both representations without any call-site changes.
    """
    if hasattr(stars, "draw"):          # ParallaxStarfield (or any drawable)
        stars.draw(surface)
        return
    for star in stars:
        brightness = int(star["base"] + 35 * math.sin(tick * 1.5 + star["phase"]))
        c = max(80, min(255, brightness))
        pygame.draw.circle(surface, (c, c, c), (star["x"], star["y"]), star["r"])


# ---------------------------------------------------------------------------
# View: Main Menu
# ---------------------------------------------------------------------------
def draw_menu(surface: pygame.Surface, stars: list, tick: float,
              buttons: list, title_font: pygame.font.Font,
              sub_font: pygame.font.Font, mouse_pos: tuple,
              difficulty_label: str = "MEDIUM"):
    """Render the animated main-menu screen."""
    surface.fill(DEEP_SPACE)
    draw_stars(surface, stars, tick)

    title_surf = title_font.render("ASTRO-NASH", True, ACCENT_CYAN)
    title_rect = title_surf.get_rect(center=(SCREEN_W // 2, 175))
    surface.blit(title_surf, title_rect)

    line_y = title_rect.bottom + 8
    pygame.draw.line(surface, ACCENT_CYAN,
                     (title_rect.left, line_y), (title_rect.right, line_y), 2)

    sub_surf = sub_font.render("Evolutionary Conquest", True, ACCENT_GOLD)
    surface.blit(sub_surf, sub_surf.get_rect(center=(SCREEN_W // 2, line_y + 28)))

    for btn in buttons:
        btn.draw(surface, mouse_pos)

    # Difficulty selector (sits below the 6-button stack)
    diff_surf = sub_font.render(f"Difficulty:   [ {difficulty_label} ]",
                                True, ACCENT_GOLD)
    surface.blit(diff_surf, diff_surf.get_rect(center=(SCREEN_W // 2, 580)))
    hint_surf = sub_font.render("[ LEFT / RIGHT arrow  to change ]",
                                True, (80, 80, 120))
    surface.blit(hint_surf, hint_surf.get_rect(center=(SCREEN_W // 2, 604)))

    ver = sub_font.render("v0.2  —  School Project Build", True, (80, 80, 120))
    surface.blit(ver, (10, SCREEN_H - 28))


# ---------------------------------------------------------------------------
# Galactic-map helpers (locked planets + stability bars)
# ---------------------------------------------------------------------------
def _draw_locked_overlay(surface: pygame.Surface, planet, small_font):
    """Draw a grey translucent overlay + LOCKED label over a locked planet."""
    px, py = planet.position
    r      = planet.radius

    overlay = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(overlay, (20, 20, 40, 200), (r + 2, r + 2), r)
    surface.blit(overlay, (px - r - 2, py - r - 2))
    pygame.draw.circle(surface, (70, 70, 90), (px, py), r, 2)

    lock_surf = small_font.render("LOCKED", True, (110, 110, 130))
    surface.blit(lock_surf, (px - lock_surf.get_width() // 2, py - 8))


def _draw_stability_bar(surface: pygame.Surface, planet, progress: float):
    """Draw a small green stability bar below an unlocked planet."""
    px, py  = planet.position
    bar_w   = 80
    bar_h   = 6
    bx      = px - bar_w // 2
    by      = py + planet.radius + 6

    pygame.draw.rect(surface, (30, 40, 70), (bx, by, bar_w, bar_h), border_radius=3)
    fill_w = int(bar_w * progress)
    if fill_w > 0:
        pygame.draw.rect(surface, (0, 200, 100),
                         (bx, by, fill_w, bar_h), border_radius=3)


# ---------------------------------------------------------------------------
# View: Galactic Map
# ---------------------------------------------------------------------------
def draw_galactic_map(surface: pygame.Surface, stars: list, tick: float,
                      planets: list, mouse_pos: tuple, planet_renderer,
                      title_font: pygame.font.Font, ui_font: pygame.font.Font,
                      small_font: pygame.font.Font,
                      conquered_planets: list | None = None,
                      galaxy_manager=None):
    """
    Render the galactic map with planet sprites, hover labels, conquest markers,
    locked-planet overlays, and cooperative-stability bars.
    """
    surface.fill(DEEP_SPACE)
    draw_stars(surface, stars, tick)

    header = title_font.render("GALACTIC MAP", True, ACCENT_CYAN)
    surface.blit(header, (20, 14))
    pygame.draw.line(surface, ACCENT_CYAN, (20, 60), (500, 60), 1)

    # Conquest progress counter (top-right)
    if conquered_planets is not None:
        n_conquered, n_total = len(conquered_planets), len(planets)
        prog_surf = ui_font.render(
            f"Conquered: {n_conquered} / {n_total}", True, ACCENT_GOLD
        )
        surface.blit(prog_surf, (SCREEN_W - prog_surf.get_width() - 20, 14))

    hint = ui_font.render(
        "Click a planet to inspect it   |   ESC → Main Menu", True, DIM_WHITE
    )
    surface.blit(hint, (20, SCREEN_H - 28))

    for planet in planets:
        if getattr(planet, "is_locked", False):
            # Draw a dim placeholder circle so locked planets are still visible
            px, py = planet.position
            pygame.draw.circle(surface, (35, 35, 55), (px, py), planet.radius)
            _draw_locked_overlay(surface, planet, small_font)
        else:
            planet_renderer.draw_on_map(surface, planet, mouse_pos,
                                        ui_font, small_font)
            # Stability bar for unlock progress
            if galaxy_manager:
                progress = galaxy_manager.stability_progress(planet.name)
                _draw_stability_bar(surface, planet, progress)

    # Gold star markers over conquered planets
    if conquered_planets:
        for planet in planets:
            if planet.name in conquered_planets:
                px, py = planet.position
                star_surf = ui_font.render("★", True, ACCENT_GOLD)
                surface.blit(star_surf, (
                    px - star_surf.get_width() // 2,
                    py - planet.radius - star_surf.get_height() - 4,
                ))


# ---------------------------------------------------------------------------
# View: Planet Detail
# ---------------------------------------------------------------------------
def draw_planet_detail(surface: pygame.Surface, stars, tick: float,
                       planet, controller, game_theory,
                       sprite_renderer, planet_renderer,
                       title_font: pygame.font.Font, ui_font: pygame.font.Font,
                       small_font: pygame.font.Font,
                       mouse_pos: tuple, last_interaction,
                       is_conquered: bool = False,
                       booster_count: int = 0):
    """
    Render the planet detail view.

    Layout: left 900 px — planet + orbiting species sprites.
            right 380 px — side panel with stats, Nash log, action area.
    """
    surface.fill(DEEP_SPACE)
    draw_stars(surface, stars, tick)

    # --- Planet visualisation (left 900 px) ---
    cx, cy = 450, 360
    base_r  = 140
    planet_renderer.draw_in_detail(surface, planet, (cx, cy), base_r)

    orbit_angles = [tick * 0.5, tick * 0.5 + math.pi]
    for i, sp in enumerate(planet.species_list):
        angle   = orbit_angles[i]
        orbit_r = base_r + 70 + i * 35
        sx = int(cx + orbit_r * math.cos(angle))
        sy = int(cy + orbit_r * math.sin(angle))
        blit_rect = sprite_renderer.render(surface, sp, (sx, sy), tick,
                                           orbit_angle=angle)
        name_surf = small_font.render(sp.name, True, sp.color)
        surface.blit(name_surf,
                     (blit_rect.centerx - name_surf.get_width() // 2,
                      blit_rect.bottom + 3))

    # Planet name header
    title_surf = title_font.render(planet.name, True, ACCENT_GOLD)
    surface.blit(title_surf, (20, 14))
    if is_conquered:
        badge = ui_font.render("★ EQUILIBRIUM", True, ACCENT_GOLD)
        surface.blit(badge, (880 - badge.get_width(), 20))
    pygame.draw.line(surface, ACCENT_GOLD, (20, 60), (880, 60), 1)

    # Resource bar
    bar_x, bar_y, bar_w, bar_h = 20, 68, 860, 14
    fill_w = int(bar_w * (planet.resources / planet.max_resources))
    pygame.draw.rect(surface, (40, 40, 80),
                     (bar_x, bar_y, bar_w, bar_h), border_radius=4)
    pygame.draw.rect(surface, ACCENT_CYAN,
                     (bar_x, bar_y, fill_w, bar_h), border_radius=4)
    surface.blit(
        small_font.render(
            f"Resources: {int(planet.resources)} / {planet.max_resources}",
            True, WHITE,
        ),
        (bar_x + 4, bar_y),
    )

    # --- Side panel (right 380 px) ---
    panel_surf = pygame.Surface((380, SCREEN_H), pygame.SRCALPHA)
    panel_surf.fill((10, 10, 35, 220))
    surface.blit(panel_surf, (900, 0))
    pygame.draw.line(surface, ACCENT_CYAN, (900, 0), (900, SCREEN_H), 2)

    py = 20

    surface.blit(ui_font.render("SPECIES ON PLANET", True, ACCENT_CYAN), (910, py))
    py += 34

    for sp in planet.species_list:
        sp.calculate_fitness()
        surface.blit(ui_font.render(sp.name, True, sp.color), (910, py))
        py += 24
        for line in [
            f"  Pop:        {sp.population}",
            f"  Speed:      {sp.dna['speed']:.2f}",
            f"  Aggression: {sp.dna['aggression']:.2f}",
            f"  Metabolism: {sp.dna['metabolism']:.2f}",
            f"  Fitness:    {sp.fitness:.2f}",
        ]:
            surface.blit(small_font.render(line, True, DIM_WHITE), (910, py))
            py += 18
        py += 8

    # Nash log
    pygame.draw.line(surface, ACCENT_CYAN, (910, py), (1270, py), 1)
    py += 8
    surface.blit(ui_font.render("NASH LOG", True, ACCENT_CYAN), (910, py))
    py += 26

    if last_interaction and len(planet.species_list) == 2:
        act_a, act_b = last_interaction[:2]
        sp_a, sp_b   = planet.species_list[0], planet.species_list[1]
        is_ne        = game_theory.is_nash_equilibrium(act_a, act_b)

        surface.blit(
            small_font.render(f"{sp_a.name}: {act_a.upper()}", True, sp_a.color),
            (910, py),
        )
        py += 18
        surface.blit(
            small_font.render(f"{sp_b.name}: {act_b.upper()}", True, sp_b.color),
            (910, py),
        )
        py += 18
        ne_color = ACCENT_GOLD if is_ne else (255, 80, 80)
        surface.blit(
            small_font.render(
                "Nash Equilibrium: YES" if is_ne else "Nash Equilibrium: NO",
                True, ne_color,
            ),
            (910, py),
        )
        py += 18
        surface.blit(
            small_font.render(f"Coop Weight: {game_theory.coop_weight:.1f}",
                              True, DIM_WHITE),
            (910, py),
        )
        py += 26
    else:
        surface.blit(
            small_font.render("(waiting for interaction...)", True, DIM_WHITE),
            (910, py),
        )
        py += 26

    # Actions section header
    pygame.draw.line(surface, ACCENT_CYAN, (910, py), (1270, py), 1)
    py += 10
    surface.blit(ui_font.render("ACTIONS", True, ACCENT_CYAN), (910, py))

    # Buildings section header (fixed position, buttons drawn separately)
    pygame.draw.line(surface, ACCENT_CYAN, (910, 636), (1270, 636), 1)
    surface.blit(small_font.render("BUILDINGS  (Church/MilBase/AirDef)",
                                   True, ACCENT_CYAN), (910, 639))

    # Footer
    surface.blit(
        ui_font.render(f"Evolution Points: {controller.evolution_points}",
                       True, ACCENT_GOLD),
        (910, SCREEN_H - 36),
    )
    surface.blit(
        small_font.render(
            f"ESC → Map  |  D → Disaster  |  Boosters: {booster_count}",
            True, (80, 80, 120)),
        (910, SCREEN_H - 18),
    )


# ---------------------------------------------------------------------------
# View: How to Play  (new state)
# ---------------------------------------------------------------------------
def draw_how_to_play(surface: pygame.Surface, stars: list, tick: float,
                     title_font: pygame.font.Font, ui_font: pygame.font.Font,
                     small_font: pygame.font.Font):
    """
    Render the professional How to Play instructional overlay.

    Layout: centred panel (920 × 600 px) on the star-field background.
    Sections: Objective · Mechanics · The Conflict · Controls.
    """
    surface.fill(DEEP_SPACE)
    draw_stars(surface, stars, tick)

    PANEL_W, PANEL_H = 920, 600
    panel_x = (SCREEN_W - PANEL_W) // 2   # 180
    panel_y = (SCREEN_H - PANEL_H) // 2   #  60

    # Semitransparent panel + border
    overlay = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
    overlay.fill((5, 5, 25, 215))
    surface.blit(overlay, (panel_x, panel_y))
    pygame.draw.rect(surface, ACCENT_CYAN,
                     (panel_x, panel_y, PANEL_W, PANEL_H),
                     width=2, border_radius=10)

    # Pulsing title
    glow     = int(200 + 55 * math.sin(tick * 1.5))
    t_surf   = title_font.render("HOW  TO  PLAY", True, (0, glow, 255))
    surface.blit(t_surf, t_surf.get_rect(
        centerx=panel_x + PANEL_W // 2, top=panel_y + 18
    ))

    # Separator below title
    sep_y = panel_y + 104
    pygame.draw.line(surface, ACCENT_CYAN,
                     (panel_x + 30, sep_y), (panel_x + PANEL_W - 30, sep_y), 1)

    # ---- Section content ----
    SECTIONS = [
        (
            "OBJECTIVE",
            [
                "Manage the evolution of 3 species  (Predator · Gatherer · Technician)",
                "to guide all planets toward a stable Galactic Nash Equilibrium.",
            ],
        ),
        (
            "MECHANICS",
            [
                "Click any planet on the Galactic Map to enter its local simulation.",
                "Spend Evolution Points to buff a species' Speed, Aggression, or Metabolism.",
            ],
        ),
        (
            "THE CONFLICT",
            [
                "Watch the Nash Log on the right panel.",
                "Cooperation yields shared resources; Competition risks population loss.",
                "Nash Equilibrium: neither species gains by changing strategy alone.",
            ],
        ),
        (
            "CONTROLS",
            [
                "[ ESC ]   Return to the Galactic Map  (or back to this screen)",
                "[ M ]     Toggle music mute",
                "[ D ]     Trigger a test Disaster on the selected planet",
            ],
        ),
    ]

    TEXT_X = panel_x + 48
    cy     = panel_y + 120

    for header, lines in SECTIONS:
        # Section header with arrow marker
        surface.blit(
            ui_font.render(f"  ▸  {header}", True, ACCENT_GOLD),
            (TEXT_X, cy),
        )
        cy += 30

        for line in lines:
            surface.blit(
                small_font.render(f"        {line}", True, (210, 225, 245)),
                (TEXT_X, cy),
            )
            cy += 21

        cy += 14   # gap between sections

    # Bottom separator + ESC back hint
    bot_sep = panel_y + PANEL_H - 54
    pygame.draw.line(surface, ACCENT_CYAN,
                     (panel_x + 30, bot_sep), (panel_x + PANEL_W - 30, bot_sep), 1)
    back_surf = ui_font.render("[ ESC  —  BACK TO MENU ]", True, ACCENT_CYAN)
    surface.blit(back_surf, back_surf.get_rect(
        centerx=panel_x + PANEL_W // 2, top=bot_sep + 12
    ))


def run_how_to_play(surface: pygame.Surface, clock: pygame.time.Clock,
                    title_font: pygame.font.Font, ui_font: pygame.font.Font,
                    small_font: pygame.font.Font, stars):
    """
    Blocking how-to-play screen for use inside the Pause Menu flow.

    Identical content to the state-machine HOW_TO_PLAY state, but runs its
    own inner event loop so it can be called from any blocking context
    (e.g. PauseMenu) without a GameStateManager transition.
    """
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
        draw_how_to_play(surface, stars, tick, title_font, ui_font, small_font)
        pygame.display.flip()


# ---------------------------------------------------------------------------
# View: Victory screen
# ---------------------------------------------------------------------------
def draw_win_screen(surface: pygame.Surface, stars: list, tick: float,
                    title_font: pygame.font.Font, ui_font: pygame.font.Font,
                    small_font: pygame.font.Font,
                    conquered_planets: list, total_planets: int):
    """
    Render the victory screen shown when all planets are conquered.

    Uses a gold-tinted star field to distinguish the mood from the
    normal deep-space background.
    """
    surface.fill((10, 8, 2))
    for star in stars:
        b = max(80, min(255, int(star["base"] + 35 * math.sin(tick * 2.0 + star["phase"]))))
        pygame.draw.circle(surface, (b, int(b * 0.75), 0),
                           (star["x"], star["y"]), star["r"])

    cx   = SCREEN_W // 2
    glow = int(200 + 55 * math.sin(tick * 2.0))

    l1 = title_font.render("GALACTIC EQUILIBRIUM", True, (glow, int(glow * 0.75), 0))
    l2 = title_font.render("ACHIEVED", True, ACCENT_GOLD)
    surface.blit(l1, l1.get_rect(centerx=cx, top=70))
    surface.blit(l2, l2.get_rect(centerx=cx, top=150))

    pygame.draw.line(surface, ACCENT_GOLD, (cx - 320, 228), (cx + 320, 228), 2)

    surface.blit(
        ui_font.render("All species have reached stable mutual cooperation.",
                       True, (220, 200, 120)),
        ui_font.render("", True, WHITE).get_rect(
            centerx=cx, top=246),  # placeholder for centering
    )
    desc = ui_font.render(
        "All species have reached stable mutual cooperation.", True, (220, 200, 120)
    )
    surface.blit(desc, desc.get_rect(centerx=cx, top=246))

    prog = ui_font.render(
        f"CONQUERED:  {len(conquered_planets)} / {total_planets}  PLANETS",
        True, ACCENT_GOLD,
    )
    surface.blit(prog, prog.get_rect(centerx=cx, top=302))

    # Planet name grid (3 per row)
    COL_W, py = 270, 348
    for i, name in enumerate(conquered_planets):
        col = i % 3
        row = i // 3
        x = cx - COL_W * 1 + col * COL_W   # 3 columns centred
        ns = ui_font.render(f"★  {name}", True, ACCENT_GOLD)
        surface.blit(ns, ns.get_rect(centerx=x + COL_W // 2, top=py + row * 32))

    pygame.draw.line(surface, ACCENT_GOLD,
                     (cx - 320, SCREEN_H - 72), (cx + 320, SCREEN_H - 72), 1)
    esc = ui_font.render("[ ESC  —  RETURN TO MENU ]", True, ACCENT_GOLD)
    surface.blit(esc, esc.get_rect(centerx=cx, top=SCREEN_H - 56))


# ---------------------------------------------------------------------------
# View: Loss screen
# ---------------------------------------------------------------------------
def draw_loss_screen(surface: pygame.Surface, stars: list, tick: float,
                     title_font: pygame.font.Font, ui_font: pygame.font.Font,
                     small_font: pygame.font.Font):
    """Render the defeat screen shown when total species extinction is reached."""
    surface.fill((8, 2, 2))
    for star in stars:
        b = max(15, min(90, int(star["base"] * 0.35 + 15 * math.sin(tick * 0.7 + star["phase"]))))
        pygame.draw.circle(surface, (b, 0, 0), (star["x"], star["y"]), star["r"])

    RED      = (220, 40,  40)
    DIM_RED  = (160, 80,  80)
    cx       = SCREEN_W // 2
    pulse    = int(170 + 50 * math.sin(tick * 1.2))

    l1 = title_font.render("☠  EXTINCTION EVENT", True, (pulse, 20, 20))
    l2 = title_font.render("GALACTIC COLLAPSE", True, RED)
    surface.blit(l1, l1.get_rect(centerx=cx, top=70))
    surface.blit(l2, l2.get_rect(centerx=cx, top=150))

    pygame.draw.line(surface, RED, (cx - 320, 228), (cx + 320, 228), 2)

    for i, line in enumerate([
        "All species across the galaxy have perished.",
        "No Nash Equilibrium was ever achieved.",
        "",
        "The galaxy falls silent.",
    ]):
        s = ui_font.render(line, True, DIM_RED)
        surface.blit(s, s.get_rect(centerx=cx, top=250 + i * 38))

    pygame.draw.line(surface, RED,
                     (cx - 320, SCREEN_H - 72), (cx + 320, SCREEN_H - 72), 1)
    esc = ui_font.render("[ ESC  —  RETURN TO MENU ]", True, RED)
    surface.blit(esc, esc.get_rect(centerx=cx, top=SCREEN_H - 56))


# ---------------------------------------------------------------------------
# HUD overlay: time scale indicator
# ---------------------------------------------------------------------------
def draw_time_hud(surface: pygame.Surface, small_font: pygame.font.Font,
                  time_controller):
    """
    Render the time-scale badge in the top-right corner (below the mute badge).

    Colour coding: red = paused, gold = fast-forward, green = normal.
    The controller is passed as a duck-typed object so UI_Elements has no
    hard import dependency on logic.TimeController.
    """
    label = time_controller.label
    if time_controller.is_paused:
        color = (255, 80, 80)
    elif time_controller.time_scale == 2.0:
        color = ACCENT_GOLD
    else:
        color = (100, 200, 120)
    surf = small_font.render(f"[F/N] {label}", True, color)
    surface.blit(surf, (SCREEN_W - surf.get_width() - 10, 28))
