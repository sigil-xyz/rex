"""Floating pill indicator for Rex.

Two modes:
  rex-indicator          — start the GTK4 overlay daemon (blocks)
  rex-indicator show <state>  — send state to running daemon
  rex-indicator hide          — hide the overlay
  rex-indicator quit          — stop the daemon

States: listening, thinking, done, error

The daemon listens on $XDG_RUNTIME_DIR/rex-indicator.sock.
Rex daemon sends updates via the async_show() / async_hide() helpers.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_SOCKET_FILENAME = "rex-indicator.sock"


def _socket_path() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    return Path(runtime) / _SOCKET_FILENAME


# ---------------------------------------------------------------------------
# Sync client  (CLI usage: rex-indicator show listening)
# ---------------------------------------------------------------------------


def _send(command: str, timeout: float = 0.3) -> bool:
    path = _socket_path()
    if not path.exists():
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect(str(path))
            sock.sendall((command + "\n").encode())
        return True
    except OSError:
        return False


def show(state: str) -> bool:
    return _send(f"show {state}")


def hide() -> bool:
    return _send("hide")


# ---------------------------------------------------------------------------
# Async client  (used by RexDaemon — non-blocking, fire-and-forget)
# ---------------------------------------------------------------------------


async def async_show(state: str) -> None:
    path = str(_socket_path())
    try:
        _, writer = await asyncio.wait_for(asyncio.open_unix_connection(path), timeout=0.05)
        writer.write(f"show {state}\n".encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass  # indicator not running — silently skip


async def async_hide() -> None:
    path = str(_socket_path())
    try:
        _, writer = await asyncio.wait_for(asyncio.open_unix_connection(path), timeout=0.05)
        writer.write(b"hide\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Daemon (GTK4 layer-shell overlay process)
# ---------------------------------------------------------------------------

_CSS = b"""
window {
    background: transparent;
}

.pill {
    background-color: rgba(26, 27, 38, 0.96);
    border-radius: 100px;
    border: 1px solid rgba(61, 89, 161, 0.75);
    padding: 12px 24px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
}

.pill-label {
    color: #c0caf5;
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.02em;
}

spinner {
    color: #7aa2f7;
    -gtk-icon-size: 14px;
}

.status-dot {
    min-width: 10px;
    min-height: 10px;
    border-radius: 50%;
}

