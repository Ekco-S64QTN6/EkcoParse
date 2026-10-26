"""Compact 1-line urgent alert ticker."""

from textual.widgets import Static
from rich.markup import escape

from ekco_parse.ui.theme import (
    COLOR_CYAN,
    COLOR_MAGENTA,
    COLOR_PURPLE,
    COLOR_GREEN,
    COLOR_AMBER,
    COLOR_RED,
    COLOR_MUTED,
)


class TickerWidget(Static):
    """1-line alert ticker: only shows text when there is an active alert."""

    def on_mount(self) -> None:
        self.border_title = "ALERT"

    def update_alerts(self, alerts: list[dict], last_log: str = "") -> None:
        if alerts:
            latest = alerts[0]
            cat = latest.get("category", "alert").upper()
            txt = escape(latest.get("text", ""))
            color = latest.get("color", COLOR_AMBER)
            t_str = latest.get("timestamp").strftime("%H:%M:%S") if latest.get("timestamp") else ""

            if cat == "RAID":
                self.update(f"[bold {COLOR_RED}]▲ RAID ({t_str}):[/] [bold white]{txt}[/]")
            elif "RECAST" in txt.upper() or cat == "DOT":
                self.update(f"[bold {COLOR_MAGENTA}]● ROTATION ({t_str}):[/] [bold white]{txt}[/]")
            else:
                self.update(f"[bold {color}]● ({t_str}):[/] [bold white]{txt}[/]")
        elif last_log:
            clean = escape(last_log.strip())
            if len(clean) > 45:
                clean = clean[:42] + ".."
            self.update(f"[{COLOR_MUTED}]{clean}[/]")
        else:
            self.update("")
