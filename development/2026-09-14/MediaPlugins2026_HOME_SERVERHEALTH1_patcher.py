# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import re
import shutil
import sys

PLUGIN_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
HOME_REL = "screens/HomeScreen.py"
MARKER = "# MEDIAPLUGINS2026_HOME_SERVERHEALTH1"

CLASSIFY_AND_ERROR = '    @staticmethod\n    def _classifyServerFailure(err):\n        text = (str(err or "")).strip().lower()\n        auth_markers = (\n            "401", "403", "unauthorized", "forbidden",\n            "authentication", "auth failed", "login failed",\n            "invalid token", "expired token", "token expired",\n            "invalid credentials", "access denied", "not authorized",\n            "account locked", "locked out", "account disabled",\n            "account suspended",\n        )\n        if any(marker in text for marker in auth_markers):\n            return "auth"\n\n        offline_markers = (\n            "timeout", "timed out", "connection refused",\n            "connection reset", "connection aborted", "network is unreachable",\n            "no route to host", "name or service not known",\n            "temporary failure in name resolution", "dns",\n            "host unreachable", "server unreachable",\n        )\n        if any(marker in text for marker in offline_markers):\n            return "offline"\n        return "error"\n\n    def _onServerError(self, server_cfg, err):\n        now = time.monotonic()\n        started = self._timing_login_started.get(server_cfg.name, now)\n        log.warning("TIMING HOME +%.3fs %s LOGIN FAIL in %.3fs: %s", now - self._timing_load_started, server_cfg.name, now - started, err)\n        self._pipelineTiming("LOGIN_FAIL", "server=%r login_ms=%.1f error=%r" % (server_cfg.name, (now - started) * 1000.0, str(err)))\n        state = self._classifyServerFailure(err)\n        self.server_status[server_cfg.name] = state\n        log.warning("Server %s status=%s: %s", server_cfg.name, state, err)\n        self._renderStatus()\n        self._renderServerSwitch()\n        self._requestFinished()\n'
STATUS_HELPERS_AND_RENDER = '    @staticmethod\n    def _healthStatusText(state, compact=False):\n        labels = {\n            "online": "✓ Online",\n            "auth": "! Login nötig",\n            "offline": "× Offline",\n            "error": "! Fehler",\n            "connecting": "… Prüfe",\n            "–": "– Nicht aktiv",\n        }\n        text = labels.get(state, labels["–"])\n        if compact and text == "– Nicht aktiv":\n            return "–"\n        return text\n\n    def _protocolHealthState(self, provider):\n        states = []\n        for name, cfg in self.server_configs.items():\n            if (getattr(cfg, "protocol", "") or "").lower() == provider:\n                states.append(self.server_status.get(name, "connecting"))\n\n        if not states:\n            return "–"\n        for state in ("online", "auth", "error", "offline", "connecting"):\n            if state in states:\n                return state\n        return "error"\n\n    def _renderStatus(self):\n        emby = self._healthStatusText(self._protocolHealthState("emby"))\n        jelly = self._healthStatusText(self._protocolHealthState("jellyfin"))\n        plex = self._healthStatusText(self._protocolHealthState("plex"))\n        self["server_status"].setText(\n            "Serverstatus:   Emby %s     Jellyfin %s     Plex %s" %\n            (emby, jelly, plex)\n        )\n        self._renderServerSwitch()\n'
SERVER_SWITCH_STATUS = '    def _serverSwitchStatus(self, provider):\n        return self._healthStatusText(\n            self._protocolHealthState(provider),\n            compact=True,\n        )\n'

def read(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()

def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)

def replace_method(text, name, replacement):
    pattern = re.compile(r'(?ms)^    def %s\(.*?(?=^    def |\Z)' % re.escape(name))
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError("%s: erwartete genau 1 Methode, gefunden %d" % (name, len(matches)))
    match = matches[0]
    return text[:match.start()] + replacement.rstrip() + "\n\n" + text[match.end():]

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else PLUGIN_DEFAULT
    home_path = os.path.join(root, HOME_REL)
    if not os.path.isfile(home_path):
        raise SystemExit("HomeScreen fehlt: %s" % home_path)

    original = read(home_path)
    if MARKER in original:
        print("SERVERHEALTH1 bereits installiert")
        return

    patched = original.replace(
        "# -*- coding: utf-8 -*-",
        "# -*- coding: utf-8 -*-\n" + MARKER,
        1,
    )
    patched = replace_method(patched, "_onServerError", CLASSIFY_AND_ERROR)
    patched = replace_method(patched, "_renderStatus", STATUS_HELPERS_AND_RENDER)
    patched = replace_method(patched, "_serverSwitchStatus", SERVER_SWITCH_STATUS)

    compile(patched, home_path, "exec")

    backup = home_path + ".before_serverhealth1"
    if not os.path.exists(backup):
        shutil.copy2(home_path, backup)

    write(home_path, patched)
    compile(read(home_path), home_path, "exec")

    verify = read(home_path)
    required = [
        MARKER,
        "_classifyServerFailure",
        '"auth": "! Login nötig"',
        '"offline": "× Offline"',
        "_protocolHealthState",
        "_renderServerSwitch()",
    ]
    missing = [item for item in required if item not in verify]
    if missing:
        raise RuntimeError("SERVERHEALTH1 Verifikation fehlgeschlagen: %r" % missing)

    print("OK MEDIAPLUGINS2026_HOME_SERVERHEALTH1")
    print("- Online / Login nötig / Offline / Fehler / Prüfe / Nicht aktiv")
    print("- Status in Zu Server wechseln + Serverstatus-Zeile")
    print("- keyPlayCurrent / Provider-Player-Routing bleibt unverändert")
    print("Backup: %s" % backup)

if __name__ == "__main__":
    main()
