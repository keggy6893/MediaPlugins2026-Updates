# Changelog

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
