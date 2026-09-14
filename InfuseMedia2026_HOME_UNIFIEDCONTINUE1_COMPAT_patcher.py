#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys
import time

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"
MARKER = "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE1_COMPAT"

METHOD_ANCHOR = '    def _providerForItem(self, item):\n        label = (getattr(item, "source_label", "") or "").strip().lower()\n'
METHODS = '    # INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE1_COMPAT\n    @staticmethod\n    def _continueProviderIds(item):\n        raw = getattr(item, "provider_ids", None) or {}\n        result = {}\n        try:\n            iterator = raw.items()\n        except Exception:\n            iterator = ()\n        for key, value in iterator:\n            key = str(key or "").strip().lower()\n            value = str(value or "").strip().lower()\n            if key and value:\n                result[key] = value\n        return result\n\n    def _continueUnifiedKey(self, item):\n        """Provider-unabhaengige Medienidentitaet fuer Weiterschauen."""\n        series = self._homeNormalizeTitle(getattr(item, "series_name", ""))\n        season = getattr(item, "season_number", None)\n        episode = getattr(item, "episode_number", None)\n\n        if series and season is not None and episode is not None:\n            try:\n                return ("episode", series, int(season), int(episode))\n            except Exception:\n                pass\n\n        ids = self._continueProviderIds(item)\n        for key in ("imdb", "tmdb", "tvdb"):\n            value = ids.get(key, "")\n            if value:\n                return ("provider-id", key, value)\n\n        title = self._homeNormalizeTitle(getattr(item, "title", ""))\n        if not title:\n            return None\n\n        year = int(getattr(item, "year", 0) or 0)\n        if year:\n            return ("title-year", title, year)\n\n        runtime = int(getattr(item, "runtime_ticks", 0) or 0)\n        if runtime > 0:\n            runtime_minutes = int(round(runtime / 600000000.0))\n            runtime_bucket = int(round(runtime_minutes / 5.0) * 5)\n            return ("title-runtime", title, runtime_bucket)\n\n        return None\n\n    @staticmethod\n    def _continueProgressRatio(item):\n        resume = max(0, int(getattr(item, "resume_ticks", 0) or 0))\n        runtime = max(0, int(getattr(item, "runtime_ticks", 0) or 0))\n        if runtime > 0:\n            return min(1.0, max(0.0, float(resume) / float(runtime)))\n        return 0.0\n\n    def _continueUnifiedScore(self, item):\n        last_played = str(getattr(item, "last_played_date", "") or "")\n        resume = max(0, int(getattr(item, "resume_ticks", 0) or 0))\n        width = max(0, int(getattr(item, "video_width", 0) or 0))\n        height = max(0, int(getattr(item, "video_height", 0) or 0))\n        return (\n            1 if last_played else 0,\n            last_played,\n            self._continueProgressRatio(item),\n            resume,\n            width * height,\n        )\n\n    def _unifyContinueAcrossProviders(self, items):\n        result = []\n        positions = {}\n        groups = {}\n\n        for item in items or []:\n            key = self._continueUnifiedKey(item)\n            if key is None:\n                result.append(item)\n                continue\n\n            if key not in positions:\n                positions[key] = len(result)\n                groups[key] = [item]\n                result.append(item)\n                continue\n\n            groups[key].append(item)\n            pos = positions[key]\n            current = result[pos]\n            if self._continueUnifiedScore(item) > self._continueUnifiedScore(current):\n                result[pos] = item\n\n        merged = 0\n        for key, members in groups.items():\n            if len(members) <= 1:\n                continue\n\n            representative = result[positions[key]]\n            physical = []\n            seen = set()\n            providers = []\n\n            for member in members:\n                variants = list(getattr(member, "ui_variants", None) or [member])\n                for variant in variants:\n                    identity = (\n                        str(getattr(variant, "server_name", "") or ""),\n                        str(getattr(variant, "id", "") or ""),\n                    )\n                    if identity in seen:\n                        continue\n                    seen.add(identity)\n                    physical.append(variant)\n\n                    provider = self._providerForItem(variant)\n                    if provider and provider not in providers:\n                        providers.append(provider)\n\n            try:\n                representative.ui_variants = physical\n                representative.ui_variant_count = len(physical)\n                representative.ui_unified_continue = True\n                representative.ui_unified_providers = tuple(providers)\n                representative.ui_unified_provider_count = len(providers)\n                representative.ui_unified_resume_provider = self._providerForItem(\n                    representative\n                )\n            except Exception:\n                pass\n\n            merged += 1\n\n        if merged:\n            try:\n                log.info(\n                    "UNIFIED_CONTINUE groups=%d input=%d output=%d",\n                    merged,\n                    len(items or []),\n                    len(result),\n                )\n            except Exception:\n                pass\n\n        return result\n\n    def _filteredContinue(self, items, provider):\n        if provider == "all":\n            return self._unifyContinueAcrossProviders(items)\n\n        result = []\n        seen = set()\n\n        for item in items or []:\n            variants = list(getattr(item, "ui_variants", None) or [item])\n            candidates = [\n                variant for variant in variants\n                if self._providerForItem(variant) == provider\n            ]\n            if not candidates:\n                continue\n\n            best = max(candidates, key=self._continueUnifiedScore)\n            identity = (\n                str(getattr(best, "server_name", "") or ""),\n                str(getattr(best, "id", "") or ""),\n            )\n            if identity in seen:\n                continue\n            seen.add(identity)\n            result.append(best)\n\n        return result\n\n    def _providerForItem(self, item):\n        label = (getattr(item, "source_label", "") or "").strip().lower()\n'
OLD_FILTER = 'self.continueRow.setItems(self._filtered(self._all_continue_items, self.continue_filter))'
NEW_FILTER = 'self.continueRow.setItems(self._filteredContinue(self._all_continue_items, self.continue_filter))'


