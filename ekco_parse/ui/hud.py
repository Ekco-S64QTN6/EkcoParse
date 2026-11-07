"""Click-through game HUD (Qt).

A display-only overlay: frameless, transparent, never takes focus, and marked
``WindowTransparentForInput`` so the compositor gives it an empty input region —
every mouse click goes straight through to the game underneath, like a classic
Windows game overlay. Kitty cannot do this, which is why the Textual dashboard
always swallowed clicks.

Wayland does not let clients position or raise themselves; placement and
always-on-top come from a KWin window rule matching the app id ``ekco-hud``.

Window decoration / interaction is configurable via the ``hud`` section of
``config.yaml``:

    hud:
      frameless: true        # false -> show title bar + borders
      always_on_top: true
      click_through: true    # false -> HUD (and its title bar) accept mouse input
"""

import os
import sys
import time
from typing import List, Optional

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QWidget

from ekco_parse.config import Config, load_config
from ekco_parse.models import Timer
from ekco_parse.session import LogSession
from ekco_parse.spells import SPELL_DB

APP_ID = "ekco-hud"
GAME_PROCESS = "eqgame.exe"


def game_running() -> bool:
    """True if the EverQuest client (under Wine) is running."""
    try:
        for pid in os.listdir("/proc"):
            if pid.isdigit():
                try:
                    with open(f"/proc/{pid}/comm") as f:
                        if f.read().strip() == GAME_PROCESS:
                            return True
                except OSError:
                    continue
    except OSError:
        pass
    return False


def fmt_time(seconds: float) -> str:
    s = max(0, int(round(seconds)))
    if s >= 3600:
        return f"{s // 3600}h{(s % 3600) // 60:02d}"
    return f"{s // 60}:{s % 60:02d}"


