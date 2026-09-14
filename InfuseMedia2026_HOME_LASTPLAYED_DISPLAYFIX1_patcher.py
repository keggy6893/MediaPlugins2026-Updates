#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys
import time

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"
MARKER = "# INFUSEMEDIA2026_HOME_LASTPLAYED_DISPLAYFIX1"

REQUIRED = (
    "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE3_RESUMESCORE_FIX",
)

OLD = '    @staticmethod\n    def _previewDate(value):\n        value = str(value or "")\n        if len(value) >= 10 and value[4:5] == "-" and value[7:8] == "-":\n            result = "%s.%s.%s" % (value[8:10], value[5:7], value[0:4])\n            if len(value) >= 16 and value[10:11] in ("T", " "):\n                result += ", %s" % value[11:16]\n            return result\n        return value[:22]\n'
NEW = '    # INFUSEMEDIA2026_HOME_LASTPLAYED_DISPLAYFIX1\n    @staticmethod\n    def _previewDate(value):\n        """Nur echte Datum-/Zeitwerte in der Home-Detailleiste anzeigen."""\n        value = str(value or "").strip()\n        if not value:\n            return ""\n\n        # Server-Rohwerte wie 00000000001787574043 sind keine nutzbare\n        # Datumsanzeige und sollen nicht im UI erscheinen.\n        if value.isdigit():\n            return ""\n\n        # Erwartetes ISO-aehnliches Format: YYYY-MM-DD[ T]HH:MM...\n        if len(value) >= 10 and value[4:5] == "-" and value[7:8] == "-":\n            try:\n                year = int(value[0:4])\n                month = int(value[5:7])\n                day = int(value[8:10])\n                if not (1 <= month <= 12 and 1 <= day <= 31):\n                    return ""\n\n                result = "%02d.%02d.%04d" % (day, month, year)\n\n                if len(value) >= 16 and value[10:11] in ("T", " "):\n                    hour = int(value[11:13])\n                    minute = int(value[14:16])\n                    if 0 <= hour <= 23 and 0 <= minute <= 59:\n                        result += ", %02d:%02d" % (hour, minute)\n                return result\n            except Exception:\n                return ""\n\n        # Unbekannte Formate nicht ungeprueft ins UI durchreichen.\n        return ""\n'


def fail(message):
    raise SystemExit("ABBRUCH: %s" % message)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_DEFAULT

    if not os.path.isfile(target):
        fail("HomeScreen.py nicht gefunden: %s" % target)

    with io.open(target, "r", encoding="utf-8") as handle:
        original = handle.read()

    if MARKER in original:
        print("HOME_LASTPLAYED_DISPLAYFIX1 bereits installiert")
        return

    for required in REQUIRED:
        if required not in original:
            fail("Erforderlicher Patch fehlt: %s" % required)

    count = original.count(OLD)
    if count != 1:
        fail(
            "_previewDate: erwartet genau 1 passende Methode, gefunden %d"
            % count
        )

    patched = original.replace(OLD, NEW, 1)
    compile(patched, target, "exec")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = target + ".before_lastplayed_displayfix1_" + stamp
    shutil.copy2(target, backup)

    tmp = target + ".lastplayed_displayfix1.tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(patched)
    os.replace(tmp, target)

    with io.open(target, "r", encoding="utf-8") as handle:
        verify = handle.read()

    compile(verify, target, "exec")

    checks = (
        MARKER,
        "if value.isdigit():",
        'return ""',
        'result = "%02d.%02d.%04d"',
    )
    missing = [x for x in checks if x not in verify]
    if missing:
        fail("Nachkontrolle fehlgeschlagen: %r" % missing)

    print("OK INFUSEMEDIA2026_HOME_LASTPLAYED_DISPLAYFIX1")
    print("- numerische LastPlayed-Rohwerte werden in der Detailleiste ausgeblendet")
    print("- echte ISO-Daten werden als TT.MM.JJJJ, HH:MM formatiert")
    print("- Fortschritt/Resume/Merge bleiben unveraendert")
    print("- Snapshot/Player/Serverdaten bleiben unveraendert")
    print("- Backup:", backup)


if __name__ == "__main__":
    main()
