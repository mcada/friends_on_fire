import os, sys

os.chdir(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.getcwd())

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

from objects.Rocks import Rock


@pytest.fixture(scope="session", autouse=True)
def init_pygame():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


@pytest.fixture
def game():
    Rock.sprites = None
    from Game import Game

    g = Game()
    yield g


@pytest.fixture
def actions():
    return {
        "left": False,
        "right": False,
        "up": False,
        "down": False,
        "action1": False,
        "action2": False,
        "start": False,
        "space": False,
        "escape": False,
    }
