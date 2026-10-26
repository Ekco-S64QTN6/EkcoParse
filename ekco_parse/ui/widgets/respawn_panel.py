"""Mob respawn countdown timer panel for Project 1999."""

from rich.markup import escape
from textual.widgets import Static

from ekco_parse.models import Timer
from ekco_parse.ui.theme import COLOR_GREEN, COLOR_AMBER, COLOR_RED, COLOR_MUTED


class RespawnWidget(Static):
    """Compact mob respawn countdowns sorted by soonest to pop."""

    def on_mount(self) -> None:
        self.border_title = "RESPAWNS"

    def format_respawn_time(self, seconds: float) -> str:
        if seconds <= 0:
            return "NOW!"
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"

    def update_respawns(self, sorted_respawns: list[Timer]) -> None:
        count = len(sorted_respawns)
        if not sorted_respawns:
            self.border_title = "RESPAWNS"
            self.update("")
            return

        self.border_title = f"RESPAWNS ({count})"
        content_width = max(1, self.content_size.width or (self.size.width - 4) or 80)
        time_width = 6
        status_width = 9
        lines = []

        for timer in sorted_respawns:
            rem = max(0.0, timer.remaining_seconds)
            time_str = self.format_respawn_time(rem)

            # Color the countdown and short status only; avoid distracting bars.
            pct = rem / timer.total_seconds if timer.total_seconds > 0 else 0
            if rem <= 0:
                status_text, status_color = "◆ UP NOW!", COLOR_RED
                time_styled = f"[bold {COLOR_RED}]{time_str:>{time_width}}[/]"
            elif pct <= 0.15:
                status_text, status_color = "● SOON", COLOR_RED
                time_styled = f"[bold {COLOR_RED}]{time_str:>{time_width}}[/]"
            elif pct <= 0.40:
                status_text, status_color = "● CLOSE", COLOR_AMBER
                time_styled = f"[bold {COLOR_AMBER}]{time_str:>{time_width}}[/]"
            else:
                status_text, status_color = "○ WAIT", COLOR_MUTED
                time_styled = f"[bold {COLOR_GREEN}]{time_str:>{time_width}}[/]"

            name = timer.name
            gap_width = max(
                1,
                content_width - (len(name) + 1 + time_width + 1 + status_width),
            )
            status_tag = f"[bold {status_color}]{status_text:>{status_width}}[/]"
            lines.append(
                f"[bold white]{escape(name)}[/] {time_styled}{' ' * gap_width}{status_tag}"
            )

        self.update("\n".join(lines))
