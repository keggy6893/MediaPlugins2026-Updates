# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
TARGET_REL = "screens/BackupScreen.py"

MARKER = "# MEDIAPLUGINS2026_BACKUPDIALOG_LAYERFIX1"
REQUIRED = "# MEDIAPLUGINS2026_AUTOBACKUP1_SCREEN"


def read(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            "%s: erwartete genau 1 Fundstelle, gefunden %d" % (label, count)
        )
    return text.replace(old, new, 1)


def patch(text):
    if MARKER in text:
        return text
    if REQUIRED not in text:
        raise RuntimeError("AUTOBACKUP1 BackupScreen-Basis fehlt")

    text = replace_once(
        text,
        REQUIRED + "\n",
        REQUIRED + "\n" + MARKER + "\n",
        "Marker",
    )

    text = replace_once(
        text,
        '<eLabel position="0,0" size="1240,500" backgroundColor="#06121D"\n'
        '                borderWidth="2" borderColor="#1B4C6B" />',
        '<eLabel zPosition="0" position="0,0" size="1240,500" backgroundColor="#06121D"\n'
        '                borderWidth="2" borderColor="#1B4C6B" />',
        "Dialog-Hintergrund",
    )
    text = replace_once(
        text,
        '<eLabel position="0,0" size="1240,4" backgroundColor="#23D7F2" />',
        '<eLabel zPosition="5" position="0,0" size="1240,4" backgroundColor="#23D7F2" />',
        "Cyan-Kopflinie",
    )
    text = replace_once(
        text,
        '<eLabel position="42,130" size="1156,1" backgroundColor="#244863" />',
        '<eLabel zPosition="5" position="42,130" size="1156,1" backgroundColor="#244863" />',
        "Trennlinie",
    )

    widget_names = (
        "brand",
        "year",
        "kicker",
        "title",
        "body",
        "status",
        "key_yellow",
        "key_red",
        "key_ok",
    )
    for name in widget_names:
        old = '<widget name="%s"' % name
        new = '<widget zPosition="20" name="%s"' % name
        text = replace_once(text, old, new, "Widget %s" % name)

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

    backup = target + ".before_backupdialog_layerfix1"
    if not os.path.exists(backup):
        shutil.copy2(target, backup)

    write(target, patched)

    verify = read(target)
    compile(verify, target, "exec")

    required = [
        MARKER,
        '<eLabel zPosition="0" position="0,0" size="1240,500"',
        '<eLabel zPosition="5" position="0,0" size="1240,4"',
        '<widget zPosition="20" name="brand"',
        '<widget zPosition="20" name="body"',
        '<widget zPosition="20" name="key_yellow"',
        '<widget zPosition="20" name="key_ok"',
    ]
    missing = [item for item in required if item not in verify]
    if missing:
        raise RuntimeError(
            "BACKUPDIALOG_LAYERFIX1 Verifikation fehlgeschlagen: %r" % missing
        )

    print("OK MEDIAPLUGINS2026_BACKUPDIALOG_LAYERFIX1")
    print("- Ursache behoben: Vollflaechen-eLabel ueberdeckte Text/Buttons")
    print("- Hintergrund zPosition 0")
    print("- Cyan-/Trennlinien zPosition 5")
    print("- Text, Status und Tasten zPosition 20")
    print("- Backup-/Exportlogik unveraendert")
    print("Backup: %s" % backup)


if __name__ == "__main__":
    main()
