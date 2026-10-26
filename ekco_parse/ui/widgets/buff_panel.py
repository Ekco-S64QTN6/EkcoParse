"""High-density active buffs and utilities running clock widget."""

from textual.widgets import Static
from rich.markup import escape

from ekco_parse.models import Timer
from ekco_parse.ui.theme import COLOR_GREEN, COLOR_AMBER, COLOR_RED


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
            self.border_title = "BUFFS"
            self.update("")
            return

        content_width = max(1, self.content_size.width or (self.size.width - 4) or 80)
        status_width = 8  # "EXPIRED!"
        lines = []
        for timer in sorted_buffs:
            rem = max(0.0, timer.remaining_seconds)
            time_str = self.format_buff_time(rem)
            time_width = max(7, len(time_str))
            # Keep full spell names; the old 18-character cap cut off valid names.
            name = timer.name

            if timer.remaining_seconds <= 0:
                status_text, status_color = "EXPIRED!", COLOR_RED
                time_styled = f"[bold {COLOR_RED}]{time_str:>{time_width}}[/]"
            elif rem <= 60.0:
                status_text, status_color = "RECAST!", COLOR_RED
                time_styled = f"[bold {COLOR_RED}]{time_str:>{time_width}}[/]"
            elif rem <= 180.0:
                status_text, status_color = "FADING", COLOR_AMBER
                time_styled = f"[bold {COLOR_AMBER}]{time_str:>{time_width}}[/]"
            else:
                status_text, status_color = "ACTIVE", COLOR_GREEN
                time_styled = f"[bold white]{time_str:>{time_width}}[/]"

            # Use whitespace instead of a colored progress bar, keeping the
            # status label aligned to the panel's right edge.
            gap_width = max(
                1,
                content_width - (len(name) + 1 + time_width + 1 + status_width),
            )
            status_tag = f"[bold {status_color}]{status_text:>{status_width}}[/]"
            lines.append(
                f"[bold white]{escape(name)}[/] {time_styled}{' ' * gap_width}{status_tag}"
            )

        self.update("\n".join(lines))
