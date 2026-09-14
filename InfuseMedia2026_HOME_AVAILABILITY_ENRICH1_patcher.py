#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys
import time

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"
MARKER = "# INFUSEMEDIA2026_HOME_AVAILABILITY_ENRICH1"

OLD_CROSS_AND_VERSIONS = '    def _previewCrossKey(self, item):\n        provider_ids = getattr(item, "provider_ids", None) or {}\n        for key in ("imdb", "tmdb", "tvdb"):\n            value = str(provider_ids.get(key, "") or "").strip().lower()\n            if value:\n                return ("id", key, value)\n        title = self._homeNormalizeTitle(getattr(item, "title", ""))\n        if not title:\n            return None\n        year = int(getattr(item, "year", 0) or 0)\n        return ("title", title, year) if year else ("title", title)\n\n    def _previewVersionsByProvider(self, selected):\n        result = {"emby": [], "plex": [], "jellyfin": []}\n        selected_key = self._previewCrossKey(selected)\n        selected_identity = (\n            str(getattr(selected, "server_name", "") or ""),\n            str(getattr(selected, "id", "") or ""),\n        )\n        seen = set()\n        pools = self._all_continue_items + self._all_favorite_items + self._all_latest_items\n        for candidate in pools:\n            if selected_key is None:\n                candidate_identity = (\n                    str(getattr(candidate, "server_name", "") or ""),\n                    str(getattr(candidate, "id", "") or ""),\n                )\n                if candidate_identity != selected_identity:\n                    continue\n            elif self._previewCrossKey(candidate) != selected_key:\n                continue\n            members = list(getattr(candidate, "ui_variants", None) or [candidate])\n            for member in members:\n                provider = self._providerForItem(member)\n                identity = (provider, str(getattr(member, "id", "") or ""))\n                if provider not in result or identity in seen:\n                    continue\n                seen.add(identity)\n                result[provider].append(member)\n        # Der fokussierte Eintrag muss auch bei unvollstaendigen Metadaten\n        # sicher in seiner Providerzeile erscheinen.\n        provider = self._providerForItem(selected)\n        if provider in result and not result[provider]:\n            result[provider] = list(getattr(selected, "ui_variants", None) or [selected])\n        return result\n'
NEW_CROSS_AND_VERSIONS = '    # INFUSEMEDIA2026_HOME_AVAILABILITY_ENRICH1\n    def _previewCrossKey(self, item):\n        provider_ids = getattr(item, "provider_ids", None) or {}\n        for key in ("imdb", "tmdb", "tvdb"):\n            value = str(provider_ids.get(key, "") or "").strip().lower()\n            if value:\n                return ("id", key, value)\n        title = self._homeNormalizeTitle(getattr(item, "title", ""))\n        if not title:\n            return None\n        year = int(getattr(item, "year", 0) or 0)\n        return ("title", title, year) if year else ("title", title)\n\n    def _previewAvailabilityTitleAliases(self, item):\n        """Sichere Titel-Aliase nur fuer die Verfuegbarkeitsanzeige."""\n        raw = str(getattr(item, "title", "") or "").strip()\n        result = []\n\n        def add(value):\n            value = self._homeNormalizeTitle(value)\n            if value and len(value) >= 4 and value not in result:\n                result.append(value)\n\n        add(raw)\n\n        # Beispiel:\n        # "James Bond 007 - Skyfall" -> zusaetzlicher Alias "skyfall".\n        # Nur klare Trennzeichen verwenden; kein aggressives Wort-Loeschen.\n        for separator in (" - ", " – ", " — "):\n            if separator in raw:\n                tail = raw.rsplit(separator, 1)[-1].strip()\n                add(tail)\n\n        return tuple(result)\n\n    @staticmethod\n    def _previewAvailabilityRuntimeClose(left, right):\n        left = int(getattr(left, "runtime_ticks", 0) or 0)\n        right = int(getattr(right, "runtime_ticks", 0) or 0)\n        if left <= 0 or right <= 0:\n            return False\n        # Maximal 10 Minuten Differenz: verschiedene Encodes/Cuts duerfen\n        # leicht abweichen, deutlich andere Filme aber nicht.\n        return abs(left - right) <= (10 * 60 * 10000000)\n\n    def _previewAvailabilityMatch(self, selected, candidate):\n        """Strenger Cross-Provider-Match fuer \'Verfuegbar bei\'."""\n        if selected is None or candidate is None:\n            return False\n\n        # 1. Externe IDs sind der staerkste Treffer.\n        left_ids = self._continueProviderIds(selected) if hasattr(self, "_continueProviderIds") else {}\n        right_ids = self._continueProviderIds(candidate) if hasattr(self, "_continueProviderIds") else {}\n        for key in ("imdb", "tmdb", "tvdb"):\n            if left_ids.get(key) and left_ids.get(key) == right_ids.get(key):\n                return True\n\n        # 2. Titel bzw. sicherer Suffix-Alias muss uebereinstimmen.\n        left_titles = set(self._previewAvailabilityTitleAliases(selected))\n        right_titles = set(self._previewAvailabilityTitleAliases(candidate))\n        if not left_titles or not right_titles or not (left_titles & right_titles):\n            return False\n\n        left_year = int(getattr(selected, "year", 0) or 0)\n        right_year = int(getattr(candidate, "year", 0) or 0)\n\n        # Wenn beide Jahre bekannt sind, muessen sie identisch sein.\n        if left_year and right_year:\n            return left_year == right_year\n\n        # Fehlt auf mindestens einer Seite das Jahr, dient die Laufzeit als\n        # Sicherheitsnetz. Damit matchen gleiche Encodes trotz Metadatenluecke.\n        return self._previewAvailabilityRuntimeClose(selected, candidate)\n\n    def _previewAvailabilityQuery(self, item):\n        raw = str(getattr(item, "title", "") or "").strip()\n        for separator in (" - ", " – ", " — "):\n            if separator in raw:\n                tail = raw.rsplit(separator, 1)[-1].strip()\n                if len(tail) >= 4:\n                    return tail\n        return raw\n\n    def _previewAvailabilityState(self):\n        if not hasattr(self, "_preview_availability_cache"):\n            self._preview_availability_cache = {}\n        if not hasattr(self, "_preview_availability_done"):\n            self._preview_availability_done = set()\n        if not hasattr(self, "_preview_availability_inflight"):\n            self._preview_availability_inflight = set()\n        return (\n            self._preview_availability_cache,\n            self._preview_availability_done,\n            self._preview_availability_inflight,\n        )\n\n    def _requestPreviewAvailability(self, selected):\n        """Andere Provider asynchron suchen; keinerlei Resume-Daten schreiben."""\n        key = self._previewDetailKey(selected)\n        if key is None or getattr(selected, "is_demo", False):\n            return\n\n        query = self._previewAvailabilityQuery(selected)\n        if len(query) < 2:\n            return\n\n        cache, done, inflight = self._previewAvailabilityState()\n        cache.setdefault(key, [])\n\n        selected_provider = self._providerForItem(selected)\n\n        for server_name, client in self.clients.items():\n            cfg = self.server_configs.get(server_name)\n            provider = str(getattr(cfg, "protocol", "") or "").lower()\n            if provider not in ("emby", "jellyfin", "plex"):\n                continue\n\n            # Der Provider des echten Resume-Eintrags ist bereits bekannt.\n            if provider == selected_provider:\n                continue\n\n            request_key = (key, server_name)\n            if request_key in done or request_key in inflight:\n                continue\n            if not hasattr(client, "search"):\n                done.add(request_key)\n                continue\n\n            inflight.add(request_key)\n\n            def on_items(items, rk=request_key, target=selected, target_key=key):\n                _cache, _done, _inflight = self._previewAvailabilityState()\n                _inflight.discard(rk)\n                _done.add(rk)\n\n                existing = {\n                    (\n                        str(getattr(x, "server_name", "") or ""),\n                        str(getattr(x, "id", "") or ""),\n                    )\n                    for x in _cache.setdefault(target_key, [])\n                }\n\n                for candidate in items or []:\n                    try:\n                        if not self._previewAvailabilityMatch(target, candidate):\n                            continue\n                        identity = (\n                            str(getattr(candidate, "server_name", "") or ""),\n                            str(getattr(candidate, "id", "") or ""),\n                        )\n                        if identity in existing:\n                            continue\n                        existing.add(identity)\n                        _cache[target_key].append(candidate)\n                    except Exception:\n                        continue\n\n                current = self._previewItem()\n                if self._previewDetailKey(current) == target_key:\n                    self._updatePreview()\n\n            def on_error(error, rk=request_key, target_key=key):\n                _cache, _done, _inflight = self._previewAvailabilityState()\n                _inflight.discard(rk)\n                _done.add(rk)\n                try:\n                    log.warning(\n                        "Home-Verfuegbarkeitssuche fehlgeschlagen (%s): %s",\n                        rk[1], error,\n                    )\n                except Exception:\n                    pass\n\n            try:\n                client.search(query, on_items, on_error)\n            except Exception as error:\n                on_error(error)\n\n    def _previewVersionsByProvider(self, selected):\n        result = {"emby": [], "plex": [], "jellyfin": []}\n        selected_key = self._previewCrossKey(selected)\n        selected_identity = (\n            str(getattr(selected, "server_name", "") or ""),\n            str(getattr(selected, "id", "") or ""),\n        )\n        seen = set()\n        pools = self._all_continue_items + self._all_favorite_items + self._all_latest_items\n\n        for candidate in pools:\n            if selected_key is None:\n                candidate_identity = (\n                    str(getattr(candidate, "server_name", "") or ""),\n                    str(getattr(candidate, "id", "") or ""),\n                )\n                if candidate_identity != selected_identity:\n                    continue\n            elif self._previewCrossKey(candidate) != selected_key:\n                # Der alte Home-Pool-Match bleibt absichtlich konservativ.\n                continue\n\n            members = list(getattr(candidate, "ui_variants", None) or [candidate])\n            for member in members:\n                provider = self._providerForItem(member)\n                identity = (\n                    provider,\n                    str(getattr(member, "server_name", "") or ""),\n                    str(getattr(member, "id", "") or ""),\n                )\n                if provider not in result or identity in seen:\n                    continue\n                seen.add(identity)\n                result[provider].append(member)\n\n        # Zusaetzliche Suchtreffer anderer Provider NUR fuer die Anzeige.\n        cache, _done, _inflight = self._previewAvailabilityState()\n        availability_key = self._previewDetailKey(selected)\n        for member in cache.get(availability_key, []):\n            provider = self._providerForItem(member)\n            identity = (\n                provider,\n                str(getattr(member, "server_name", "") or ""),\n                str(getattr(member, "id", "") or ""),\n            )\n            if provider not in result or identity in seen:\n                continue\n            seen.add(identity)\n            result[provider].append(member)\n\n        # Der fokussierte echte Eintrag muss sicher erscheinen.\n        provider = self._providerForItem(selected)\n        if provider in result and not result[provider]:\n            result[provider] = list(getattr(selected, "ui_variants", None) or [selected])\n\n        return result\n'
OLD_CACHED = '        cached = self._preview_detail_cache.get(key)\n        if cached is not None:\n            self._mergePreviewDetail(item, cached)\n            return\n'
NEW_CACHED = '        cached = self._preview_detail_cache.get(key)\n        if cached is not None:\n            self._mergePreviewDetail(item, cached)\n            # INFUSEMEDIA2026_HOME_AVAILABILITY_ENRICH1:\n            # Erst mit angereicherten Details auf anderen Providern suchen.\n            self._requestPreviewAvailability(item)\n            return\n'
OLD_LOADED = '        self._preview_detail_cache[key] = detail\n        self._mergePreviewDetail(target, detail)\n\n        # Die Antwort darf nur die Karte aktualisieren, die jetzt noch im\n'
NEW_LOADED = '        self._preview_detail_cache[key] = detail\n        self._mergePreviewDetail(target, detail)\n\n        # INFUSEMEDIA2026_HOME_AVAILABILITY_ENRICH1:\n        # Resume bleibt am echten Continue-Item; andere Provider liefern\n        # ausschliesslich Verfuegbarkeits-/Qualitaetsinformationen.\n        self._requestPreviewAvailability(target)\n\n        # Die Antwort darf nur die Karte aktualisieren, die jetzt noch im\n'


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
        print("HOME_AVAILABILITY_ENRICH1 bereits installiert")
        return

    required = (
        "def _previewCrossKey(self, item):",
        "def _previewVersionsByProvider(self, selected):",
        "def _preparePreviewDetail(self, item):",
        "def _previewDetailLoaded(self, serial, key, target, detail):",
        "self.clients",
        "self.server_configs",
    )
    missing = [x for x in required if x not in original]
    if missing:
        fail("HomeScreen-Struktur unerwartet; fehlt: %r" % missing)

    patched = original
    patched = replace_once(
        patched,
        OLD_CROSS_AND_VERSIONS,
        NEW_CROSS_AND_VERSIONS,
        "Preview-Verfuegbarkeitsblock",
    )
    patched = replace_once(
        patched,
        OLD_CACHED,
        NEW_CACHED,
        "Detail-Cache-Hook",
    )
    patched = replace_once(
        patched,
        OLD_LOADED,
        NEW_LOADED,
        "Detail-Loaded-Hook",
    )

    compile(patched, target, "exec")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = target + ".before_home_availability_enrich1_" + stamp
    shutil.copy2(target, backup)

    tmp = target + ".availability_enrich1.tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(patched)
    os.replace(tmp, target)

    with io.open(target, "r", encoding="utf-8") as handle:
        verify = handle.read()

    compile(verify, target, "exec")

    checks = (
        MARKER,
        "def _requestPreviewAvailability(self, selected):",
        "def _previewAvailabilityMatch(self, selected, candidate):",
        "cache.get(availability_key, [])",
        "client.search(query, on_items, on_error)",
    )
    missing = [x for x in checks if x not in verify]
    if missing:
        fail("Nachkontrolle fehlgeschlagen: %r" % missing)

    print("OK INFUSEMEDIA2026_HOME_AVAILABILITY_ENRICH1")
    print("- Resume/Progress bleibt ausschliesslich am echten Weiterschauen-Eintrag")
    print("- andere verbundene Provider werden nach geladenen Detaildaten gesucht")
    print("- Treffer ergaenzen nur 'Verfuegbar bei' und Qualitaet")
    print("- keine Treffer werden in ui_variants/Continue-Filter geschrieben")
    print("- Skyfall: 'James Bond 007 - Skyfall' kann ueber Alias 'Skyfall' matchen")
    print("- Suchergebnisse werden pro Karte/Server gecacht; keine Request-Schleife")
    print("- keine Player-/Resume-/Server-Schreiblogik geaendert")
    print("- Backup:", backup)


if __name__ == "__main__":
    main()
