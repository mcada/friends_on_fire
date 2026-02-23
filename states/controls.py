import pygame
from states.state import State
from Game import BINDABLE_ACTIONS, ALWAYS_RESERVED, MAX_PLAYERS


RESET_IDX = len(BINDABLE_ACTIONS)
TOTAL_ITEMS = RESET_IDX + 1


class Controls(State):
    def __init__(self, game):
        State.__init__(self, game)
        self.background = self.game.background.copy()
        dark = pygame.Surface(self.background.get_size())
        dark.fill((0, 0, 0))
        dark.set_alpha(150)
        self.background.blit(dark, (0, 0))
        self.selected = 0
        self.player_idx = 0
        self.listening = False
        self.message = ""
        self.message_timer = 0
        self.game.reset_keys()

    @property
    def _bindings(self):
        return self.game.all_bindings[self.player_idx]

    def update(self, delta_time, actions):
        if self.message_timer > 0:
            self.message_timer -= delta_time

        if self.listening:
            key = self.game.last_keydown
            if key is not None:
                self.game.last_keydown = None
                if key == pygame.K_ESCAPE:
                    self.listening = False
                elif key in self.game.reserved_keys_for(self.player_idx):
                    self.message = "That key is used by another player!"
                    self.message_timer = 2.0
                else:
                    self._rebind(self.selected, key)
                    self.listening = False
            self.game.reset_keys()
            return

        if actions["left"]:
            self.player_idx = (self.player_idx - 1) % MAX_PLAYERS
            self.message = ""
        if actions["right"]:
            self.player_idx = (self.player_idx + 1) % MAX_PLAYERS
            self.message = ""

        if actions["up"]:
            self.selected = (self.selected - 1) % TOTAL_ITEMS
        if actions["down"]:
            self.selected = (self.selected + 1) % TOTAL_ITEMS

        if actions["start"] or actions["space"]:
            if self.selected < RESET_IDX:
                self.listening = True
                self.game.last_keydown = None
            elif self.selected == RESET_IDX:
                self._reset_defaults()
        elif actions["escape"]:
            self.exit_state()

        self.game.reset_keys()

    def _rebind(self, idx, new_key):
        action = BINDABLE_ACTIONS[idx][0]
        for other_action, keys in self._bindings.items():
            if other_action != action and new_key in keys:
                keys.remove(new_key)
        self._bindings[action] = [new_key]
        self.game._build_key_maps()
        self.game.save_bindings()

    def _reset_defaults(self):
        defaults = self.game.default_bindings(self.player_idx)
        self.game.all_bindings[self.player_idx] = defaults
        self.game._build_key_maps()
        self.game.save_bindings()
        self.message = f"P{self.player_idx + 1} controls reset to defaults"
        self.message_timer = 2.0

    def _key_names(self, action):
        keys = self._bindings.get(action, [])
        if not keys:
            return "---"
        return ", ".join(pygame.key.name(k).upper() for k in keys)

    def render(self, display):
        display.blit(self.background, (0, 0))
        cx = self.game.GAME_WIDTH / 2
        col_label = cx - 130
        col_key = cx + 200

        self.game.draw_text_sized(
            display, "Controls", (255, 220, 60), cx, 40, 46,
        )

        # Player tabs
        tab_y = 85
        tab_w = 100
        total_tab_w = MAX_PLAYERS * tab_w + (MAX_PLAYERS - 1) * 10
        tab_start = cx - total_tab_w / 2 + tab_w / 2
        for i in range(MAX_PLAYERS):
            tx = tab_start + i * (tab_w + 10)
            if i == self.player_idx:
                color = (255, 255, 255)
                label = f"[ P{i + 1} ]"
            else:
                color = (100, 100, 100)
                label = f"  P{i + 1}  "
            self.game.draw_text_sized(display, label, color, tx, tab_y, 26)

        start_y = 125
        for i, (action, label) in enumerate(BINDABLE_ACTIONS):
            y = start_y + i * 40

            if i == self.selected and self.listening:
                color = (255, 255, 100)
                key_text = "Press a key..."
            elif i == self.selected:
                color = (255, 255, 255)
                key_text = self._key_names(action)
            else:
                color = (160, 160, 160)
                key_text = self._key_names(action)

            prefix = "> " if i == self.selected else "  "
            self.game.draw_text_sized(
                display, prefix + label, color, col_label, y, 26,
            )
            self.game.draw_text_sized(
                display, key_text, color, col_key, y, 26,
            )

        reset_y = start_y + len(BINDABLE_ACTIONS) * 40 + 15
        if self.selected == RESET_IDX:
            self.game.draw_text_sized(
                display, "> Reset Defaults", (255, 255, 255), cx, reset_y, 26,
            )
        else:
            self.game.draw_text_sized(
                display, "  Reset Defaults", (160, 160, 160), cx, reset_y, 26,
            )

        if self.message_timer > 0:
            self.game.draw_text_sized(
                display, self.message, (255, 200, 60), cx, reset_y + 45, 22,
            )

        foot_y = self.game.GAME_HEIGHT - 48
        self.game.draw_text_sized(
            display,
            "Left/Right: switch player  \u00b7  Enter: rebind  \u00b7  Escape: back",
            (120, 120, 120), cx, foot_y, 20,
        )
        self.game.draw_text_sized(
            display,
            "Enter/Escape and other players' keys are reserved.",
            (120, 120, 120), cx, foot_y + 22, 20,
        )
