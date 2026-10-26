"""Ultra-compact 1-line telemetry header (no banner)."""

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


class HeaderWidget(Static):
    """Minimal 1-line top status bar with zero banner art to maximize game visibility."""

    def update_header(
        self,
        character: str,
        server: str,
        zone: str,
        log_file: str,
        is_tailing: bool,
        active_target: str = "NONE",
        fight_duration: float = 0.0,
        encounter_dps: float = 0.0,
        total_damage: int = 0,
        audio_on: bool = True,
    ) -> None:
        tail_status = f"[bold {COLOR_GREEN}]● LIVE[/]" if is_tailing else f"[bold {COLOR_RED}]▲ SCAN[/]"

        if active_target and active_target not in ("NONE", "Unknown Target", "YOU"):
            # Combat mode: 1 line showing target & DPS
            content = (
                f"[bold {COLOR_CYAN}]EKCO[/] [bold {COLOR_RED}]▲ {escape(active_target)}[/]  "
                f"[bold {COLOR_GREEN}]{encounter_dps:.1f} DPS[/]  "
                f"[bold white]{fight_duration:.0f}s[/]  "
                f"[{COLOR_MUTED}]({total_damage:,} dmg)[/]  |  "
                f"{tail_status}"
            )
        else:
            # Standby mode: 1 line showing player, server, zone
            content = (
                f"[bold {COLOR_CYAN}]EKCO PARSE[/]  [bold #59FF8E]{escape(character)}[/]  "
                f"[{COLOR_AMBER}]{server.upper()}[/]  "
                f"[bold white]{escape(zone)}[/]  |  "
                f"{tail_status}"
            )

        self.update(content)
