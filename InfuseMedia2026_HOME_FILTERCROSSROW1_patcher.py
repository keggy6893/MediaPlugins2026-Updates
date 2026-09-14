# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"
MARKER = "# INFUSEMEDIA2026_HOME_FILTERCROSSROW1"
BACKUP_SUFFIX = ".before_filtercrossrow1"

OLD_LEFT = '        elif self.zone == "latest_filter":\n            self.latest_filter_index = max(0, self.latest_filter_index - 1)\n            self._renderFilters()\n'
NEW_LEFT = '        elif self.zone == "latest_filter":\n            # INFUSEMEDIA2026_HOME_FILTERCROSSROW1\n            # Linker Rand von "Neu hinzugefuegt" -> rechter Rand "Favoriten".\n            if self.latest_filter_index <= 0:\n                self.zone = "fav_filter"\n                self.favorite_filter_index = 3\n                self._refreshFocus()\n                return\n            self.latest_filter_index = max(0, self.latest_filter_index - 1)\n            self._renderFilters()\n'
OLD_RIGHT = '        elif self.zone == "fav_filter":\n            self.favorite_filter_index = min(3, self.favorite_filter_index + 1)\n            self._renderFilters()\n'
NEW_RIGHT = '        elif self.zone == "fav_filter":\n            # INFUSEMEDIA2026_HOME_FILTERCROSSROW1\n            # Rechter Rand "Favoriten" -> linker Rand "Neu hinzugefuegt".\n            if self.favorite_filter_index >= 3:\n                self.zone = "latest_filter"\n                self.latest_filter_index = 0\n                self._refreshFocus()\n                return\n            self.favorite_filter_index = min(3, self.favorite_filter_index + 1)\n            self._renderFilters()\n'


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            "%s: erwartete genau 1 Fundstelle, gefunden %d" % (label, count)
        )
    return text.replace(old, new, 1)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_DEFAULT

    if not os.path.isfile(target):
        raise SystemExit("Datei nicht gefunden: %s" % target)

    with io.open(target, "r", encoding="utf-8") as f:
        original = f.read()

    if MARKER in original:
        print("HOME_FILTERCROSSROW1 bereits installiert: %s" % target)
        return

    patched = replace_once(
        original, OLD_LEFT, NEW_LEFT,
        "latest_filter LINKS"
    )
    patched = replace_once(
        patched, OLD_RIGHT, NEW_RIGHT,
        "fav_filter RECHTS"
    )

    if patched.startswith("# -*- coding: utf-8 -*-"):
        first, rest = patched.split("\n", 1)
        patched = first + "\n" + MARKER + "\n" + rest
    else:
        patched = MARKER + "\n" + patched

    compile(patched, target, "exec")

    backup = target + BACKUP_SUFFIX
    if not os.path.exists(backup):
        shutil.copy2(target, backup)

    with io.open(target, "w", encoding="utf-8", newline="\n") as f:
        f.write(patched)

    with io.open(target, "r", encoding="utf-8") as f:
        verify = f.read()
    compile(verify, target, "exec")

    required = [
        MARKER,
        'self.zone = "latest_filter"',
        'self.latest_filter_index = 0',
        'self.zone = "fav_filter"',
        'self.favorite_filter_index = 3',
    ]
    missing = [x for x in required if x not in verify]
    if missing:
        raise RuntimeError("FILTERCROSSROW1 Verifikation fehlgeschlagen: %r" % missing)

    print("OK INFUSEMEDIA2026_HOME_FILTERCROSSROW1: %s" % target)
    print("- Favoriten Plex + RECHTS -> Neu hinzugefuegt Alle")
    print("- Neu hinzugefuegt Alle + LINKS -> Favoriten Plex")
    print("- normale Filter-Navigation innerhalb der Leisten bleibt erhalten")
    print("- Poster-/Crossrow-/Player-/Serverlogik unveraendert")
    print("- Backup: %s" % backup)


if __name__ == "__main__":
    main()
