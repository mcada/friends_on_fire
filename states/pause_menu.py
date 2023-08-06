import pygame, os
from states.state import State

# from states.party import PartyMenu


class PauseMenu(State):
    def __init__(self, game):
        self.game = game
        self.game.reset_keys()
        State.__init__(self, game)
        # Set the menu
        # self.menu_img = pygame.image.load(os.path.join(self.game.assets_dir, "map", "menu.png"))
        # self.menu_rect = self.menu_img.get_rect()
        # self.menu_rect.center = (self.game.GAME_W*.85, self.game.GAME_H*.4)

    def update(self, delta_time, actions):
        if actions["start"]:
            self.exit_state()
        self.game.reset_keys()

    def render(self, display):
        # render the gameworld behind the menu, which is right before the pause menu on the stack
        # self.game.state_stack[-2].render(display)
        self.prev_state.render(display)
        # display.blit(self.menu_img, self.menu_rect)
        self.game.draw_text(
            display,
            "PAUSE",
            "white",
            self.game.GAME_WIDTH / 2,
            self.game.GAME_HEIGHT / 2,
        )

    def exit_state(self):
        self.game.get_events()
        self.game.state_stack.pop()
