# -*- coding: utf-8 -*-
"""PC-Patcher fuer MediaPlugins2026 HomeScreen Server-Health-Badges."""

from __future__ import print_function

import datetime
import py_compile
import re
from pathlib import Path

MARKER = "# MEDIAPLUGINS2026_HOME_HEALTHBADGE1"

ON_ERROR = r'''    def _onServerError(self, server_cfg, err):
        now = time.monotonic()
        started = self._timing_login_started.get(server_cfg.name, now)
        error_text = str(err or "")
        error_folded = error_text.casefold()
        auth_markers = (
            "401", "403", "unauthorized", "forbidden",
            "authentication", "authenticate", "access denied",
            "invalid token", "expired token", "token expired",
            "not authorized", "anmeldung", "zugriff verweigert",
        )
        state = "auth_required" if any(marker in error_folded for marker in auth_markers) else "offline"
        log.warning(
            "TIMING HOME +%.3fs %s LOGIN FAIL in %.3fs state=%s: %s",
            now - self._timing_load_started, server_cfg.name,
            now - started, state, error_text,
        )
        self._pipelineTiming(
            "LOGIN_FAIL",
            "server=%r login_ms=%.1f state=%s error=%r" %
            (server_cfg.name, (now - started) * 1000.0, state, error_text),
        )
        self.server_status[server_cfg.name] = state
        log.warning("Server %s status=%s: %s", server_cfg.name, state, error_text)
        self._renderStatus()
        self._requestFinished()

'''

RENDER_STATUS = r'''    def _renderStatus(self):
        health = {
            "online": ("Online", "#37d67a"),
            "connecting": ("Pruefung", "#f3c84f"),
            "offline": ("Offline", "#e05252"),
            "auth_required": ("Anmeldung", "#ff9f43"),
            "unconfigured": ("Nicht eingerichtet", "#596b78"),
        }
        protocol_states = {"emby": [], "jellyfin": [], "plex": []}

        for name, cfg in self.server_configs.items():
            protocol = (getattr(cfg, "protocol", "") or "").lower()
            if protocol in protocol_states:
                protocol_states[protocol].append(
                    self.server_status.get(name, "connecting")
                )

        resolved = {}
        for protocol in ("emby", "jellyfin", "plex"):
            states = protocol_states[protocol]
            if not states:
                state = "unconfigured"
            elif "online" in states:
                state = "online"
            elif "connecting" in states:
                state = "connecting"
            elif "auth_required" in states:
                state = "auth_required"
            else:
                state = "offline"

            resolved[protocol] = state
            label, color = health[state]
            widget = self.get("availability_%s_icon" % (
                "jelly" if protocol == "jellyfin" else protocol
            ))
            if widget is not None:
                widget.setText("")
                self._setWidgetBackground(widget, color)
                widget.show()

        self["server_status"].setText(
            "Serverstatus:  Emby %s   Jellyfin %s   Plex %s" %
            (
                health[resolved["emby"]][0],
                health[resolved["jellyfin"]][0],
                health[resolved["plex"]][0],
            )
        )

'''

def replace_method(text, method_name, next_method_name, replacement):
    pattern = re.compile(
        r"(?ms)^    def " + re.escape(method_name) +
        r"\(.*?(?=^    def " + re.escape(next_method_name) + r"\()"
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(
            "%s: genau eine Methode erwartet, gefunden %d" %
            (method_name, len(matches))
        )
    return text[:matches[0].start()] + replacement + text[matches[0].end():]

def main():
    here = Path(__file__).resolve().parent
    candidates = [
        path for path in here.glob("MediaPlugins2026_HomeScreen_*.py")
        if "HEALTHBADGE1" not in path.name
    ]
    if not candidates:
        raise RuntimeError(
            "Keine MediaPlugins2026_HomeScreen_*.py neben dem Patcher gefunden."
        )

    source = max(candidates, key=lambda path: path.stat().st_mtime)
    text = source.read_text(encoding="utf-8-sig")
    if MARKER in text:
        raise RuntimeError("Diese HomeScreen-Datei ist bereits gepatcht.")

    text = text.replace(
        "# -*- coding: utf-8 -*-",
        "# -*- coding: utf-8 -*-\n" + MARKER,
        1,
    )
    text = replace_method(text, "_onServerError", "_requestFinished", ON_ERROR)
    text = replace_method(text, "_renderStatus", "_previewItem", RENDER_STATUS)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    output = here / (
        "MediaPlugins2026_HomeScreen_HEALTHBADGE1_%s.py" % stamp
    )
    output.write_text(text, encoding="utf-8", newline="\n")
    py_compile.compile(str(output), doraise=True)

    print("OK")
    print("Quelle :", source)
    print("Ausgabe:", output)
    print("Syntax : geprueft")

if __name__ == "__main__":
    main()
