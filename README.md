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

## 2026.1-r21

Der stabile r21-Hotfix härtet die Poster-Pipeline nach Reboots:

- persistenter interner Poster-Cache ohne HDD/USB-Abhängigkeit
- Cache-Validierung, atomische Writes und Retry
- Cold-Boot-Reparatur und Schutz vor verspäteten Callbacks
- abgesicherter Preview-/Ambient-State
- dunkler Poster-Fallback
- HTTP-Debuglogs schwärzen Token/API-Keys

Release-IPK: `enigma2-plugin-extensions-mediaplugins2026_2026.1-r21_all.ipk`

SHA256: `eecd6482a64abea0c63453951eb3529adbf30b8145dd05880279c73b0eed9e5a`

## 2026.1-r20

Der stabile r20-Stand ergänzt r19 um:

- Poster-Fallbacks für Emby/Plex in „Neu hinzugefügt“
- automatische tägliche Konfigurationssicherung mit 7-Tage-Rotation
- sichtbare Sicherungen-Karte im Settings-Screen
- Emby/Plex Provider-Icons
- zentralen Dialog **Sicherung & Wiederherstellung** mit Sichern, Export und Import

Release-IPK: `enigma2-plugin-extensions-mediaplugins2026_2026.1-r20_all.ipk`

SHA256: `79691535ad537029fed97331eb7c1c94cbd02256d1840c60ac76bffe41df611f`

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
