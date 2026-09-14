# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import re
import shutil
import sys

PLUGIN_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
JELLY_REL = "backends/jellyfin_client.py"
PLEX_REL = "backends/plex_client.py"
HOME_REL = "screens/HomeScreen.py"
MARKER_JELLY = "# MEDIAPLUGINS2026_LATEST_POSTERFIX1_EMBY"
MARKER_PLEX = "# MEDIAPLUGINS2026_LATEST_POSTERFIX1_PLEX"
MARKER_HOME = "# MEDIAPLUGINS2026_LATEST_POSTERFIX1_HOME"

JELLY_METHOD = '''    # MEDIAPLUGINS2026_LATEST_POSTERFIX1_EMBY
    def _fetch_latest_by_type(self, sections, callback, error_callback):
        primary_url = (
            "%s/Users/%s/Items/Latest?Limit=40"
            "&Fields=ImageTags,PrimaryImageItemId,SeriesId,ParentId,"
            "DateCreated,Overview,Genres,ProductionYear,RunTimeTicks,"
            "MediaSources,UserData,SeriesName,IndexNumber,ParentIndexNumber,"
            "ProviderIds,Container"
        ) % (self._build_base_url(), self.user_id)

        def finish(items):
            sections.append({
                "section_id": "latest",
                "title": "Neu hinzugefügt",
                "items": (items or [])[:15],
                "is_resume": False,
            })
            callback(sections)

        def convert(raw_items):
            items = []
            for raw in raw_items or []:
                if not isinstance(raw, dict) or raw.get("IsFolder"):
                    continue

                item = MediaItem.from_jellyfin(raw, self)
                image_tags = raw.get("ImageTags")
                image_tags_known = isinstance(image_tags, dict)
                has_own_primary = bool(image_tags.get("Primary")) if image_tags_known else None
                fallback_id = raw.get("PrimaryImageItemId") or raw.get("SeriesId")

                if has_own_primary is False:
                    if fallback_id and str(fallback_id) != str(raw.get("Id") or ""):
                        item.poster_url = self.get_image_url(fallback_id, "Primary")
                    elif image_tags_known:
                        continue

                items.append(item)
                if len(items) >= 15:
                    break
            return items

        def parse_latest_list(data):
            raw = json.loads(data)
            if not isinstance(raw, list):
                return []
            return convert(raw)

        def parse_fallback_items(data):
            parsed = json.loads(data)
            raw = parsed.get("Items", []) if isinstance(parsed, dict) else []
            return convert(raw)

        def start_fallback(reason):
            log.warning(
                "Home Latest (%s): Items/Latest leer/fehlgeschlagen (%s), verwende DateCreated-Fallback mit Poster-Fallback",
                self.server_name, reason
            )
            fallback_url = (
                "%s/Users/%s/Items?"
                "Recursive=true&Filters=IsNotFolder"
                "&IncludeItemTypes=Movie,Series,Season,Episode"
                "&SortBy=DateCreated&SortOrder=Descending"
                "&Limit=40"
                "&Fields=DateCreated,Overview,Genres,ProductionYear,RunTimeTicks,"
                "MediaSources,UserData,SeriesName,SeriesId,PrimaryImageItemId,"
                "ParentId,ImageTags,IndexNumber,ParentIndexNumber,"
                "ProviderIds,Container"
            ) % (self._build_base_url(), self.user_id)

            def on_fallback(data):
                try:
                    items = parse_fallback_items(data)
                    log.info(
                        "Home Latest (%s): DateCreated-PosterFallback count=%d",
                        self.server_name, len(items)
                    )
                    finish(items)
                except Exception as exc:
                    log.warning(
                        "Home Latest (%s): DateCreated-PosterFallback nicht verwertbar: %s",
                        self.server_name, exc
                    )
                    finish([])

            def on_fallback_error(err):
                log.warning(
                    "Home Latest (%s): DateCreated-PosterFallback fehlgeschlagen: %s",
                    self.server_name, err
                )
                finish([])

            self._get(fallback_url, on_fallback, on_fallback_error)

        def on_latest(data):
            try:
                items = parse_latest_list(data)
            except Exception as exc:
                start_fallback("parse: %s" % exc)
                return

            if items:
                log.info(
                    "Home Latest (%s): Items/Latest PosterFallback count=%d",
                    self.server_name, len(items)
                )
                finish(items)
                return

            start_fallback("0 verwertbare Eintraege")

        def on_latest_error(err):
            start_fallback("request: %s" % err)

        self._get(primary_url, on_latest, on_latest_error)
'''

PLEX_OLD = '''        if media_type == "episode":
            # Episode: echtes 16:9-Still in passender Aufloesung.
            poster_url = self._image_url(
                a.get("thumb") or a.get("parentThumb") or a.get("grandparentThumb"),
                640,
                360,
            )
        else:
            # Filme/Serien/Staffeln bleiben Hochformat-Poster.
            poster_url = self._image_url(
                a.get("thumb") or a.get("parentThumb") or a.get("grandparentThumb"),
                320,
                480,
            )
'''

PLEX_NEW = '''        # MEDIAPLUGINS2026_LATEST_POSTERFIX1_PLEX
        poster_path = (
            a.get("thumb")
            or a.get("parentThumb")
            or a.get("grandparentThumb")
        )
        poster_from_parent_key = False

        if not poster_path:
            poster_parent_key = (
                a.get("grandparentRatingKey")
                or a.get("parentRatingKey")
            )
            if poster_parent_key:
                poster_path = "/library/metadata/%s/thumb" % poster_parent_key
                poster_from_parent_key = True

        if media_type == "episode" and not poster_from_parent_key:
            poster_url = self._image_url(poster_path, 640, 360)
        else:
            poster_url = self._image_url(poster_path, 320, 480)
'''

