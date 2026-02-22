import os, pygame
from states.state import State

LEVEL_ITEMS = [
    {"label": "Endless", "mode": "endless"},
    {"label": "Level 1", "mode": "level", "level_num": 1},
    {"label": "Level 2", "mode": "level", "level_num": 2},
    {"label": "Level 3", "mode": "level", "level_num": 3},
]

DESCRIPTIONS = {
    "endless": "Survive as long as you can. No time limit.",
    "1": "Survive 60 seconds to advance.",
    "2": "Survive 60 seconds. Harder asteroids.",
    "3": "Survive 60 seconds. Maximum difficulty.",
}


class LevelSelect(State):
    def __init__(self, game):
        State.__init__(self, game)
        self.background = pygame.image.load(
            os.path.join(self.game.assets_dir, "bg.jpeg")
        )
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

        self.game.draw_text_sized(
            display, "Select Mode", (255, 220, 60), cx, cy - 120, 46,
        )

        for i, item in enumerate(LEVEL_ITEMS):
            y = cy - 30 + i * 50
            if i == self.selected:
                color = (255, 255, 255)
                prefix = "> "
            else:
                color = (160, 160, 160)
                prefix = "  "
            self.game.draw_text_sized(display, prefix + item["label"], color, cx, y, 36)

        sel = LEVEL_ITEMS[self.selected]
        desc_key = "endless" if sel["mode"] == "endless" else str(sel.get("level_num", ""))
        desc = DESCRIPTIONS.get(desc_key, "")
        self.game.draw_text_sized(
            display, desc, (180, 200, 220), cx, cy + 170, 24,
        )

        self.game.draw_text_sized(
            display, "Escape to go back", (120, 120, 120),
            cx, self.game.GAME_HEIGHT - 30, 20,
        )
