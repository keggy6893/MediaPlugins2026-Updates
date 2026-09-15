# Changelog

## Entwicklungs-Hotfix nach 2026.1-r20 – Poster-Pipeline

- Poster-Pipeline gegen Cold-Boot-/Snapshot-Probleme gehärtet.
- persistenter Poster-Cache ausschließlich intern unter `/etc/enigma2/mediaplugins2026/poster_cache`.
- keine HDD-/USB-Abhängigkeit; harte Grenzen: 12 MiB, 120 Dateien, 14 Tage.
- Cache-Dateien werden vor Verwendung als echte Bilddaten validiert.
- atomische Cache-Schreibvorgänge und ein begrenzter Retry für transiente Downloadfehler.
- Schutz vor stale asynchronen Poster-Callbacks.
- Cold-Boot-Reparaturrunden für noch nicht aufgelöste sichtbare Poster.
- `image_cache = ImageCache()` als Modul-Singleton wiederhergestellt und `_stable_cache_key()` wieder als `@staticmethod` validiert.
- Preview-/Ambient-Callback-State im HomeScreen defensiv initialisiert.
- auf der Testbox nach Reboot bestätigt: `POSTER_REPAIR round=1 ready=20 total=20`, Poster aus lokalem Cache sichtbar und interner Cache aktiv.
- autoritativer Finalizer: `development/2026-09-15/MediaPlugins2026_POSTER_PIPELINE_FINALIZE1_patcher.py`.
- Dokumentation: `development/2026-09-15/README.md`.
- stabiler Update-Kanal bleibt unverändert; noch kein neuer Release.

## Entwicklungs-Hotfix nach 2026.1-r19

### Home / Poster

- **Leere Poster in „Neu hinzugefügt“**: Emby Season/Episode verwenden jetzt Serien-/PrimaryImageItem-Poster als Fallback.
- Emby-Einträge ohne irgendein verwertbares Poster werden aus der Latest-Reihe ausgelassen.
- Plex kann fehlende `thumb`/`parentThumb`/`grandparentThumb` über `grandparentRatingKey` bzw. `parentRatingKey` auflösen.
- Der Home-Snapshot-Reuse startet nach dem Live-Item-Tausch wieder den Poster-Prefetch.
- Auf der Testbox bestätigt: `Neu hinzugefügt` zeigt Emby 15 + Plex 15 ohne leere Poster.

### Sicherungen / Restore

- automatische Konfigurationssicherung einmal pro Kalendertag beim ersten Pluginstart
- persistenter 7-Tage-Verlauf unter `/etc/enigma2/mediaplugins2026/backups`
- Backup-Verzeichnis `0700`, Sicherungsdateien `0600`
- sichtbare `Sicherungen`-Karte unter dem GitHub-Update-Bereich
- Karte zeigt letzte Sicherung sowie `X / 7 vorhanden`
- eigener Media-Plugins-2026-Sicherungsdialog
- getrennte Aktionen:
  - `GRÜN Jetzt sichern`
  - `GELB Exportieren`
  - `BLAU Importieren/Wiederherstellen`
  - `ROT Abbrechen`
- Import/Wiederherstellung hat einen eigenen Bestätigungsschritt
- nach erfolgreicher Aktion bleibt nur `OK Schließen`
- finale Dialogüberschrift: **Sicherung & Wiederherstellung**
- `BLAU Importieren` wurde aus dem Haupt-Settings-Screen entfernt und in den Sicherungsdialog verschoben
- nach Restore wird die Serverliste im Settings-Screen neu geladen

### Settings / Providericons

- sichtbares Cyan Backup-/Database-Icon in der Sicherungskarte
- Emby- und Plex-Providericons in den Serverkarten und im rechten Detailbereich
- finale Größe auf der Testbox: 26 px in Serverkarten, 24 px im Detailbereich
- vier gleichmäßige Hauptbuttons nach Entfernung des redundanten Import-Buttons
- Footer-Hinweis berücksichtigt nun `Sicherungen`

### Dokumentation

Die autoritativen Patcher liegen unter `development/2026-09-14/`.

Für neue r19-Testboxen ist die finale Reihenfolge dokumentiert in:

`development/2026-09-14/README.md`

Der zusammengefasste finale Sicherungs-/Restore-Patcher ist:

`development/2026-09-14/MediaPlugins2026_BACKUP_RESTORE_FINAL1_patcher.py`

Historische Zwischenfixes des Dialog-Debuggings liegen unter `development/2026-09-14/intermediate/`.

Der stabile Update-Kanal bleibt zunächst auf `2026.1-r19`; `update.json` wird erst mit einem bewusst gebauten Folge-Release angehoben.

## 2026.1-r21

Stabiler Poster-Pipeline-Hotfix auf Basis von r20.

### Neu und bestätigt

