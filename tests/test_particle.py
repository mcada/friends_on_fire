import random
from states.game_world import Particle


def test_particle_moves():
    random.seed(42)
    p = Particle(100, 100)
    old_x, old_y = p.x, p.y
    p.update(0.1)
    assert (p.x, p.y) != (old_x, old_y)


def test_particle_alive_during_lifetime():
    random.seed(42)
    p = Particle(100, 100)
    assert p.update(0.01) is True


def test_particle_dies_after_lifetime():
    random.seed(42)
    p = Particle(100, 100)
    assert p.update(10.0) is False


def test_particle_shrinks_over_time():
    import pygame

    random.seed(42)
    p = Particle(100, 100)
    initial_size = p.size
    p.update(p.lifetime * 0.9)
    remaining = 1 - p.age / p.lifetime
    effective = max(1, int(p.size * remaining))
    assert effective < initial_size
