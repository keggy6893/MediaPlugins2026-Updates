# Changelog

## Entwicklungs-Hotfix 2026-09-14 (nach 2026.1-r18)

Auf der Testbox bestätigter Entwicklungsstand nach dem r18-Release:

- **Server-Health im Home-Screen**: Emby/Jellyfin/Plex zeigen `Online`, `Login nötig`, `Offline`, `Fehler`, `Prüfe` oder `Nicht aktiv`, sowohl in „Zu Server wechseln“ als auch in der unteren Serverstatus-Zeile.
- **Emby „Neu hinzugefügt“ Fallback**: bleibt `/Items/Latest` leer oder schlägt fehl, wird auf eine rekursive `DateCreated`-Abfrage für Movie/Series/Season/Episode ausgewichen.
- **Provider-Player-Routing wiederhergestellt**: Emby startet wieder den eigenen **EmbyFlowE2-Player**, Plex den **Plex2026-Player**; Jellyfin bleibt auf dem internen MediaPlugins-Player.
- Der Player-Routing-Fix wurde nach dem Server-Health-Umbau erneut auf der Box bestätigt.

Die zugehörigen, getesteten Entwicklungsdateien liegen unter `development/2026-09-14/`.

**Wichtig:** Dieser Entwicklungsstand ist noch **nicht** als neue IPK veröffentlicht. `update.json` bleibt deshalb unverändert auf `2026.1-r18`.

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