class HudWindow(QWidget):
    def __init__(self, config: Config):
        super().__init__()
        hud = config.raw.get("hud", {}) or {}
        self.width_px = int(hud.get("width", 300))
        self.row_h = int(hud.get("row_height", 22))
        self.bg_alpha = int(255 * float(hud.get("background_opacity", 0.55)))
        self.max_rows = int(hud.get("max_rows", 14))
        self.show_dps = bool(hud.get("show_dps", True))
        self.show_respawns = bool(hud.get("show_respawns", True))
        self.dps_rows = int(hud.get("dps_rows", 4))  # top combatants, like the old panel
        # Hide over the desktop when the game is closed; reappear when it runs.
        self.follow_game = bool(hud.get("hide_when_game_closed", True))

        # ── window decoration / interaction toggles ──────────────────────
        # Defaults preserve the original hardcoded behaviour.
        self.frameless = bool(hud.get("frameless", True))
        self.always_on_top = bool(hud.get("always_on_top", True))
        self.click_through = bool(hud.get("click_through", True))

        self._last_game_check = 0.0
        self.font = QFont(hud.get("font_family", "Maple Mono NF"), int(hud.get("font_size", 10)))
        self.font.setStyleStrategy(QFont.PreferAntialias)
        self.small = QFont(self.font)
        self.small.setPointSize(max(7, self.font.pointSize() - 2))

        self.setWindowTitle("Ekco HUD")
        self._apply_window_flags()

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        # Mouse transparency is only needed for the click-through HUD. When the
        # user turns click_through off (so they can drag the title bar), the
        # window must receive normal mouse events.
        self.setAttribute(Qt.WA_TransparentForMouseEvents, self.click_through)
        self.setFocusPolicy(Qt.NoFocus)
        # Fixed size, rows packed from the top. Resizing per row count made KWin
        # keep the window's centre, so dropping out of combat (fewer rows) slid
        # the buffs down the screen. The window is transparent and click-through,
        # so the unused space below the rows is invisible.
        self.setFixedSize(self.width_px, self.row_h * self.max_rows + 8)

        self.session = LogSession(config)
        self.session.start()
        self._last = time.time()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(int(1000 * config.tick_interval_sec))

    # ── window flags ─────────────────────────────────────────────────────
    def _apply_window_flags(self) -> None:
        """Build window flags from the config toggles.

        Must be called before show(); changing flags on a visible window
        requires re-showing it, which we avoid by only doing this at init.
        """
        flags = Qt.Window
        if self.frameless:
            flags |= Qt.FramelessWindowHint
        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        if self.click_through:
            flags |= Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput
        self.setWindowFlags(flags)

    # ── data ─────────────────────────────────────────────────────────────
    def _tick(self) -> None:
        now = time.time()
        self.session.tick(max(0.01, now - self._last))
        self._last = now
        self.session.poll()
        if self.follow_game and now - self._last_game_check >= 3.0:
            self._last_game_check = now
            running = game_running()
            if running and not self.isVisible():
                self.show()
            elif not running and self.isVisible():
                self.hide()
        self.update()

    def _rows(self) -> List[tuple]:
        te = self.session.timer_engine
        rows: List[tuple] = []
        enc = self.session.dps_engine.active_encounter
        if self.show_dps and enc and enc.total_damage:
            rows.append(("dps", enc))
            ranked = sorted(enc.combatants.values(), key=lambda c: c.damage_dealt, reverse=True)
            for c in [c for c in ranked if c.damage_dealt > 0][: self.dps_rows]:
                rows.append(("combatant", (c, enc)))
        for t in te.get_sorted_dots():
            rows.append(("timer", t))
        for t in te.get_sorted_buffs():
            rows.append(("timer", t))
        if self.show_respawns:
            for t in te.get_sorted_respawns()[:3]:
                rows.append(("timer", t))
        return rows[: self.max_rows]

    # ── drawing ──────────────────────────────────────────────────────────
    def _outlined_text(self, p: QPainter, x: float, y: float, text: str, color: QColor, font: QFont) -> None:
        path = QPainterPath()
        path.addText(x, y, font, text)
        p.setPen(QPen(QColor(0, 0, 0, 230), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawPath(path)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        fm = QFontMetrics(self.font)
        y = 4.0
        for kind, item in self._rows():
            rect = QRectF(2, y, self.width_px - 4, self.row_h - 3)
            if kind == "dps":
                self._draw_dps(p, rect, item, fm)
            elif kind == "combatant":
                self._draw_combatant(p, rect, item, fm)
            else:
                self._draw_timer(p, rect, item, fm)
            y += self.row_h
        p.end()

    def _draw_dps(self, p: QPainter, rect: QRectF, enc, fm: QFontMetrics) -> None:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(10, 10, 16, self.bg_alpha))
        p.drawRoundedRect(rect, 4, 4)
        base = rect.y() + (rect.height() + fm.ascent() - fm.descent()) / 2
        target = enc.target if len(enc.target) <= 22 else enc.target[:21] + "…"
        self._outlined_text(p, rect.x() + 6, base, f"DPS {enc.total_dps:,.0f}", QColor("#FFC857"), self.font)
        self._outlined_text(p, rect.x() + 96, base, target, QColor("#E8E8F0"), self.font)
        right = fmt_time(enc.duration_seconds)
        self._outlined_text(p, rect.right() - fm.horizontalAdvance(right) - 6, base, right, QColor("#A0A0B0"), self.font)

    def _draw_combatant(self, p: QPainter, rect: QRectF, item, fm: QFontMetrics) -> None:
        c, enc = item
        share = c.damage_dealt / enc.total_damage if enc.total_damage else 0.0
        dps = c.damage_dealt / enc.duration_seconds if enc.duration_seconds else 0.0
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(10, 10, 16, self.bg_alpha))
        p.drawRoundedRect(rect, 4, 4)
        p.setBrush(QColor(89, 255, 142, 70))
        p.drawRoundedRect(QRectF(rect.x(), rect.y(), rect.width() * share, rect.height()), 4, 4)
        base = rect.y() + (rect.height() + fm.ascent() - fm.descent()) / 2
        right = f"{dps:,.0f}  {share * 100:3.0f}%"
        right_w = fm.horizontalAdvance(right)
        name = fm.elidedText(c.name, Qt.ElideRight, int(rect.width() - right_w - 24))
        self._outlined_text(p, rect.x() + 14, base, name, QColor("#E8E8F0"), self.small)
        self._outlined_text(p, rect.right() - right_w - 6, base, right, QColor("#59FF8E"), self.font)

    def _draw_timer(self, p: QPainter, rect: QRectF, t: Timer, fm: QFontMetrics) -> None:
        color = QColor(t.color or "#00F5FF")
        sdef = SPELL_DB.lookup_by_name(t.name)
        warn_at = sdef.recast_warning_seconds if sdef else 10.0
        expired = t.remaining_seconds <= 0
        warning = not expired and t.remaining_seconds <= warn_at
        blink_on = int(time.time() * 2) % 2 == 0

        # backing plate + progress fill
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(10, 10, 16, self.bg_alpha))
        p.drawRoundedRect(rect, 4, 4)
        fill = QColor(color)
        fill.setAlpha(110 if not (warning and blink_on) else 190)
        w = rect.width() * (t.progress_pct if not expired else 1.0)
        if expired:
            fill = QColor(255, 64, 64, 170 if blink_on else 90)
        p.setBrush(fill)
        p.drawRoundedRect(QRectF(rect.x(), rect.y(), w, rect.height()), 4, 4)

        base = rect.y() + (rect.height() + fm.ascent() - fm.descent()) / 2
        right = "RECAST" if expired else fmt_time(t.remaining_seconds)
        right_w = fm.horizontalAdvance(right)
        label = t.name
        tgt = (t.target or "").strip()
        if t.category == "respawn":
            label = f"↻ {t.name}"
        elif tgt and tgt.casefold() not in ("self", "pet", "unknown target"):
            label = f"{t.name} › {tgt}"
        avail = rect.width() - right_w - 18
        label = fm.elidedText(label, Qt.ElideRight, int(avail))
        self._outlined_text(p, rect.x() + 6, base, label, QColor("#FFFFFF"), self.font)
        self._outlined_text(p, rect.right() - right_w - 6, base, right,
                            QColor("#FF6060") if expired or warning else QColor("#FFFFFF"), self.font)


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    QGuiApplication.setDesktopFileName(APP_ID)  # Wayland app_id -> KWin rule match
    app = QApplication(argv)
    app.setApplicationName(APP_ID)
    config_path = None
    if "--config" in argv:
        config_path = argv[argv.index("--config") + 1]
    hud = HudWindow(load_config(config_path))
    hud.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
