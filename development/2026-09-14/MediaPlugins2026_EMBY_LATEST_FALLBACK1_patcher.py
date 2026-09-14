# -*- coding: utf-8 -*-
import io
import os
import re
import shutil
import sys

MARKER = "MEDIAPLUGINS2026_EMBY_LATEST_FALLBACK1"
DEFAULT_ROOT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"

def read_text(path):
    with io.open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_text(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

def patch_client(text):
    if MARKER in text:
        raise RuntimeError("LATEST_FALLBACK1 ist bereits installiert")

    pattern = re.compile(
        r"(?ms)^    def _fetch_latest_by_type\(self, sections, callback, error_callback\):\n"
        r".*?"
        r"(?=^    def get_items\(self, library_id, callback, error_callback,)"
    )
    match = pattern.search(text)
    if not match:
        raise RuntimeError("Methode _fetch_latest_by_type nicht eindeutig gefunden")

    replacement = '''    # MEDIAPLUGINS2026_EMBY_LATEST_FALLBACK1
    def _fetch_latest_by_type(self, sections, callback, error_callback):
        primary_url = "%s/Users/%s/Items/Latest?Limit=15" % (
            self._build_base_url(), self.user_id
        )

        def finish(items):
            sections.append({
                "section_id": "latest",
                "title": "Neu hinzugefügt",
                "items": items or [],
                "is_resume": False,
            })
            callback(sections)

        def parse_latest_list(data):
            raw = json.loads(data)
            if not isinstance(raw, list):
                return []
            raw = [i for i in raw if isinstance(i, dict) and not i.get("IsFolder")]
            return [MediaItem.from_jellyfin(i, self) for i in raw][:15]

        def parse_fallback_items(data):
            parsed = json.loads(data)
            raw = parsed.get("Items", []) if isinstance(parsed, dict) else []
            raw = [i for i in raw if isinstance(i, dict) and not i.get("IsFolder")]
            return [MediaItem.from_jellyfin(i, self) for i in raw][:15]

        def start_fallback(reason):
            log.warning(
                "Home Latest (%s): Items/Latest leer/fehlgeschlagen (%s), verwende DateCreated-Fallback",
                self.server_name, reason
            )
            fallback_url = (
                "%s/Users/%s/Items?"
                "Recursive=true&Filters=IsNotFolder"
                "&IncludeItemTypes=Movie,Series,Season,Episode"
                "&SortBy=DateCreated&SortOrder=Descending"
                "&Limit=15"
                "&Fields=DateCreated,Overview,Genres,ProductionYear,RunTimeTicks,"
                "MediaSources,UserData,SeriesName,IndexNumber,ParentIndexNumber,"
                "ProviderIds,Container"
            ) % (self._build_base_url(), self.user_id)

            def on_fallback(data):
                try:
                    items = parse_fallback_items(data)
                    log.info(
                        "Home Latest (%s): DateCreated-Fallback count=%d",
                        self.server_name, len(items)
                    )
                    finish(items)
                except Exception as exc:
                    log.warning(
                        "Home Latest (%s): DateCreated-Fallback nicht verwertbar: %s",
                        self.server_name, exc
                    )
                    finish([])

            def on_fallback_error(err):
                log.warning(
                    "Home Latest (%s): DateCreated-Fallback fehlgeschlagen: %s",
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
                    "Home Latest (%s): Items/Latest count=%d",
                    self.server_name, len(items)
                )
                finish(items)
                return

            start_fallback("0 verwertbare Eintraege")

        def on_latest_error(err):
            start_fallback("request: %s" % err)

        self._get(primary_url, on_latest, on_latest_error)

'''

    patched = text[:match.start()] + replacement + text[match.end():]
    compile(patched, "jellyfin_client.py", "exec")
    return patched

def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ROOT
    target = os.path.join(root, "backends", "jellyfin_client.py")
    if not os.path.isfile(target):
        raise SystemExit("Datei nicht gefunden: %s" % target)

    original = read_text(target)
    patched = patch_client(original)

    backup = target + ".before_emby_latest_fallback1"
    if not os.path.exists(backup):
        shutil.copy2(target, backup)

    write_text(target, patched)

    print("OK MEDIAPLUGINS2026_EMBY_LATEST_FALLBACK1")
    print("Geaendert: %s" % target)
    print("Backup:    %s" % backup)
    print("- Items/Latest bleibt Primaerweg")
    print("- bei leer/Fehler: DateCreated-Fallback")
    print("- IncludeItemTypes: Movie,Series,Season,Episode")
    print("- keine Login-/Token-/Plex-/HomeScreen-Aenderung")

if __name__ == "__main__":
    main()
