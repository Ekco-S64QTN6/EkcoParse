"""Tank mitigation, avoidance statistics, and incoming damage panel."""

from textual.widgets import Static
from rich.markup import escape

from ekco_parse.models import CombatantStats, Encounter
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


class MitigationWidget(Static):
    """Monitors tank mitigation, defensive avoidance percentages, and incoming damage."""

    def on_mount(self) -> None:
        self.border_title = "TANK MITIGATION & DEFENSE"

    def update_mitigation(self, encounter: Encounter | None, player_stats: CombatantStats | None) -> None:
        if not encounter or not player_stats:
            self.update(
                f"  [{COLOR_MUTED}]▲ NO ACTIVE INCOMING DAMAGE[/]\n\n"
                f"  [{COLOR_GREEN}]• Mitigation Tracking:[/] Dodges, Parries, Blocks, Ripostes, Absorbed Dmg.\n"
                f"  [{COLOR_CYAN}]• Avoidance Metric:[/]    Calculates live defensive avoidance %."
            )
            return

        p = player_stats
        duration = encounter.duration_seconds
        dps_taken = p.damage_taken / duration if duration > 0 else 0.0

        total_defenses = p.dodges + p.parries + p.ripostes + p.blocks
        avoid_bar = render_progress_bar(p.avoidance_rate, 100.0, width=14, color=COLOR_GREEN)

        content = (
            f"[bold {COLOR_CYAN}]DAMAGE TAKEN:[/] [bold {COLOR_RED}]{p.damage_taken:,}[/]  |  "
            f"[bold {COLOR_CYAN}]HITS TAKEN:[/] [bold white]{p.hits_taken}[/]  |  "
            f"[bold {COLOR_CYAN}]INCOMING DPS:[/] [bold {COLOR_RED}]{dps_taken:.1f}[/]\n"
            f"[bold {COLOR_CYAN}]MAX HIT TAKEN:[/] [bold {COLOR_RED}]{p.max_hit_taken}[/]  |  "
            f"[bold {COLOR_CYAN}]HEALS RECEIVED:[/] [bold {COLOR_GREEN}]{p.healing_received:,}[/]\n"
            f"───────────────────────────────────────────────────────────────────\n"
            f"[bold {COLOR_GREEN}]AVOIDANCE RATE:[/] [bold white]{p.avoidance_rate:>5.1f}%[/]  {avoid_bar}\n"
            f"  [bold white]Dodges:[/] [bold {COLOR_GREEN}]{p.dodges}[/]  |  "
            f"[bold white]Parries:[/] [bold {COLOR_GREEN}]{p.parries}[/]  |  "
            f"[bold white]Blocks:[/] [bold {COLOR_GREEN}]{p.blocks}[/]  |  "
            f"[bold white]Ripostes:[/] [bold {COLOR_GREEN}]{p.ripostes}[/]"
        )
        self.update(content)
