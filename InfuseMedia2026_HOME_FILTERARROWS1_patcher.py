# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"
MARKER = "# INFUSEMEDIA2026_HOME_FILTERARROWS1"
BACKUP_SUFFIX = ".before_filterarrows1"

NEW_KEYUP = '    def keyUp(self):\n        self._touchHomeSlideshow()\n\n        if self.zone == "server_switch":\n            if self.server_switch_index > 0:\n                self.server_switch_index -= 1\n                self._renderServerSwitch()\n            else:\n                self._leaveServerSwitch()\n            return\n\n        # INFUSEMEDIA2026_HOME_FILTERARROWS1\n        # Pfeil HOCH betritt zuerst die sichtbare Filterleiste der jeweiligen\n        # unteren Posterreihe. Ein weiteres HOCH geht zur vorherigen Medienreihe.\n        if self.zone == "latest":\n            self.zone = "latest_filter"\n            self._refreshFocus()\n            return\n\n        if self.zone == "favorites":\n            self.zone = "fav_filter"\n            self._refreshFocus()\n            return\n\n        if self.zone == "latest_filter":\n            if self.favoritesRow.getCount() > 0:\n                self.zone = "favorites"\n            elif self.continueRow.getCount() > 0:\n                self.zone = "continue"\n            self._refreshFocus()\n            return\n\n        if self.zone == "fav_filter":\n            if self.continueRow.getCount() > 0:\n                self.zone = "continue"\n                self._refreshFocus()\n            return\n\n        self._moveZone(-1)\n\n'


def replace_keyup(text):
    start_token = "    def keyUp(self):\n"
    end_token = "    def keyDown(self):\n"

    starts = []
    pos = 0
    while True:
        pos = text.find(start_token, pos)
        if pos < 0:
            break
        starts.append(pos)
        pos += len(start_token)

    if len(starts) != 1:
        raise RuntimeError(
            "keyUp: erwartete genau 1 Methode, gefunden %d" % len(starts)
        )

    start = starts[0]
    end = text.find(end_token, start)
    if end < 0:
        raise RuntimeError("keyDown nach keyUp nicht gefunden")

    return text[:start] + NEW_KEYUP + text[end:]


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_DEFAULT

    if not os.path.isfile(target):
        raise SystemExit("Datei nicht gefunden: %s" % target)

    with io.open(target, "r", encoding="utf-8") as handle:
        original = handle.read()

    if MARKER in original:
        print("HOME_FILTERARROWS1 bereits installiert: %s" % target)
        return

    if 'self.zone == "latest_filter"' not in original:
        raise RuntimeError("latest_filter-Zone nicht gefunden")
    if 'self.zone == "fav_filter"' not in original:
        raise RuntimeError("fav_filter-Zone nicht gefunden")

    patched = replace_keyup(original)

    if patched.startswith("# -*- coding: utf-8 -*-"):
        first, rest = patched.split("\n", 1)
        patched = first + "\n" + MARKER + "\n" + rest
    else:
        patched = MARKER + "\n" + patched

    compile(patched, target, "exec")

    backup = target + BACKUP_SUFFIX
    if not os.path.exists(backup):
        shutil.copy2(target, backup)

    with io.open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(patched)

    with io.open(target, "r", encoding="utf-8") as handle:
        verify = handle.read()

    compile(verify, target, "exec")

    required = [
        MARKER,
        'if self.zone == "latest":',
        'self.zone = "latest_filter"',
        'if self.zone == "favorites":',
        'self.zone = "fav_filter"',
    ]
    missing = [x for x in required if x not in verify]
    if missing:
        raise RuntimeError("FILTERARROWS1 Verifikation fehlgeschlagen: %r" % missing)

    print("OK INFUSEMEDIA2026_HOME_FILTERARROWS1: %s" % target)
    print("- Neu hinzugefuegt Poster + HOCH -> Filterleiste (Alle/Emby/Jellyfin/Plex)")
    print("- Favoriten Poster + HOCH -> Filterleiste")
    print("- RUNTER vom Filter -> zurueck zur jeweiligen Posterreihe")
    print("- weiteres HOCH vom Filter -> vorherige Medienreihe")
    print("- LINKS/RECHTS im Filter und OK-Auswahl bleiben unveraendert")
    print("- Crossrow/Poster/Player/Serverdaten unveraendert")
    print("- Backup: %s" % backup)


if __name__ == "__main__":
    main()
