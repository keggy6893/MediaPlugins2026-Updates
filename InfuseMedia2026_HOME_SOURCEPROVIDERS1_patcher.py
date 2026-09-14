#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys
import time

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"
MARKER = "# INFUSEMEDIA2026_HOME_SOURCEPROVIDERS1"
REQUIRED = "# INFUSEMEDIA2026_HOME_AVAILABILITY_ENRICH1"

OLD = '        source_text = provider_name\n        if len(variants) > 1:\n            source_text += " · %d Versionen" % len(variants)\n        self["preview_source"].setText(source_text)\n        self._setWidgetColor(self["preview_source"], _PROVIDER_COLORS.get(provider, "#aebac5"))\n'
NEW = '        # INFUSEMEDIA2026_HOME_SOURCEPROVIDERS1\n        # Quellenzeile aus der tatsaechlich erkannten Verfuegbarkeit bauen.\n        # Resume/Fortschritt bleiben weiterhin am ausgewaehlten Provider.\n        availability_versions = self._previewVersionsByProvider(item)\n        available_provider_names = []\n        for availability_provider in ("emby", "jellyfin", "plex"):\n            if availability_versions.get(availability_provider):\n                available_provider_names.append(\n                    _PROVIDER_NAMES.get(\n                        availability_provider,\n                        availability_provider.capitalize(),\n                    )\n                )\n\n        source_text = " · ".join(available_provider_names) if available_provider_names else provider_name\n        if len(variants) > 1:\n            source_text += " · %d Versionen" % len(variants)\n\n        self["preview_source"].setText(source_text)\n        self._setWidgetColor(self["preview_source"], _PROVIDER_COLORS.get(provider, "#aebac5"))\n'


def fail(message):
    raise SystemExit("ABBRUCH: %s" % message)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_DEFAULT

    if not os.path.isfile(target):
        fail("HomeScreen.py nicht gefunden: %s" % target)

    with io.open(target, "r", encoding="utf-8") as handle:
        original = handle.read()

    if MARKER in original:
        print("HOME_SOURCEPROVIDERS1 bereits installiert")
        return

    if REQUIRED not in original:
        fail("HOME_SOURCEPROVIDERS1 erwartet zuerst HOME_AVAILABILITY_ENRICH1")

    count = original.count(OLD)
    if count != 1:
        fail(
            "Preview-Quellenzeile: erwartet genau 1 Fundstelle, gefunden %d"
            % count
        )

    patched = original.replace(OLD, NEW, 1)
    compile(patched, target, "exec")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = target + ".before_home_sourceproviders1_" + stamp
    shutil.copy2(target, backup)

    tmp = target + ".sourceproviders1.tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(patched)
    os.replace(tmp, target)

    with io.open(target, "r", encoding="utf-8") as handle:
        verify = handle.read()

    compile(verify, target, "exec")

    checks = (
        MARKER,
        "availability_versions = self._previewVersionsByProvider(item)",
        'for availability_provider in ("emby", "jellyfin", "plex"):',
        'source_text = " · ".join(available_provider_names)',
    )
    missing = [x for x in checks if x not in verify]
    if missing:
        fail("Nachkontrolle fehlgeschlagen: %r" % missing)

    print("OK INFUSEMEDIA2026_HOME_SOURCEPROVIDERS1")
    print("- markierte Quellenzeile zeigt alle tatsaechlich gefundenen Provider")
    print("- Beispiel Skyfall: Emby · Plex · 2 Versionen")
    print("- Resume-/Fortschrittsquelle bleibt unveraendert")
    print("- Providerfarbe bleibt die Farbe des ausgewaehlten Resume-Providers")
    print("- Availability-Matcher/Player/Snapshot/Serverdaten unveraendert")
    print("- Backup:", backup)


if __name__ == "__main__":
    main()
