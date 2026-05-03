"""
CombatManager.py — UFO Incursion event system and Space Invaders mini-game.

Random incursions interrupt the Simulation state and demand a player
decision: delegate damage calculation to the building pipeline (auto) or
personally repel the fleet via the mini-game.

Damage pipeline
---------------
  _BASE_DAMAGE  ──►  BuildingManager.apply_disaster  ──►  species population

Mini-game outcome
-----------------
  surviving_ufos / total_ufos  →  damage fraction fed through the pipeline.
  Zero survivors  →  zero damage regardless of buildings.
"""

import random
import pygame

from ui.UI_Elements import (
    SCREEN_W, SCREEN_H, DEEP_SPACE, ACCENT_CYAN, ACCENT_GOLD,
    DIM_WHITE, WHITE, BTN_DARK, BTN_HOVER, draw_stars,
)

_BASE_DAMAGE      = 40      # raw population damage per incursion event
_INCURSION_CHANCE = 0.008   # probability per second per unlocked planet
_COOLDOWN_S       = 90.0    # seconds before the same planet may be attacked again


class CombatManager:
    """
    Manages per-planet UFO incursion timers and provides two resolution paths:
    auto-resolve (instant, building-weighted) and an interactive mini-game.

    Attributes:
        _cooldowns : planet_name → remaining cooldown before next incursion.
        _pending   : planet_name → True while an unresolved incursion waits.
    """

    def __init__(self):
        self._cooldowns: dict[str, float] = {}
        self._pending:   dict[str, bool]  = {}

    def reset(self):
        """Clear all state for a fresh game session."""
        self._cooldowns.clear()
        self._pending.clear()

    # ------------------------------------------------------------------
    # Per-frame tick
    # ------------------------------------------------------------------

    def tick(self, dt: float, planets: list) -> list[str]:
        """
        Advance cooldown timers and roll for new incursions.

        Locked planets are never targeted.  A planet with an unresolved
        incursion is skipped until the player resolves it.

        Returns:
            Names of planets with a newly triggered incursion this frame.
        """
        triggered = []
        for planet in planets:
            if getattr(planet, "is_locked", False):
                continue
            name = planet.name
            if self._pending.get(name):
                continue
            cd = self._cooldowns.get(name, 0.0)
            if cd > 0:
                self._cooldowns[name] = max(0.0, cd - dt)
                continue
            if random.random() < _INCURSION_CHANCE * dt:
                self._pending[name] = True
                triggered.append(name)
        return triggered

    def has_pending(self, planet_name: str) -> bool:
        """Return True if an unresolved incursion exists on this planet."""
        return self._pending.get(planet_name, False)

    # ------------------------------------------------------------------
    # Choice modal
    # ------------------------------------------------------------------

    def show_choice(self, screen: pygame.Surface, clock: pygame.time.Clock,
                    font_title, font_ui, font_small,
                    snapshot: pygame.Surface, planet_name: str) -> str:
        """
        Blocking modal that presents the player with an incursion response.

        Args:
            snapshot    : Screen capture taken just before opening the modal;
                          displayed frozen behind the overlay.
            planet_name : Displayed in the alert header.

        Returns:
            'AUTO'   — delegate to building-based auto-resolve.
            'DEFEND' — launch the Space Invaders mini-game.
        """
        cx = SCREEN_W // 2
        cy = SCREEN_H // 2
        aw = 180
        ah = 52
        auto_r   = pygame.Rect(cx - aw - 10, cy + 40, aw, ah)
        defend_r = pygame.Rect(cx + 10,       cy + 40, aw, ah)

        while True:
            clock.tick(60)
            mx, my = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a:
                        return "AUTO"
                    if event.key == pygame.K_d:
                        return "DEFEND"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if auto_r.collidepoint(mx, my):
                        return "AUTO"
                    if defend_r.collidepoint(mx, my):
                        return "DEFEND"

            # Frozen background + translucent dim
            screen.blit(snapshot, (0, 0))
            ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 155))
            screen.blit(ov, (0, 0))

            # Alert panel
            pw, ph = 460, 190
            panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
            panel.fill((14, 4, 4, 230))
            screen.blit(panel, (cx - pw // 2, cy - ph // 2))
            pygame.draw.rect(screen, (220, 40, 40),
                             (cx - pw // 2, cy - ph // 2, pw, ph), 2, border_radius=8)

            al = font_title.render("UFO  INCURSION!", True, (220, 40, 40))
            screen.blit(al, al.get_rect(centerx=cx, top=cy - ph // 2 + 12))
            pl = font_small.render(f"Planet {planet_name} is under attack.",
                                   True, DIM_WHITE)
            screen.blit(pl, pl.get_rect(centerx=cx, top=cy - 4))

            for rect, label, hint in [
                (auto_r,   "Auto-Resolve", "[A]"),
                (defend_r, "Defend",       "[D]"),
            ]:
                hov = rect.collidepoint(mx, my)
                pygame.draw.rect(screen, BTN_HOVER if hov else BTN_DARK,
                                 rect, border_radius=6)
                pygame.draw.rect(screen, ACCENT_CYAN, rect, 1, border_radius=6)
                t = font_ui.render(f"{hint}  {label}", True,
                                   ACCENT_GOLD if hov else WHITE)
                screen.blit(t, t.get_rect(center=rect.center))

            pygame.display.flip()

    # ------------------------------------------------------------------
    # Auto-resolve
    # ------------------------------------------------------------------

    def resolve_auto(self, planet_name: str,
                     building_manager, planets: list) -> int:
        """
        Instantly resolve an incursion using the building damage pipeline.

        AirDefense halves the damage; MilitaryBase floors population
        afterward.  Damage is split evenly across all species on the planet.

        Returns:
            Final per-species damage applied.
        """
        final = building_manager.apply_disaster(planet_name, _BASE_DAMAGE)
        self._apply_damage(planet_name, final, planets)
        self._clear(planet_name)
        return final

    # ------------------------------------------------------------------
    # Space Invaders mini-game
    # ------------------------------------------------------------------

    def run_minigame(self, screen: pygame.Surface, clock: pygame.time.Clock,
                     font_ui, font_small, stars,
                     planet_name: str, building_manager, planets: list) -> int:
        """
        Self-contained Space Invaders mini-game for manual planet defence.

        Controls: ARROW KEYS to move, SPACE to fire.

        The fraction of surviving UFOs at game-end determines the raw damage,
        which is then passed through the building pipeline exactly as
        auto-resolve would.

        Returns:
            Final damage applied to the planet after building reduction.
        """
        COLS, ROWS    = 5, 3
        UFO_W, UFO_H  = 38, 18
        H_GAP, V_GAP  = 70, 50
        START_X = (SCREEN_W - (COLS - 1) * H_GAP) // 2
        START_Y = 130

        SHIP_W, SHIP_H = 44, 22
        SHIP_Y         = SCREEN_H - 80
        SHIP_SPEED     = 320.0
        P_BUL_SPD      = 500.0
        E_BUL_SPD      = 210.0
        FIRE_INT       = 1.8        # avg seconds between enemy shots
        GRID_SPD_INIT  = 80.0
        DROP_DIST      = 20
        TIMEOUT        = 50.0
        MAX_LIVES      = 3

        # UFO grid
        ufos = [
            {"x": float(START_X + c * H_GAP),
             "y": float(START_Y + r * V_GAP),
             "alive": True}
            for r in range(ROWS) for c in range(COLS)
        ]
        total_ufos = len(ufos)

        ship_x    = float(SCREEN_W // 2)
        lives     = MAX_LIVES
        pbullet   = {"x": 0.0, "y": 0.0, "active": False}
        ebullets: list[dict] = []
        grid_dx   = GRID_SPD_INIT
        fire_t    = FIRE_INT
        time_left = TIMEOUT
        held      = {pygame.K_LEFT: False, pygame.K_RIGHT: False}

        while True:
            dt        = clock.tick(60) / 1000.0
            time_left -= dt
            alive     = [u for u in ufos if u["alive"]]

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN:
                    if event.key in held:
                        held[event.key] = True
                    if event.key == pygame.K_SPACE and not pbullet["active"]:
                        pbullet.update(x=ship_x,
                                       y=float(SHIP_Y - SHIP_H // 2),
                                       active=True)
                if event.type == pygame.KEYUP:
                    if event.key in held:
                        held[event.key] = False

            # Ship movement (clamped to screen edges)
            if held[pygame.K_LEFT]:
                ship_x = max(SHIP_W / 2.0, ship_x - SHIP_SPEED * dt)
            if held[pygame.K_RIGHT]:
                ship_x = min(SCREEN_W - SHIP_W / 2.0, ship_x + SHIP_SPEED * dt)

            # Player bullet physics and UFO hit detection
            if pbullet["active"]:
                pbullet["y"] -= P_BUL_SPD * dt
                if pbullet["y"] < 0:
                    pbullet["active"] = False
                else:
                    for u in alive:
                        if (abs(pbullet["x"] - u["x"]) < UFO_W / 2
                                and abs(pbullet["y"] - u["y"]) < UFO_H / 2):
                            u["alive"] = False
                            pbullet["active"] = False
                            alive = [u for u in ufos if u["alive"]]
                            break

            # UFO grid movement with wall-bounce and accelerating drop
            if alive:
                xs = [u["x"] for u in alive]
                if max(xs) + UFO_W / 2 >= SCREEN_W - 4 and grid_dx > 0:
                    grid_dx = -abs(grid_dx) * 1.06
                    for u in alive:
                        u["y"] += DROP_DIST
                elif min(xs) - UFO_W / 2 <= 4 and grid_dx < 0:
                    grid_dx = abs(grid_dx) * 1.06
                    for u in alive:
                        u["y"] += DROP_DIST
                for u in alive:
                    u["x"] += grid_dx * dt

            # Random UFO fire
            fire_t -= dt
            if fire_t <= 0 and alive:
                sh = random.choice(alive)
                ebullets.append({"x": sh["x"], "y": sh["y"] + UFO_H / 2})
                fire_t = FIRE_INT * random.uniform(0.7, 1.3)

            # Enemy bullet movement and player hit detection
            next_eb = []
            for eb in ebullets:
                eb["y"] += E_BUL_SPD * dt
                if eb["y"] > SCREEN_H:
                    continue
                if (abs(eb["x"] - ship_x) < SHIP_W / 2
                        and abs(eb["y"] - SHIP_Y) < SHIP_H / 2):
                    lives -= 1
                    continue
                next_eb.append(eb)
            ebullets = next_eb

            # Instant loss if UFOs reach the player line
            if alive and max(u["y"] for u in alive) >= SHIP_Y - SHIP_H:
                lives = 0

            victory   = not alive
            game_over = victory or lives <= 0 or time_left <= 0

            # ---- Draw ----
            screen.fill(DEEP_SPACE)
            draw_stars(screen, stars, 0)

            for u in ufos:
                if u["alive"]:
                    rect = (int(u["x"] - UFO_W / 2), int(u["y"] - UFO_H / 2),
                            UFO_W, UFO_H)
                    pygame.draw.ellipse(screen, ACCENT_CYAN, rect)
                    pygame.draw.ellipse(screen, (0, 150, 200), rect, 2)

            # Player ship drawn as a gold triangle
            sx = int(ship_x)
            pygame.draw.polygon(screen, ACCENT_GOLD, [
                (sx,                  SHIP_Y - SHIP_H // 2),
                (sx - SHIP_W // 2,    SHIP_Y + SHIP_H // 2),
                (sx + SHIP_W // 2,    SHIP_Y + SHIP_H // 2),
            ])

            if pbullet["active"]:
                pygame.draw.rect(screen, (255, 255, 80),
                                 (int(pbullet["x"]) - 2,
                                  int(pbullet["y"]) - 6, 4, 12))
            for eb in ebullets:
                pygame.draw.rect(screen, (255, 60, 60),
                                 (int(eb["x"]) - 2, int(eb["y"]), 4, 10))

            life_str = "[ ]" * lives + "   " * (MAX_LIVES - lives)
            screen.blit(font_ui.render(
                f"DEFENDING  {planet_name.upper()}    "
                f"LIVES: {life_str}    "
                f"TIME: {max(0, time_left):.0f}s    "
                f"UFOs: {len(alive)}/{total_ufos}",
                True, ACCENT_GOLD), (16, 10))
            screen.blit(font_small.render(
                "ARROW KEYS: move   |   SPACE: fire",
                True, (60, 60, 90)), (16, 42))
            pygame.draw.line(screen, ACCENT_CYAN, (0, 60), (SCREEN_W, 60), 1)

            pygame.display.flip()

            if game_over:
                result  = ("VICTORY! — UFOs repelled."
                           if victory else "OVERWHELMED! — Evacuating.")
                r_color = (0, 220, 100) if victory else (220, 60, 60)
                msg = font_ui.render(result, True, r_color)
                screen.blit(msg, msg.get_rect(
                    centerx=SCREEN_W // 2, centery=SCREEN_H // 2))
                pygame.display.flip()
                pygame.time.wait(1800)
                break

        # Damage calculation: survivor fraction through building pipeline
        remaining = sum(1 for u in ufos if u["alive"])
        raw_dmg   = int(_BASE_DAMAGE * remaining / total_ufos)
        final     = building_manager.apply_disaster(planet_name, raw_dmg)
        self._apply_damage(planet_name, final, planets)
        self._clear(planet_name)
        return final

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _apply_damage(self, planet_name: str, damage: int, planets: list):
        """Split damage evenly across all species on the named planet."""
        for planet in planets:
            if planet.name == planet_name:
                n = max(len(planet.species_list), 1)
                for sp in planet.species_list:
                    sp.population = max(0, sp.population - damage // n)
                return

    def _clear(self, planet_name: str):
        """Mark incursion resolved and start the post-attack cooldown."""
        self._pending[planet_name]   = False
        self._cooldowns[planet_name] = _COOLDOWN_S
