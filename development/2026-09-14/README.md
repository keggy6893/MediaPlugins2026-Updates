# Entwicklungsstand 2026-09-14

Dieser Ordner sichert den auf der Testbox bestätigten bzw. aktuell getesteten Entwicklungsstand rund um r19.

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

### `MediaPlugins2026_LATEST_POSTERFIX1_patcher.py`

Post-r19-Fix für leere Poster in `Neu hinzugefügt`:

- Emby Season/Episode: verwendet `PrimaryImageItemId` bzw. `SeriesId` als Poster-Fallback
- Emby-Einträge ohne irgendein verwertbares Poster werden übersprungen
- Plex: wenn `thumb`, `parentThumb` und `grandparentThumb` fehlen, wird das Poster aus `grandparentRatingKey`/`parentRatingKey` abgeleitet
- der Snapshot-Reuse-Pfad startet nach dem Live-Tausch wieder den Poster-Prefetch
- legt Backups von `jellyfin_client.py`, `plex_client.py` und `HomeScreen.py` an
- Syntaxprüfung der drei gepatchten Dateien wurde auf der Testbox ohne Fehler ausgeführt

## Bestätigter Teststand

Auf der Box bestätigt:

- Serverstatus zeigt Emby/Plex online und Jellyfin nicht aktiv.
- Emby-`Items/Latest` lieferte 0; der DateCreated-Fallback liefert wieder neue Inhalte.
- Nach Wiederherstellung der Provider-Bridge startet Emby wieder den EmbyFlowE2-Player.
- r19 wurde als stabile IPK veröffentlicht und vom integrierten Updater erkannt.
- `LATEST_POSTERFIX1` wurde erfolgreich angewendet; die anschließende Python-Syntaxprüfung war fehlerfrei.

## Release-Status

`2026.1-r19` ist der aktuelle stabile Release. `LATEST_POSTERFIX1` liegt zunächst als Post-r19-Entwicklungsfix in diesem Ordner. `update.json` bleibt bis zu einem bestätigten Folge-Release auf `2026.1-r19`.
