"""High-density active buffs and utilities running clock widget."""

from textual.widgets import Static
from rich.markup import escape

from ekco_parse.models import Timer
from ekco_parse.ui.theme import (
    COLOR_CYAN,
    COLOR_MAGENTA,
    COLOR_PURPLE,
    COLOR_GREEN,
    COLOR_AMBER,
    COLOR_RED,
    COLOR_MUTED,
    render_progress_bar,
)


class BuffClockWidget(Static):
    """Ultra-clean, single-line running clock list for active buffs and utilities."""

    def on_mount(self) -> None:
        self.border_title = "BUFFS"

    def format_buff_time(self, seconds: float) -> str:
        if seconds <= 0:
            return "00:00"
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h}h {m:02d}m"
        if m > 0:
            return f"{m:02d}m {s:02d}s"
        return f"{s:02d}s"

    def update_buffs(self, sorted_buffs: list[Timer]) -> None:
        count = len(sorted_buffs)
        self.border_title = f"BUFFS ({count}/15)"

        if not sorted_buffs:
            self.border_title = f"BUFFS"
            self.update("")
            return

        lines = []
        for timer in sorted_buffs:
            rem = max(0.0, timer.remaining_seconds)
            time_str = self.format_buff_time(rem)
            total = timer.total_seconds
            p_bar = render_progress_bar(rem, total, width=8, color=timer.color)

            name = timer.name
            if len(name) > 18:
                name = name[:16] + ".."
            name_padded = f"{name:<18}"

            if timer.remaining_seconds <= 0:
                status_tag = f"[bold {COLOR_RED}]EXPIRED![/]"
                time_styled = f"[bold {COLOR_RED}]{time_str:>7}[/]"
            elif rem <= 60.0:
                status_tag = f"[bold {COLOR_RED}]RECAST![/]"
                time_styled = f"[bold {COLOR_RED}]{time_str:>7}[/]"
            elif rem <= 180.0:
                status_tag = f"[bold {COLOR_AMBER}]FADING[/]"
                time_styled = f"[bold {COLOR_AMBER}]{time_str:>7}[/]"
            else:
                status_tag = f"[bold {COLOR_GREEN}]ACTIVE[/]"
                time_styled = f"[bold white]{time_str:>7}[/]"

            lines.append(f"[bold white]{name_padded}[/] {time_styled} {p_bar} {status_tag}")

        self.update("\n".join(lines))
