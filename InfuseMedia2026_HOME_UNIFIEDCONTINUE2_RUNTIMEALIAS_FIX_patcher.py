#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function
import io, os, shutil, sys, time

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"
MARKER = "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE2_RUNTIMEALIAS_FIX"
REQUIRED = (
    "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE1_COMPAT",
    "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE1_SKIPFINAL2_FIX",
    "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE2_MULTIALIAS",
)
OLD = '        if title and not is_episode:\n            year = int(getattr(item, "year", 0) or 0)\n            if year:\n                aliases.append(("title-year", title, year))\n            else:\n                # Laufzeit nur als Fallback, wenn kein Jahr vorhanden ist.\n                runtime = int(getattr(item, "runtime_ticks", 0) or 0)\n                if runtime > 0:\n                    runtime_minutes = int(round(runtime / 600000000.0))\n                    runtime_bucket = int(round(runtime_minutes / 5.0) * 5)\n                    aliases.append(\n                        ("title-runtime", title, runtime_bucket)\n                    )\n'
NEW = '        if title and not is_episode:\n            year = int(getattr(item, "year", 0) or 0)\n            if year:\n                aliases.append(("title-year", title, year))\n\n            # INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE2_RUNTIMEALIAS_FIX\n            runtime = int(getattr(item, "runtime_ticks", 0) or 0)\n            if runtime > 0:\n                runtime_minutes = int(round(runtime / 600000000.0))\n                runtime_bucket = int(round(runtime_minutes / 5.0) * 5)\n                aliases.append(\n                    ("title-runtime", title, runtime_bucket)\n                )\n'

def fail(msg):
    raise SystemExit("ABBRUCH: %s" % msg)

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_DEFAULT
    if not os.path.isfile(target):
        fail("HomeScreen.py nicht gefunden: %s" % target)

    with io.open(target, "r", encoding="utf-8") as h:
        original = h.read()

    if MARKER in original:
        print("UNIFIEDCONTINUE2_RUNTIMEALIAS_FIX bereits installiert")
        return

    for required in REQUIRED:
        if required not in original:
            fail("Erforderlicher Patch fehlt: %s" % required)

    count = original.count(OLD)
    if count != 1:
        fail("Runtime-Alias-Block: erwartet genau 1 Fundstelle, gefunden %d" % count)

    patched = original.replace(OLD, NEW, 1)
    compile(patched, target, "exec")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = target + ".before_unifiedcontinue2_runtimealias_" + stamp
    shutil.copy2(target, backup)

    tmp = target + ".runtimealiasfix.tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as h:
        h.write(patched)
    os.replace(tmp, target)

    with io.open(target, "r", encoding="utf-8") as h:
        verify = h.read()
    compile(verify, target, "exec")

    if MARKER not in verify:
        fail("Verifikation fehlgeschlagen: Marker fehlt")
    if OLD in verify:
        fail("Verifikation fehlgeschlagen: alter Fallback-Block noch vorhanden")

    print("OK INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE2_RUNTIMEALIAS_FIX")
    print("- Titel+Laufzeit wird jetzt immer zusaetzlich erzeugt")
    print("- Titel+Jahr bleibt erhalten")
    print("- 6 Underground Plex 2019 + Emby year=None koennen jetzt matchen")
    print("- 5-Minuten-Laufzeit-Bucket bleibt unveraendert")
    print("- keine Snapshot-/Render-/Player-/Server-Schreiblogik geaendert")
    print("- Backup:", backup)

if __name__ == "__main__":
    main()
