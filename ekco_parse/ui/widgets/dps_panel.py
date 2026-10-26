"""GamParse-style live DPS meter and encounter breakdown widget."""

from textual.widgets import Static
from rich.markup import escape

from ekco_parse.models import Encounter
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


class DpsWidget(Static):
    """Ultra-compact live DPS meter and combat breakdown."""

    def on_mount(self) -> None:
        self.border_title = "COMBAT DPS"

    def update_encounter(self, encounter: Encounter | None, session_total_dmg: int = 0) -> None:
        if not encounter or not encounter.combatants:
            self.border_title = "COMBAT DPS"
            self.update("")
            return

        total_dmg = encounter.total_damage
        duration = encounter.duration_seconds
        enc_dps = encounter.total_dps

        self.border_title = f"FIGHT: {encounter.target} ({enc_dps:.1f} DPS)"

        rows = []
        ranked = sorted(
            encounter.combatants.values(),
            key=lambda c: c.damage_dealt,
            reverse=True,
        )

        for c in ranked[:5]:
            c_name = c.name
            if len(c_name) > 12:
                c_name = c_name[:10] + ".."
            c_padded = f"{c_name:<12}"

            dmg_str = f"{c.damage_dealt:,}"
            dps_val = c.damage_dealt / duration
            p_bar = render_progress_bar(c.damage_dealt, total_dmg, width=6, color=COLOR_CYAN if c.name == "You" else COLOR_MAGENTA)

            row = f"[bold white]{c_padded}[/] [bold {COLOR_GREEN}]{dps_val:>5.1f}[/] {p_bar} [{COLOR_MUTED}]{dmg_str}[/]"
            rows.append(row)

        self.update("\n".join(rows))
