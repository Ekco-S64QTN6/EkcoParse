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

        rows = [
            f"[{COLOR_MUTED}]{'PLAYER':<10} {'DPS':>5} {'DAMAGE':>6} {'SHARE':>5} {'ACC':>4} {'CRIT':>4} {'MAX':>4}[/]"
        ]
        ranked = sorted(
            encounter.combatants.values(),
            key=lambda c: c.damage_dealt,
            reverse=True,
        )

        for c in ranked[:4]:
            c_name = c.name
            if len(c_name) > 10:
                c_name = c_name[:8] + ".."
            c_padded = f"{c_name:<10}"

            dps_val = c.damage_dealt / duration if duration > 0 else 0.0
            share_pct = (c.damage_dealt / total_dmg * 100.0) if total_dmg > 0 else 0.0
            damage_str = f"{c.damage_dealt:>6,}"
            accuracy_str = f"{c.accuracy:>3.0f}%"
            crit_str = f"{c.crit_rate:>3.0f}%"

            row = (
                f"[bold white]{c_padded}[/] "
                f"[bold {COLOR_GREEN}]{dps_val:>5.1f}[/] "
                f"[{COLOR_MUTED}]{damage_str}[/] "
                f"[bold {COLOR_CYAN}]{share_pct:>4.1f}%[/] "
                f"[bold {COLOR_GREEN}]{accuracy_str}[/] "
                f"[bold {COLOR_AMBER}]{crit_str}[/] "
                f"[bold white]{c.max_hit:>4}[/]"
            )
            rows.append(row)

        self.update("\n".join(rows))
