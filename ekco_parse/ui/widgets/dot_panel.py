"""Damage Over Time (DoT) and CC running clock panel for Project 1999."""

from textual.widgets import Static
from rich.markup import escape

from ekco_parse.models import Timer
from ekco_parse.ui.theme import COLOR_AMBER, COLOR_GREEN, COLOR_RED


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
        # content_size excludes borders and padding, so this aligns the rightmost
        # status column with the panel's actual inner edge.
        content_width = max(1, self.content_size.width or (self.size.width - 4) or 80)
        status_width = 11  # "RECAST SOON" / "RECAST NOW!"
        lines = []

        for timer in sorted_dots:
            rem = max(0.0, timer.remaining_seconds)
            clock_plain = self.format_clock(rem)
            spell_name = timer.name
            target_str = f"({timer.target})" if timer.target and timer.target != "Self" else ""
            label = f"{spell_name} {target_str}".strip()

            if timer.remaining_seconds <= 0:
                status_text, status_color = "RECAST NOW!", COLOR_RED
                clock_str = f"[bold {COLOR_RED}]{clock_plain}[/]"
            elif rem <= 10.0:
                status_text, status_color = "RECAST SOON", COLOR_RED
                clock_str = f"[bold {COLOR_RED}]{clock_plain}[/]"
            elif rem <= 20.0:
                status_text, status_color = "LOW", COLOR_AMBER
                clock_str = f"[bold {COLOR_AMBER}]{clock_plain}[/]"
            else:
                status_text, status_color = "ACTIVE", COLOR_GREEN
                clock_str = f"[bold white]{clock_plain}[/]"

            # With the progress bar removed, use the freed space to keep the
            # status column at the right edge of the panel.
            gap_width = max(
                1,
                content_width - (len(label) + 1 + len(clock_plain) + 1 + status_width),
            )
            status_tag = f"[bold {status_color}]{status_text:>{status_width}}[/]"
            lines.append(
                f"[bold white]{escape(label)}[/] {clock_str}{' ' * gap_width}{status_tag}"
            )

        self.update("\n".join(lines))
