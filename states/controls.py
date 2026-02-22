import pygame
from states.state import State
from Game import BINDABLE_ACTIONS, RESERVED_KEYS


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
        self.listening = False
        self.message = ""
        self.message_timer = 0
        self.game.reset_keys()

    def update(self, delta_time, actions):
        if self.message_timer > 0:
            self.message_timer -= delta_time

        if self.listening:
            key = self.game.last_keydown
            if key is not None:
                self.game.last_keydown = None
                if key == pygame.K_ESCAPE:
                    self.listening = False
                elif key in RESERVED_KEYS:
                    self.message = "That key is reserved!"
                    self.message_timer = 2.0
                else:
                    self._rebind(self.selected, key)
                    self.listening = False
            self.game.reset_keys()
            return

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
        for other_action, keys in self.game.bindings.items():
            if other_action != action and new_key in keys:
                keys.remove(new_key)
        self.game.bindings[action] = [new_key]
        self.game._build_key_maps()
        self.game.save_bindings()

    def _reset_defaults(self):
        self.game.bindings = self.game.default_bindings()
        self.game._build_key_maps()
        self.game.save_bindings()
        self.message = "Controls reset to defaults"
        self.message_timer = 2.0

    def _key_names(self, action):
        keys = self.game.bindings.get(action, [])
        if not keys:
            return "---"
        return ", ".join(pygame.key.name(k).upper() for k in keys)

    def render(self, display):
        display.blit(self.background, (0, 0))
        cx = self.game.GAME_WIDTH / 2
        col_label = cx - 130
        col_key = cx + 200

        self.game.draw_text_sized(
            display, "Controls", (255, 220, 60), cx, 50, 46,
        )

        start_y = 130
        for i, (action, label) in enumerate(BINDABLE_ACTIONS):
            y = start_y + i * 45

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
                display, prefix + label, color, col_label, y, 28,
            )
            self.game.draw_text_sized(
                display, key_text, color, col_key, y, 28,
            )

        reset_y = start_y + len(BINDABLE_ACTIONS) * 45 + 20
        if self.selected == RESET_IDX:
            self.game.draw_text_sized(
                display, "> Reset Defaults", (255, 255, 255), cx, reset_y, 28,
            )
        else:
            self.game.draw_text_sized(
                display, "  Reset Defaults", (160, 160, 160), cx, reset_y, 28,
            )

        if self.message_timer > 0:
            self.game.draw_text_sized(
                display, self.message, (255, 200, 60), cx, reset_y + 50, 24,
            )

        foot_y = self.game.GAME_HEIGHT - 55
        self.game.draw_text_sized(
            display,
            "Arrow keys, Enter, and Escape are always active.",
            (120, 120, 120), cx, foot_y, 20,
        )
        self.game.draw_text_sized(
            display,
            "Enter to rebind \u00b7 Escape to go back",
            (120, 120, 120), cx, foot_y + 28, 20,
        )
