# -*- coding: utf-8 -*-
"""Read-only credential bridge for existing Enigma2 media plugins.

Media Plugins 2026 must not force users to type the same server credentials again.
This module therefore *reads* already persisted Enigma2/plugin configuration and
returns normalized candidates.  It never changes another plugin's files.

The scanner is deliberately conservative: a candidate is only returned when a
provider (Emby/Jellyfin/Plex), a server address and some usable authentication
material can be identified.  Secrets are never written to the log here.
"""
import base64
import glob
import hashlib
import json
import os
import re

from . import log

PROVIDERS = ("emby", "jellyfin", "plex")

_ADDRESS_KEYS = (
    "server", "server_url", "serverurl", "url", "base_url", "baseurl",
    "address", "host", "hostname", "server_ip", "serverip", "ip",
    # Common Plex/DreamPlex/PlexDream variants.
    "plex_ip", "plexip", "pms_ip", "pmsip", "serverhost", "plex_url", "plexurl",
)
_USER_KEYS = (
    "username", "user", "login", "user_name", "email",
    # DreamPlex stores these exact field names in /etc/enigma2/settings.
    "myplexusername", "myplextokenusername", "plexonlineusername",
)
_PASSWORD_KEYS = (
    "password", "pass", "passwd", "pw", "myplexpassword",
)
_TOKEN_KEYS = (
    "token", "access_token", "accesstoken", "api_key", "apikey",
    "x_plex_token", "x-plex-token", "plex_token",
    # DreamPlex / PlexDream / Plex Media Server naming.
    "myplextoken", "authtoken", "auth_token", "authenticationtoken",
    "plexonlinetoken",
)
_USER_ID_KEYS = ("user_id", "userid", "userId", "myplexid")
_PORT_KEYS = ("port", "server_port", "serverport", "plexport", "pmsport")
_PATH_KEYS = ("path", "base_path", "basepath")
_HTTPS_KEYS = ("https", "ssl", "use_https", "usehttps")
_NAME_KEYS = ("name", "server_name", "servername", "title")


