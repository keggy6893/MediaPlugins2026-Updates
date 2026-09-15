# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
TARGET_REL = "screens/BackupScreen.py"

MARKER = "# MEDIAPLUGINS2026_BACKUP_TITLE1"
OLD_TITLE = 'self["title"] = Label("Sicherung oder Export?")'
NEW_TITLE = 'self["title"] = Label("Sicherung & Wiederherstellung")'


def read(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def patch(text):
    if MARKER in text:
        return text

    if OLD_TITLE not in text:
        raise RuntimeError(
            'Erwartete Überschrift "Sicherung oder Export?" nicht gefunden'
        )

    text = text.replace(OLD_TITLE, NEW_TITLE, 1)

    class_anchor = "class MediaPluginsBackupScreen(Screen):\n"
    if class_anchor in text:
        text = text.replace(
            class_anchor,
            MARKER + "\n" + class_anchor,
            1,
        )
    else:
        text = MARKER + "\n" + text

    compile(text, "BackupScreen.py", "exec")
    return text


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DEFAULT
    target = os.path.join(root, TARGET_REL)

    if not os.path.isfile(target):
        raise SystemExit("BackupScreen.py nicht gefunden: %s" % target)

    original = read(target)
    patched = patch(original)

    compile(patched, target, "exec")

    backup = target + ".before_backup_title1"
    if not os.path.exists(backup):
        shutil.copy2(target, backup)

    write(target, patched)

    verify = read(target)
    compile(verify, target, "exec")

    if NEW_TITLE not in verify:
        raise RuntimeError("Neue Überschrift wurde nicht geschrieben")

    print("OK MEDIAPLUGINS2026_BACKUP_TITLE1")
    print("- Überschrift: Sicherung & Wiederherstellung")
    print("- Sicherungs-/Export-/Importlogik unverändert")
    print("Backup: %s" % backup)


if __name__ == "__main__":
    main()