.dot-listening { background-color: #f7768e; }
.dot-done      { background-color: #9ece6a; }
.dot-error     { background-color: #e0af68; }
"""

# (label, dot-css-class)  None dot-class → use spinner
_STATES: dict[str, tuple[str, str | None]] = {
    "listening": ("Listening…", "dot-listening"),
    "thinking": ("Thinking…", None),
    "done": ("Done", "dot-done"),
    "error": ("Error", "dot-error"),
}

_AUTO_DISMISS_MS: dict[str, int] = {
    "done": 1500,
    "error": 3000,
}


def _ensure_layer_shell_preloaded() -> None:
    """Re-exec with LD_PRELOAD if gtk4-layer-shell wasn't linked first.

    The library must appear before libwayland-client in the dynamic linker's
    load order, or layer-shell protocol negotiation silently fails at runtime.
    Re-execing with LD_PRELOAD is the recommended workaround per the upstream
    docs at https://github.com/wmww/gtk4-layer-shell/blob/main/linking.md
    """
    lib = "/usr/lib/libgtk4-layer-shell.so.0"
    preload = os.environ.get("LD_PRELOAD", "")
    if lib not in preload and Path(lib).exists():
        os.environ["LD_PRELOAD"] = f"{lib}:{preload}".strip(":")
        os.execv(sys.executable, [sys.executable] + sys.argv)


def _run_daemon() -> None:
    _ensure_layer_shell_preloaded()

    try:
        import gi

        gi.require_version("Gdk", "4.0")
        gi.require_version("Gtk", "4.0")
        gi.require_version("Gtk4LayerShell", "1.0")
        from gi.repository import Gdk, GLib, Gtk, Gtk4LayerShell
    except (ImportError, ValueError) as exc:
        sys.exit(
            f"rex-indicator: missing dependency — {exc}\n"
            "  install: sudo pacman -S gtk4 gtk4-layer-shell python-gobject"
        )

    import importlib.util

    _HAVE_CAIRO = importlib.util.find_spec("cairo") is not None

    class PillWindow(Gtk.ApplicationWindow):  # type: ignore[misc]
        def __init__(self, app: Gtk.Application) -> None:
            super().__init__(application=app)

            # ── Layer shell ──────────────────────────────────────────────
            Gtk4LayerShell.init_for_window(self)
            Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
            Gtk4LayerShell.set_namespace(self, "rex-indicator")
            Gtk4LayerShell.set_exclusive_zone(self, 0)
            Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)
            # Anchor top only → compositor centres horizontally
            Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, True)
            Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.LEFT, False)
            Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, False)
            Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.BOTTOM, False)

            self.set_decorated(False)
            self.set_resizable(False)

            # ── Widgets ──────────────────────────────────────────────────
            self._dot = Gtk.Box()
            self._dot.add_css_class("status-dot")
            self._dot.set_size_request(10, 10)
            self._dot.set_valign(Gtk.Align.CENTER)

            self._spinner = Gtk.Spinner()
            self._spinner.set_size_request(14, 14)
            self._spinner.set_valign(Gtk.Align.CENTER)

            self._label = Gtk.Label()
            self._label.add_css_class("pill-label")
            self._label.set_valign(Gtk.Align.CENTER)

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.set_valign(Gtk.Align.CENTER)
            row.append(self._dot)
            row.append(self._spinner)
            row.append(self._label)

            pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            pill.add_css_class("pill")
            pill.set_halign(Gtk.Align.CENTER)
            pill.append(row)

            self.set_child(pill)

            self._dot.set_visible(False)
            self._spinner.set_visible(False)
            self._dismiss_source: int | None = None

            self.connect("realize", self._on_realize)
            self.set_visible(False)

        def _on_realize(self, *_: object) -> None:
            # Set top margin = 35% of primary monitor height
            display = Gdk.Display.get_default()
            if display is not None:
                monitors = display.get_monitors()
                if monitors.get_n_items() > 0:
                    monitor = monitors.get_item(0)
                    if monitor is not None:
                        h = monitor.get_geometry().height
                        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.TOP, int(h * 0.35))

            # Input passthrough — empty cairo region means no pointer/touch events
            if _HAVE_CAIRO:
                import cairo

                surface = self.get_surface()
                if surface is not None:
                    surface.set_input_region(cairo.Region())

        # ── State machine ────────────────────────────────────────────────

        def _cancel_dismiss(self) -> None:
            if self._dismiss_source is not None:
                GLib.source_remove(self._dismiss_source)
                self._dismiss_source = None

        def update_state(self, state: str) -> None:
            self._cancel_dismiss()

            spec = _STATES.get(state)
            if spec is None:
                logger.warning("unknown indicator state: %r", state)
                return
            label_text, dot_class = spec

            for cls in ("dot-listening", "dot-done", "dot-error"):
                self._dot.remove_css_class(cls)

            if dot_class is not None:
                self._dot.add_css_class(dot_class)
                self._dot.set_visible(True)
                self._spinner.stop()
                self._spinner.set_visible(False)
            else:
                self._dot.set_visible(False)
                self._spinner.set_visible(True)
                self._spinner.start()

            self._label.set_label(label_text)
            self.set_visible(True)
            self.present()

            if state in _AUTO_DISMISS_MS:
                self._dismiss_source = GLib.timeout_add(_AUTO_DISMISS_MS[state], self._auto_dismiss)

        def hide_pill(self) -> None:
            self._cancel_dismiss()
            self._spinner.stop()
            self.set_visible(False)

        def _auto_dismiss(self) -> bool:
            self._dismiss_source = None
            self.hide_pill()
            return GLib.SOURCE_REMOVE  # type: ignore[no-any-return]

    class IndicatorApp(Gtk.Application):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__(application_id="xyz.sigil.rex.indicator")
            self._window: PillWindow | None = None
            self._server: socket.socket | None = None

        def do_activate(self) -> None:
            display = Gdk.Display.get_default()
            if display is not None:
                css_provider = Gtk.CssProvider()
                css_provider.load_from_data(_CSS)
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                )

            self._window = PillWindow(self)
            # Present once to realize the window (layer-shell needs a mapped surface)
            # then immediately hide — shown again only when a state arrives.
            self._window.present()
            self._window.set_visible(False)

            self._start_socket()

        def _start_socket(self) -> None:
            path = _socket_path()
            path.unlink(missing_ok=True)

            srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(str(path))
            srv.listen(8)
            srv.setblocking(False)
            self._server = srv

            GLib.io_add_watch(srv.fileno(), GLib.IO_IN, self._on_incoming)

        def _on_incoming(self, _fd: int, _cond: int) -> bool:
            assert self._server and self._window
            try:
                conn, _ = self._server.accept()
                with conn:
                    raw = conn.recv(256).decode(errors="replace").strip()
            except OSError:
                return GLib.SOURCE_CONTINUE  # type: ignore[no-any-return]

            parts = raw.split(maxsplit=1)
            if not parts:
                return GLib.SOURCE_CONTINUE  # type: ignore[no-any-return]

            cmd, arg = parts[0], parts[1] if len(parts) > 1 else ""

            if cmd == "show" and arg:
                GLib.idle_add(self._window.update_state, arg)
            elif cmd == "hide":
                GLib.idle_add(self._window.hide_pill)
            elif cmd == "quit":
                self.quit()

            return GLib.SOURCE_CONTINUE  # type: ignore[no-any-return]

        def do_shutdown(self) -> None:
            if self._server:
                self._server.close()
            _socket_path().unlink(missing_ok=True)
            Gtk.Application.do_shutdown(self)

    app = IndicatorApp()
    sys.exit(app.run([sys.argv[0]]))


# ---------------------------------------------------------------------------
# Auto-start helper
# ---------------------------------------------------------------------------


def _auto_start() -> None:
    import subprocess

    subprocess.Popen(
        [sys.executable, "-m", "rex.cli.indicator"],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def indicator_main() -> None:
    args = sys.argv[1:]

    # No args → daemon mode
    if not args:
        _run_daemon()
        return

    cmd = args[0]

    if cmd == "show" and len(args) >= 2:
        state = args[1]
        if not show(state):
            _auto_start()
            import time

            for _ in range(15):
                time.sleep(0.1)
                if show(state):
                    return
            logger.debug("indicator daemon did not start in time")
        return

    if cmd == "hide":
        hide()
        return

    if cmd == "quit":
        _send("quit")
        return

    print(
        "usage: rex-indicator [show <state> | hide | quit]",
        file=sys.stderr,
    )
    print("  states: listening, thinking, done, error", file=sys.stderr)
    sys.exit(1)
