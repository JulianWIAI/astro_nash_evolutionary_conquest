"""
main.py — Entry point for Astro-Nash: Evolutionary Conquest.

State machine
-------------
  MENU        →  MAP           (NEW GAME)
  MENU        →  HOW_TO_PLAY  (HOW TO PLAY button)
  HOW_TO_PLAY →  MENU          (ESC)
  MAP         →  SIMULATION   (click an unlocked planet)
  MAP/SIM     →  MENU          (ESC)
  WIN_SCREEN  →  MENU          (blocking WinScreen.run(), then auto-transition)
  LOSS_SCREEN →  MENU / MAP   (blocking LossScreen.run(), returns 'MENU'/'RELOAD')

  MENU also launches self-contained blocking screens via run():
    PROFILE · LEADERBOARD · CREDITS · MUSIC GALLERY (from PROFILE)

Keyboard shortcuts
------------------
  M          Toggle music mute                      (all states)
  P          Pause menu overlay                     (MAP, SIMULATION)
  F / N      Fast ×2 / Normal speed                 (MAP, SIMULATION)
  S / L      Save / Load                            (MAP, SIMULATION)
  D          Trigger Disaster on selected planet    (SIMULATION)
  LEFT/RIGHT Cycle difficulty                       (MENU)

All gameplay logic lives in logic/, ui/, and audio/.
"""

import os
import sys
import pygame

from logic.Simulation        import SimulationManager
from logic.GameStateManager  import GameStateManager
from logic.TimeController    import TimeController
from logic.SaveManager       import SaveManager
from logic.GalaxyManager     import GalaxyManager
from logic.DifficultyManager import DifficultyManager
from logic.Building          import Church, MilitaryBase, AirDefense
from logic.ProfileManager    import ProfileManager
from logic.BadgeEngine       import BadgeEngine
from logic.Leaderboard       import Leaderboard
from logic.CombatManager     import CombatManager
from logic.PowerUpManager    import PowerUpManager
from ui.UI_Elements import (
    SCREEN_W, SCREEN_H, FPS, ACCENT_GOLD,
    draw_menu, draw_galactic_map, draw_planet_detail,
    draw_how_to_play, draw_time_hud, run_how_to_play,
    create_menu_buttons, create_detail_buttons,
    FloatingTextManager,
)
from ui.PlayerController import PlayerController
from ui.SpriteRenderer   import SpriteRenderer
from ui.PlanetRenderer   import PlanetRenderer
from ui.ProfileUI        import ProfileUI
from ui.MusicGallery     import MusicGallery
from ui.CreditsUI        import CreditsUI
from ui.PauseMenu        import PauseMenu
from ui.WinScreen        import WinScreen
from ui.LossScreen       import LossScreen
from ui.Visuals          import ParallaxStarfield
from audio.MusicManager  import MusicManager


