#!/bin/bash
# ==============================================================================
# Ekco Parse - Desktop Companion Launcher for Project 1999 EverQuest
# ==============================================================================

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR" || exit 1

VENV_DIR="$BASE_DIR/.venv"
PY="$VENV_DIR/bin/python"

# 1. Initialize venv if missing
if [ ! -f "$PY" ]; then
    echo "[Ekco Parse] Initializing virtual environment with uv..."
    if command -v uv >/dev/null 2>&1; then
        uv venv "$VENV_DIR"
        uv pip install -r requirements.txt --python "$PY"
    else
        python3 -m venv "$VENV_DIR"
        "$VENV_DIR/bin/pip" install -r requirements.txt
    fi
fi

# 2. Terminal emulator detection
detect_terminal() {
    for t in kitty alacritty wezterm foot konsole xterm; do
        if command -v "$t" >/dev/null 2>&1; then
            echo "$t"
            return
        fi
    done
    echo ""
}

# Kitty overlay flags: transparent background, no padding, no decorations
# Fully transparent terminal background; Textual emits ANSI-default backgrounds
# too, so individual widget cells do not paint opaque black rectangles.
KITTY_OVERLAY_OPTS="-o background_opacity=0.0 -o window_padding_width=0 -o hide_window_decorations=no"

# 3. Argument routing
case "$1" in
    --overlay|-o)
        echo "[Ekco Parse] Starting Transparent Borderless Overlay..."
        TERM_EMU=$(detect_terminal)
        if [ "$TERM_EMU" = "kitty" ]; then
            exec kitty $KITTY_OVERLAY_OPTS --title "Ekco Parse" -- "$PY" -m ekco_parse.main "${@:2}"
        else
            exec "$PY" -m ekco_parse.main "${@:2}"
        fi
        ;;
    --map|-m)
        echo "[Ekco Parse] Starting Standalone Map Window..."
        TERM_EMU=$(detect_terminal)
        if [ "$TERM_EMU" = "kitty" ]; then
            exec kitty --title "Ekco Map GPS" -- "$PY" -m ekco_parse.main --map "${@:2}"
        else
            exec "$PY" -m ekco_parse.main --map "${@:2}"
        fi
        ;;
    --all|-a)
        TERM_EMU=$(detect_terminal)
        echo "[Ekco Parse] Launching companion overlay and map using $TERM_EMU..."
        if [ "$TERM_EMU" = "kitty" ]; then
            setsid kitty --title "Ekco Map GPS" -- "$PY" -m ekco_parse.main --map >/dev/null 2>&1 &
            exec kitty $KITTY_OVERLAY_OPTS --title "Ekco Parse" -- "$PY" -m ekco_parse.main "${@:2}"
        elif [ "$TERM_EMU" = "xterm" ]; then
            setsid xterm -title "Ekco Map GPS" -e "$PY" -m ekco_parse.main --map >/dev/null 2>&1 &
            exec "$PY" -m ekco_parse.main "${@:2}"
        else
            exec "$PY" -m ekco_parse.main "${@:2}"
        fi
        ;;
    --sim|-s)
        echo "[Ekco Parse] Starting Companion with realistic P99 log simulator..."
        exec "$PY" -m ekco_parse.main --simulate "${@:2}"
        ;;
    --test|-t)
        echo "[Ekco Parse] Running test suite..."
        exec "$PY" -m unittest discover -s tests -v
        ;;
    --help|-h)
        echo "Ekco Parse Launcher Usage:"
        echo "  ./run.sh           Run companion as transparent overlay (default)"
        echo "  ./run.sh --overlay Launch standalone transparent borderless overlay window"
        echo "  ./run.sh --map     Launch standalone radar vector map window"
        echo "  ./run.sh --all     Launch both companion overlay and radar map in separate windows"
        echo "  ./run.sh --sim     Run with realistic P99 log simulator"
        echo "  ./run.sh --test    Run automated unit test suite"
        echo ""
        echo "Window management: App auto-sets always-on-top via xdotool."
        echo "In kitty: transparent bg, no window decorations, no padding."
        echo "Any terminal: remove title bar/frame from your window manager."
        ;;
    *)
        # Default: run as overlay with kitty if available
        TERM_EMU=$(detect_terminal)
        if [ "$TERM_EMU" = "kitty" ]; then
            exec kitty $KITTY_OVERLAY_OPTS --title "Ekco Parse" -- "$PY" -m ekco_parse.main "$@"
        else
            exec "$PY" -m ekco_parse.main "$@"
        fi
        ;;
esac
