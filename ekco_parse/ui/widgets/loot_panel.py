"""Session kill counter, experience milestones, and loot ledger panel."""

from textual.widgets import Static
from rich.markup import escape

from ekco_parse.loot_engine import LootEngine
from ekco_parse.ui.theme import (
    COLOR_CYAN,
    COLOR_MAGENTA,
    COLOR_PURPLE,
    COLOR_GREEN,
    COLOR_AMBER,
    COLOR_RED,
    COLOR_MUTED,
)


class LootWidget(Static):
    """Displays slain mob counts, experience ticks per hour, and item loot history."""

    def on_mount(self) -> None:
        self.border_title = "KILL & LOOT LEDGER"

    def update_loot(self, engine: LootEngine) -> None:
        if engine.total_kills == 0 and engine.total_looted == 0 and engine.exp_ticks == 0:
            self.update(
                f"  [{COLOR_MUTED}]▲ NO MOBS SLAIN OR LOOT LOGGED THIS SESSION[/]\n\n"
                f"  [{COLOR_GREEN}]• Kill Counter:[/] Tracks slain mobs, exp milestones, and kills/hour.\n"
                f"  [{COLOR_AMBER}]• Loot Ledger:[/]  Parses '--You have looted a ...--' item drops."
            )
            return

        k_hr = engine.kills_per_hour
        exp_hr = engine.exp_per_hour

        summary = (
            f"[bold {COLOR_CYAN}]KILLS:[/] [bold white]{engine.total_kills}[/] ([bold {COLOR_GREEN}]{k_hr:.1f}/hr[/]) | "
            f"[bold {COLOR_CYAN}]EXP TICKS:[/] [bold {COLOR_AMBER}]{engine.exp_ticks}[/] ([bold {COLOR_GREEN}]{exp_hr:.1f}/hr[/]) | "
            f"[bold {COLOR_CYAN}]LOOTED:[/] [bold white]{engine.total_looted}[/]\n"
            f"───────────────────────────────────────────────────────────────────"
        )

        # Recent loot list
        loot_lines = [f"[bold {COLOR_AMBER}]RECENT LOOT ITEMS:[/]\n"]
        if engine.loot_records:
            for record in list(engine.loot_records)[:5]:
                t_str = record.timestamp.strftime("%H:%M:%S")
                looter = escape(record.looter)
                item = escape(record.item)
                loot_lines.append(f"  [{COLOR_MUTED}]{t_str}[/] [bold {COLOR_CYAN}]{looter}[/] looted [bold white]{item}[/]")
        else:
            loot_lines.append(f"  [{COLOR_MUTED}]No items looted yet.[/]")

        # Top slain mobs
        mob_lines = [f"\n[bold {COLOR_MAGENTA}]TOP SLAIN MOBS:[/]\n"]
        top_mobs = engine.get_top_mobs(limit=4)
        if top_mobs:
            for mob, count in top_mobs:
                m_str = escape(mob)
                mob_lines.append(f"  [bold white]{count:>3}x[/]  [bold {COLOR_PURPLE}]{m_str}[/]")
        else:
            mob_lines.append(f"  [{COLOR_MUTED}]No mobs recorded yet.[/]")

        content = f"{summary}\n" + "\n".join(loot_lines) + "\n" + "\n".join(mob_lines)
        self.update(content)
