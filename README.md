# Bestätigte Änderungen nach 2026.1-r17

Stand: 14.09.2026

Dieses Archiv enthält ausschließlich Änderungen, die nach der letzten veröffentlichten stabilen IPK `2026.1-r17` erfolgreich getestet bzw. auf der Box bestätigt wurden.

## Erfolgreich bestätigt

- Home-Uhr synchronisiert mit der Boxzeit
- finaler Home-Navigationsfluss inkl. Cross-Row-Navigation und Filterpfeilen
- zweizeilige Titel und längere Titelanzeige
- funktionierender Serverwechsel
- Plex Serien-/Staffelbrowser und finale Episoden-UI
- Disney-artige Suche inkl. Z-Order-, Detail- und Beschreibungsfixes
- providerübergreifende Versionen in der Suche
- Unified Continue für Emby/Plex mit Multi-Alias- und Laufzeit-Matching
- korrekte Auswahl des Resume-/Fortschrittsstands
- saubere LastPlayed-Anzeige ohne rohe Zahlenwerte
- providerübergreifende Verfügbarkeits-Erkennung
- Quellenanzeige wie `Emby · Plex · 2 Versionen`

## Bewusst noch nicht als bestätigt enthalten

- 60-Minuten-Autorefresh
- getrennte Aktualisierungszeiten für Emby/Jellyfin/Plex

Diese beiden Punkte wurden danach gebaut, waren zum Zeitpunkt dieses GitHub-Snapshots aber noch nicht ausdrücklich auf der Box bestätigt. Ebenfalls ausgeschlossen sind abgebrochene/experimentelle Patches sowie nicht bestätigte Search-Autosave-/Availability-Width-/Player-Versuche.

`update.json` bleibt absichtlich auf `2026.1-r17`, bis daraus eine konsolidierte IPK gebaut und als kompletter Stand getestet wurde.
