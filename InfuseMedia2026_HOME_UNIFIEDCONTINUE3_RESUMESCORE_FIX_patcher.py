#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys
import time

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"

MARKER = "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE3_RESUMESCORE_FIX"
REQUIRED = (
    "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE1_COMPAT",
    "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE1_SKIPFINAL2_FIX",
    "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE2_MULTIALIAS",
    "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE2_RUNTIMEALIAS_FIX",
)

OLD = '    def _continueUnifiedScore(self, item):\n        last_played = str(getattr(item, "last_played_date", "") or "")\n        resume = max(0, int(getattr(item, "resume_ticks", 0) or 0))\n        width = max(0, int(getattr(item, "video_width", 0) or 0))\n        height = max(0, int(getattr(item, "video_height", 0) or 0))\n        return (\n            1 if last_played else 0,\n            last_played,\n            self._continueProgressRatio(item),\n            resume,\n            width * height,\n        )\n'
NEW = '    # INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE3_RESUMESCORE_FIX\n    @staticmethod\n    def _continueLastPlayedKey(item):\n        """Nur echte Datum-/Zeitwerte fuer die Resume-Auswahl akzeptieren.\n\n        Erwartete Serverformate sind ISO-aehnlich, z.B.\n        2026-09-14T08:43:11Z oder 2026-09-14 08:43:11.\n        Rein numerische/zero-padded Rohwerte werden absichtlich ignoriert.\n        """\n        value = str(getattr(item, "last_played_date", "") or "").strip()\n        if not value:\n            return 0\n\n        # Rohwerte wie 00000000001788888651 duerfen nicht lexikographisch\n        # gegen echte Datumswerte gewinnen.\n        if value.isdigit():\n            return 0\n\n        # ISO YYYY-MM-DD[ T]HH:MM[:SS][...]\n        try:\n            if (\n                len(value) >= 10\n                and value[4:5] == "-"\n                and value[7:8] == "-"\n            ):\n                year = int(value[0:4])\n                month = int(value[5:7])\n                day = int(value[8:10])\n\n                hour = 0\n                minute = 0\n                second = 0\n\n                if len(value) >= 16 and value[10:11] in ("T", " "):\n                    hour = int(value[11:13])\n                    minute = int(value[14:16])\n                    if len(value) >= 19 and value[16:17] == ":":\n                        second = int(value[17:19])\n\n                if not (1 <= month <= 12 and 1 <= day <= 31):\n                    return 0\n                if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):\n                    return 0\n\n                return (\n                    year * 10000000000\n                    + month * 100000000\n                    + day * 1000000\n                    + hour * 10000\n                    + minute * 100\n                    + second\n                )\n        except Exception:\n            return 0\n\n        return 0\n\n    def _continueUnifiedScore(self, item):\n        last_played_key = self._continueLastPlayedKey(item)\n        resume = max(0, int(getattr(item, "resume_ticks", 0) or 0))\n        width = max(0, int(getattr(item, "video_width", 0) or 0))\n        height = max(0, int(getattr(item, "video_height", 0) or 0))\n\n        # Reihenfolge:\n        # 1. echtes Datum vorhanden\n        # 2. bei echten Daten: neuester Zeitpunkt\n        # 3. sonst bzw. bei Gleichstand: hoechster Fortschritt\n        # 4. absolute Resume-Position\n        # 5. Aufloesung als letzter Tie-Breaker\n        return (\n            1 if last_played_key else 0,\n            last_played_key,\n            self._continueProgressRatio(item),\n            resume,\n            width * height,\n        )\n'


def fail(message):
    raise SystemExit("ABBRUCH: %s" % message)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_DEFAULT

    if not os.path.isfile(target):
        fail("HomeScreen.py nicht gefunden: %s" % target)

    with io.open(target, "r", encoding="utf-8") as handle:
        original = handle.read()

    if MARKER in original:
        print("UNIFIEDCONTINUE3_RESUMESCORE_FIX bereits installiert")
        return

    for required in REQUIRED:
        if required not in original:
            fail("Erforderlicher Patch fehlt: %s" % required)

    count = original.count(OLD)
    if count != 1:
        fail(
            "Resume-Score-Block: erwartet genau 1 Fundstelle, gefunden %d"
            % count
        )

    patched = original.replace(OLD, NEW, 1)
    compile(patched, target, "exec")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = target + ".before_unifiedcontinue3_resumescore_" + stamp
    shutil.copy2(target, backup)

    tmp = target + ".resumescorefix.tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(patched)
    os.replace(tmp, target)

    with io.open(target, "r", encoding="utf-8") as handle:
        verify = handle.read()

    compile(verify, target, "exec")

    checks = (
        MARKER,
        "def _continueLastPlayedKey(item):",
        "if value.isdigit():",
        "last_played_key = self._continueLastPlayedKey(item)",
    )
    missing = [item for item in checks if item not in verify]
    if missing:
        fail("Nachkontrolle fehlgeschlagen: %r" % missing)

    print("OK INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE3_RESUMESCORE_FIX")
    print("- numerische/zero-padded LastPlayed-Rohwerte werden ignoriert")
    print("- echte ISO-Datumswerte bleiben fuer 'zuletzt gespielt' aktiv")
    print("- bei ungueltigem Datum gewinnt der hoehere Fortschritt")
    print("- 6 Underground sollte damit den Emby-Stand ~77 Prozent nehmen")
    print("- Merge/Snapshot/SKIPFINAL2/Player/Serverdaten unveraendert")
    print("- Backup:", backup)


if __name__ == "__main__":
    main()
