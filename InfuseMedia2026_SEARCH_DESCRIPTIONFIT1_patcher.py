# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/SearchScreen.py"
MARKER = "# INFUSEMEDIA2026_SEARCH_DESCRIPTIONFIT1"
BACKUP_SUFFIX = ".before_search_descriptionfit1"

OLD_OVERVIEW_WIDGET = '<widget name="preview_overview" position="180,878" size="790,76" font="Regular;18" foregroundColor="#dce5ea" transparent="1" />'
NEW_OVERVIEW_WIDGET = '<widget name="preview_overview" position="180,876" size="790,92" font="Regular;18" foregroundColor="#dce5ea" transparent="1" />'
OLD_BADGES_WIDGET = '<widget name="preview_badges" position="180,960" size="790,31" font="Regular;18" foregroundColor="#e8c558" transparent="1" />'
NEW_BADGES_WIDGET = '<widget name="preview_badges" position="180,974" size="790,27" font="Regular;17" foregroundColor="#e8c558" transparent="1" />'
OLD_SHORT = '        self["preview_overview"].setText(self._short(overview, 320))\n'
NEW_SHORT = '        # INFUSEMEDIA2026_SEARCH_DESCRIPTIONFIT1\n        # Die Vorschau hat Platz fuer ca. vier saubere Zeilen. Ein bewusst\n        # kuerzeres Limit verhindert, dass Text unter die Technik-Badges laeuft.\n        self["preview_overview"].setText(self._short(overview, 250))\n'


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
        print("SEARCH_DESCRIPTIONFIT1 bereits installiert: %s" % target)
        return

    if "# INFUSEMEDIA2026_SEARCH_ENRICH_HISTORY1" not in original:
        raise RuntimeError("SEARCH_DESCRIPTIONFIT1 erwartet SEARCH_ENRICH_HISTORY1")

    patched = replace_once(
        original, OLD_OVERVIEW_WIDGET, NEW_OVERVIEW_WIDGET,
        "preview_overview-Geometrie"
    )
    patched = replace_once(
        patched, OLD_BADGES_WIDGET, NEW_BADGES_WIDGET,
        "preview_badges-Geometrie"
    )
    patched = replace_once(
        patched, OLD_SHORT, NEW_SHORT,
        "Beschreibungslimit"
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

    with io.open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(patched)

    with io.open(target, "r", encoding="utf-8") as handle:
        verify = handle.read()

    compile(verify, target, "exec")

    required = [
        MARKER,
        'name="preview_overview" position="180,876" size="790,92"',
        'name="preview_badges" position="180,974" size="790,27"',
        'self._short(overview, 250)',
    ]
    missing = [x for x in required if x not in verify]
    if missing:
        raise RuntimeError("SEARCH_DESCRIPTIONFIT1 Verifikation fehlgeschlagen: %r" % missing)

    print("OK INFUSEMEDIA2026_SEARCH_DESCRIPTIONFIT1: %s" % target)
    print("- Beschreibungsfeld: 76 -> 92 px")
    print("- Technik-Badges tiefer und kompakter")
    print("- Vorschautext sauber auf 250 Zeichen ellipsiert")
    print("- kein Text mehr unter/gegen die Badges")
    print("- Live-Suche / Verlauf / Detail-Nachladen unveraendert")
    print("- Backup: %s" % backup)


if __name__ == "__main__":
    main()
