# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"
MARKER = "# INFUSEMEDIA2026_HOME_NAVFLOW2_FIXED"
BACKUP_SUFFIX = ".before_navflow2_fixed"

OLD_ZONES = '    def _zones(self):\n        zones = []\n        if self.continueRow.getCount() > 0:\n            zones.append("continue")\n        zones.append("fav_filter")\n        if self.favoritesRow.getCount() > 0:\n            zones.append("favorites")\n        zones.append("latest_filter")\n        if self.latestRow.getCount() > 0:\n            zones.append("latest")\n        zones.append("server_switch")\n        return zones\n'
NEW_ZONES = '    def _zones(self):\n        # Normale HOCH/RUNTER-Navigation folgt nur sichtbaren Reihen.\n        # Filterchips bleiben ueber GELB erreichbar.\n        zones = []\n        if self.continueRow.getCount() > 0:\n            zones.append("continue")\n        if self.favoritesRow.getCount() > 0:\n            zones.append("favorites")\n        if self.latestRow.getCount() > 0:\n            zones.append("latest")\n        zones.append("server_switch")\n        return zones\n'
OLD_DOWN = '    def keyDown(self):\n        self._touchHomeSlideshow()\n\n        if self.zone == "server_switch":\n            providers = self._serverSwitchProviders()\n            if self.server_switch_index < len(providers) - 1:\n                self.server_switch_index += 1\n                self._renderServerSwitch()\n            return\n\n        # Navigation muss der sichtbaren Reihenfolge folgen:\n        # Favoriten -> Filter Neu hinzugefuegt -> Neu hinzugefuegt -> Serverwechsel.\n        # Nur von der letzten Medienreihe direkt in den Serverbereich springen.\n        if self.zone == "latest":\n            self._enterServerSwitch(self._previewItem(), self.zone)\n            return\n\n        self._moveZone(1)\n'
NEW_DOWN = '    def keyDown(self):\n        self._touchHomeSlideshow()\n\n        if self.zone == "server_switch":\n            providers = self._serverSwitchProviders()\n            if self.server_switch_index < len(providers) - 1:\n                self.server_switch_index += 1\n                self._renderServerSwitch()\n            return\n\n        if self.zone == "fav_filter":\n            if self.favoritesRow.getCount() > 0:\n                self.zone = "favorites"\n                self._refreshFocus()\n            return\n\n        if self.zone == "latest_filter":\n            if self.latestRow.getCount() > 0:\n                self.zone = "latest"\n                self._refreshFocus()\n            return\n\n        # Sichtbar: Weiterschauen -> Favoriten -> Neu hinzugefuegt -> Serverwechsel.\n        self._moveZone(1)\n'
OLD_UP = '    def keyUp(self):\n        self._touchHomeSlideshow()\n        if self.zone == "server_switch":\n            if self.server_switch_index > 0:\n                self.server_switch_index -= 1\n                self._renderServerSwitch()\n            else:\n                self._leaveServerSwitch()\n            return\n        self._moveZone(-1)\n'
NEW_UP = '    def keyUp(self):\n        self._touchHomeSlideshow()\n        if self.zone == "server_switch":\n            if self.server_switch_index > 0:\n                self.server_switch_index -= 1\n                self._renderServerSwitch()\n            else:\n                self._leaveServerSwitch()\n            return\n\n        if self.zone == "fav_filter":\n            if self.favoritesRow.getCount() > 0:\n                self.zone = "favorites"\n                self._refreshFocus()\n            return\n\n        if self.zone == "latest_filter":\n            if self.latestRow.getCount() > 0:\n                self.zone = "latest"\n                self._refreshFocus()\n            return\n\n        self._moveZone(-1)\n'


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            "%s: erwartete genau 1 Fundstelle, gefunden %d" % (label, count)
        )
    return text.replace(old, new, 1)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_DEFAULT
    if not os.path.isfile(target):
        raise SystemExit("Datei nicht gefunden: %s" % target)

    with io.open(target, "r", encoding="utf-8") as handle:
        original = handle.read()

    if MARKER in original:
        print("HOME_NAVFLOW2_FIXED bereits installiert: %s" % target)
        return

    patched = replace_once(original, OLD_ZONES, NEW_ZONES, "_zones")
    patched = replace_once(patched, OLD_DOWN, NEW_DOWN, "keyDown")
    patched = replace_once(patched, OLD_UP, NEW_UP, "keyUp")

    if patched.startswith("# -*- coding: utf-8 -*-"):
        first, rest = patched.split("\n", 1)
        patched = first + "\n" + MARKER + "\n" + rest
    else:
        patched = MARKER + "\n" + patched

    compile(patched, target, "exec")

    backup = target + BACKUP_SUFFIX
    if not os.path.exists(backup):
        shutil.copy2(target, backup)

    with io.open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(patched)

    with io.open(target, "r", encoding="utf-8") as handle:
        verify = handle.read()
    compile(verify, target, "exec")

    z0 = verify.index("    def _zones(self):")
    z1 = verify.index("    def _moveZone", z0)
    zones = verify[z0:z1]

    if 'zones.append("fav_filter")' in zones:
        raise RuntimeError("fav_filter noch in normaler _zones-Liste")
    if 'zones.append("latest_filter")' in zones:
        raise RuntimeError("latest_filter noch in normaler _zones-Liste")
    if 'zones.append("latest")' not in zones:
        raise RuntimeError("latest fehlt in normaler _zones-Liste")

    print("OK INFUSEMEDIA2026_HOME_NAVFLOW2_FIXED: %s" % target)
    print("- HOCH/RUNTER: Weiterschauen -> Favoriten -> Neu hinzugefuegt -> Serverwechsel")
    print("- unsichtbare Filter-Zonen aus normaler Navigation entfernt")
    print("- Filter bleiben per GELB erreichbar")
    print("- HOCH/RUNTER im Filter geht direkt zur Posterreihe")
    print("- Links/Rechts in Neu hinzugefuegt funktioniert normal")
    print("- keine Poster-/Server-/Login-Daten geaendert")
    print("- Backup: %s" % backup)


if __name__ == "__main__":
    main()
