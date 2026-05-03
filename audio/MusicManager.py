"""
MusicManager.py — Dynamic, state-driven music system with crossfade transitions.

Track selection priority (highest wins):
    1. disaster_theme  — overrides everything while a disaster event is active.
    2. war_theme       — planet view, any species chose COMPETE last Nash tick.
    3. coop_theme      — planet view, both species COOPERATED last Nash tick.
    4. map_theme       — galactic map or main menu (default fallback).

Crossfade:
    Volume is manually ramped down from TARGET_VOLUME to 0 over FADE_DURATION
    seconds, the new track is loaded at volume 0, then ramped up to
    TARGET_VOLUME.  Manual ramping (instead of pygame's async fadeout) gives
    precise control over timing and allows interrupting a fade mid-way when
    an urgent track needs to take over (e.g. disaster fires during a cooperate
    crossfade).

Missing files:
    If an audio file is absent the manager silently skips it — the game never
    crashes because of missing music assets.
"""

import os
import pygame


class MusicManager:
    """
    Manages background music tracks with priority-based selection and crossfading.

    Call update_track() every frame with the current game context.
    Call tick(dt) every frame so the volume ramp advances.

    Internal FSM states
    -------------------
    'idle'       — no music loaded or previous load failed.
    'playing'    — a track is playing at full TARGET_VOLUME.
    'fading_out' — volume is ramping toward 0; _next_track is queued.
    'fading_in'  — new track just loaded; volume is ramping toward TARGET_VOLUME.

    Attributes:
        FADE_DURATION  : Crossfade length in seconds.
        TARGET_VOLUME  : Master volume at full loudness (0.0 – 1.0).
    """

    FADE_DURATION = 1.5    # seconds for a full fade-out or fade-in
    TARGET_VOLUME = 0.75   # leave some headroom below maximum

    # Internal name → filename mapping (all files live in assets/music/).
    _TRACKS: dict[str, str] = {
        "map_theme":      "map_theme.mp3",
        "coop_theme":     "coop_theme.mp3",
        "war_theme":      "war_theme.mp3",
        "disaster_theme": "disaster_theme.mp3",
    }

    def __init__(self, asset_dir: str):
        """
        Initialise the music manager and ensure pygame.mixer is ready.

        Args:
            asset_dir : Absolute path to the folder containing the .mp3 files.
        """
        self._asset_dir      = asset_dir
        self._current_track: str | None = None   # track name currently loaded
        self._next_track:    str | None = None   # track queued after fade-out
        self._state          = "idle"
        self._fade_timer     = 0.0
        self._muted          = False

        # Initialise mixer with good defaults if it isn't already running.
        if not pygame.mixer.get_init():
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_track(self, game_state: str, nash_status: str, is_disaster: bool):
        """
        Select the correct track for the current game context and request a
        crossfade if it differs from what is already playing or queued.

        This method is safe to call every frame — it only acts when a change
        is actually needed.

        Args:
            game_state  : Active view: 'menu', 'galactic_map', 'planet_detail'.
            nash_status : Last resolved Nash action: 'cooperate', 'compete', 'idle'.
            is_disaster : True while a disaster event timer is non-zero.
        """
        desired = self._determine_track(game_state, nash_status, is_disaster)

        # Skip if the desired track is already current or already queued.
        if desired == self._current_track and self._state in ("playing", "fading_in"):
            return
        if desired == self._next_track:
            return

        self._request_crossfade(desired)

    def tick(self, dt: float):
        """
        Advance the crossfade volume ramp by one frame.

        Must be called once per game loop iteration — typically right after
        update_track().

        Args:
            dt : Elapsed seconds since the previous frame.
        """
        if self._state == "fading_out":
            self._fade_timer += dt
            progress = min(1.0, self._fade_timer / self.FADE_DURATION)
            vol = (1.0 - progress) * self.TARGET_VOLUME
            pygame.mixer.music.set_volume(0.0 if self._muted else vol)

            if progress >= 1.0:
                # Fade-out complete — load the next track and begin fade-in.
                pygame.mixer.music.stop()
                if self._next_track:
                    self._load_and_play(self._next_track)
                    self._next_track = None

        elif self._state == "fading_in":
            self._fade_timer += dt
            progress = min(1.0, self._fade_timer / self.FADE_DURATION)
            vol = progress * self.TARGET_VOLUME
            pygame.mixer.music.set_volume(0.0 if self._muted else vol)

            if progress >= 1.0:
                self._state = "playing"
                pygame.mixer.music.set_volume(
                    0.0 if self._muted else self.TARGET_VOLUME
                )

    def toggle_mute(self):
        """
        Silence or restore audio.  Toggled by the M key in the main loop.

        When unmuting, the volume is restored to wherever the fade currently
        is so there is no sudden volume jump.
        """
        self._muted = not self._muted

        if self._muted:
            pygame.mixer.music.set_volume(0.0)
        else:
            # Restore to the correct volume for the current fade state.
            if self._state == "playing":
                pygame.mixer.music.set_volume(self.TARGET_VOLUME)
            elif self._state in ("fading_in", "fading_out"):
                progress = min(1.0, self._fade_timer / self.FADE_DURATION)
                if self._state == "fading_in":
                    pygame.mixer.music.set_volume(progress * self.TARGET_VOLUME)
                else:
                    pygame.mixer.music.set_volume(
                        (1.0 - progress) * self.TARGET_VOLUME
                    )

    @property
    def is_muted(self) -> bool:
        """True when the M-key mute toggle is active."""
        return self._muted

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _determine_track(self, game_state: str, nash_status: str,
                          is_disaster: bool) -> str:
        """
        Apply the priority rules and return the desired track name.

        Args:
            game_state  : Current view string.
            nash_status : 'cooperate', 'compete', or 'idle'.
            is_disaster : Whether the disaster timer is active.

        Returns:
            str: A key from _TRACKS.
        """
        if is_disaster:
            return "disaster_theme"
        if game_state == "SIMULATION":
            return "war_theme" if nash_status == "compete" else "coop_theme"
        return "map_theme"

    def _request_crossfade(self, track_name: str):
        """
        Queue a new track and start the volume ramp-down.

        Edge cases handled:
          - Nothing playing → load immediately with a fade-in.
          - Currently fading_in → convert the in-progress fade-in into a
            fade-out at the same volume level (no jump) then load new track.
          - Currently fading_out → just update _next_track; existing timer runs.
          - Currently playing → start a fresh fade-out.

        Args:
            track_name : Key from _TRACKS.
        """
        self._next_track = track_name

        if self._state == "idle":
            self._load_and_play(track_name)
            self._next_track = None

        elif self._state == "playing":
            self._state = "fading_out"
            self._fade_timer = 0.0

        elif self._state == "fading_in":
            # Mirror the current fade-in progress into an equivalent fade-out
            # position so volume stays continuous (no audible jump).
            in_progress = min(1.0, self._fade_timer / self.FADE_DURATION)
            self._state = "fading_out"
            # Equivalent fade-out start: (1 - in_progress) of the way through
            self._fade_timer = (1.0 - in_progress) * self.FADE_DURATION

        # If already fading_out, _next_track is updated; timer continues.

    def _load_and_play(self, track_name: str):
        """
        Load a music file and begin playing it at volume 0 (fade-in starts).

        Plays with -1 (infinite loop) for seamless looping.  If the file is
        missing or corrupt the manager moves to 'idle' and marks the track as
        current to prevent repeated failing load attempts.

        Args:
            track_name : Key from _TRACKS.
        """
        filename = self._TRACKS.get(track_name, "")
        path = os.path.join(self._asset_dir, filename)

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.0)
            pygame.mixer.music.play(-1)          # -1 = loop seamlessly
            self._current_track = track_name
            self._state = "fading_in"
            self._fade_timer = 0.0
        except (pygame.error, FileNotFoundError, OSError):
            # Missing / corrupt file — stay silent but mark track as "handled"
            # so we don't retry every frame.
            self._current_track = track_name
            self._state = "idle"
