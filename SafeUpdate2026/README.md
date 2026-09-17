# SafeUpdate2026

SafeUpdate2026 ist ein Enigma2-Plugin für KEXEC-/Multiboot-Systeme.

## Telnet-Installation

```sh
wget -qO- https://raw.githubusercontent.com/keggy6893/MediaPlugins2026-Updates/main/SafeUpdate2026/install.sh | sh
```

Der Installer lädt die aktuelle Version, prüft SHA256 und Python-Syntax, sichert eine vorhandene Installation und führt bei Installationsfehlern einen Rollback aus.

## Aktueller Teststand

- Version: `2026.1-r24`
- Backup vor Update
- Live-Fortschritt mit Prozentanzeige
- erneute physische Prüfung gespeicherter Backups
- dynamische Box-/Modellerkennung für verschiedene Enigma2-Receiver
- Update wird erst nach verifiziertem Backup freigegeben

**Hinweis:** Der automatische 24h-Sicherheitsbackup-Modus ist noch in Entwicklung.
