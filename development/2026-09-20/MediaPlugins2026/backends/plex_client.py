# -*- coding: utf-8 -*-
# INFUSEMEDIA2026_PLEX_EPISODEUI3
# INFUSEMEDIA2026_PLEX_SEASONBROWSER1
# INFUSEMEDIA2026_HOME_SECTIONID1
"""Plex Media Server backend for MediaPlugins2026.

This backend intentionally targets a directly reachable Plex Media Server.
Authentication uses an existing X-Plex-Token (entered in the password/token
field).  Unauthenticated LAN servers are also supported when the server allows
it.  Plex account/PIN login is deliberately kept separate from the local PMS
client and can be added later without changing the MediaServerClient API.
"""
import time
import json
import os
import xml.etree.ElementTree as ET
from urllib.parse import quote

from .base import MediaServerClient
from .http_helper import HttpHelper
from .media_item import MediaItem
from ..utils import log


# INFUSEMEDIA2026_R16_PLEX_FAST_CACHE_LOCALTEST

class PlexClient(MediaServerClient):
    PRODUCT = "MediaPlugins2026"
    VERSION = "2026.1-r15"
    CLIENT_ID = "enigma2-mediaplugins2026-plex"

    def __init__(self, *args, **kwargs):
        super(PlexClient, self).__init__(*args, **kwargs)
        if self.port is None:
            self.port = 32400
        # r16 speedfix: Plex must never stall the whole home wall for 10s per candidate.
        self.http = HttpHelper(timeout=4)
        # r8: prefer an imported token; password remains backward compatible.
        self.token = self.token or self.password or ""
        self.user_id = "plex"

    def _headers(self):
        h = {
            b"X-Plex-Product": [self.PRODUCT.encode("utf-8")],
            b"X-Plex-Version": [self.VERSION.encode("utf-8")],
            b"X-Plex-Client-Identifier": [self.CLIENT_ID.encode("utf-8")],
            b"Accept": [b"application/xml"],
        }
        if self.token:
            h[b"X-Plex-Token"] = [self.token.encode("utf-8")]
        return h

    def _with_token(self, url):
        if not self.token or "X-Plex-Token=" in url:
            return url
        return url + ("&" if "?" in url else "?") + "X-Plex-Token=" + quote(self.token)

    def _get(self, url, callback, error_callback):
        self.http.get(self._with_token(url), self._headers(), callback, error_callback)

    def _parse_xml(self, data):
        return ET.fromstring(data or "<MediaContainer />")

    def _image_url(self, path, width=320, height=480):
        if not path:
            return None
        if path.startswith("http://") or path.startswith("https://"):
            return self._with_token(path)
        # Let PMS resize artwork server-side to keep Enigma2 memory use bounded.
        source = path if path.startswith("/") else "/" + path
        url = ("%s/photo/:/transcode?width=%d&height=%d&minSize=1&upscale=1&url=%s"
               % (self._build_base_url(), width, height, quote(source, safe="")))
        return self._with_token(url)

    @staticmethod
    def _epoch_string(value):
        try:
            return "%020d" % int(value or 0)
        except Exception:
            return ""

    def _item_from_element(self, el):
        a = el.attrib
        item_id = a.get("ratingKey") or a.get("key") or ""
        media = el.find("Media")
        part = media.find("Part") if media is not None else None

        stream_url = ""
        if part is not None:
            part_key = part.attrib.get("key") or ""
            if part_key:
                stream_url = self._with_token(
                    self._build_base_url() + (part_key if part_key.startswith("/") else "/" + part_key)
                )

        provider_ids = {}
        for guid in el.findall("Guid"):
            gid = guid.attrib.get("id") or ""
            if "://" in gid:
                k, v = gid.split("://", 1)
                if k and v:
                    provider_ids[k.lower()] = v

        try:
            year = int(a.get("year")) if a.get("year") else None
        except Exception:
            year = None

        try:
            duration_ms = int(a.get("duration") or 0)
        except Exception:
            duration_ms = 0
        try:
            view_offset_ms = int(a.get("viewOffset") or 0)
        except Exception:
            view_offset_ms = 0

        video_codec = (media.attrib.get("videoCodec") if media is not None else "") or ""
        audio_codec = (media.attrib.get("audioCodec") if media is not None else "") or ""
        try:
            video_width = int((media.attrib.get("width") if media is not None else 0) or 0)
        except Exception:
            video_width = 0
        try:
            video_height = int((media.attrib.get("height") if media is not None else 0) or 0)
        except Exception:
            video_height = 0
        try:
            audio_channels = int((media.attrib.get("audioChannels") if media is not None else 0) or 0)
        except Exception:
            audio_channels = 0

        title = a.get("title") or a.get("grandparentTitle") or "?"
        series_name = a.get("grandparentTitle") or (title if a.get("type") == "show" else "")
        try:
            season_number = int(a.get("parentIndex")) if a.get("parentIndex") else None
        except Exception:
            season_number = None
        try:
            episode_number = int(a.get("index")) if a.get("index") else None
        except Exception:
            episode_number = None

        # INFUSEMEDIA2026_PLEX_SEASONBROWSER1
        media_type = str(a.get("type") or "").strip().lower()
        if media_type == "season":
            series_name = a.get("parentTitle") or a.get("grandparentTitle") or series_name or ""
            try:
                season_number = int(a.get("index")) if a.get("index") else season_number
            except Exception:
                pass
            episode_number = None
        elif media_type == "episode":
            series_name = a.get("grandparentTitle") or a.get("parentTitle") or series_name or ""

        # MEDIAPLUGINS2026_LATEST_POSTERFIX1_PLEX
        poster_path = (
            a.get("thumb")
            or a.get("parentThumb")
            or a.get("grandparentThumb")
        )
        poster_from_parent_key = False

        if not poster_path:
            poster_parent_key = (
                a.get("grandparentRatingKey")
                or a.get("parentRatingKey")
            )
            if poster_parent_key:
                poster_path = "/library/metadata/%s/thumb" % poster_parent_key
                poster_from_parent_key = True

        if media_type == "episode" and not poster_from_parent_key:
            poster_url = self._image_url(poster_path, 640, 360)
        else:
            poster_url = self._image_url(poster_path, 320, 480)

        item = MediaItem(
            item_id=item_id,
            title=title,
            server_name=self.server_name,
            year=year,
            overview=a.get("summary") or "",
            genres=[x.attrib.get("tag") for x in el.findall("Genre") if x.attrib.get("tag")],
            rating=a.get("rating"),
            poster_url=poster_url,
            backdrop_url=self._image_url(a.get("art"), 1920, 1080),
            stream_url=stream_url,
            resume_ticks=view_offset_ms * 10000,
            played=(a.get("viewCount") not in (None, "", "0")),
            last_played_date=self._epoch_string(a.get("lastViewedAt")),
            date_created=self._epoch_string(a.get("addedAt")),
            series_name=series_name,
            season_number=season_number,
            episode_number=episode_number,
            video_codec=video_codec,
            video_width=video_width,
            video_height=video_height,
            audio_codec=audio_codec,
            audio_channels=audio_channels,
            runtime_ticks=duration_ms * 10000,
            parent_id=a.get("parentRatingKey") or a.get("grandparentRatingKey") or "",
            provider_ids=provider_ids,
            is_favorite=False,
            media_type=media_type,
            video_type="VideoFile",
            container=(media.attrib.get("container") if media is not None else "") or "",
        )
        item.source_label = "PLEX"
        return item

    def _items_from_root(self, root):
        items = []
        # Search recursively because /hubs/search wraps results inside Hub nodes.
        for el in root.iter():
            if el.tag not in ("Video", "Directory"):
                continue
            # Library section directories are handled by get_libraries, not media rows.
            if el.attrib.get("scanner") or el.attrib.get("agent"):
                continue
            if not (el.attrib.get("ratingKey") or el.attrib.get("key")):
                continue
            try:
                items.append(self._item_from_element(el))
            except Exception as e:
                log.warning("Plex item konnte nicht gelesen werden: %s", e)
        return items

    # --- Auth -----------------------------------------------------
    DISCOVERY_ADDRESS = "plex://account-discovery"

    def _plex2026_cached_server(self):
        """Return Plex2026's already tested server endpoint when available.

        Plex2026Phase1 persists its last working PMS in plex2026_server.json.
        Reusing that cache avoids doing plex.tv resource discovery and probing
        several dead/relay candidates on every MediaPlugins2026 start.
        """
        path = "/etc/enigma2/plex2026_server.json"
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                data = json.load(handle)
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        uri = str(data.get("uri") or "").strip().rstrip("/")
        token = str(data.get("token") or self.token or "").strip()
        if not uri.startswith(("http://", "https://")):
            return None
        return uri, token

    def login(self, callback, error_callback):
        # PLEX_LOCAL_DISCOVERY_FIX_20260920
        # Do NOT inherit Plex2026Phase1's cached endpoint here.  That cache can
        # contain a remote reverse-proxy URI which is reachable for metadata but
        # unsuitable for long-running Enigma2 Direct Play.  MediaPlugins2026
        # must use its own configured endpoint/discovery order; account discovery
        # already prefers owned + local + non-relay PMS connections.
        self._active_base_url = None
        if self.address.rstrip("/").lower() == self.DISCOVERY_ADDRESS:
            self._discover_account_servers(callback, error_callback)
            return
        # A Plex2026-imported concrete endpoint may be paired with the Plex
        # account token. PMS itself can require the server-specific accessToken
        # returned by plex.tv /api/resources. Try the configured endpoint first;
        # on failure resolve the account resources and retry with their tokens.
        self._login_candidates(
            self._candidate_base_urls(),
            callback,
            lambda direct_err: self._discover_account_servers(
                callback,
                lambda discovery_err: error_callback("%s / %s" % (direct_err, discovery_err)),
            ),
        )

    def _login_candidates(self, candidates, callback, error_callback, tokens=None):
        if not candidates:
            error_callback("Keine gueltige Plex-Serveradresse")
            return
        errors = []
        original_token = self.token

        def try_candidate(index):
            if index >= len(candidates):
                self.token = original_token
                error_callback(" / ".join(errors[-4:]) if errors else "Plex-Verbindung fehlgeschlagen")
                return
            self._active_base_url = candidates[index].rstrip("/")
            if tokens and index < len(tokens) and tokens[index]:
                self.token = tokens[index]
            else:
                self.token = original_token
            self._get(self._active_base_url + "/identity",
                      lambda data: self._on_identity(data, callback, error_callback),
                      lambda err: failed(index, err))

        def failed(index, err):
            errors.append("%s: %s" % (candidates[index], err))
            try_candidate(index + 1)

        try_candidate(0)

    def _discover_account_servers(self, callback, error_callback):
        if not self.token:
            error_callback("Plex2026-Token fehlt")
            return
        url = "https://plex.tv/api/resources?includeHttps=1&includeRelay=1"

        def done(data):
            try:
                root = self._parse_xml(data)
                found = []
                for device in root.findall("Device"):
                    provides = (device.attrib.get("provides") or "").lower().split(",")
                    if "server" not in [x.strip() for x in provides]:
                        continue
                    device_token = device.attrib.get("accessToken") or self.token
                    owned = device.attrib.get("owned", "1")
                    for conn in device.findall("Connection"):
                        uri = (conn.attrib.get("uri") or "").strip().rstrip("/")
                        if not uri.startswith(("http://", "https://")):
                            continue
                        local = conn.attrib.get("local", "0") == "1"
                        relay = conn.attrib.get("relay", "0") == "1"
                        # Prefer owned + local + non-relay connections, but keep
                        # every advertised URI as fallback for remote users.
                        rank = (0 if owned == "1" else 1, 0 if local else 1, 1 if relay else 0, 0 if uri.startswith("https://") else 1)
                        found.append((rank, uri, device_token))
                if not found:
                    raise ValueError("Kein Plex Media Server im Plex-Konto gefunden")
                found.sort(key=lambda x: x[0])
                urls, tokens, seen = [], [], set()
                for _rank, uri, token in found:
                    if uri in seen:
                        continue
                    seen.add(uri)
                    urls.append(uri)
                    tokens.append(token)
                self._login_candidates(urls, callback, error_callback, tokens=tokens)
            except Exception as exc:
                error_callback("Plex-Servererkennung fehlgeschlagen: %s" % exc)

        self._get(url, done, lambda err: error_callback("Plex-Konto nicht erreichbar: %s" % err))

    def _on_identity(self, data, callback, error_callback):
        try:
            root = self._parse_xml(data)
            # Presence of the identity MediaContainer is enough; PMS may omit machineIdentifier.
            if root.tag != "MediaContainer":
                raise ValueError("Ungueltige Plex-Antwort")
            callback(self.token, self.user_id)
        except Exception as e:
            error_callback(str(e))

    # --- Library --------------------------------------------------
    # MEDIAPLUGINS2026_REMOTE_SERVERNAME1_PLEX
    def get_server_display_name(self, callback, error_callback):
        base = self._build_base_url()
        if not base:
            error_callback("Keine aktive Serveradresse")
            return

        def done(data):
            try:
                root = self._parse_xml(data)
                attrs = getattr(root, "attrib", {}) or {}
                name = (
                    attrs.get("friendlyName")
                    or attrs.get("FriendlyName")
                    or attrs.get("name")
                    or attrs.get("title")
                    or ""
                )
                name = str(name or "").strip()
                if not name:
                    raise ValueError("Plex FriendlyName fehlt")
                callback(name)
            except Exception as exc:
                error_callback(str(exc))

        self._get(base.rstrip("/") + "/", done, error_callback)

    def get_libraries(self, callback, error_callback):
        url = self._build_base_url() + "/library/sections"

        def done(data):
            try:
                root = self._parse_xml(data)
                libs = []
                for el in root.findall("Directory"):
                    key = el.attrib.get("key")
                    title = el.attrib.get("title") or "Bibliothek"
                    if key:
                        libs.append({"Id": key, "Name": title, "Type": el.attrib.get("type", "")})
                callback(libs)
            except Exception as e:
                error_callback(str(e))

        self._get(url, done, error_callback)

    def get_home_sections(self, callback, error_callback):
        # r16 speedfix: Resume and recently-added are independent. Fetch both
        # in parallel so a missing/slow Continue Watching hub cannot delay the
        # "Neu hinzugefügt" row by another full network timeout.
        result = {"resume": [], "latest": []}
        finished = {"resume": False, "latest": False}
        delivered = [False]

        def maybe_done():
            if delivered[0] or not (finished["resume"] and finished["latest"]):
                return
            delivered[0] = True
            callback([
                {"section_id": "continue", "title": "Weiterschauen", "items": result["resume"], "is_resume": True},
                {"section_id": "latest", "title": "Neu hinzugefügt", "items": result["latest"], "is_resume": False},
            ])

        def resume_done(data):
            try:
                result["resume"] = self._items_from_root(self._parse_xml(data))[:10]
            except Exception:
                result["resume"] = []
            finished["resume"] = True
            maybe_done()

        def latest_done(data):
            try:
                result["latest"] = self._items_from_root(self._parse_xml(data))[:15]
            except Exception:
                result["latest"] = []
            finished["latest"] = True
            maybe_done()

        def resume_failed(err):
            finished["resume"] = True
            maybe_done()

        def latest_failed(err):
            finished["latest"] = True
            maybe_done()

        base = self._build_base_url()
        self._get(base + "/hubs/home/continueWatching?X-Plex-Container-Size=10",
                  resume_done, resume_failed)
        self._get(base + "/library/recentlyAdded?X-Plex-Container-Size=15",
                  latest_done, latest_failed)

    def get_items(self, library_id, callback, error_callback,
                  start_index=0, limit=50, sort_by="SortName",
                  name_starts_with=None, name_less_than=None):
        # Die A-Z-Parameter werden vom gemeinsamen LibraryBrowser uebergeben.
        # Plex verwendet hier weiterhin seine bestehende serverseitige
        # Pagination; die Parameter werden bewusst nur kompatibel akzeptiert.
        url = ("%s/library/sections/%s/all?X-Plex-Container-Start=%d&X-Plex-Container-Size=%d"
               % (self._build_base_url(), library_id, int(start_index), int(limit)))

        def done(data):
            try:
                root = self._parse_xml(data)
                items = self._items_from_root(root)
                total = int(root.attrib.get("totalSize") or root.attrib.get("size") or len(items))
                callback(items, total)
            except Exception as e:
                error_callback(str(e))

        self._get(url, done, error_callback)

    def get_item_detail(self, item_id, callback, error_callback):
        url = "%s/library/metadata/%s" % (self._build_base_url(), item_id)

        def done(data):
            try:
                root = self._parse_xml(data)
                items = self._items_from_root(root)
                if not items:
                    raise ValueError("Plex-Metadaten nicht gefunden")
                callback(items[0])
            except Exception as e:
                error_callback(str(e))

        self._get(url, done, error_callback)

    def get_children(self, item_id, callback, error_callback, limit=500):
        url = ("%s/library/metadata/%s/children?X-Plex-Container-Start=0&X-Plex-Container-Size=%d" % (self._build_base_url(), quote(str(item_id)), int(limit)))

        def done(data):
            try:
                root = self._parse_xml(data)
                callback(self._items_from_root(root))
            except Exception as exc:
                error_callback(str(exc))

        self._get(url, done, error_callback)

    # MEDIAPLUGINS2026_PLEX_SIMILAR_PROVIDER1
    def get_similar_items(self, item_id, callback, error_callback, limit=5):
        try:
            limit = max(1, min(20, int(limit or 5)))
        except Exception:
            limit = 5

        url = "%s/hubs/metadata/%s/related?includeExternalMedia=0" % (
            self._build_base_url(),
            quote(str(item_id)),
        )

        def done(data):
            try:
                root = self._parse_xml(data)
                source = self._items_from_root(root)
                seen = set()
                items = []
                for item in source:
                    iid = str(getattr(item, "id", "") or "")
                    if not iid or iid == str(item_id) or iid in seen:
                        continue
                    seen.add(iid)
                    items.append(item)
                    if len(items) >= limit:
                        break
                callback(items)
            except Exception as exc:
                error_callback(str(exc))

        self._get(url, done, error_callback)

    def get_item_by_id(self, item_id, callback, error_callback):
        self.get_item_detail(item_id, callback, error_callback)

    def search(self, query, callback, error_callback):
        url = "%s/hubs/search?query=%s" % (self._build_base_url(), quote(query or ""))

        def done(data):
            try:
                callback(self._items_from_root(self._parse_xml(data))[:60])
            except Exception as e:
                error_callback(str(e))

        self._get(url, done, error_callback)

    # --- Playback -------------------------------------------------
    def get_stream_url(self, item_id, item=None):
        direct = getattr(item, "stream_url", "") if item is not None else ""
        if direct:
            return direct
        # Deliberately do not guess a Plex transcode URL without media decision data.
        # The detail screen refresh normally fills stream_url from Media/Part.
        raise ValueError("Plex Direct-Play-Pfad fuer diesen Eintrag nicht verfuegbar")

    def _timeline(self, item_id, position_ticks, state):
        ms = int(position_ticks or 0) // 10000
        url = ("%s/:/timeline?ratingKey=%s&key=%s&state=%s&time=%d"
               % (self._build_base_url(), quote(str(item_id)),
                  quote("/library/metadata/%s" % item_id, safe=""), state, ms))
        self._get(url, lambda data: None, lambda err: None)

    def report_playback_started(self, item_id, position_ticks=0):
        self._timeline(item_id, position_ticks, "playing")

    def report_playback_progress(self, item_id, position_ticks):
        self._timeline(item_id, position_ticks, "playing")

    def report_playback_stopped(self, item_id, position_ticks):
        self._timeline(item_id, position_ticks, "stopped")

    def mark_watched(self, item_id, watched=True):
        endpoint = "/:/scrobble" if watched else "/:/unscrobble"
        url = "%s%s?key=%s&identifier=com.plexapp.plugins.library" % (
            self._build_base_url(), endpoint, quote(str(item_id)))
        self._get(url, lambda data: None, lambda err: None)

    # Plex server favorites/watchlist are account/cloud features, not a direct
    # equivalent of Jellyfin/Emby FavoriteItems. Keep the backend honest.
    def set_favorite(self, item_id, favorite=True, callback=None, error_callback=None):
        if error_callback:
            error_callback("Plex-Watchlist/Favoriten werden in diesem Build noch nicht geschrieben")

    def get_favorites(self, callback, error_callback, limit=500):
        callback([])

    def get_image_url(self, item_id, image_type="Primary"):
        # Raw Plex artwork paths are part of item metadata and are handled by
        # _item_from_element(). There is no stable timestamp-free equivalent
        # that can be derived from ratingKey alone.
        return None
