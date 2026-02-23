import pygame
from states.state import State
from Game import MAX_PLAYERS

PLAYER_OPTIONS = [f"{i} Player{'s' if i > 1 else ''}" for i in range(1, MAX_PLAYERS + 1)]


class PlayerSelect(State):
    def __init__(self, game):
        State.__init__(self, game)
        self.background = self.game.background.copy()
        dark = pygame.Surface(self.background.get_size())
        dark.fill((0, 0, 0))
        dark.set_alpha(150)
        self.background.blit(dark, (0, 0))
        self.selected = 0
        self.game.reset_keys()

    def update(self, delta_time, actions):
        if actions["up"]:
            self.selected = (self.selected - 1) % len(PLAYER_OPTIONS)
        if actions["down"]:
            self.selected = (self.selected + 1) % len(PLAYER_OPTIONS)

        if actions["start"] or actions["space"]:
            self._launch()
        elif actions["escape"]:
            self.exit_state()

        self.game.reset_keys()

    def _launch(self):
        self.game.num_players = self.selected + 1
        from states.level_select import LevelSelect
        LevelSelect(self.game).enter_state()

    def render(self, display):
        display.blit(self.background, (0, 0))
        cx = self.game.GAME_WIDTH / 2
        cy = self.game.GAME_HEIGHT / 2

        self.game.draw_text_sized(
            display, "How Many Players?", (255, 220, 60), cx, cy - 120, 46,
        )

        for i, label in enumerate(PLAYER_OPTIONS):
            y = cy - 40 + i * 50
            if i == self.selected:
                color = (255, 255, 255)
                prefix = "> "
            else:
                color = (160, 160, 160)
                prefix = "  "
            self.game.draw_text_sized(display, prefix + label, color, cx, y, 34)

        info_y = cy + 120
        n = self.selected + 1
        labels = self.game.get_binding_labels()
        for p in range(n):
            bl = labels[p]
            txt = f"P{p + 1}: {bl['move']}  \u00b7  {bl['fire']} / {bl['secondary']} / {bl['cycle']}"
            pc = (200, 200, 200) if p == 0 else (255, 100, 100) if p == 1 else (255, 220, 80)
            self.game.draw_text_sized(display, txt, pc, cx, info_y + p * 28, 20)

        self.game.draw_text_sized(
            display, "Escape to go back", (120, 120, 120),
            cx, self.game.GAME_HEIGHT - 30, 20,
        )