- Poster bleiben nach vollständigem Reboot verfügbar
- persistenter Cache unter `/etc/enigma2/mediaplugins2026/poster_cache`
- keine HDD-/USB-Abhängigkeit
- harte Cache-Grenzen: 12 MiB / 120 Dateien / 14 Tage
- Bildvalidierung, atomische Writes und ein Retry bei transienten Fehlern
- Generation Guard gegen verspätete asynchrone Poster-Callbacks
- automatische Cold-Boot-Reparatur sichtbarer Poster
- Preview-/Ambient-Async-State defensiv abgesichert
- dunkler Poster-Fallback
- sensible Token/API-Key-Parameter werden in HTTP-Debuglogs geschwärzt
- r20-Funktionsumfang bleibt erhalten

IPK: `enigma2-plugin-extensions-mediaplugins2026_2026.1-r21_all.ipk`

SHA256: `eecd6482a64abea0c63453951eb3529adbf30b8145dd05880279c73b0eed9e5a`

## 2026.1-r20

Stabiler Release des auf der Testbox bestätigten Post-r19-Stands.

### Neu und bestätigt

- leere Poster in „Neu hinzugefügt“ für Emby/Plex behoben
- tägliche Auto-Sicherung mit 7-Tage-Rotation und privaten Dateirechten
- sichtbare Sicherungen-Karte mit Status und Verlauf
- Emby/Plex Provider-Icons in Serverkarten und Detailbereich
- zentraler Dialog „Sicherung & Wiederherstellung“
- GRÜN: heutige Sicherung aktualisieren, GELB: Export, BLAU: Import/Restore, ROT: Abbrechen
- Import aus dem Settings-Hauptscreen entfernt und logisch in den Sicherungsdialog verschoben
- Paket-Hygiene geprüft: keine Backups oder `.pyc`-Dateien

IPK: `enigma2-plugin-extensions-mediaplugins2026_2026.1-r20_all.ipk`

SHA256: `79691535ad537029fed97331eb7c1c94cbd02256d1840c60ac76bffe41df611f`

## 2026.1-r19

Stabiler Release des auf der Testbox bestätigten Post-r18-Stands.

### Neu und bestätigt

- **Server-Health im Home-Screen**: Emby/Jellyfin/Plex unterscheiden Online, Login nötig, Offline, Fehler, Prüfe und Nicht aktiv.
- **Emby „Neu hinzugefügt“ Fallback**: bei leerem/fehlerhaftem `/Items/Latest` wird rekursiv nach `DateCreated` abgefragt.
- **Provider-Player-Routing**: Emby startet den EmbyFlowE2-Player, Plex den Plex2026-Player; Jellyfin bleibt intern.
- Paket-Hygiene erneut geprüft: keine Backups, `.pyc` oder Runtime-Dateien.

IPK: `enigma2-plugin-extensions-mediaplugins2026_2026.1-r19_all.ipk`

SHA256: `e7c42839b3bcf96d922cd9b9f463517751619c2fe96c84aa50fc31a4d0e63edb`

## 2026.1-r18

Erster konsolidierter Release unter dem Namen **Media Plugins 2026**.

### Neu und bestätigt

- Neues **Media Plugins 2026** Branding inklusive neuem Plugin-Logo und Preview-Grafiken
- Modernes Dark-Navy/Cyan-Settings-Fenster bei unveränderter 1600×900-Fenstergröße
- Integrierter **GitHub-Update-Bereich** mit Versions-, Kanal-, Quellen- und Statusanzeige
- Settings-FinalPolish: konsistente Beschriftungen, bereinigte Hinweise und gekürzte lange Server-URLs
- Search-Verfügbarkeitsbreite-Fix: Versions-/Qualitätsangaben wie `2 Versionen · 4K · 1080p` werden vollständig angezeigt
- Unified Continue / Weiterschauen über mehrere Provider
- Providerübergreifende Availability-/Versions-Erkennung für Emby, Jellyfin und Plex
- Verbesserte Resume-Auswahl und formatierte LastPlayed-Anzeige
- Überarbeitete Home-Navigation, Filter und Serverwechsel
- Plex Serien-/Staffelbrowser und finale Episoden-UI mit 5×2 Episodenraster und 16:9-Thumbnails
- Moderne Suche mit Versionszusammenführung und Detailanzeige
- Updater-Kompatibilität für das alte r17-Manifest während der Umstellung auf den neuen Paketnamen

### Paket-Hygiene

Die finale r18-IPK enthält keine Backup-Dateien, keine `.pyc`-Dateien und keine Runtime-, Snapshot-, Suchverlaufs- oder Credential-Dateien.

Paketname:

`enigma2-plugin-extensions-mediaplugins2026`

## 2026.1-r17

Letzte stabile Veröffentlichung unter dem bisherigen Projektnamen. Das alte r17-Release bleibt als Historie erhalten.
