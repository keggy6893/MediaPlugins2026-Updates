# Media Plugins 2026

Eine gemeinsame Enigma2-Oberfläche für Emby, Jellyfin und Plex.

## Funktionen

- Unified Continue / Weiterschauen über mehrere Provider
- Providerübergreifende Verfügbarkeit und Versionsanzeige
- Favoriten und zuletzt hinzugefügte Inhalte
- Moderne Suche mit Provider-/Versionsinformationen
- Plex Serien-, Staffel- und Episodenansicht
- Serverwechsel direkt aus der Oberfläche
- Lokaler Home-Snapshot für schnellen Start
- Modernes Dark-Navy/Cyan-Settings-Fenster
- Integrierter GitHub-Update-Bereich
- Eigenes Media Plugins 2026 Branding und Logo

## 2026.1-r19

Der stabile r19-Stand ergänzt r18 um:

- Server-Health-Status für Emby/Jellyfin/Plex im Home-Screen
- Emby-Fallback für „Neu hinzugefügt“, falls `/Items/Latest` leer bleibt
- Provider-Player-Routing: Emby → EmbyFlowE2, Plex → Plex2026

Release-IPK: `enigma2-plugin-extensions-mediaplugins2026_2026.1-r19_all.ipk`

SHA256: `e7c42839b3bcf96d922cd9b9f463517751619c2fe96c84aa50fc31a4d0e63edb`

## Paket

`enigma2-plugin-extensions-mediaplugins2026`

## 2026.1-r18

Der r18-Build ist auf der Box bestätigt und enthält den konsolidierten Media-Plugins-2026-Stand inklusive Branding, Settings, GitHub-Updater, FinalPolish, Search-Verfügbarkeitsbreite-Fix, Unified Continue / Availability sowie der Plex Serien-/Staffel-/Episoden-UI.

Die Release-IPK ist bereinigt: keine Backup-Dateien, keine `.pyc`-Dateien und keine Runtime-/Snapshot-/Suchverlaufsdaten im Paket.