def fail(message):
    raise SystemExit("ABBRUCH: %s" % message)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_DEFAULT

    if not os.path.isfile(target):
        fail("HomeScreen.py nicht gefunden: %s" % target)

    with io.open(target, "r", encoding="utf-8") as handle:
        source = handle.read()

    if MARKER in source:
        print("INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE1_COMPAT bereits installiert")
        return

    if "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE1\n" in source:
        fail("alter UNIFIEDCONTINUE1-Marker gefunden")

    required = (
        "def _homeNormalizeTitle(value):",
        "def _providerForItem(self, item):",
        "self._all_continue_items",
        "self.continue_filter",
        "resume_ticks",
    )
    missing = [x for x in required if x not in source]
    if missing:
        fail("HomeScreen-Struktur unerwartet; fehlt: %r" % missing)

    anchor_count = source.count(METHOD_ANCHOR)
    if anchor_count != 1:
        fail("Provider-Methodenanker: erwartet 1, gefunden %d" % anchor_count)

    filter_count = source.count(OLD_FILTER)
    if filter_count < 1 or filter_count > 4:
        fail("Continue-Renderanker: erwartet 1 bis 4, gefunden %d" % filter_count)

    patched = source.replace(METHOD_ANCHOR, METHODS, 1)
    patched = patched.replace(OLD_FILTER, NEW_FILTER)

    if patched.startswith("# -*- coding: utf-8 -*-"):
        first, rest = patched.split("\n", 1)
        patched = first + "\n" + MARKER + "\n" + rest
    else:
        patched = MARKER + "\n" + patched

    compile(patched, target, "exec")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = target + ".before_unifiedcontinue1_compat_" + stamp
    shutil.copy2(target, backup)

    tmp = target + ".unifiedcontinue1_compat.tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(patched)
    os.replace(tmp, target)

    with io.open(target, "r", encoding="utf-8") as handle:
        verify = handle.read()
    compile(verify, target, "exec")

    checks = (
        MARKER,
        "def _continueUnifiedKey(self, item):",
        "def _unifyContinueAcrossProviders(self, items):",
        "def _filteredContinue(self, items, provider):",
        NEW_FILTER,
    )
    missing = [x for x in checks if x not in verify]
    if missing:
        fail("Nachkontrolle fehlgeschlagen: %r" % missing)

    print("OK INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE1_COMPAT")
    print("- _buildLayout / Snapshot / SKIPFINAL2 bleiben unangetastet")
    print("- Unified Continue entsteht erst beim Rendern")
    print("- Alle: gleiche Medien ueber Provider -> eine Karte")
    print("- Providerfilter bleiben getrennt")
    print("- neuester Last-Played-Stand gewinnt, dann Fortschritt")
    print("- nur lesend, keine Server-Schreibzugriffe")
    print("- ersetzte Continue-Renderstellen:", filter_count)
    print("- Backup:", backup)


if __name__ == "__main__":
    main()
