# -*- coding: utf-8 -*-
import json
import os
import base64

from .utils import log

CONFIG_PATH = "/etc/enigma2/mediaplugins2026_unified.json"
LEGACY_CONFIG_PATH = "/etc/enigma2/infusemedia2026.json"
BACKUP_PATH = "/etc/enigma2/mediaplugins2026_unified_backup.json"


def _obfuscate(password):
    if not password:
        return ""
    xored = bytes([b ^ 0x5A for b in password.encode("utf-8")])
    return base64.b64encode(xored).decode("ascii")


def _deobfuscate(stored):
    if not stored:
        return ""
    try:
        raw = base64.b64decode(stored.encode("ascii"))
        return bytes([b ^ 0x5A for b in raw]).decode("utf-8")
    except Exception:
        return ""


class ServerConfig(object):
    def __init__(self, name, protocol, address, port, username="",
                 password="", https="auto", path="", library_mode=False,
                 token="", user_id="", imported_from=""):
        self.name = name
        self.protocol = protocol      # "jellyfin" | "emby" | "plex"
        self.address = address
        self.port = port
        self.username = username
        self.password = password
        self.https = https
        self.path = path
        self.library_mode = library_mode
        self.token = token or ""
        self.user_id = user_id or ""
        self.imported_from = imported_from or ""

    def to_dict(self):
        return {
            "name": self.name,
            "protocol": self.protocol,
            "address": self.address,
            "port": self.port,
            "username": self.username,
            "password": _obfuscate(self.password),
            "https": self.https,
            "path": self.path,
            "library_mode": self.library_mode,
            "token": _obfuscate(self.token),
            "user_id": self.user_id,
            "imported_from": self.imported_from,
        }

    @classmethod
    def from_dict(cls, d):
        d = dict(d or {})
        # Backward compatible with r1-r7 and tolerant of future extra keys.
        return cls(
            name=d.get("name", ""),
            protocol=d.get("protocol", ""),
            address=d.get("address", ""),
            port=d.get("port", ""),
            username=d.get("username", ""),
            password=_deobfuscate(d.get("password", "")),
            https=d.get("https", "auto"),
            path=d.get("path", ""),
            library_mode=bool(d.get("library_mode", False)),
            token=_deobfuscate(d.get("token", "")),
            user_id=d.get("user_id", ""),
            imported_from=d.get("imported_from", ""),
        )


