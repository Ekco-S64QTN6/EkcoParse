"""Theme tokens, color palettes, and UI render utilities matching dwarffortress-antfarm."""

from rich.markup import escape


# dwarffortress-antfarm color tokens
COLOR_BG = "#05070D"            # Void dark screen background
COLOR_PANEL_BG = "#0D1120"      # Slate navy panel background
COLOR_CYAN = "#00F5FF"          # Primary accent / Column Left
COLOR_MAGENTA = "#FF2D95"       # Secondary accent / Column Right
COLOR_PURPLE = "#B64CFF"        # Tertiary / Header / Director accent
COLOR_GREEN = "#59FF8E"         # Success / Health / Avoidance
COLOR_AMBER = "#FFC857"         # Warning / In-progress / Buffs
COLOR_RED = "#FF4040"           # Danger / Raid Alert / Enrage
COLOR_MUTED = "grey37"
COLOR_DIM = "#505A70"
COLOR_WHITE = "#FFFFFF"

# Sparkline characters
SPARK_CHARS = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]


def render_progress_bar(value: float, max_value: float, width: int = 15, color: str = "cyan") -> str:
    """Render a block character progress bar: [bold #color]████[/][grey37]░░░░[/]."""
    if max_value <= 0:
        return f"[{COLOR_MUTED}]{'░' * width}[/]"

    percent = min(1.0, max(0.0, value / max_value))
    filled_len = int(percent * width)
    empty_len = width - filled_len

    block_char = "█"
    empty_char = "░"

    if color in ["pink", "magenta", "#FF2D95", COLOR_MAGENTA]:
        color_tag = f"bold {COLOR_MAGENTA}"
    elif color in ["yellow", "warning", "amber", "#FFC857", COLOR_AMBER]:
        color_tag = f"bold {COLOR_AMBER}"
    elif color in ["red", "danger", "#FF4040", COLOR_RED]:
        color_tag = f"bold {COLOR_RED}"
    elif color in ["green", "success", "#59FF8E", COLOR_GREEN]:
        color_tag = f"bold {COLOR_GREEN}"
    elif color in ["purple", "violet", "#B64CFF", COLOR_PURPLE]:
        color_tag = f"bold {COLOR_PURPLE}"
    else:
        color_tag = f"bold {COLOR_CYAN}"

    return f"[{color_tag}]{block_char * filled_len}[/][{COLOR_MUTED}]{empty_char * empty_len}[/]"


def render_sparkline(values: list, max_len: int = 16) -> str:
    """Render a unicode sparkline from numerical history."""
    if not values:
        return " " * max_len

    recent = values[-max_len:]
    low, high = min(recent), max(recent)
    span = max(1.0, float(high - low))

    out = []
    for val in recent:
        lvl = int(((val - low) / span) * (len(SPARK_CHARS) - 1))
        lvl = max(0, min(len(SPARK_CHARS) - 1, lvl))
        out.append(SPARK_CHARS[lvl])

    # Pad if fewer than max_len
    if len(out) < max_len:
        out = [" "] * (max_len - len(out)) + out

    return "".join(out)


def get_ascii_logo() -> str:
    """Stylized ASCII logo banner for Ekco Parse."""
    return (
        f"[bold {COLOR_CYAN}] ___ _  _____ ___ [/][bold {COLOR_MAGENTA}]  ___  _   ___ ___ ___ [/]\n"
        f"[bold {COLOR_CYAN}]| __| |/ / __/ _ \\[/][bold {COLOR_MAGENTA}] | _ \\/_\\ | _ \\ __| __|[/]\n"
        f"[bold {COLOR_CYAN}]| _|| ' < (_| (_) |[/][bold {COLOR_MAGENTA}] |  _/ _ \\|   /__\\| _| [/]\n"
        f"[bold {COLOR_CYAN}]|___|_|\\_\\___\\___/[/][bold {COLOR_MAGENTA}] |_|/_/ \\_\\_|_\\___|___|[/]"
    )


def get_map_logo() -> str:
    """Stylized ASCII logo banner for Ekco Map standalone window."""
    return (
        f"[bold {COLOR_GREEN}] ___ _  _____ [/][bold {COLOR_CYAN}]  __  __   _   ___ [/]\n"
        f"[bold {COLOR_GREEN}]| __| |/ / _ \\[/][bold {COLOR_CYAN}] |  \\/  | /_\\ | _ \\[/]\n"
        f"[bold {COLOR_GREEN}]| _|| ' < (_) |[/][bold {COLOR_CYAN}] | |\\/| |/ _ \\|  _/[/]\n"
        f"[bold {COLOR_GREEN}]|___|_|\\_\\___/[/][bold {COLOR_CYAN}] |_|  |_/_/ \\_\\_|  [/]"
    )
