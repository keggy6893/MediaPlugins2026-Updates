# -*- coding: utf-8 -*-
from urllib.parse import urlsplit


class MediaServerClient(object):
    """Gemeinsames Interface für Emby-, Jellyfin- und Plex-Clients."""

    def __init__(self, name, address, port, username, password,
                 https="auto", path="", library_mode=False, token="", user_id=""):
        self.server_name = name
        self.address = (address or "").strip()
        self.port = int(port) if str(port or "").strip() else None
        self.username = username
        self.password = password
        self.https = https          # "auto" | "on" | "off"
        self.path = (path or "").strip()
        self.library_mode = library_mode
        self.token = token or None
        self.user_id = user_id or None
        self._active_base_url = None

    def login(self, callback, error_callback):
        raise NotImplementedError

    def get_home_sections(self, callback, error_callback):
        raise NotImplementedError

    def get_libraries(self, callback, error_callback):
        raise NotImplementedError

    def get_items(self, library_id, callback, error_callback,
                  start_index=0, limit=50, sort_by="SortName"):
        raise NotImplementedError

    def get_item_detail(self, item_id, callback, error_callback):
        raise NotImplementedError

    def get_item_by_id(self, item_id, callback, error_callback):
        raise NotImplementedError

    def search(self, query, callback, error_callback):
        raise NotImplementedError

    def get_stream_url(self, item_id, item=None):
        raise NotImplementedError

    def report_playback_started(self, item_id, position_ticks=0):
        raise NotImplementedError

    def report_playback_progress(self, item_id, position_ticks):
        raise NotImplementedError

    def report_playback_stopped(self, item_id, position_ticks):
        raise NotImplementedError

    def mark_watched(self, item_id, watched=True):
        raise NotImplementedError

    def set_favorite(self, item_id, favorite=True, callback=None, error_callback=None):
        """r56: Favoritenstatus serverseitig setzen/entfernen (Jellyfin/Emby
        FavoriteItems-API), statt nur lokal auf der Box zu speichern."""
        raise NotImplementedError

    def get_favorites(self, callback, error_callback, limit=500):
        """r56: Alle serverseitig als Favorit markierten Items dieses Servers laden."""
        raise NotImplementedError

    def get_image_url(self, item_id, image_type="Primary"):
        raise NotImplementedError

    def _candidate_base_urls(self):
        """Erzeugt robuste Basis-URLs.

        Akzeptiert sowohl nur Host/IP (192.168.0.20) als auch komplette
        Eingaben (http://host:8096/jellyfin). Bei HTTPS=Auto wird zuerst
        das aus der Adresse erkennbare Schema verwendet, andernfalls HTTP
        und danach HTTPS probiert.
        """
        raw = self.address.strip().rstrip("/")
        if not raw:
            return []

        has_scheme = "://" in raw
        parsed = urlsplit(raw if has_scheme else "//" + raw)
        host = parsed.hostname or raw.split("/")[0].split(":")[0]
        embedded_port = parsed.port
        embedded_path = (parsed.path or "").strip("/")

        port = embedded_port if embedded_port is not None else self.port
        path = self.path.strip("/") or embedded_path

        if self.https == "on":
            schemes = ["https"]
        elif self.https == "off":
            schemes = ["http"]
        elif has_scheme and parsed.scheme in ("http", "https"):
            # Explizite Eingabe respektieren, aber bei Auto als Fallback
            # auch das andere Schema probieren.
            other = "https" if parsed.scheme == "http" else "http"
            schemes = [parsed.scheme, other]
        else:
            schemes = ["http", "https"]

        urls = []
        for scheme in schemes:
            default_port = 443 if scheme == "https" else 80
            base = "%s://%s" % (scheme, host)
            if port is not None and port != default_port:
                base += ":%d" % port
            if path:
                base += "/" + path
            if base not in urls:
                urls.append(base)
        return urls

    def _build_base_url(self):
        if self._active_base_url:
            return self._active_base_url
        candidates = self._candidate_base_urls()
        return candidates[0] if candidates else ""