class FavoriteEntry(object):
    def __init__(self, entry_type, ref_id, server_name, title, icon=None):
        self.entry_type = entry_type    # "library" | "item" | "link"
        self.ref_id = ref_id
        self.server_name = server_name
        self.title = title
        self.icon = icon

    def to_dict(self):
        return {
            "entry_type": self.entry_type,
            "ref_id": self.ref_id,
            "server_name": self.server_name,
            "title": self.title,
            "icon": self.icon,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


class ConfigStore(object):
    def __init__(self):
        self.servers = []
        self.favorites = []
        self.last_auto_import = []
        self._load()
        # r8: bestehende Einzelplugin-Zugaenge automatisch uebernehmen.
        # Andere Plugins werden dabei ausschliesslich gelesen.
        self.auto_import_existing()

    def _load(self):
        load_path = CONFIG_PATH
        migrated = False
        if not os.path.isfile(load_path):
            if os.path.isfile(LEGACY_CONFIG_PATH):
                load_path = LEGACY_CONFIG_PATH
                migrated = True
            else:
                return
        try:
            with open(load_path, "r") as f:
                data = json.load(f)
            self.servers = [ServerConfig.from_dict(s) for s in data.get("servers", [])]
            self.favorites = [FavoriteEntry.from_dict(x) for x in data.get("favorites", [])]
            log.info("Config geladen: %d Server, %d Favoriten", len(self.servers), len(self.favorites))
            if migrated:
                self._save()
                log.info("Alte InfuseMedia2026-Konfiguration nach Media Plugins 2026 migriert")
        except Exception as e:
            log.exception("Config konnte nicht geladen werden: %s", e)

    def _save(self):
        data = {
            "servers": [s.to_dict() for s in self.servers],
            "favorites": [f.to_dict() for f in self.favorites],
        }
        try:
            conf_dir = os.path.dirname(CONFIG_PATH)
            if not os.path.isdir(conf_dir):
                os.makedirs(conf_dir)
            with open(CONFIG_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.exception("Config konnte nicht gespeichert werden: %s", e)

    def export_backup(self, path=BACKUP_PATH):
        """Export server configuration and favorites to a portable JSON backup."""
        data = {
            "format": "MediaPlugins2026Backup",
            "version": 1,
            "servers": [s.to_dict() for s in self.servers],
            "favorites": [f.to_dict() for f in self.favorites],
        }
        backup_dir = os.path.dirname(path)
        if backup_dir and not os.path.isdir(backup_dir):
            os.makedirs(backup_dir)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass
        log.info("Konfiguration exportiert: %s (%d Server)", path, len(self.servers))
        return path

    def import_backup(self, path=BACKUP_PATH):
        """Validate a backup completely before replacing the live configuration."""
        if not os.path.isfile(path):
            raise ValueError("Backup-Datei nicht gefunden: %s" % path)

        with open(path, "r") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Ungueltiges Backup-Format")
        if data.get("format") not in (None, "MediaPlugins2026Backup", "InfuseMedia2026Backup"):
            raise ValueError("Diese Datei ist kein Media-Plugins-2026-Backup")

        raw_servers = data.get("servers")
        if not isinstance(raw_servers, list):
            raise ValueError("Backup enthaelt keine gueltige Serverliste")

        # Build everything first. No live data is changed until all entries validate.
        new_servers = []
        names = set()
        for raw in raw_servers:
            if not isinstance(raw, dict):
                raise ValueError("Ungueltiger Servereintrag im Backup")
            server = ServerConfig.from_dict(raw)
            if not server.name or not server.address:
                raise ValueError("Servereintrag ohne Name oder Adresse")
            if server.protocol not in ("jellyfin", "emby", "plex"):
                raise ValueError("Unbekannter Servertyp: %s" % server.protocol)
            if server.name in names:
                raise ValueError("Doppelter Servername im Backup: %s" % server.name)
            names.add(server.name)
            new_servers.append(server)

        new_favorites = []
        raw_favorites = data.get("favorites", [])
        if raw_favorites is not None:
            if not isinstance(raw_favorites, list):
                raise ValueError("Ungueltige Favoritenliste im Backup")
            for raw in raw_favorites:
                if not isinstance(raw, dict):
                    raise ValueError("Ungueltiger Favoriteneintrag im Backup")
                fav = FavoriteEntry.from_dict(raw)
                # Keep only favorites that still point at imported servers.
                if fav.server_name in names:
                    new_favorites.append(fav)

        self.servers = new_servers
        self.favorites = new_favorites
        self._save()
        log.info("Konfiguration importiert: %s (%d Server, %d Favoriten)",
                 path, len(self.servers), len(self.favorites))
        return len(self.servers), len(self.favorites)

    @staticmethod
    def _server_key(server):
        return (
            str(getattr(server, "protocol", "") or "").strip().lower(),
            str(getattr(server, "address", "") or "").strip().rstrip("/").lower(),
        )

    def _unique_name(self, wanted):
        wanted = (wanted or "Medienserver").strip() or "Medienserver"
        used = set(s.name for s in self.servers)
        if wanted not in used:
            return wanted
        index = 2
        while "%s %d" % (wanted, index) in used:
            index += 1
        return "%s %d" % (wanted, index)

    # INFUSEMEDIA2026_R16_IMPORT_SOURCE_DEDUPE_LOCALTEST
    def auto_import_existing(self):
        """Copy existing standalone-plugin credentials into our own config.

        No source file is modified.  Existing Media Plugins 2026 servers win; a
        discovered server with the same provider+address is never duplicated.
        """
        try:
            from .utils.credential_bridge import discover_existing_credentials
            candidates = discover_existing_credentials()
        except Exception as exc:
            log.warning("CredentialBridge konnte nicht gestartet werden: %s", exc)
            return []

        # Collapse only entries that originate from the exact same standalone
        # config source. This does NOT collapse different Plex servers merely
        # because they share an account token. Prefer a concrete endpoint over
        # the old account-discovery sentinel.
        deduped = []
        by_source = {}
        changed = False
        for server in self.servers:
            source = str(getattr(server, "imported_from", "") or "").strip()
            protocol = str(getattr(server, "protocol", "") or "").lower()
            source_key = (protocol, source) if source else None
            if not source_key or source_key not in by_source:
                deduped.append(server)
                if source_key:
                    by_source[source_key] = server
                continue
            current = by_source[source_key]
            current_discovery = str(getattr(current, "address", "") or "").rstrip("/").lower() == "plex://account-discovery"
            new_discovery = str(getattr(server, "address", "") or "").rstrip("/").lower() == "plex://account-discovery"
            if current_discovery and not new_discovery:
                idx = deduped.index(current)
                deduped[idx] = server
                by_source[source_key] = server
            changed = True
        if changed:
            self.servers = deduped
            self._save()

        existing = set(self._server_key(s) for s in self.servers)
        imported = []
        for raw in candidates:
            protocol = str(raw.get("protocol") or "").lower()
            address = str(raw.get("address") or "").strip()
            source = str(raw.get("source") or "").strip()
            key = (protocol, address.rstrip("/").lower())
            if not address or protocol not in ("emby", "jellyfin", "plex"):
                continue

            # Same import source means the standalone plugin has updated its
            # endpoint. Refresh our copied endpoint/auth instead of creating a
            # second Plex entry that would repeat slow account discovery.
            source_match = None
            if source:
                for existing_server in self.servers:
                    if ((getattr(existing_server, "protocol", "") or "").lower() == protocol and
                            (getattr(existing_server, "imported_from", "") or "") == source):
                        source_match = existing_server
                        break
            if source_match is not None:
                if address.rstrip("/").lower() != "plex://account-discovery":
                    source_match.address = address.rstrip("/")
                    source_match.port = raw.get("port", "")
                    source_match.path = raw.get("path", "")
                    source_match.https = raw.get("https", "auto")
                # Dieselbe bekannte Importquelle darf ihre kopierten
                # Zugangsdaten aktualisieren. So kann nach einem abgelaufenen
                # Token der Passwort-Fallback mit den aktuellen Credentials
                # arbeiten, ohne die Fremdkonfiguration selbst zu veraendern.
                if raw.get("username"):
                    source_match.username = raw.get("username")
                if raw.get("password"):
                    source_match.password = raw.get("password")
                if raw.get("token"):
                    source_match.token = raw.get("token")
                if raw.get("user_id"):
                    source_match.user_id = raw.get("user_id")
                self._save()
                existing.add(self._server_key(source_match))
                continue

            if key in existing:
                continue
            server = ServerConfig(
                name=self._unique_name(raw.get("name") or (protocol.capitalize() + " · uebernommen")),
                protocol=protocol,
                address=address,
                port=raw.get("port", ""),
                username=raw.get("username", ""),
                password=raw.get("password", ""),
                https=raw.get("https", "auto"),
                path=raw.get("path", ""),
                library_mode=False,
                token=raw.get("token", ""),
                user_id=raw.get("user_id", ""),
                imported_from=raw.get("source", ""),
            )
            self.servers.append(server)
            existing.add(key)
            imported.append(protocol)
            log.info("Zugang automatisch uebernommen: %s aus %s", protocol, raw.get("source", "bestehender Konfiguration"))

        if imported:
            self._save()
            self.last_auto_import = list(imported)
        return imported

    def update_server_endpoint(self, name, address):
        """Persist an auto-discovered server URI (used by Plex2026 bridge)."""
        address = str(address or "").strip().rstrip("/")
        if not address:
            return False
        changed = False
        for server in self.servers:
            if server.name != name:
                continue
            if server.address != address:
                server.address = address
                # URI already contains scheme/port/path; avoid overriding it.
                server.port = ""
                server.path = ""
                server.https = "auto"
                changed = True
            break
        if changed:
            self._save()
        return changed

    def update_server_auth(self, name, token="", user_id=""):
        changed = False
        for server in self.servers:
            if server.name != name:
                continue
            if token and token != server.token:
                server.token = token
                changed = True
            if user_id and user_id != server.user_id:
                server.user_id = user_id
                changed = True
            break
        if changed:
            self._save()
        return changed

    def add_server(self, server_cfg):
        self.servers.append(server_cfg)
        self._save()

    def remove_server(self, name):
        self.servers = [s for s in self.servers if s.name != name]
        self.favorites = [f for f in self.favorites if f.server_name != name]
        self._save()

    def get_servers(self):
        return list(self.servers)

    def is_favorite(self, entry_type, ref_id, server_name):
        return any(
            f.entry_type == entry_type and f.ref_id == ref_id and f.server_name == server_name
            for f in self.favorites
        )

    def add_favorite(self, entry):
        if not self.is_favorite(entry.entry_type, entry.ref_id, entry.server_name):
            self.favorites.append(entry)
            self._save()

    def remove_favorite(self, entry_type, ref_id, server_name):
        self.favorites = [
            f for f in self.favorites
            if not (f.entry_type == entry_type and f.ref_id == ref_id and f.server_name == server_name)
        ]
        self._save()

    def toggle_favorite(self, entry):
        if self.is_favorite(entry.entry_type, entry.ref_id, entry.server_name):
            self.remove_favorite(entry.entry_type, entry.ref_id, entry.server_name)
            return False
        self.add_favorite(entry)
        return True

    def get_favorites(self):
        return list(self.favorites)


config_store = ConfigStore()


def get_configured_servers():
    return config_store.get_servers()
