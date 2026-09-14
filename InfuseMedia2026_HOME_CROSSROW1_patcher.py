# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"
MARKER = "# INFUSEMEDIA2026_HOME_CROSSROW1"
BACKUP_SUFFIX = ".before_crossrow1"

LEFT_ANCHOR = '    def keyLeft(self):\n        self._touchHomeSlideshow()\n'
LEFT_INSERT = '    def keyLeft(self):\n        self._touchHomeSlideshow()\n\n        # INFUSEMEDIA2026_HOME_CROSSROW1\n        # Untere Bereiche horizontal wie eine zusammenhaengende Reihe.\n        if self.zone == "latest" and self.latestRow.index <= 0:\n            if self.favoritesRow.getCount() > 0:\n                self.zone = "favorites"\n                self.favoritesRow.index = self.favoritesRow.getCount() - 1\n                self.favoritesRow._ensureVisible()\n                self.favoritesRow._prefetchVisible()\n                self.favoritesRow._render()\n                self._refreshFocus()\n                self._updatePreview()\n                return\n'
RIGHT_ANCHOR = '    def keyRight(self):\n        self._touchHomeSlideshow()\n'
RIGHT_INSERT = '    def keyRight(self):\n        self._touchHomeSlideshow()\n\n        # INFUSEMEDIA2026_HOME_CROSSROW1\n        # Letztes Favoriten-Poster -> erstes "Neu hinzugefuegt"-Poster.\n        if (\n            self.zone == "favorites"\n            and self.favoritesRow.getCount() > 0\n            and self.favoritesRow.index >= self.favoritesRow.getCount() - 1\n        ):\n            if self.latestRow.getCount() > 0:\n                self.zone = "latest"\n                self.latestRow.index = 0\n                self.latestRow._ensureVisible()\n                self.latestRow._prefetchVisible()\n                self.latestRow._render()\n                self._refreshFocus()\n                self._updatePreview()\n                return\n'


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

    with io.open(target, "r", encoding="utf-8") as handle:
        original = handle.read()

    if MARKER in original:
        print("HOME_CROSSROW1 bereits installiert: %s" % target)
        return

    patched = replace_once(original, LEFT_ANCHOR, LEFT_INSERT, "keyLeft")
    patched = replace_once(patched, RIGHT_ANCHOR, RIGHT_INSERT, "keyRight")

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

    print("OK INFUSEMEDIA2026_HOME_CROSSROW1: %s" % target)
    print("- letztes Favoriten-Poster + RECHTS -> erstes Neu-hinzugefuegt-Poster")
    print("- erstes Neu-hinzugefuegt-Poster + LINKS -> letztes Favoriten-Poster")
    print("- normale LINKS/RECHTS-Navigation innerhalb der Reihen bleibt erhalten")
    print("- HOCH/RUNTER, Filter, Serverwechsel und Playerlogik unveraendert")
    print("- keine Server-/Login-/Poster-Daten geaendert")
    print("- Backup: %s" % backup)


if __name__ == "__main__":
    main()
