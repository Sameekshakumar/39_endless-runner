import math
import random
from array import array

import pygame

DEFAULT_RATE = 44100


def _ensure_mixer():
    """Make sure the mixer is up in signed 16-bit. Returns (rate, channels) or None."""
    try:
        init = pygame.mixer.get_init()
        if init is None or init[1] != -16:
            pygame.mixer.quit()
            pygame.mixer.init(DEFAULT_RATE, -16, 2)
            init = pygame.mixer.get_init()
        if init is None:
            return None
        return init[0], init[2]
    except pygame.error:
        return None


def _make_sound(notes, wave, rate, channels, volume=0.4, fade=0.4, noise=0.0):
    """
    notes: list of (start_hz, end_hz, seconds); frequency slides linearly per note.
    wave:  "sine" or "square"
    fade:  fraction of the total length used for the fade-out at the end
    noise: 0..1 mix of random noise into the tone
    """
    samples = []
    phase = 0.0
    for f0, f1, dur in notes:
        n = int(rate * dur)
        for i in range(n):
            freq = f0 + (f1 - f0) * i / n
            phase += 2 * math.pi * freq / rate
            if wave == "square":
                s = 1.0 if math.sin(phase) >= 0 else -1.0
            else:
                s = math.sin(phase)
            if noise:
                s = s * (1 - noise) + random.uniform(-1, 1) * noise
            samples.append(s)

    total = len(samples)
    fade_n = max(1, int(total * fade))
    attack_n = max(1, int(rate * 0.005))  # tiny fade-in so it doesn't click

    buf = array("h")
    for i, s in enumerate(samples):
        env = 1.0
        if i < attack_n:
            env = i / attack_n
        if i >= total - fade_n:
            env = min(env, (total - i) / fade_n)
        v = int(s * env * volume * 32767)
        for _ in range(channels):
            buf.append(v)

    return pygame.mixer.Sound(buffer=buf.tobytes())


class Sounds:
    def __init__(self):
        self.enabled = False
        self._jump = self._score = self._death = None

        fmt = _ensure_mixer()
        if fmt is None:
            return  # no audio device, game just runs silent
        rate, ch = fmt

        try:
            # Jump: quick rising sine blip
            self._jump = _make_sound([(300, 700, 0.15)], "sine", rate, ch, fade=0.4)
            # Score: two-note "ding" going up
            self._score = _make_sound(
                [(880, 880, 0.08), (1320, 1320, 0.12)], "sine", rate, ch, volume=0.35, fade=0.5
            )
            # Death: low, harsh, falling square wave with some noise
            self._death = _make_sound(
                [(400, 70, 0.5)], "square", rate, ch, volume=0.3, fade=0.5, noise=0.25
            )
            self.enabled = True
        except pygame.error:
            self.enabled = False

    def play_jump(self):
        if self.enabled:
            self._jump.play()

    def play_score(self):
        if self.enabled:
            self._score.play()

    def play_death(self):
        if self.enabled:
            self._death.play()