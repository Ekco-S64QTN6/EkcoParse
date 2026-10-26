"""Mob respawn countdown timer panel for Project 1999."""

from textual.widgets import Static
from rich.markup import escape

from ekco_parse.models import Timer
from ekco_parse.ui.theme import (
    COLOR_CYAN,
    COLOR_GREEN,
    COLOR_AMBER,
    COLOR_RED,
    COLOR_MUTED,
    render_progress_bar,
)


class RespawnWidget(Static):
    """Color-coded mob respawn countdown timers sorted by soonest to pop."""

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
        lines = []

        for timer in sorted_respawns:
            rem = max(0.0, timer.remaining_seconds)
            time_str = self.format_respawn_time(rem)
            total = timer.total_seconds
            p_bar = render_progress_bar(rem, total, width=6, color=COLOR_AMBER)

            name = timer.name
            if len(name) > 18:
                name = name[:16] + ".."
            name_padded = f"{name:<18}"

            # Color coding: green (far), yellow (medium), red (soon/now)
            pct = rem / total if total > 0 else 0
            if rem <= 0:
                # Mob should be up NOW
                status = f"[bold {COLOR_RED}]◆ UP NOW![/]"
                time_styled = f"[bold {COLOR_RED}]{time_str:>6}[/]"
            elif pct <= 0.15:
                # Very soon (red) - last 15% of timer
                status = f"[bold {COLOR_RED}]● SOON[/]"
                time_styled = f"[bold {COLOR_RED}]{time_str:>6}[/]"
            elif pct <= 0.40:
                # Getting close (yellow)
                status = f"[bold {COLOR_AMBER}]● CLOSE[/]"
                time_styled = f"[bold {COLOR_AMBER}]{time_str:>6}[/]"
            else:
                # Plenty of time (green)
                status = f"[{COLOR_MUTED}]○ WAIT[/]"
                time_styled = f"[bold {COLOR_GREEN}]{time_str:>6}[/]"

            lines.append(f"[bold white]{name_padded}[/] {time_styled} {p_bar} {status}")

        self.update("\n".join(lines))
