# Entwicklungsstand 2026-09-14

Dieser Ordner sichert den auf der Testbox bestätigten bzw. aktuell getesteten Entwicklungsstand rund um r19.

## Home / Provider / Poster

### `MediaPlugins2026_HOME_SERVERHEALTH1_patcher.py`

- Server-Health für Emby/Jellyfin/Plex
- Zustände: Online, Login nötig, Offline, Fehler, Prüfe, Nicht aktiv
- Status sowohl im Serverwechsel als auch in der unteren Statuszeile

### `MediaPlugins2026_EMBY_LATEST_FALLBACK1_patcher.py`

- `/Items/Latest` bleibt Primärweg
- Fallback auf rekursive `DateCreated`-Abfrage
- Movie, Series, Season, Episode

### `MediaPlugins2026_PROVIDERPLAYER_RESTORE1_FIXED.py`

- Emby → EmbyFlowE2 eigener Player
- Plex → Plex2026 eigener Player
- Jellyfin → interner MediaPlugins-Player
- HomeScreen und MediaDetail verwenden wieder die Provider-Bridge

### `MediaPlugins2026_LATEST_POSTERFIX1_patcher.py`

- Emby Season/Episode: Serien-/PrimaryImageItem-Poster als Fallback
- Einträge ohne irgendein verwertbares Poster werden übersprungen
- Plex: Poster-Fallback über `grandparentRatingKey`/`parentRatingKey`
- Snapshot-Reuse startet wieder den Poster-Prefetch

## Sicherung / Settings / Icons

### `MediaPlugins2026_AUTOBACKUP1_patcher.py`

Grundlage für die neue Sicherungsfunktion:

- einmal pro Kalendertag automatische Konfigurationssicherung beim ersten Pluginstart
- 7-Tage-Rotation
- persistent unter `/etc/enigma2/mediaplugins2026/backups`
- Backup-Ordner `0700`, Dateien `0600`
- Pluginstart wird durch einen Backup-Fehler nicht blockiert

### `MediaPlugins2026_BACKUPCARD_UI1_FIXED.py`

- sichtbare Karte `Sicherungen` direkt unter `GitHub Update`
- Status `Heute HH:MM ✓` und `X / 7 vorhanden`
- rechte Detailansicht mit Automatik, Verlauf, letzter Sicherung und Speicherort
- Cyan Backup-/Database-Icon
- Navigation Server → Update → Sicherungen

### `MediaPlugins2026_ICONALIGN_PROVIDERICONS1_FIXED.py`

- Emby-/Plex-Providericons in den Serverkarten
- Providericon auch in der rechten Server-Detailansicht
- Backup-Icon präzise in der Sicherungskarte ausgerichtet

### `MediaPlugins2026_PROVIDERICON_POLISH1_patcher.py`

Zwischenstufe zur Feinabstimmung der Providericons. Die zunächst zu großen Icons wurden verkleinert.

### `MediaPlugins2026_PROVIDERICON_VISIBLE1_patcher.py`

Finale auf der Testbox sichtbare Providericon-Größe:

- Emby/Plex links 26 px
- Detailansicht 24 px
- kompaktere PNGs mit weniger transparentem Rand
- sauberer Abstand zwischen Icon und Providernamen

### `MediaPlugins2026_BACKUP_RESTORE_FINAL1_patcher.py`

**Autoritativer finaler Backup-/Restore-Stand.** Dieser Patcher fasst die späteren Dialogkorrekturen zusammen und ersetzt die Zwischenstufen im Ordner `intermediate/`.

- Haupt-Settings: `BLAU Importieren` entfernt
- Haupt-Settings: vier gleichmäßige Tasten `GRÜN Server hinzufügen`, `ROT Entfernen`, `GELB Exportieren`, `ZURÜCK`
- Sicherungsdialog:
  - `GRÜN Jetzt sichern`
  - `GELB Exportieren`
  - `BLAU Importieren/Wiederherstellen`
  - `ROT Abbrechen`
- Import hat einen eigenen Bestätigungsschritt
- nach Sicherung/Export/Import bleiben nur `OK Schließen`
- Restore aktualisiert anschließend die Serverliste im Settings-Screen
- Dialog verwendet keine vollflächige `eLabel`, die Text überdecken kann
- finale Überschrift: `Sicherung & Wiederherstellung`

### `MediaPlugins2026_BACKUP_TITLE1_patcher.py`

Kleiner inkrementeller Patch für Boxen, auf denen der Restore-Dialog bereits installiert ist:

- `Sicherung oder Export?` → `Sicherung & Wiederherstellung`

`BACKUP_RESTORE_FINAL1` enthält diese Überschrift bereits.

## Zwischenstände

Unter `intermediate/` liegen die tatsächlich während der Testbox-Debuggingfolge angewendeten Zwischenfixes:

- `MediaPlugins2026_BACKUPDIALOG_LAYERFIX1_patcher.py`
- `MediaPlugins2026_BACKUPDIALOG_NOOVERLAY1_patcher.py`
- `MediaPlugins2026_BACKUP_ACTIONS1_patcher.py`

Sie dokumentieren die Fehlerbehebung, sind für neue Installationen aber durch `BACKUP_RESTORE_FINAL1` ersetzt.

## Bestätigter Teststand

Auf der Box bestätigt:

- Serverstatus zeigt Emby/Plex online und Jellyfin nicht aktiv.
- Emby-`Items/Latest` lieferte 0; der DateCreated-Fallback liefert wieder neue Inhalte.
- Emby startet wieder den EmbyFlowE2-Player.
- `Neu hinzugefügt` zeigt Emby 15 + Plex 15 ohne leere Poster.
- tägliche Sicherung wurde angelegt und in der Settings-Karte sichtbar angezeigt.
- Sicherungsdialog rendert vollständig im Media-Plugins-2026-Stil.
- manueller Export nach `/tmp/mediaplugins2026_unified_backup.json` funktioniert.
- Emby-/Plex-Icons werden im Settings-Screen sichtbar dargestellt.
- Backup-/Restore-Dialog zeigt final die vier getrennten Aktionen Sichern, Export, Import und Abbrechen.

## Empfohlene Patch-Reihenfolge für r19-Testbox

1. `MediaPlugins2026_AUTOBACKUP1_patcher.py`
2. `MediaPlugins2026_BACKUPCARD_UI1_FIXED.py`
3. `MediaPlugins2026_ICONALIGN_PROVIDERICONS1_FIXED.py`
4. `MediaPlugins2026_PROVIDERICON_POLISH1_patcher.py`
5. `MediaPlugins2026_PROVIDERICON_VISIBLE1_patcher.py`
6. `MediaPlugins2026_BACKUP_RESTORE_FINAL1_patcher.py`

`MediaPlugins2026_BACKUP_TITLE1_patcher.py` ist danach nicht mehr nötig, weil die finale Überschrift bereits in Schritt 6 enthalten ist.

## Release-Status

`2026.1-r19` bleibt der aktuelle stabile Release. Die hier dokumentierten Poster-, Sicherungs-, Restore- und Settings-Fixes sind der bestätigte Entwicklungsstand für den nächsten Release. `update.json` bleibt bis zu einem bewusst gebauten Folge-Release auf `2026.1-r19`.
