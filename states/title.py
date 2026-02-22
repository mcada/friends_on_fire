import pygame
from states.state import State


MENU_ITEMS = ["New Game", "Controls", "Scoreboard", "Exit"]


class Title(State):
    def __init__(self, game):
        State.__init__(self, game)
        self.background = self.game.background.copy()
        dark = pygame.Surface(self.background.get_size())
        dark.fill((0, 0, 0))
        dark.set_alpha(150)
        self.background.blit(dark, (0, 0))
        self.selected = 0
        self.game.play_music("menu")

    def update(self, delta_time, actions):
        if actions["up"]:
            self.selected = (self.selected - 1) % len(MENU_ITEMS)
        if actions["down"]:
            self.selected = (self.selected + 1) % len(MENU_ITEMS)

        if actions["start"] or actions["space"]:
            self._activate()

        self.game.reset_keys()

    def _activate(self):
        label = MENU_ITEMS[self.selected]
        if label == "New Game":
            from states.level_select import LevelSelect
            new_state = LevelSelect(self.game)
            new_state.enter_state()
        elif label == "Controls":
            from states.controls import Controls
            new_state = Controls(self.game)
            new_state.enter_state()
        elif label == "Scoreboard":
            from states.scoreboard import Scoreboard
            new_state = Scoreboard(self.game)
            new_state.enter_state()
        elif label == "Exit":
            self.game.playing = False
            self.game.running = False

    def render(self, display):
        display.blit(self.background, (0, 0))
        cx = self.game.GAME_WIDTH / 2
        cy = self.game.GAME_HEIGHT / 2

        self.game.draw_text_sized(
            display, "Friends on Fire!", (255, 220, 60), cx, cy - 100, 50
        )

        for i, item in enumerate(MENU_ITEMS):
            y = cy - 10 + i * 50
            if i == self.selected:
                color = (255, 255, 255)
                prefix = "> "
            else:
                color = (160, 160, 160)
                prefix = "  "
            self.game.draw_text_sized(display, prefix + item, color, cx, y, 36)