HOME_HELPER = '''    # MEDIAPLUGINS2026_LATEST_POSTERFIX1_HOME
    def _homePrefetchMissingVisiblePosters(self):
        # Snapshot-Schnellpfad tauscht Live-Items absichtlich ohne Komplett-Render.
        # Neue Live-Items muessen trotzdem ihre Poster laden duerfen.
        for row in (self.continueRow, self.favoritesRow, self.latestRow):
            try:
                row._prefetchVisible()
            except Exception as exc:
                log.warning("Home Poster-Prefetch nach Snapshot-Reuse fehlgeschlagen: %s", exc)

'''

HOME_ANCHOR = '''        row._ensureVisible()

    def _buildLayout(self):
'''
HOME_ANCHOR_NEW = '''        row._ensureVisible()

''' + HOME_HELPER + '''    def _buildLayout(self):
'''

HOME_SWAP_OLD = '''            self._homeSwapRowItemsWithoutRender(
                self.latestRow,
                live_latest_filtered,
            )

            self["message"].setText("")
'''
HOME_SWAP_NEW = '''            self._homeSwapRowItemsWithoutRender(
                self.latestRow,
                live_latest_filtered,
            )

            self._homePrefetchMissingVisiblePosters()

            self["message"].setText("")
'''


def read(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def replace_method(text, name, replacement):
    pattern = re.compile(r"(?ms)^    def %s\(.*?(?=^    def |\Z)" % re.escape(name))
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError("%s: erwartete genau 1 Methode, gefunden %d" % (name, len(matches)))
    match = matches[0]
    return text[:match.start()] + replacement.rstrip() + "\n\n" + text[match.end():]


def backup(path, suffix):
    target = path + suffix
    if not os.path.exists(target):
        shutil.copy2(path, target)
    return target


def patch_jelly(text):
    if MARKER_JELLY in text:
        return text
    return replace_method(text, "_fetch_latest_by_type", JELLY_METHOD)


def patch_plex(text):
    if MARKER_PLEX in text:
        return text
    count = text.count(PLEX_OLD)
    if count != 1:
        raise RuntimeError("Plex Posterblock: erwartete genau 1 Fundstelle, gefunden %d" % count)
    return text.replace(PLEX_OLD, PLEX_NEW, 1)


def patch_home(text):
    if MARKER_HOME in text:
        return text
    if text.count(HOME_ANCHOR) != 1:
        raise RuntimeError("Home helper anchor nicht eindeutig gefunden")
    if text.count(HOME_SWAP_OLD) != 1:
        raise RuntimeError("Home snapshot swap anchor nicht eindeutig gefunden")
    text = text.replace(HOME_ANCHOR, HOME_ANCHOR_NEW, 1)
    text = text.replace(HOME_SWAP_OLD, HOME_SWAP_NEW, 1)
    return text


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else PLUGIN_DEFAULT
    jelly_path = os.path.join(root, JELLY_REL)
    plex_path = os.path.join(root, PLEX_REL)
    home_path = os.path.join(root, HOME_REL)

    for path in (jelly_path, plex_path, home_path):
        if not os.path.isfile(path):
            raise SystemExit("Datei nicht gefunden: %s" % path)

    jelly_original = read(jelly_path)
    plex_original = read(plex_path)
    home_original = read(home_path)

    jelly_new = patch_jelly(jelly_original)
    plex_new = patch_plex(plex_original)
    home_new = patch_home(home_original)

    compile(jelly_new, jelly_path, "exec")
    compile(plex_new, plex_path, "exec")
    compile(home_new, home_path, "exec")

    jelly_backup = backup(jelly_path, ".before_latest_posterfix1")
    plex_backup = backup(plex_path, ".before_latest_posterfix1")
    home_backup = backup(home_path, ".before_latest_posterfix1")

    write(jelly_path, jelly_new)
    write(plex_path, plex_new)
    write(home_path, home_new)

    compile(read(jelly_path), jelly_path, "exec")
    compile(read(plex_path), plex_path, "exec")
    compile(read(home_path), home_path, "exec")

    if MARKER_JELLY not in read(jelly_path):
        raise RuntimeError("Emby/Jellyfin Posterfix Marker fehlt")
    if MARKER_PLEX not in read(plex_path):
        raise RuntimeError("Plex Posterfix Marker fehlt")
    if MARKER_HOME not in read(home_path):
        raise RuntimeError("Home Poster-Prefetch Marker fehlt")

    print("OK MEDIAPLUGINS2026_LATEST_POSTERFIX1")
    print("- Emby Season/Episode: Serien-/PrimaryImageItem-Poster als Fallback")
    print("- Emby: Eintraege ohne irgendein verwertbares Poster werden uebersprungen")
    print("- Plex: fehlendes thumb/parentThumb -> grandparent/parent ratingKey Poster")
    print("- Snapshot-Reuse startet Poster-Prefetch fuer frische Live-Items")
    print("- Filme/Serien mit vorhandenem Poster bleiben unveraendert")
    print("Emby/Jellyfin Backup: %s" % jelly_backup)
    print("Plex Backup:          %s" % plex_backup)
    print("Home Backup:          %s" % home_backup)


if __name__ == "__main__":
    main()