def _new_game_objects(difficulty_manager=None):
    sim              = SimulationManager(difficulty_manager=difficulty_manager)
    controller       = PlayerController()
    stability_dur    = getattr(difficulty_manager, "stability_duration", 30.0)
    galaxy_manager   = GalaxyManager(sim.planets, stability_duration=stability_dur)
    return sim, controller, galaxy_manager


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "AstroNash.EvolutionaryConquest.1.0")
        except Exception:
            pass

    pygame.init()
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.png")
    if os.path.exists(icon_path):
        pygame.display.set_icon(pygame.image.load(icon_path))
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Astro-Nash: Evolutionary Conquest")
    clock  = pygame.time.Clock()

    _mono = "consolas, courier new, menlo, monaco"
    font_title = pygame.font.SysFont(_mono, 64, bold=True)
    font_ui    = pygame.font.SysFont(_mono, 22, bold=True)
    font_small = pygame.font.SysFont(_mono, 16)

    # Parallax starfield — duck-types with all existing draw_stars() call sites
    stars = ParallaxStarfield(SCREEN_W, SCREEN_H)

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # ---- Session-level managers (survive New Game) ----
    sprite_renderer    = SpriteRenderer(os.path.join(base_dir, "assets", "characters"))
    planet_renderer    = PlanetRenderer(os.path.join(base_dir, "assets", "planets"))
    music_manager      = MusicManager(os.path.join(base_dir, "assets", "music"))
    time_controller    = TimeController()
    save_manager       = SaveManager(os.path.join(base_dir, "savegame.json"))
    difficulty_manager = DifficultyManager()
    profile_manager    = ProfileManager(os.path.join(base_dir, "global_profiles.json"))
    badge_engine       = BadgeEngine()
    leaderboard        = Leaderboard(os.path.join(base_dir, "leaderboard.json"))
    profile_ui         = ProfileUI()
    music_gallery      = MusicGallery()
    credits_ui         = CreditsUI()
    combat_manager     = CombatManager()
    powerup_manager    = PowerUpManager()
    pause_menu         = PauseMenu()
    win_screen         = WinScreen()
    loss_screen        = LossScreen()
    float_texts        = FloatingTextManager()

    # ---- Per-game objects (re-created on New Game) ----
    sim, controller, galaxy_manager = _new_game_objects(difficulty_manager)
    gsm            = GameStateManager(total_planets=len(sim.planets))
    menu_buttons   = create_menu_buttons(font_ui)
    detail_buttons = create_detail_buttons(font_ui, font_small)

    session_time = 0.0
    tick         = 0.0
    running      = True

    while running:
        dt        = clock.tick(FPS) / 1000.0
        tick     += dt
        mouse_pos = pygame.mouse.get_pos()
        state     = gsm.current_state

        if state in ("MAP", "SIMULATION"):
            session_time += dt

        # ---- Events -------------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                k = event.key
                if k == pygame.K_m:
                    music_manager.toggle_mute()
                if state in ("MAP", "SIMULATION"):
                    if k == pygame.K_p:
                        # Pause overlay: captures the last frame as backdrop
                        action = pause_menu.run(
                            screen, clock, font_title, font_ui, screen.copy())
                        if action == "HOW_TO_PLAY":
                            run_how_to_play(screen, clock, font_title,
                                            font_ui, font_small, stars)
                        elif action == "PROFILE":
                            profile_ui.run(
                                screen, clock, font_title, font_ui, font_small,
                                stars, profile_manager,
                                os.path.join(base_dir, "assets", "badges"),
                                music_gallery,
                                os.path.join(base_dir, "assets", "music"))
                        elif action == "MENU":
                            gsm.transition("MENU")
                    elif k == pygame.K_f:
                        time_controller.toggle_fast()
                    elif k == pygame.K_n:
                        time_controller.set_normal()
                    elif k == pygame.K_s:
                        save_manager.save(gsm, controller, sim)
                    elif k == pygame.K_l:
                        save_manager.load(gsm, controller, sim)
                if state == "MENU":
                    if k == pygame.K_LEFT:
                        difficulty_manager.cycle_prev()
                    elif k == pygame.K_RIGHT:
                        difficulty_manager.cycle_next()

            # ---- State-specific input ----
            if state == "MENU":
                if menu_buttons[0].is_clicked(event):           # New Game
                    sim, controller, galaxy_manager = _new_game_objects(difficulty_manager)
                    gsm = GameStateManager(total_planets=len(sim.planets))
                    badge_engine.reset_session()
                    combat_manager.reset()
                    powerup_manager.reset()
                    float_texts.reset()
                    session_time = 0.0
                    gsm.transition("MAP")
                elif menu_buttons[1].is_clicked(event):         # How to Play
                    gsm.transition("HOW_TO_PLAY")
                elif menu_buttons[2].is_clicked(event):         # Profile
                    profile_ui.run(screen, clock, font_title, font_ui, font_small,
                                   stars, profile_manager,
                                   os.path.join(base_dir, "assets", "badges"),
                                   music_gallery,
                                   os.path.join(base_dir, "assets", "music"))
                elif menu_buttons[3].is_clicked(event):         # Leaderboard
                    leaderboard.run_screen(screen, clock,
                                           font_title, font_ui, font_small, stars)
                elif menu_buttons[4].is_clicked(event):         # Credits
                    credits_ui.run(screen, clock,
                                   font_title, font_ui, font_small, stars)
                elif menu_buttons[5].is_clicked(event):         # Quit
                    running = False

            elif state == "HOW_TO_PLAY":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    gsm.transition("MENU")

            elif state == "MAP":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    gsm.transition("MENU")
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for planet in sim.planets:
                        if planet.is_clicked(mouse_pos) and not planet.is_locked:
                            controller.select_planet(planet)
                            sim.reset_selected_planet()
                            gsm.transition("SIMULATION")
                            break

            elif state == "SIMULATION":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    gsm.transition("MAP")

                p = controller.selected_planet
                if event.type == pygame.KEYDOWN and event.key == pygame.K_d and p:
                    sim.trigger_disaster(p)
                    badge_engine.unlock_special("badge_disaster", profile_manager)

                if detail_buttons["disaster"].is_clicked(event) and p:
                    sim.trigger_disaster(p)
                    badge_engine.unlock_special("badge_disaster", profile_manager)
                if detail_buttons["resources"].is_clicked(event):
                    controller.spawn_resources(
                        evo_gain=difficulty_manager.evolution_point_gain)
                if p and p.species_list:
                    tgt = p.species_list[0]
                    if detail_buttons["evo_speed"].is_clicked(event):
                        controller.spend_evolution_point(tgt, "speed")
                    if detail_buttons["evo_agg"].is_clicked(event):
                        controller.spend_evolution_point(tgt, "aggression")
                    if detail_buttons["evo_meta"].is_clicked(event):
                        controller.spend_evolution_point(tgt, "metabolism")
                if detail_buttons["coop_up"].is_clicked(event):
                    controller.adjust_coop_weight(sim.game_theory)
                # Evolution Booster: apply to selected planet's primary species
                if detail_buttons["booster"].is_clicked(event) and p:
                    powerup_manager.apply(p)

                if p:
                    built = {b.name for b in sim.building_manager.get_buildings(p.name)}
                    if detail_buttons["church"].is_clicked(event) and "Church" not in built:
                        if sim.building_manager.construct(Church(), p, sim.game_theory, controller):
                            badge_engine.unlock_special("badge_builder", profile_manager)
                    if detail_buttons["military"].is_clicked(event) and "MilitaryBase" not in built:
                        if sim.building_manager.construct(MilitaryBase(), p, sim.game_theory, controller):
                            badge_engine.unlock_special("badge_builder", profile_manager)
                    if detail_buttons["airdef"].is_clicked(event) and "AirDefense" not in built:
                        if sim.building_manager.construct(AirDefense(), p, sim.game_theory, controller):
                            badge_engine.unlock_special("badge_builder", profile_manager)

        # ---- Simulation tick ----
        sim.tick(dt, controller.selected_planet, gsm.current_state,
                 time_controller.time_scale)

        # ---- EP income from simulation (passive + milestones) ----
        if sim.ep_gained_this_tick > 0:
            controller.evolution_points += sim.ep_gained_this_tick
            if state == "SIMULATION":
                float_texts.add(f"+{sim.ep_gained_this_tick} EP",
                                1060, SCREEN_H - 80)

        # ---- UFO Incursion resolution ----------------------------------------
        # tick() fires new incursions; each is immediately routed to either the
        # interactive mini-game (selected planet, SIMULATION) or auto-resolve.
        if gsm.current_state in ("MAP", "SIMULATION"):
            for pname in combat_manager.tick(dt, sim.planets):
                sel = controller.selected_planet
                if gsm.current_state == "SIMULATION" and sel and sel.name == pname:
                    choice = combat_manager.show_choice(
                        screen, clock, font_title, font_ui, font_small,
                        screen.copy(), pname)
                    if choice == "DEFEND":
                        combat_manager.run_minigame(
                            screen, clock, font_ui, font_small, stars,
                            pname, sim.building_manager, sim.planets)
                    else:
                        combat_manager.resolve_auto(pname, sim.building_manager,
                                                    sim.planets)
                else:
                    combat_manager.resolve_auto(pname, sim.building_manager,
                                                sim.planets)

        # ---- Galaxy stability ----
        galaxy_manager.tick(
            dt * time_controller.time_scale,
            controller.selected_planet if state == "SIMULATION" else None,
            sim.last_interaction       if state == "SIMULATION" else None,
            building_manager=sim.building_manager,
        )

        # ---- Planet-unlock EP milestone ----
        if galaxy_manager.milestone_ep > 0:
            amt = galaxy_manager.milestone_ep
            galaxy_manager.milestone_ep = 0
            controller.evolution_points += amt
            float_texts.add(f"+{amt} EP  UNLOCK!", SCREEN_W // 2 - 80,
                            SCREEN_H // 2 - 100)

        # ---- Nash badge tracking (fires once per new interaction tuple) ----
        badge_engine.on_interaction(sim.last_interaction, profile_manager)

        # ---- Planet conquest ----
        if (gsm.current_state == "SIMULATION"
                and sim.last_interaction and controller.selected_planet):
            act_a, act_b = sim.last_interaction[:2]
            if act_a == "cooperate" and act_b == "cooperate":
                if gsm.try_conquer(controller.selected_planet.name):
                    badge_engine.on_planet_conquered(
                        controller.selected_planet.name, profile_manager)
                    powerup_manager.award()   # reward one booster per conquest
                    controller.evolution_points += 50
                    float_texts.add("+50 EP  CONQUEST!", SCREEN_W // 2 - 90,
                                    SCREEN_H // 2 - 120)

        # ---- Win / Loss — blocking cinematic screens -------------------------
        outcome = gsm.update(sim.planets)
        if outcome == "WIN_SCREEN":
            saved_time = session_time
            profile_manager.add_stat(len(gsm.conquered_planets), saved_time)
            leaderboard.submit(
                profile_manager.get_active_profile().get("username", "Player"),
                len(gsm.conquered_planets), saved_time, difficulty_manager.label)
            if difficulty_manager.label == "HARD":
                badge_engine.unlock_special("badge_hard_mode", profile_manager)
            session_time = 0.0
            gsm.transition("WIN_SCREEN")
            win_screen.run(screen, clock, font_title, font_ui, font_small, stars,
                           gsm.conquered_planets, len(sim.planets), saved_time,
                           profile_manager,
                           os.path.join(base_dir, "assets", "badges"))
            gsm.transition("MENU")
        elif outcome == "LOSS_SCREEN":
            profile_manager.add_stat(len(gsm.conquered_planets), session_time)
            session_time = 0.0
            gsm.transition("LOSS_SCREEN")
            action = loss_screen.run(screen, clock, font_title, font_ui, font_small,
                                     stars, gsm.conquered_planets, len(sim.planets))
            if action == "RELOAD":
                save_manager.load(gsm, controller, sim)
                gsm.transition("MAP")
            else:
                gsm.transition("MENU")

        # ---- Music ----
        music_manager.update_track(gsm.current_state, sim.nash_status,
                                   sim.is_disaster_active)
        music_manager.tick(dt)

        # ---- Dynamic button labels (live inventory / build state) ----
        if gsm.current_state == "SIMULATION" and controller.selected_planet:
            built = {b.name for b in sim.building_manager.get_buildings(
                controller.selected_planet.name)}
            detail_buttons["church"].label   = "Church [OK]"  if "Church"       in built else "Church [2]"
            detail_buttons["military"].label = "MilBase [OK]" if "MilitaryBase" in built else "MilBase [3]"
            detail_buttons["airdef"].label   = "AirDef [OK]"  if "AirDefense"   in built else "AirDef [4]"
            detail_buttons["booster"].label  = f"EvoBoost [{powerup_manager.inventory}]"

        # ---- Draw ----
        state = gsm.current_state

        if state == "MENU":
            draw_menu(screen, stars, tick, menu_buttons,
                      font_title, font_ui, mouse_pos,
                      difficulty_label=difficulty_manager.label)
        elif state == "HOW_TO_PLAY":
            draw_how_to_play(screen, stars, tick, font_title, font_ui, font_small)
        elif state == "MAP":
            draw_galactic_map(screen, stars, tick, sim.planets, mouse_pos,
                              planet_renderer, font_title, font_ui, font_small,
                              gsm.conquered_planets, galaxy_manager=galaxy_manager)
        elif state == "SIMULATION" and controller.selected_planet:
            is_conquered = controller.selected_planet.name in gsm.conquered_planets
            draw_planet_detail(
                screen, stars, tick,
                controller.selected_planet, controller, sim.game_theory,
                sprite_renderer, planet_renderer,
                font_title, font_ui, font_small,
                mouse_pos, sim.last_interaction,
                is_conquered=is_conquered,
                booster_count=powerup_manager.inventory,
            )
            for btn in detail_buttons.values():
                btn.draw(screen, mouse_pos)

        # ---- Persistent HUD overlays ----
        if music_manager.is_muted:
            mute = font_small.render("[M] MUTED", True, (255, 80, 80))
            screen.blit(mute, (SCREEN_W - mute.get_width() - 10, 8))
        if state in ("MAP", "SIMULATION"):
            draw_time_hud(screen, font_small, time_controller)

        # ---- Floating EP reward texts ----
        if state in ("MAP", "SIMULATION"):
            float_texts.draw_and_update(screen, font_ui, dt)

        # ---- Galaxy unlock notification ----
        if galaxy_manager.notification_timer > 0:
            fade    = min(1.0, galaxy_manager.notification_timer / 2.0)
            r, g, b = ACCENT_GOLD
            color   = (int(r * fade), int(g * fade), int(b * fade))
            notif   = font_ui.render(
                f"*  {galaxy_manager.notification_text}  *", True, color)
            screen.blit(notif, notif.get_rect(
                centerx=SCREEN_W // 2, centery=SCREEN_H // 2 - 60))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
