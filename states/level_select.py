import pygame
from states.state import State

LEVEL_ITEMS = [
    {"label": "Endless", "mode": "endless"},
    {"label": "Level 1", "mode": "level", "level_num": 1},
    {"label": "Level 2", "mode": "level", "level_num": 2},
    {"label": "Level 3", "mode": "level", "level_num": 3},
    {"label": "Boss Challenge", "mode": "boss_challenge"},
    {"label": "Testing", "mode": "testing"},
]

DESCRIPTIONS = {
    "endless": "Survive as long as you can. No time limit.",
    "1": "Survive 120 seconds to advance.",
    "2": "Survive 120 seconds. Harder asteroids.",
    "3": "Survive 120 seconds. Maximum difficulty.",
    "boss_challenge": "Face the boss at full power. No asteroids.",
    "testing": "Endless mode with all weapons pre-equipped.",
}


class LevelSelect(State):
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
            self.selected = (self.selected - 1) % len(LEVEL_ITEMS)
        if actions["down"]:
            self.selected = (self.selected + 1) % len(LEVEL_ITEMS)

        if actions["start"] or actions["space"]:
            self._launch()
        elif actions["escape"]:
            self.exit_state()

        self.game.reset_keys()

    def _launch(self):
        from states.game_world import Game_World
        item = LEVEL_ITEMS[self.selected]
        new_state = Game_World(self.game, game_mode=item["mode"],
                               level_num=item.get("level_num", 0))
        new_state.enter_state()

    def render(self, display):
        display.blit(self.background, (0, 0))
        cx = self.game.GAME_WIDTH / 2
        cy = self.game.GAME_HEIGHT / 2

        n = len(LEVEL_ITEMS)
        item_spacing = 40
        list_height = (n - 1) * item_spacing
        list_top = cy - list_height / 2 - 10

        self.game.draw_text_sized(
            display, "Select Mode", (255, 220, 60), cx, list_top - 60, 46,
        )

        for i, item in enumerate(LEVEL_ITEMS):
            y = list_top + i * item_spacing
            if i == self.selected:
                color = (255, 255, 255)
                prefix = "> "
            else:
                color = (160, 160, 160)
                prefix = "  "
            self.game.draw_text_sized(display, prefix + item["label"], color, cx, y, 34)

        list_bottom = list_top + list_height
        sel = LEVEL_ITEMS[self.selected]
        if sel["mode"] in ("endless", "boss_challenge", "testing"):
            desc_key = sel["mode"]
        else:
            desc_key = str(sel.get("level_num", ""))
        desc = DESCRIPTIONS.get(desc_key, "")
        self.game.draw_text_sized(
            display, desc, (180, 200, 220), cx, list_bottom + 50, 24,
        )

        self.game.draw_text_sized(
            display, "Escape to go back", (120, 120, 120),
            cx, self.game.GAME_HEIGHT - 30, 20,
        )
