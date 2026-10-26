"""Damage Over Time (DoT) and CC running clock panel for Project 1999."""

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


class DotClockWidget(Static):
    """Running clock display for offensive DoTs and CC, strictly sorted by time to fade."""

    def on_mount(self) -> None:
        self.border_title = "DoTs & CC"

    def format_clock(self, seconds: float) -> str:
        if seconds <= 0:
            return "00:00"
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"

    def update_dots(self, sorted_dots: list[Timer]) -> None:
        count = len(sorted_dots)
        if not sorted_dots:
            self.border_title = "DoTs"
            self.update("")
            return

        self.border_title = f"DoT ROTATIONS ({count})"
        lines = []

        for timer in sorted_dots:
            rem = max(0.0, timer.remaining_seconds)
            clock_str = self.format_clock(rem)
            total = timer.total_seconds
            p_bar = render_progress_bar(rem, total, width=8, color=timer.color)

            spell_name = timer.name
            target_str = f"({timer.target})" if timer.target and timer.target != "Self" else ""
            label = f"{spell_name} {target_str}".strip()
            if len(label) > 18:
                label = label[:16] + ".."
            label_padded = f"{label:<18}"

            if timer.remaining_seconds <= 0:
                status_tag = f"[bold {COLOR_RED}]RECAST NOW![/]"
                clock_str = f"[bold {COLOR_RED}]{clock_str}[/]"
            elif rem <= 10.0:
                status_tag = f"[bold {COLOR_RED}]RECAST SOON[/]"
                clock_str = f"[bold {COLOR_RED}]{clock_str}[/]"
            elif rem <= 20.0:
                status_tag = f"[bold {COLOR_AMBER}]LOW[/]"
                clock_str = f"[bold {COLOR_AMBER}]{clock_str}[/]"
            else:
                status_tag = f"[bold {COLOR_GREEN}]ACTIVE[/]"
                clock_str = f"[bold white]{clock_str}[/]"

            lines.append(f"[bold white]{label_padded}[/] {clock_str} {p_bar} {status_tag}")

        self.update("\n".join(lines))
