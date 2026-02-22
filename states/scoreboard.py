import pygame
from states.state import State


class Scoreboard(State):
    def __init__(self, game):
        State.__init__(self, game)
        self.game.reset_keys()

    def update(self, delta_time, actions):
        if actions["escape"] or actions["start"] or actions["space"]:
            self.exit_state()
        self.game.reset_keys()

    def render(self, display):
        display.fill((15, 15, 30))
        cx = self.game.GAME_WIDTH / 2
        self.game.draw_text_sized(display, "Top 10 Scores", (255, 220, 60), cx, 50, 44)

        scores = self.game.high_scores
        if not scores:
            self.game.draw_text_sized(
                display, "No scores yet. Go play!", (160, 160, 160), cx, 200, 30
            )
        else:
            header_y = 110
            self.game.draw_text_sized(
                display, "#     Kills     Time", (180, 180, 255), cx, header_y, 28
            )
            for i, entry in enumerate(scores):
                y = header_y + 40 + i * 38
                rank = f"{i + 1}."
                kills = str(entry.get("kills", 0))
                time_s = f"{entry.get('time', 0)}s"
                line = f"{rank:<4}  {kills:>6} kills   {time_s:>6}"
                color = (255, 255, 255) if i < 3 else (180, 180, 180)
                self.game.draw_text_sized(display, line, color, cx, y, 26)

        self.game.draw_text_sized(
            display,
            "Press Escape / Space to go back",
            (120, 120, 120),
            cx,
            self.game.GAME_HEIGHT - 40,
            24,
        )
