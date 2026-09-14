#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys
import time

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"

MARKER = "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE2_MULTIALIAS"
REQUIRED = (
    "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE1_COMPAT",
    "# INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE1_SKIPFINAL2_FIX",
)

OLD_KEY = '    def _continueUnifiedKey(self, item):\n        """Provider-unabhaengige Medienidentitaet fuer Weiterschauen."""\n        series = self._homeNormalizeTitle(getattr(item, "series_name", ""))\n        season = getattr(item, "season_number", None)\n        episode = getattr(item, "episode_number", None)\n\n        if series and season is not None and episode is not None:\n            try:\n                return ("episode", series, int(season), int(episode))\n            except Exception:\n                pass\n\n        ids = self._continueProviderIds(item)\n        for key in ("imdb", "tmdb", "tvdb"):\n            value = ids.get(key, "")\n            if value:\n                return ("provider-id", key, value)\n\n        title = self._homeNormalizeTitle(getattr(item, "title", ""))\n        if not title:\n            return None\n\n        year = int(getattr(item, "year", 0) or 0)\n        if year:\n            return ("title-year", title, year)\n\n        runtime = int(getattr(item, "runtime_ticks", 0) or 0)\n        if runtime > 0:\n            runtime_minutes = int(round(runtime / 600000000.0))\n            runtime_bucket = int(round(runtime_minutes / 5.0) * 5)\n            return ("title-runtime", title, runtime_bucket)\n\n        return None\n'
NEW_KEY = '    # INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE2_MULTIALIAS\n    def _continueUnifiedAliases(self, item):\n        """Alle sicheren Cross-Provider-Identitaeten eines Continue-Eintrags.\n\n        Ein Film darf gleichzeitig IMDb/TMDb/TVDb UND Titel+Jahr besitzen.\n        So koennen zwei Server trotz unterschiedlicher externer ID-Typen ueber\n        Titel+Jahr zusammenfinden. Episoden verwenden zusaetzlich die stabile\n        Serie+Staffel+Folge-Identitaet.\n        """\n        aliases = []\n\n        series = self._homeNormalizeTitle(getattr(item, "series_name", ""))\n        season = getattr(item, "season_number", None)\n        episode = getattr(item, "episode_number", None)\n        is_episode = False\n\n        if series and season is not None and episode is not None:\n            try:\n                aliases.append(\n                    ("episode", series, int(season), int(episode))\n                )\n                is_episode = True\n            except Exception:\n                pass\n\n        ids = self._continueProviderIds(item)\n        for key in ("imdb", "tmdb", "tvdb"):\n            value = ids.get(key, "")\n            if value:\n                aliases.append(("provider-id", key, value))\n\n        title = self._homeNormalizeTitle(getattr(item, "title", ""))\n        if title and not is_episode:\n            year = int(getattr(item, "year", 0) or 0)\n            if year:\n                aliases.append(("title-year", title, year))\n            else:\n                # Laufzeit nur als Fallback, wenn kein Jahr vorhanden ist.\n                runtime = int(getattr(item, "runtime_ticks", 0) or 0)\n                if runtime > 0:\n                    runtime_minutes = int(round(runtime / 600000000.0))\n                    runtime_bucket = int(round(runtime_minutes / 5.0) * 5)\n                    aliases.append(\n                        ("title-runtime", title, runtime_bucket)\n                    )\n\n        # Reihenfolge stabil halten, Dubletten entfernen.\n        result = []\n        seen = set()\n        for alias in aliases:\n            if alias in seen:\n                continue\n            seen.add(alias)\n            result.append(alias)\n        return tuple(result)\n\n    def _continueUnifiedKey(self, item):\n        """Kompatibilitaets-Helfer fuer eventuell vorhandene Aufrufer."""\n        aliases = self._continueUnifiedAliases(item)\n        return aliases[0] if aliases else None\n'
OLD_UNIFY = '    def _unifyContinueAcrossProviders(self, items):\n        result = []\n        positions = {}\n        groups = {}\n\n        for item in items or []:\n            key = self._continueUnifiedKey(item)\n            if key is None:\n                result.append(item)\n                continue\n\n            if key not in positions:\n                positions[key] = len(result)\n                groups[key] = [item]\n                result.append(item)\n                continue\n\n            groups[key].append(item)\n            pos = positions[key]\n            current = result[pos]\n            if self._continueUnifiedScore(item) > self._continueUnifiedScore(current):\n                result[pos] = item\n\n        merged = 0\n        for key, members in groups.items():\n            if len(members) <= 1:\n                continue\n\n            representative = result[positions[key]]\n            physical = []\n            seen = set()\n            providers = []\n\n            for member in members:\n                variants = list(getattr(member, "ui_variants", None) or [member])\n                for variant in variants:\n                    identity = (\n                        str(getattr(variant, "server_name", "") or ""),\n                        str(getattr(variant, "id", "") or ""),\n                    )\n                    if identity in seen:\n                        continue\n                    seen.add(identity)\n                    physical.append(variant)\n\n                    provider = self._providerForItem(variant)\n                    if provider and provider not in providers:\n                        providers.append(provider)\n\n            try:\n                representative.ui_variants = physical\n                representative.ui_variant_count = len(physical)\n                representative.ui_unified_continue = True\n                representative.ui_unified_providers = tuple(providers)\n                representative.ui_unified_provider_count = len(providers)\n                representative.ui_unified_resume_provider = self._providerForItem(\n                    representative\n                )\n            except Exception:\n                pass\n\n            merged += 1\n\n        if merged:\n            try:\n                log.info(\n                    "UNIFIED_CONTINUE groups=%d input=%d output=%d",\n                    merged,\n                    len(items or []),\n                    len(result),\n                )\n            except Exception:\n                pass\n\n        return result\n'
NEW_UNIFY = '    def _unifyContinueAcrossProviders(self, items):\n        """Vereinigt Eintraege, sobald mindestens EINE sichere Identitaet passt.\n\n        Union-Find macht die Zuordnung auch transitiv stabil:\n        A teilt IMDb mit B, B teilt Titel+Jahr mit C -> A/B/C bleiben ein\n        gemeinsames Medium, ohne dass ein bestimmter ID-Typ bevorzugt wird.\n        """\n        items = list(items or [])\n        if not items:\n            return []\n\n        parent = list(range(len(items)))\n        rank = [0] * len(items)\n        alias_owner = {}\n\n        def find(index):\n            while parent[index] != index:\n                parent[index] = parent[parent[index]]\n                index = parent[index]\n            return index\n\n        def union(left, right):\n            left = find(left)\n            right = find(right)\n            if left == right:\n                return left\n            if rank[left] < rank[right]:\n                left, right = right, left\n            parent[right] = left\n            if rank[left] == rank[right]:\n                rank[left] += 1\n            return left\n\n        for index, item in enumerate(items):\n            aliases = self._continueUnifiedAliases(item)\n            for alias in aliases:\n                owner = alias_owner.get(alias)\n                if owner is None:\n                    alias_owner[alias] = index\n                    continue\n                union(index, owner)\n\n        groups = {}\n        order = []\n        for index, item in enumerate(items):\n            root = find(index)\n            if root not in groups:\n                groups[root] = []\n                order.append(root)\n            groups[root].append(item)\n\n        result = []\n        merged = 0\n\n        for root in order:\n            members = groups[root]\n\n            # Der zuletzt abgespielte Stand bleibt der sichtbare Repraesentant.\n            representative = max(\n                members,\n                key=self._continueUnifiedScore,\n            )\n\n            physical = []\n            seen = set()\n            providers = []\n\n            for member in members:\n                variants = list(\n                    getattr(member, "ui_variants", None) or [member]\n                )\n                for variant in variants:\n                    identity = (\n                        str(getattr(variant, "server_name", "") or ""),\n                        str(getattr(variant, "id", "") or ""),\n                    )\n                    if identity in seen:\n                        continue\n                    seen.add(identity)\n                    physical.append(variant)\n\n                    provider = self._providerForItem(variant)\n                    if provider and provider not in providers:\n                        providers.append(provider)\n\n            if len(members) > 1:\n                merged += 1\n                try:\n                    representative.ui_variants = physical\n                    representative.ui_variant_count = len(physical)\n                    representative.ui_unified_continue = True\n                    representative.ui_unified_providers = tuple(providers)\n                    representative.ui_unified_provider_count = len(providers)\n                    representative.ui_unified_resume_provider = (\n                        self._providerForItem(representative)\n                    )\n                except Exception:\n                    pass\n\n            result.append(representative)\n\n        if merged:\n            try:\n                log.info(\n                    "UNIFIED_CONTINUE2 groups=%d input=%d output=%d",\n                    merged,\n                    len(items),\n                    len(result),\n                )\n            except Exception:\n                pass\n\n        return result\n'


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
        print("UNIFIEDCONTINUE2_MULTIALIAS bereits installiert")
        return

    for required in REQUIRED:
        if required not in original:
            fail("Erforderlicher Patch fehlt: %s" % required)

    patched = original
    patched = replace_once(
        patched,
        OLD_KEY,
        NEW_KEY,
        "Continue-Key -> Multi-Alias",
    )
    patched = replace_once(
        patched,
        OLD_UNIFY,
        NEW_UNIFY,
        "Continue-Gruppierung -> Union-Find",
    )

    compile(patched, target, "exec")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = target + ".before_unifiedcontinue2_multialias_" + stamp
    shutil.copy2(target, backup)

    tmp = target + ".unifiedcontinue2_multialias.tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(patched)
    os.replace(tmp, target)

    with io.open(target, "r", encoding="utf-8") as handle:
        verify = handle.read()

    compile(verify, target, "exec")

    checks = (
        MARKER,
        "def _continueUnifiedAliases(self, item):",
        "Union-Find",
        "UNIFIED_CONTINUE2 groups=",
        '("title-year", title, year)',
    )
    missing = [item for item in checks if item not in verify]
    if missing:
        fail("Nachkontrolle fehlgeschlagen: %r" % missing)

    print("OK INFUSEMEDIA2026_HOME_UNIFIEDCONTINUE2_MULTIALIAS")
    print("- jedes Medium kann mehrere Match-IDs gleichzeitig besitzen")
    print("- IMDb/TMDb/TVDb + Titel/Jahr werden parallel ausgewertet")
    print("- 6 Underground Emby/Plex kann ueber Titel+Jahr zusammenfinden")
    print("- Episoden bleiben ueber Serie+Staffel+Folge abgesichert")
    print("- Union-Find verhindert ID-Prioritaetsfehler und kann transitiv mergen")
    print("- Resume-Auswahl bleibt: neuester Last-Played, dann Fortschritt")
    print("- Snapshot/SKIPFINAL2/Player/Server-Schreiblogik unveraendert")
    print("- Backup:", backup)


if __name__ == "__main__":
    main()
