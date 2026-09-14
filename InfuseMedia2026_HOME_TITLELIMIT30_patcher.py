# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"
MARKER = "# INFUSEMEDIA2026_HOME_TITLELIMIT30"
BACKUP_SUFFIX = ".before_titlelimit30"

OLD = '            title_limit = 30 if self.prefix == "continue" else 22\n'
NEW = '            # INFUSEMEDIA2026_HOME_TITLELIMIT30\n            # Alle Home-Reihen nutzen dasselbe zweizeilige Titellimit.\n            title_limit = 30\n'


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_DEFAULT

    if not os.path.isfile(target):
        raise SystemExit("Datei nicht gefunden: %s" % target)

    with io.open(target, "r", encoding="utf-8") as f:
        original = f.read()

    if MARKER in original:
        print("HOME_TITLELIMIT30 bereits installiert: %s" % target)
        return

    count = original.count(OLD)
    if count != 1:
        raise RuntimeError(
            "Titel-Limit: erwartete genau 1 Fundstelle, gefunden %d" % count
        )

    patched = original.replace(OLD, NEW, 1)

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

    if "title_limit = 30" not in verify:
        raise RuntimeError("TITLELIMIT30 Verifikation fehlgeschlagen")

    print("OK INFUSEMEDIA2026_HOME_TITLELIMIT30: %s" % target)
    print("- Weiterschauen: 30 Zeichen")
    print("- Favoriten: 30 Zeichen")
    print("- Neu hinzugefuegt: 30 Zeichen")
    print("- zweizeilige Darstellung bleibt erhalten")
    print("- Poster/Fokus/Navigation/Player unveraendert")
    print("- Backup: %s" % backup)


if __name__ == "__main__":
    main()
