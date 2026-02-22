import pygame
from states.state import State

PAUSE_ITEMS = ["Resume", "Back to Menu"]


class PauseMenu(State):
    def __init__(self, game):
        self.game = game
        self.game.reset_keys()
        State.__init__(self, game)
        pygame.mixer.music.pause()
        self.selected = 0

    def update(self, delta_time, actions):
        if actions["up"]:
            self.selected = (self.selected - 1) % len(PAUSE_ITEMS)
        if actions["down"]:
            self.selected = (self.selected + 1) % len(PAUSE_ITEMS)

        if actions["escape"]:
            self._resume()
        elif actions["start"] or actions["space"]:
            self._activate()

        self.game.reset_keys()

    def _activate(self):
        label = PAUSE_ITEMS[self.selected]
        if label == "Resume":
            self._resume()
        elif label == "Back to Menu":
            self.game.return_to_menu()

    def _resume(self):
        self.game.get_events()
        pygame.mixer.music.unpause()
        self.game.state_stack.pop()

    def render(self, display):
        self.prev_state.render(display)

        overlay = pygame.Surface((self.game.GAME_WIDTH, self.game.GAME_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(120)
        display.blit(overlay, (0, 0))

        cx = self.game.GAME_WIDTH / 2
        cy = self.game.GAME_HEIGHT / 2

        self.game.draw_text_sized(display, "PAUSED", (255, 255, 255), cx, cy - 60, 48)

        for i, item in enumerate(PAUSE_ITEMS):
            y = cy + i * 50
            if i == self.selected:
                color = (255, 255, 255)
                prefix = "> "
            else:
                color = (160, 160, 160)
                prefix = "  "
            self.game.draw_text_sized(display, prefix + item, color, cx, y, 34)
