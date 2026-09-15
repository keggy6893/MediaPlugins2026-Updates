# MediaPlugins2026 – Poster-Pipeline Hotfix (2026-09-15)

Status: **auf Testbox nach Reboot bestätigt**.

## Problem

Nach einem Reboot konnten die Poster im Home-Screen vollständig leer/weiß bleiben, obwohl Metadaten und Detailbild vorhanden waren.

## Verifizierter Stand

Der aktuelle Finalizer liegt hier:

`MediaPlugins2026_POSTER_PIPELINE_FINALIZE1_patcher.py`

Er finalisiert den bereits gehärteten Poster-Pipeline-Stand und stellt sicher:

- persistenter Poster-Cache ausschließlich intern unter `/etc/enigma2/mediaplugins2026/poster_cache`
- keine HDD-/USB-Abhängigkeit
- harte Cache-Grenzen: 12 MiB / 120 Dateien / 14 Tage
- Bildvalidierung vor Verwendung
- atomische Cache-Schreibvorgänge
- Retry bei transienten Downloadfehlern
- Cold-Boot-Reparatur für sichtbare Poster
- Schutz gegen stale asynchrone Poster-Callbacks
- `image_cache = ImageCache()` als Modul-Singleton vorhanden
- `_stable_cache_key()` wieder korrekt als `@staticmethod`
- defensiver Preview-/Ambient-Async-State im HomeScreen
- tatsächlicher Cache-Pfad wird beim Pluginstart geloggt

## Testnachweis

Auf der Testbox nach vollständigem Reboot:

- `POSTER_REPAIR round=1 ready=20 total=20`
- sichtbare Poster wurden aus lokalem Cache geladen (`READY ... source=local` / `VISIBLE ... source=local`)
- Pluginlog meldete: `PosterCache aktiv: /etc/enigma2/mediaplugins2026/poster_cache`
- interner Cache war vorhanden und befüllt
- die vorherigen AttributeErrors für `_home_ambient_closed` und `_preview_detail_inflight` traten im bestätigten Lauf nicht mehr auf

## Release-Hinweis

Der stabile Update-Kanal bleibt unverändert. Dieser Commit dokumentiert den bestätigten Entwicklungsfix; `update.json` wurde **nicht** auf eine neue Version angehoben.
