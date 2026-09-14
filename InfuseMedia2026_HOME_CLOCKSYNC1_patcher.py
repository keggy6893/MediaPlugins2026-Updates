#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys
import time

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"
MARKER = "# INFUSEMEDIA2026_HOME_CLOCKSYNC1"
BACKUP_SUFFIX = ".before_home_clocksync1"

OLD_LABELS = '        self["clock_date"] = Label("")\n        self["clock_time"] = Label("")\n        self["slogan"] = Label("Filme. Serien. Überall. Zuhause.")\n'
NEW_LABELS = '        self["clock_date"] = Label("")\n        self["clock_time"] = Label("")\n\n        # INFUSEMEDIA2026_HOME_CLOCKSYNC1\n        # Die Home-Uhr wird sekündlich aus der lokalen Box-Zeit aktualisiert.\n        # Vorher wurde sie nur einmal bei onLayoutFinish gesetzt.\n        self._clock_timer = eTimer()\n        try:\n            self._clock_timer.callback.append(self._updateClock)\n        except Exception:\n            try:\n                self._clock_timer.timeout.connect(self._updateClock)\n            except Exception:\n                pass\n\n        self["slogan"] = Label("Filme. Serien. Überall. Zuhause.")\n'

OLD_LAYOUT_HOOK = '        self.onLayoutFinish.append(self._onLayoutFinish)\n\n    # ------------------------------------------------------------------\n'
NEW_LAYOUT_HOOK = '        self.onLayoutFinish.append(self._onLayoutFinish)\n        try:\n            self.onClose.append(self._stopClockTimer)\n        except Exception:\n            pass\n\n    # ------------------------------------------------------------------\n'

OLD_CLOCK = '    def _updateClock(self):\n        try:\n            self["clock_date"].setText(time.strftime("%a, %d. %b %Y"))\n            self["clock_time"].setText(time.strftime("%H:%M"))\n        except Exception:\n            pass\n\n    def loadHome(self):\n'
NEW_CLOCK = '    def _updateClock(self):\n        # INFUSEMEDIA2026_HOME_CLOCKSYNC1\n        try:\n            now = time.localtime()\n            self["clock_date"].setText(\n                time.strftime("%a, %d. %b %Y", now)\n            )\n            self["clock_time"].setText(\n                time.strftime("%H:%M", now)\n            )\n        except Exception:\n            pass\n\n        # Single-shot bewusst selbst wieder starten: damit funktioniert die\n        # Uhr auf unterschiedlichen Enigma2/eTimer-Implementierungen stabil.\n        try:\n            self._clock_timer.start(1000, True)\n        except Exception:\n            pass\n\n    def _stopClockTimer(self):\n        try:\n            self._clock_timer.stop()\n        except Exception:\n            pass\n\n    def loadHome(self):\n'


def fail(message):
    raise SystemExit("ABBRUCH: %s" % message)


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        fail("%s: erwartet genau 1 Fundstelle, gefunden %d" % (label, count))
    return text.replace(old, new, 1)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_DEFAULT

    if not os.path.isfile(target):
        fail("HomeScreen.py nicht gefunden: %s" % target)

    with io.open(target, "r", encoding="utf-8") as handle:
        original = handle.read()

    if MARKER in original:
        print("INFUSEMEDIA2026_HOME_CLOCKSYNC1 bereits installiert")
        return

    required = (
        'self["clock_date"] = Label("")',
        'self["clock_time"] = Label("")',
        "def _onLayoutFinish(self):",
        "def _updateClock(self):",
        'time.strftime("%H:%M")',
    )
    missing = [item for item in required if item not in original]
    if missing:
        fail("HomeScreen-Struktur unerwartet; fehlt: %r" % missing)

    patched = original

    # eTimer import robust ergänzen.
    if "from enigma import eSize, eTimer" not in patched and "from enigma import eTimer, eSize" not in patched:
        if "from enigma import eSize\n" in patched:
            patched = patched.replace(
                "from enigma import eSize\n",
                "from enigma import eSize, eTimer\n",
                1,
            )
        else:
            fail("enigma eSize-Import nicht gefunden")

    patched = replace_once(
        patched,
        OLD_LABELS,
        NEW_LABELS,
        "Clock-Labels",
    )
    patched = replace_once(
        patched,
        OLD_LAYOUT_HOOK,
        NEW_LAYOUT_HOOK,
        "onClose-Hook",
    )
    patched = replace_once(
        patched,
        OLD_CLOCK,
        NEW_CLOCK,
        "_updateClock",
    )

    # Marker oben ergänzen.
    if patched.startswith("# -*- coding: utf-8 -*-"):
        first, rest = patched.split("\n", 1)
        patched = first + "\n" + MARKER + "\n" + rest
    else:
        patched = MARKER + "\n" + patched

    compile(patched, target, "exec")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = target + BACKUP_SUFFIX + "_" + stamp
    shutil.copy2(target, backup)

    temporary = target + ".clocksync1.tmp"
    with io.open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(patched)

    # Atomarer Ersatz.
    os.rename(temporary, target)

    with io.open(target, "r", encoding="utf-8") as handle:
        verify = handle.read()

    compile(verify, target, "exec")

    checks = (
        MARKER,
        "self._clock_timer = eTimer()",
        "self._clock_timer.start(1000, True)",
        "def _stopClockTimer(self):",
        'time.strftime("%H:%M", now)',
    )
    missing = [item for item in checks if item not in verify]
    if missing:
        fail("Nachkontrolle fehlgeschlagen: %r" % missing)

    print("OK INFUSEMEDIA2026_HOME_CLOCKSYNC1")
    print("- nur InfuseMedia2026/screens/HomeScreen.py geaendert")
    print("- markierte Home-Uhr wird jede Sekunde aktualisiert")
    print("- Quelle ist lokale Box-Zeit via time.localtime()")
    print("- Datum wird gleichzeitig aktualisiert")
    print("- Timer wird beim Schliessen sauber gestoppt")
    print("- Plex/Emby/Jellyfin-Player bleiben unveraendert")
    print("- Backup:", backup)


if __name__ == "__main__":
    main()