def _text(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def _first(mapping, keys):
    lower = {str(k).lower(): v for k, v in (mapping or {}).items()}
    for key in keys:
        if key.lower() in lower:
            value = _text(lower[key.lower()])
            if value:
                return value
    return ""


def _provider_from_text(text):
    value = (text or "").lower()
    # Jellyfin must win before the broad historic Emby/MediaBrowser naming.
    if "jellyfin" in value:
        return "jellyfin"
    if "plex" in value:
        return "plex"
    if "emby" in value:
        return "emby"
    return ""


def _https_mode(value):
    value = _text(value).lower()
    if value in ("1", "true", "yes", "on", "https"):
        return "on"
    if value in ("0", "false", "no", "off", "http"):
        return "off"
    return "auto"


def _legacy_deobfuscate(stored):
    """Decode the XOR/base64 format used by the old InfuseMedia config."""
    if not stored:
        return ""
    try:
        raw = base64.b64decode(_text(stored).encode("ascii"))
        return bytes([b ^ 0x5A for b in raw]).decode("utf-8")
    except Exception:
        return ""


def _candidate(protocol, values, source, password_is_obfuscated=False):
    if protocol not in PROVIDERS:
        return None
    address = _first(values, _ADDRESS_KEYS)
    if not address:
        return None

    username = _first(values, _USER_KEYS)
    password = _first(values, _PASSWORD_KEYS)
    token = _first(values, _TOKEN_KEYS)
    user_id = _first(values, _USER_ID_KEYS)
    if password_is_obfuscated and password:
        password = _legacy_deobfuscate(password)

    # Plex needs a token (or an explicitly open LAN PMS).  We do not import a
    # totally anonymous generic Plex-looking setting because it is too easy to
    # mis-detect an unrelated path.  Legacy Infuse configs are trusted here.
    if protocol == "plex":
        if not token and password:
            token = password
        if not token and not source.startswith("legacy-infuse:"):
            return None
    elif not (token or (username and password)):
        return None

    port = _first(values, _PORT_KEYS)
    path = _first(values, _PATH_KEYS)
    https = _https_mode(_first(values, _HTTPS_KEYS))
    name = _first(values, _NAME_KEYS) or (protocol.capitalize() + " · übernommen")

    return {
        "protocol": protocol,
        "name": name,
        "address": address,
        "port": port,
        "username": username,
        "password": password,
        "token": token,
        "user_id": user_id,
        "https": https,
        "path": path,
        "source": source,
    }


def _parse_settings_file(path):
    values = {}
    if not os.path.isfile(path):
        return values
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                raw = raw.rstrip("\r\n")
                if not raw or raw.lstrip().startswith("#") or "=" not in raw:
                    continue
                key, value = raw.split("=", 1)
                values[key.strip()] = value.strip()
    except Exception as exc:
        log.warning("CredentialBridge: Enigma2 settings konnten nicht gelesen werden: %s", exc)
    return values


def _settings_candidates(path):
    settings = _parse_settings_file(path)
    result = []

    # EmbyFlowE2 is known exactly and stores its login in /etc/enigma2/settings.
    # Read the values directly instead of importing the plugin module (which
    # would execute foreign UI/plugin code as a side effect).
    embyflow = {
        "server": settings.get("config.embyflow.server", ""),
        "username": settings.get("config.embyflow.username", ""),
        "password": settings.get("config.embyflow.password", ""),
        "api_key": settings.get("config.embyflow.api_key", ""),
        "name": "EmbyFlowE2",
    }
    cand = _candidate("emby", embyflow, "enigma2-settings:config.embyflow")
    if cand:
        result.append(cand)

    # Generic Enigma2 ConfigSubsection bridge for other standalone clients.
    # Group by config prefix and only inspect groups whose prefix itself names
    # one of our providers.  This avoids matching arbitrary media metadata.
    groups = {}
    for key, value in settings.items():
        lower_key = key.lower()
        if ("infusemedia2026" in lower_key or "mediaplugins2026" in lower_key or key.startswith("config.embyflow.")):
            continue
        provider = _provider_from_text(lower_key)
        if not provider or "." not in key:
            continue
        prefix, field = key.rsplit(".", 1)
        group = groups.setdefault((provider, prefix), {})
        group[field] = value

    for (provider, prefix), values in groups.items():
        values = dict(values)
        values.setdefault("name", prefix.split(".")[-1] or provider.capitalize())
        cand = _candidate(provider, values, "enigma2-settings:%s" % prefix)
        if cand:
            result.append(cand)
    return result


def _walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            for found in _walk_dicts(child):
                yield found
    elif isinstance(value, list):
        for child in value:
            for found in _walk_dicts(child):
                yield found


def _legacy_infuse_candidates(path):
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            data = json.load(handle)
    except Exception:
        return []
    result = []
    for raw in data.get("servers", []) if isinstance(data, dict) else []:
        if not isinstance(raw, dict):
            continue
        provider = _text(raw.get("protocol")).lower()
        cand = _candidate(provider, raw, "legacy-infuse:%s" % path, password_is_obfuscated=True)
        if cand:
            result.append(cand)
    return result


def _json_file_candidates(path, provider_hint=""):
    """Read one JSON config without executing the owning plugin.

    PlexDream is known to keep its account data in /data/PlexDream/plex.json.
    The JSON schema has changed over time, so we walk nested dicts and only
    accept entries that contain both a server address and usable auth material.
    """
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            data = json.load(handle)
    except Exception:
        return []

    result = []
    provider_hint = provider_hint or _provider_from_text(os.path.basename(path))
    for raw in _walk_dicts(data):
        provider = _text(raw.get("protocol") or raw.get("provider")).lower()
        if provider not in PROVIDERS:
            provider = provider_hint
        if provider not in PROVIDERS:
            continue
        cand = _candidate(provider, raw, "json:%s" % path)
        if cand:
            result.append(cand)
    return result


def _generic_json_candidates(config_dir):
    result = []
    patterns = ("*emby*.json", "*jellyfin*.json", "*plex*.json")
    excluded_words = ("history", "cache", "favorite", "search", "poster", "image")
    seen_paths = set()
    for pattern in patterns:
        for path in glob.glob(os.path.join(config_dir, pattern)):
            real = os.path.realpath(path)
            if real in seen_paths:
                continue
            seen_paths.add(real)
            base = os.path.basename(path).lower()
            if base in ("infusemedia2026.json", "mediaplugins2026.json", "mediaplugins2026_unified.json") or any(word in base for word in excluded_words):
                continue
            provider_hint = _provider_from_text(base)
            if not provider_hint:
                continue
            result.extend(_json_file_candidates(path, provider_hint))
    return result


def _known_plex_json_candidates():
    """Known read-only config locations used by standalone Plex clients.

    PlexDream (DreamOS) commonly stores its credentials under /data/PlexDream.
    Paths are probed only when present; nothing is created or modified.
    """
    result = []
    paths = (
        "/data/PlexDream/plex.json",
        "/data/plexdream/plex.json",
        "/etc/enigma2/plex.json",
        "/etc/enigma2/plexdream.json",
    )
    seen = set()
    for path in paths:
        real = os.path.realpath(path)
        if real in seen:
            continue
        seen.add(real)
        result.extend(_json_file_candidates(path, "plex"))
    return result



def _plex2026_candidates():
    """Import the standalone Plex2026 account token without user input.

    Plex2026Phase1 stores the account token in /etc/enigma2/plex2026_*.json.
    Those files intentionally contain no PMS address.  Media Plugins 2026 therefore
    imports the token with a discovery sentinel; PlexClient resolves the actual
    Plex Media Server through plex.tv /api/resources on first connection.

    The source files are read-only and never modified.
    """
    paths = (
        "/etc/enigma2/plex2026_account_token.json",
        "/etc/enigma2/plex2026_token.json",
    )
    for path in paths:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                data = json.load(handle)
        except Exception as exc:
            log.warning("CredentialBridge: Plex2026 Token-Datei nicht lesbar (%s): %s", path, exc)
            continue
        if not isinstance(data, dict):
            continue
        token = _text(data.get("auth_token"))
        if not token:
            continue
        # Do not log the token. client_identifier is deliberately not required:
        # our Plex backend uses its own stable X-Plex-Client-Identifier.
        return [{
            "protocol": "plex",
            "name": "Plex2026",
            "address": "plex://account-discovery",
            "port": "",
            "username": "",
            "password": "",
            "token": token,
            "user_id": "plex",
            "https": "auto",
            "path": "",
            "source": "plex2026:%s" % path,
        }]
    return []

def _fingerprint(candidate):
    # Hash auth material so dedupe never needs to log or persist it in cleartext.
    raw = "|".join([
        candidate.get("protocol", "").lower(),
        candidate.get("address", "").rstrip("/").lower(),
        candidate.get("username", "").lower(),
        candidate.get("token", ""),
        candidate.get("password", ""),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def discover_existing_credentials(settings_path="/etc/enigma2/settings", config_dir="/etc/enigma2"):
    """Return normalized, de-duplicated credential candidates.

    This function is intentionally read-only.  The caller decides whether to
    copy candidates into Media Plugins 2026's own configuration.
    """
    candidates = []
    # Old InfuseMedia is a known compatible schema and therefore gets a
    # dedicated decoder.  It is useful during migration from the predecessor.
    candidates.extend(_legacy_infuse_candidates(os.path.join(config_dir, "infusemedia.json")))
    candidates.extend(_settings_candidates(settings_path))
    candidates.extend(_generic_json_candidates(config_dir))
    candidates.extend(_known_plex_json_candidates())
    candidates.extend(_plex2026_candidates())

    unique = []
    seen = set()
    for cand in candidates:
        fp = _fingerprint(cand)
        if fp in seen:
            continue
        seen.add(fp)
        cand["fingerprint"] = fp
        unique.append(cand)
    return unique
