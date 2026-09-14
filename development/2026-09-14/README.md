# Entwicklungsstand 2026-09-14

Dieser Ordner sichert den auf der Testbox bestätigten Post-r18-Stand.

## Enthalten

### `MediaPlugins2026_HOME_SERVERHEALTH1_patcher.py`

Patcher für `screens/HomeScreen.py`:

- unterscheidet `Online`, `Login nötig`, `Offline`, `Fehler`, `Prüfe` und `Nicht aktiv`
- zeigt denselben Status in „Zu Server wechseln“ und in der unteren Serverstatus-Zeile
- klassifiziert Auth-/Tokenfehler getrennt von echten Verbindungsfehlern
- verändert `keyPlayCurrent()` ausdrücklich nicht und lässt das Provider-Player-Routing unangetastet

### `MediaPlugins2026_EMBY_LATEST_FALLBACK1_patcher.py`

Patcher für `backends/jellyfin_client.py`:

- `/Users/<id>/Items/Latest?Limit=15` bleibt der Primärweg
- bei leerer oder fehlerhafter Antwort Fallback auf eine rekursive Items-Abfrage
- Sortierung nach `DateCreated` absteigend
- Typen: Movie, Series, Season, Episode
- Plex, Login und HomeScreen werden nicht verändert

### `MediaPlugins2026_PROVIDERPLAYER_RESTORE1_FIXED.py`

Patcher für das Provider-Player-Routing:

- Emby → EmbyFlowE2 eigener Player
- Plex → Plex2026 eigener Player
- Jellyfin → interner MediaPlugins-Player
- patcht HomeScreen und MediaDetail
- legt `ProviderPlayerBridge.py` an
- enthält Syntax-/Readback-Prüfungen und Backups

## Bestätigter Teststand

Auf der Box bestätigt:

- Serverstatus zeigt Emby/Plex online und Jellyfin nicht aktiv.
- Plex liefert Home-`Neu hinzugefügt` weiterhin korrekt.
- Emby-`Items/Latest` lieferte 0; dafür wurde der DateCreated-Fallback ergänzt.
- Nach Wiederherstellung der Provider-Bridge startet Emby wieder den EmbyFlowE2-Player.
- Der finale Provider-Restore-Patcher wurde erfolgreich ausgeführt.

## Release-Status

Diese Dateien dokumentieren den **Entwicklungsstand nach 2026.1-r18**. Sie sind noch nicht Bestandteil einer neuen Release-IPK. `update.json` bleibt deshalb unverändert auf `2026.1-r18`.
