# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"
MARKER = "# INFUSEMEDIA2026_HOME_TWOLINETITLES1"
BACKUP_SUFFIX = ".before_twolinetitles1"

OLD_HEIGHT = '    title_height = 41 if progress else 27\n'
NEW_HEIGHT = '    # INFUSEMEDIA2026_HOME_TWOLINETITLES1\n    # Auch Favoriten/Neu hinzugefuegt erhalten zwei echte Titelzeilen.\n    title_height = 41\n'
OLD_META = '    meta_y_offset = 238 if progress else 224\n'
NEW_META = '    # Meta/Jahr beginnt unter der zweiten Titelzeile.\n    meta_y_offset = 238\n'


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
        print("HOME_TWOLINETITLES1 bereits installiert: %s" % target)
        return

    patched = replace_once(
        original,
        OLD_HEIGHT,
        NEW_HEIGHT,
        "Titelhoehe",
    )
    patched = replace_once(
        patched,
        OLD_META,
        NEW_META,
        "Meta-Position",
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
        "title_height = 41",
        "meta_y_offset = 238",
    ]
    missing = [x for x in required if x not in verify]
    if missing:
        raise RuntimeError(
            "TWOLINETITLES1 Verifikation fehlgeschlagen: %r" % missing
        )

    print("OK INFUSEMEDIA2026_HOME_TWOLINETITLES1: %s" % target)
    print("- Favoriten: zwei saubere Titelzeilen")
    print("- Neu hinzugefuegt: zwei saubere Titelzeilen")
    print("- Meta/Jahr unter die zweite Titelzeile verschoben")
    print("- Weiterschauen bleibt optisch unveraendert")
    print("- Poster/Fokus/Navigation/Player unveraendert")
    print("- keine Server-/Login-/Poster-Daten geaendert")
    print("- Backup: %s" % backup)


if __name__ == "__main__":
    main()
