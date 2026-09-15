# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import re
import shutil
import sys

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
TARGET_REL = "screens/BackupScreen.py"

MARKER = "# MEDIAPLUGINS2026_BACKUPDIALOG_NOOVERLAY1"
REQUIRED = "# MEDIAPLUGINS2026_AUTOBACKUP1_SCREEN"


def read(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def patch(text):
    if MARKER in text:
        return text

    if REQUIRED not in text:
        raise RuntimeError("AUTOBACKUP1 BackupScreen-Basis fehlt")

    text = text.replace(
        REQUIRED + "\n",
        REQUIRED + "\n" + MARKER + "\n",
        1,
    )

    pattern = re.compile(
        r'\n\s*<eLabel(?:\s+zPosition="[^"]+")?\s+position="0,0"\s+'
        r'size="1240,500"\s+backgroundColor="#06121D"\s*'
        r'\n\s*borderWidth="2"\s+borderColor="#1B4C6B"\s*/>\s*',
        re.M,
    )
    text, removed = pattern.subn("\n", text, count=1)

    if removed != 1:
        raise RuntimeError(
            "Vollflaechen-eLabel nicht eindeutig gefunden; Abbruch ohne Aenderung"
        )

    top_lines = (
        '<eLabel zPosition="5" position="0,0" size="1240,4" backgroundColor="#23D7F2" />',
        '<eLabel position="0,0" size="1240,4" backgroundColor="#23D7F2" />',
    )
    top_line = next((x for x in top_lines if x in text), None)
    if top_line is None:
        raise RuntimeError("Cyan-Kopflinie nicht gefunden")

    border_block = (
        '<eLabel zPosition="5" position="0,0" size="1240,4" backgroundColor="#23D7F2" />\n'
        '        <eLabel zPosition="5" position="0,0" size="2,500" backgroundColor="#1B4C6B" />\n'
        '        <eLabel zPosition="5" position="1238,0" size="2,500" backgroundColor="#1B4C6B" />\n'
        '        <eLabel zPosition="5" position="0,498" size="1240,2" backgroundColor="#1B4C6B" />'
    )
    text = text.replace(top_line, border_block, 1)

    for name in (
        "brand", "year", "kicker", "title", "body",
        "status", "key_yellow", "key_red", "key_ok"
    ):
        text = text.replace(
            '<widget zPosition="20" name="%s"' % name,
            '<widget zPosition="50" name="%s"' % name,
        )
        text = text.replace(
            '<widget name="%s"' % name,
            '<widget zPosition="50" name="%s"' % name,
        )

    text = text.replace(
        '<eLabel position="42,130" size="1156,1" backgroundColor="#244863" />',
        '<eLabel zPosition="5" position="42,130" size="1156,1" backgroundColor="#244863" />',
    )

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

    backup = target + ".before_backupdialog_nooverlay1"
    if not os.path.exists(backup):
        shutil.copy2(target, backup)

    write(target, patched)

    verify = read(target)
    compile(verify, target, "exec")

    if re.search(
        r'<eLabel[^>]+size="1240,500"[^>]+backgroundColor="#06121D"',
        verify,
    ):
        raise RuntimeError("Vollflaechen-eLabel ist noch vorhanden")

    required = [
        MARKER,
        '<widget zPosition="50" name="brand"',
        '<widget zPosition="50" name="body"',
        '<widget zPosition="50" name="key_yellow"',
        '<widget zPosition="50" name="key_ok"',
        'position="0,498" size="1240,2"',
    ]
    missing = [x for x in required if x not in verify]
    if missing:
        raise RuntimeError("NOOVERLAY1 Verifikation fehlgeschlagen: %r" % missing)

    print("OK MEDIAPLUGINS2026_BACKUPDIALOG_NOOVERLAY1")
    print("- vollflaechige eLabel entfernt")
    print("- Screen-Hintergrundfarbe bleibt als Flaeche")
    print("- Rahmen nur noch aus duennen Linien")
    print("- Text/Status/Buttons auf zPosition 50")
    print("- Backup-/Exportlogik unveraendert")
    print("Backup: %s" % backup)


if __name__ == "__main__":
    main()
