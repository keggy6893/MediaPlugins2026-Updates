#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys
import time

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"

MARKER = "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE1_SKIPFINAL2_FIX"
REQUIRED = (
    "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE1_COMPAT",
    "# INFUSEMEDIA2026_HOME_SNAPSHOT_SKIPFINAL2",
)

OLD = '        live_continue_filtered = self._filtered(live_continue, self.continue_filter)\n'
NEW = (
    '        # INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE1_SKIPFINAL2_FIX\n'
    '        # SKIPFINAL2 muss dieselbe Unified-Continue-Sicht verwenden wie _applyFilters.\n'
    '        live_continue_filtered = self._filteredContinue(live_continue, self.continue_filter)\n'
)


def fail(message):
    raise SystemExit("ABBRUCH: %s" % message)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_DEFAULT

    if not os.path.isfile(target):
        fail("HomeScreen.py nicht gefunden: %s" % target)

    with io.open(target, "r", encoding="utf-8") as handle:
        original = handle.read()

    if MARKER in original:
        print("UNIFIEDCONTINUE1_SKIPFINAL2_FIX bereits installiert")
        return

    for required in REQUIRED:
        if required not in original:
            fail("Erforderlicher Patch fehlt: %s" % required)

    # Die Unified-Funktion selbst muss aus COMPAT vorhanden sein.
    if "def _filteredContinue(self, items, provider):" not in original:
        fail("_filteredContinue() fehlt trotz COMPAT-Marker")

    count = original.count(OLD)
    if count != 1:
        fail(
            "SKIPFINAL2 Continue-Fast-Path: erwartet genau 1 Fundstelle, gefunden %d"
            % count
        )

    patched = original.replace(OLD, NEW, 1)
    compile(patched, target, "exec")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = target + ".before_unifiedcontinue_skipfinal2_fix_" + stamp
    shutil.copy2(target, backup)

    tmp = target + ".unifiedcontinue_skipfinal2_fix.tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(patched)
    os.replace(tmp, target)

    with io.open(target, "r", encoding="utf-8") as handle:
        verify = handle.read()

    compile(verify, target, "exec")

    if MARKER not in verify:
        fail("Verifikation fehlgeschlagen: Marker fehlt")
    if OLD in verify:
        fail("Verifikation fehlgeschlagen: alter SKIPFINAL2-Continue-Pfad noch vorhanden")
    if 'live_continue_filtered = self._filteredContinue(live_continue, self.continue_filter)' not in verify:
        fail("Verifikation fehlgeschlagen: Unified-Continue-Fast-Path fehlt")

    print("OK INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE1_SKIPFINAL2_FIX")
    print("- SKIPFINAL2 verwendet jetzt _filteredContinue() fuer Weiterschauen")
    print("- Fast-Path FINAL_BUILD_REUSE_VISIBLE bleibt erhalten")
    print("- Favoriten und Neu hinzugefuegt bleiben unveraendert")
    print("- Snapshot/Poster/Player/Serverdaten unveraendert")
    print("- nur eine Codezeile funktional umgestellt")
    print("- Backup:", backup)


if __name__ == "__main__":
    main()
