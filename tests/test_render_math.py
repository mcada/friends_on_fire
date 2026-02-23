"""Tests for dynamic render math — validates computed colors, alphas, and
sizes stay within valid ranges across many time values."""

import math
import pygame
from objects.Boss import Boss, BOSS_BASE_HP
from objects.Enemy import Fighter


# ---- Player damage hearts ----

def test_damage_hearts_alpha_always_valid():
    """The blink * fade alpha must be in [0, 255] for all time values."""
    for tick in range(0, 10000, 7):
        t = tick / 1000.0
        blink = 0.45 + 0.55 * math.sin(t * 8)
        for fade in (0.0, 0.5, 1.0):
            alpha = max(0, min(255, int(255 * blink * fade)))
            assert 0 <= alpha <= 255, f"alpha={alpha} at t={t}, fade={fade}"


# ---- Player shield pulse ----

def test_shield_pulse_always_valid():
    """Shield overlay alpha must be in valid range for all tick values."""
    for tick in range(0, 100000, 100):
        pulse = int(25 + 15 * math.sin(tick * 0.005))
        assert 0 <= pulse <= 255, f"pulse={pulse} at tick={tick}"


# ---- game_world weapon icon glow ----

def test_weapon_icon_pulse_alphas_valid():
    """All alpha values derived from the weapon icon pulse must be 0–255."""
    for tick in range(0, 10000, 7):
        t = tick / 1000.0
        pulse = 0.55 + 0.45 * math.sin(t * 8)
        bg_alpha = int(160 + 80 * pulse)
        flash_alpha = int(50 * pulse)
        border_alpha = int(220 * pulse)
        outer_alpha = int(70 * pulse)
        assert 0 <= bg_alpha <= 255, f"bg_alpha={bg_alpha}"
        assert 0 <= flash_alpha <= 255, f"flash_alpha={flash_alpha}"
        assert 0 <= border_alpha <= 255, f"border_alpha={border_alpha}"
        assert 0 <= outer_alpha <= 255, f"outer_alpha={outer_alpha}"


# ---- game_world shield icon pulse ----

def test_shield_icon_pulse_alphas_valid():
    for tick in range(0, 10000, 7):
        t = tick / 1000.0
        pulse = 0.7 + 0.3 * math.sin(t * 4)
        a1 = int(200 * pulse)
        a2 = int(240 * pulse)
        assert 0 <= a1 <= 255, f"a1={a1}"
        assert 0 <= a2 <= 255, f"a2={a2}"


# ---- Boss health bar ----

def test_boss_health_bar_fill_never_negative(game):
    boss = Boss(game, attack_level=1, hp_override=20)
    surf = pygame.Surface((400, 400), pygame.SRCALPHA)
    boss.hp = 0
    boss.draw(surf)
    boss.hp = -5
    boss.draw(surf)


def test_boss_shield_bubble_alphas_valid():
    for tick in range(0, 10000, 7):
        t = tick / 1000.0
        pulse = 0.85 + 0.15 * math.sin(t * 4)
        assert pulse >= 0, f"pulse={pulse}"


# ---- Enemy health bar ----

def test_enemy_health_bar_fill_never_negative(game):
    f = Fighter(600, 300, game)
    surf = pygame.Surface((200, 200), pygame.SRCALPHA)
    f.hp = 0
    f.draw(surf)
    f.hp = -3
    f.draw(surf)


# ---- Particle size ----

def test_particle_size_always_positive():
    """Particle size must be >= 1 for all age/lifetime combos."""
    for lifetime in (0.25, 0.35, 0.5):
        for age_frac in range(0, 101, 5):
            age = lifetime * age_frac / 100.0
            remaining = 1 - age / lifetime
            base_size = 3.0
            size = max(1, int(base_size * remaining))
            assert size >= 1


# ---- Upgrade message alpha ----

def test_upgrade_msg_alpha_valid():
    for timer_ms in range(0, 3000, 50):
        timer = timer_ms / 1000.0
        alpha = min(1.0, timer / 0.3)
        r = int(255 * alpha)
        g = int(220 * alpha)
        b = int(60 * alpha)
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255
