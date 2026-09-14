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

## Aktueller Entwicklungsstand

Der auf der Testbox bestätigte Stand vom **14.09.2026** ergänzt r18 um:

- Server-Health-Status für Emby/Jellyfin/Plex im Home-Screen
- Emby-Fallback für „Neu hinzugefügt“, falls `/Items/Latest` leer bleibt
- wiederhergestelltes Provider-Player-Routing: Emby → EmbyFlowE2, Plex → Plex2026

Die getesteten Entwicklungsdateien liegen unter [`development/2026-09-14/`](development/2026-09-14/README.md).

Dieser Stand ist noch **keine neue Release-IPK**. Der stabile Update-Kanal in `update.json` bleibt deshalb auf `2026.1-r18`.

## Paket

`enigma2-plugin-extensions-mediaplugins2026`

## 2026.1-r18

Der r18-Build ist auf der Box bestätigt und enthält den konsolidierten Media-Plugins-2026-Stand inklusive Branding, Settings, GitHub-Updater, FinalPolish, Search-Verfügbarkeitsbreite-Fix, Unified Continue / Availability sowie der Plex Serien-/Staffel-/Episoden-UI.

Die Release-IPK ist bereinigt: keine Backup-Dateien, keine `.pyc`-Dateien und keine Runtime-/Snapshot-/Suchverlaufsdaten im Paket.
