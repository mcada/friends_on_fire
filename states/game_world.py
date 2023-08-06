import pygame, os
from objects.Player import Player
from states.state import State
from states.pause_menu import PauseMenu


class Game_World(State):
    def __init__(self, game):
        State.__init__(self, game)
        self.background = pygame.image.load(
            os.path.join(self.game.assets_dir, "bg.jpeg")
        )

    def update(self, delta_time, actions):
        # Check if the game was paused
        if actions["start"]:
            new_state = PauseMenu(self.game)
            new_state.enter_state()
        self.game.player.update(delta_time, actions)
        pass

    def render(self, display):
        display.blit(self.background, (0, 0))
        self.game.player.render(display)
