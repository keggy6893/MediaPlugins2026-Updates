# -*- coding: utf-8 -*-
# INFUSEMEDIA2026_HOME_SECTIONID1
import json
from urllib.parse import quote
from .base import MediaServerClient
from .http_helper import HttpHelper
from .media_item import MediaItem
from ..utils import log


class JellyfinClient(MediaServerClient):

    CLIENT_NAME = "MediaPlugins2026"
    DEVICE_NAME = "Enigma2"
    DEVICE_ID = "enigma2-mediaplugins2026"
    VERSION = "2026.1-r15"

    def __init__(self, *args, **kwargs):
        super(JellyfinClient, self).__init__(*args, **kwargs)
        self.http = HttpHelper()

    def _auth_header(self):
        return (
            'MediaBrowser Client="%s", Device="%s", DeviceId="%s", Version="%s"'
            % (self.CLIENT_NAME, self.DEVICE_NAME, self.DEVICE_ID, self.VERSION)
        )

    def _auth_headers(self):
        h = {b"X-Emby-Authorization": [self._auth_header().encode("utf-8")]}
        if self.token:
            h[b"X-Emby-Token"] = [self.token.encode("utf-8")]
        return h

    def _get(self, url, callback, error_callback):
        self.http.get(url, self._auth_headers(), callback, error_callback)

    def _post(self, url, payload, callback, error_callback):
        headers = self._auth_headers()
        headers[b"Content-Type"] = [b"application/json"]
        self.http.post(url, payload, headers, callback, error_callback)

    def _delete(self, url, callback, error_callback):
        self.http.delete(url, self._auth_headers(), callback, error_callback)

    # --- Auth -----------------------------------------------------
    def login(self, callback, error_callback):
        candidates = self._candidate_base_urls()
        if not candidates:
            error_callback("Keine gueltige Serveradresse")
            return

        # Importierte Tokens immer serverseitig validieren. Eine gespeicherte
        # User-ID beweist nicht, dass der Token noch gueltig ist; andernfalls
        # faellt ein abgelaufener Token erst bei Home/Libraries/Favorites mit
        # HTTP 401 auf. /Users/Me validiert den Token und liefert zugleich die
        # aktuelle User-ID. Bei Fehlschlag nutzt der bestehende Ablauf das
        # Passwort als Fallback, sofern eines vorhanden ist.
        if self.token:
            token_errors = []

            def try_token_candidate(index):
                if index >= len(candidates):
                    # Ein vorhandenes Passwort ist ein sinnvoller Fallback,
                    # falls ein importierter Token abgelaufen ist.
                    if self.username and self.password:
                        login_with_password()
                    else:
                        error_callback(" / ".join(token_errors) if token_errors else "Token-Anmeldung fehlgeschlagen")
                    return
                base = candidates[index]
                self._active_base_url = base

                def token_ok(data):
                    try:
                        user = json.loads(data)
                        uid = user.get("Id") or user.get("id")
                        if not uid:
                            raise ValueError("Benutzer-ID fehlt")
                        self.user_id = uid
                        callback(self.token, self.user_id)
                    except Exception as exc:
                        token_failed(str(exc))

                def token_failed(err):
                    token_errors.append("%s: %s" % (base, err))
                    try_token_candidate(index + 1)

                self._get(base + "/Users/Me", token_ok, token_failed)

            try_token_candidate(0)
            return

        def login_with_password():
            if not self.username or not self.password:
                error_callback("Keine nutzbaren Anmeldedaten gefunden")
                return
            payload = json.dumps({"Username": self.username, "Pw": self.password}).encode("utf-8")
            errors = []

            def try_candidate(index):
                if index >= len(candidates):
                    error_callback(" / ".join(errors) if errors else "Verbindung fehlgeschlagen")
                    return
                base = candidates[index]
                self._active_base_url = base
                url = base + "/Users/AuthenticateByName"

                def failed(err):
                    errors.append("%s: %s" % (base, err))
                    self.token = None
                    self.user_id = None
                    try_candidate(index + 1)

                self._post(url, payload,
                           lambda data: self._on_login(data, callback, failed),
                           failed)

            try_candidate(0)

        login_with_password()

    def _on_login(self, data, callback, error_callback):
        try:
            result = json.loads(data)
            self.token = result["AccessToken"]
            self.user_id = result["User"]["Id"]
            callback(self.token, self.user_id)
        except Exception as e:
            error_callback(str(e))

    # --- Bibliothek -------------------------------------------------
    # MEDIAPLUGINS2026_REMOTE_SERVERNAME1_JELLYFIN
    def get_server_display_name(self, callback, error_callback):
        base = self._build_base_url()
        if not base:
            error_callback("Keine aktive Serveradresse")
            return

        def done(data):
            try:
                info = json.loads(data)
                name = (
                    info.get("ServerName")
                    or info.get("Name")
                    or info.get("serverName")
                    or ""
                )
                name = str(name or "").strip()
                if not name:
                    raise ValueError("ServerName fehlt")
                callback(name)
            except Exception as exc:
                error_callback(str(exc))

        self._get(base.rstrip("/") + "/System/Info/Public", done, error_callback)

    def get_libraries(self, callback, error_callback):
        url = "%s/Users/%s/Views" % (self._build_base_url(), self.user_id)
        self._get(url, lambda data: self._on_libraries(data, callback), error_callback)

    def _on_libraries(self, data, callback):
        result = json.loads(data)
        callback(result.get("Items", []))

    def get_home_sections(self, callback, error_callback):
        """Liefert 'Weiterschauen' + genre-/typbasierte 'Neuste X'-Reihen."""
        # r64: Recursive=true und MediaTypes=Video ergaenzt. Jellyfin und
        # Emby haben sich seit der gemeinsamen Codebasis auseinander-
        # entwickelt - Emby lieferte bei manchen Servern ohne diese
        # Parameter eine leere "Weiterschauen"-Liste zurueck, obwohl der
        # native Emby-Client fuer denselben Benutzer Eintraege anzeigte.
        url = ("%s/Users/%s/Items/Resume?Limit=10&Recursive=true&MediaTypes=Video"
               % (self._build_base_url(), self.user_id))

        def on_resume(data):
            try:
                parsed = json.loads(data)
                raw_items = [i for i in parsed.get("Items", []) if not i.get("IsFolder")]
                resume_items = [MediaItem.from_jellyfin(i, self) for i in raw_items]
                log.info("get_home_sections r64 (%s/%s): Resume roh=%d, verwendet=%d",
                         self.server_name, self.CLIENT_NAME, len(parsed.get("Items", [])), len(resume_items))
            except Exception as e:
                log.warning("get_home_sections r64 (%s): Resume-Antwort nicht verwertbar: %s - Rohdaten: %s",
                            self.server_name, e, (data or "")[:300])
                resume_items = []
            sections = [{"section_id": "continue", "title": "Weiterschauen", "items": resume_items, "is_resume": True}]
            self._fetch_latest_by_type(sections, callback, error_callback)

        def on_resume_error(err):
            log.warning("get_home_sections r64 (%s): Resume-Abfrage fehlgeschlagen: %s", self.server_name, err)
            error_callback(err)

        self._get(url, on_resume, on_resume_error)

    # MEDIAPLUGINS2026_EMBY_LATEST_FALLBACK1
    # MEDIAPLUGINS2026_LATEST_POSTERFIX1_EMBY
    def _fetch_latest_by_type(self, sections, callback, error_callback):
        primary_url = (
            "%s/Users/%s/Items/Latest?Limit=40"
            "&Fields=ImageTags,PrimaryImageItemId,SeriesId,ParentId,"
            "DateCreated,Overview,Genres,ProductionYear,RunTimeTicks,"
            "MediaSources,UserData,SeriesName,IndexNumber,ParentIndexNumber,"
            "ProviderIds,Container"
        ) % (self._build_base_url(), self.user_id)

        def finish(items):
            sections.append({
                "section_id": "latest",
                "title": "Neu hinzugefügt",
                "items": (items or [])[:15],
                "is_resume": False,
            })
            callback(sections)

        def convert(raw_items):
            items = []
            for raw in raw_items or []:
                if not isinstance(raw, dict) or raw.get("IsFolder"):
                    continue

                item = MediaItem.from_jellyfin(raw, self)
                image_tags = raw.get("ImageTags")
                image_tags_known = isinstance(image_tags, dict)
                has_own_primary = bool(image_tags.get("Primary")) if image_tags_known else None
                fallback_id = raw.get("PrimaryImageItemId") or raw.get("SeriesId")

                if has_own_primary is False:
                    if fallback_id and str(fallback_id) != str(raw.get("Id") or ""):
                        item.poster_url = self.get_image_url(fallback_id, "Primary")
                    elif image_tags_known:
                        continue

                items.append(item)
                if len(items) >= 15:
                    break
            return items

        def parse_latest_list(data):
            raw = json.loads(data)
            if not isinstance(raw, list):
                return []
            return convert(raw)

        def parse_fallback_items(data):
            parsed = json.loads(data)
            raw = parsed.get("Items", []) if isinstance(parsed, dict) else []
            return convert(raw)

        def start_fallback(reason):
            log.warning(
                "Home Latest (%s): Items/Latest leer/fehlgeschlagen (%s), verwende DateCreated-Fallback mit Poster-Fallback",
                self.server_name, reason
            )
            fallback_url = (
                "%s/Users/%s/Items?"
                "Recursive=true&Filters=IsNotFolder"
                "&IncludeItemTypes=Movie,Series,Season,Episode"
                "&SortBy=DateCreated&SortOrder=Descending"
                "&Limit=40"
                "&Fields=DateCreated,Overview,Genres,ProductionYear,RunTimeTicks,"
                "MediaSources,UserData,SeriesName,SeriesId,PrimaryImageItemId,"
                "ParentId,ImageTags,IndexNumber,ParentIndexNumber,"
                "ProviderIds,Container"
            ) % (self._build_base_url(), self.user_id)

            def on_fallback(data):
                try:
                    items = parse_fallback_items(data)
                    log.info(
                        "Home Latest (%s): DateCreated-PosterFallback count=%d",
                        self.server_name, len(items)
                    )
                    finish(items)
                except Exception as exc:
                    log.warning(
                        "Home Latest (%s): DateCreated-PosterFallback nicht verwertbar: %s",
                        self.server_name, exc
                    )
                    finish([])

            def on_fallback_error(err):
                log.warning(
                    "Home Latest (%s): DateCreated-PosterFallback fehlgeschlagen: %s",
                    self.server_name, err
                )
                finish([])

            self._get(fallback_url, on_fallback, on_fallback_error)

        def on_latest(data):
            try:
                items = parse_latest_list(data)
            except Exception as exc:
                start_fallback("parse: %s" % exc)
                return

            if items:
                log.info(
                    "Home Latest (%s): Items/Latest PosterFallback count=%d",
                    self.server_name, len(items)
                )
                finish(items)
                return

            start_fallback("0 verwertbare Eintraege")

        def on_latest_error(err):
            start_fallback("request: %s" % err)

        self._get(primary_url, on_latest, on_latest_error)

    # MEDIAPLUGINS2026_LIBRARY_SERVER_AZ1
    def get_items(self, library_id, callback, error_callback,
                   start_index=0, limit=50, sort_by="SortName",
                   name_starts_with=None, name_less_than=None):
        # r54: Filters=IsNotFolder schliesst Ordner-Eintraege direkt
        # serverseitig aus.
        # SERVER_AZ1: grosse Emby/Jellyfin-Bibliotheken werden nicht mehr
        # komplett in den RAM geladen. NameStartsWith/NameLessThan erlauben
        # dem LibraryBrowser echte serverseitige A-Z-Abfragen.
        extra = ""
        if name_starts_with not in (None, ""):
            extra += "&NameStartsWith=%s" % quote(str(name_starts_with))
        if name_less_than not in (None, ""):
            extra += "&NameLessThan=%s" % quote(str(name_less_than))

        url = ("%s/Users/%s/Items?ParentId=%s&StartIndex=%d&Limit=%d&SortBy=%s"
               "&SortOrder=Ascending&Recursive=true&Filters=IsNotFolder&Fields=Container%s"
               % (self._build_base_url(), self.user_id, library_id, start_index,
                  limit, sort_by, extra))

        def on_items(data):
            try:
                result = json.loads(data)
                raw_items = result.get("Items", [])
                # Sicherheitsnetz: manche Emby-Versionen ignorieren/kennen
                # den Filters-Parameter nicht - daher zusaetzlich clientseitig
                # anhand des IsFolder-Flags filtern.
                raw_items = [i for i in raw_items if not i.get("IsFolder")]
                items = [MediaItem.from_jellyfin(i, self) for i in raw_items]
                callback(items, result.get("TotalRecordCount", len(items)))
            except Exception as e:
                error_callback(str(e))

        self._get(url, on_items, error_callback)

    # MEDIAPLUGINS2026_JELLYFIN_SIMILAR_PROVIDER1
    def get_similar_items(self, item_id, callback, error_callback, limit=5):
        try:
            limit = max(1, min(20, int(limit or 5)))
        except Exception:
            limit = 5

        url = (
            "%s/Items/%s/Similar?UserId=%s&Limit=%d"
            "&Fields=Overview,Genres,ProviderIds,MediaStreams,Container"
            % (
                self._build_base_url(),
                quote(str(item_id)),
                quote(str(self.user_id or "")),
                limit,
            )
        )

        def on_similar(data):
            try:
                result = json.loads(data)
                if isinstance(result, dict):
                    raw_items = result.get("Items", []) or []
                elif isinstance(result, list):
                    raw_items = result
                else:
                    raw_items = []
                raw_items = [i for i in raw_items if not i.get("IsFolder")]
                items = [MediaItem.from_jellyfin(i, self) for i in raw_items]
                callback(items[:limit])
            except Exception as exc:
                error_callback(str(exc))

        self._get(url, on_similar, error_callback)

    def get_item_detail(self, item_id, callback, error_callback):
        url = "%s/Users/%s/Items/%s" % (self._build_base_url(), self.user_id, item_id)

        def on_detail(data):
            try:
                callback(MediaItem.from_jellyfin(json.loads(data), self))
            except Exception as e:
                error_callback(str(e))

        self._get(url, on_detail, error_callback)

    def get_item_by_id(self, item_id, callback, error_callback):
        self.get_item_detail(item_id, callback, error_callback)

    def search(self, query, callback, error_callback):
        from urllib.parse import quote
        url = ("%s/Users/%s/Items?searchTerm=%s&Recursive=true&Limit=30&Filters=IsNotFolder"
               % (self._build_base_url(), self.user_id, quote(query)))

        def on_search(data):
            try:
                raw_items = [i for i in json.loads(data).get("Items", []) if not i.get("IsFolder")]
                items = [MediaItem.from_jellyfin(i, self) for i in raw_items]
                callback(items)
            except Exception as e:
                error_callback(str(e))

        self._get(url, on_search, error_callback)


    # MEDIAPLUGINS2026_AUDIOPLAYER1
    def get_audio_stream_candidates(self, item_id, item=None):
        """Direct-Play + kompatibler Server-Fallback fuer Audio/Hörbücher.

        Der erste URL-Pfad liefert das Originalformat (MP3/AAC/M4A/M4B/FLAC/
        WAV/OGG/OPUS/ALAC usw.). Kann die Box es nicht starten, verwendet der
        AudioPlayer einmalig den Universal-Endpunkt als MP3-Fallback.
        """
        base = self._build_base_url().rstrip("/")
        iid = quote(str(item_id or ""))
        token = quote(str(self.token or ""))
        user_id = quote(str(self.user_id or ""))
        container = str(getattr(item, "container", "") or "").strip().lower().lstrip(".")
        safe_container = container if container.replace("_", "").replace("-", "").isalnum() else ""

        if safe_container:
            direct = "%s/Audio/%s/stream.%s?Static=true&api_key=%s" % (base, iid, safe_container, token)
        else:
            direct = "%s/Audio/%s/stream?Static=true&api_key=%s" % (base, iid, token)

        fallback = (
            "%s/Audio/%s/universal?UserId=%s&DeviceId=mediaplugins2026-audio"
            "&MaxStreamingBitrate=320000&Container=mp3&TranscodingContainer=mp3"
            "&TranscodingProtocol=http&AudioCodec=mp3&api_key=%s"
            % (base, iid, user_id, token)
        )
        label = "DIRECT %s" % ((container or getattr(item, "audio_codec", "") or "AUDIO").upper())
        return [(label, direct), ("FALLBACK MP3", fallback)]

    def get_audio_info(self, item_id, callback, error_callback):
        url = (
            "%s/Users/%s/Items/%s?Fields=Chapters,MediaSources,People,Artists,Album,AlbumArtist,Container"
            % (self._build_base_url(), self.user_id, quote(str(item_id or "")))
        )

        def done(data):
            try:
                raw = json.loads(data)
                chapters = []
                for chapter in raw.get("Chapters") or []:
                    chapters.append({
                        "name": chapter.get("Name") or "",
                        "start_ticks": int(chapter.get("StartPositionTicks") or 0),
                    })
                source = (raw.get("MediaSources") or [{}])[0] or {}
                audio_stream = None
                for stream in source.get("MediaStreams") or []:
                    if str(stream.get("Type") or "").lower() == "audio":
                        audio_stream = stream
                        break
                artists = raw.get("Artists") or []
                artist = ", ".join(str(x) for x in artists if x)
                if not artist:
                    artist = str(raw.get("AlbumArtist") or "")
                callback({
                    "chapters": chapters,
                    "artist": artist,
                    "container": source.get("Container") or raw.get("Container") or "",
                    "codec": (audio_stream or {}).get("Codec") or "",
                    "channels": (audio_stream or {}).get("Channels") or 0,
                })
            except Exception as exc:
                error_callback(str(exc))

        self._get(url, done, error_callback)

    # --- Wiedergabe -----------------------------------------------
    def get_stream_url(self, item_id, item=None):
        # r69: BD-ISO/DVD-ISO bzw. per Ordner erkannte BluRay/DVD-Titel
        # enthalten keine direkt abspielbare Videodatei, sondern die
        # komplette Disc-Struktur (BDMV/STREAM-Playlists bzw. VIDEO_TS).
        # Ein simpler Datei-Stream der Rohbytes ("static=true") ist fuer
        # keinen Player interpretierbar - der Server muss das Hauptfeature
        # per Transcoding in einen normalen HLS-Stream umwandeln.
        video_type = (getattr(item, "video_type", "") or "").lower()
        container = (getattr(item, "container", "") or "").lower()
        needs_transcode = video_type in ("iso", "bluray", "dvd") or container == "iso"
        if needs_transcode:
            log.info("get_stream_url r69 (%s): '%s' ist %s/%s - erzwinge Transcoding statt Direct-Play",
                     self.server_name, getattr(item, "title", item_id), video_type or "?", container or "?")
            # r72: HLS (master.m3u8) lieferte trotz SegmentContainer=ts
            # (r71) immer noch keine gueltige Position - das Problem liegt
            # also tiefer als nur fMP4-vs-TS-Segmente, vermutlich generell
            # am mehrstufigen HLS-Playlist-Mechanismus (Master- + Medien-
            # Playlist + einzelne Segment-Requests) auf dieser Plattform.
            # Alle normalen Dateien laufen dagegen zuverlaessig ueber einen
            # simplen, durchgehenden HTTP-Stream (stream?static=true) - das
            # ist der erprobte, funktionierende Pfad. Deshalb jetzt statt
            # HLS ein durchgehender TRANSKODIERTER Stream ueber denselben
            # /stream-Endpunkt (ohne static=true, mit .ts-Endung fuer
            # MPEG-TS-Container) - kein Playlist-Mechanismus mehr noetig,
            # nur eine einzige lange HTTP-Antwort wie bei Direct-Play.
            return ("%s/Videos/%s/stream.ts?api_key=%s&VideoCodec=h264&AudioCodec=aac,ac3"
                    "&MaxStreamingBitrate=25000000&TranscodingMaxAudioChannels=6"
                    "&RequireAvc=false&Container=ts"
                    % (self._build_base_url(), item_id, self.token))
        return ("%s/Videos/%s/stream?static=true&api_key=%s"
                % (self._build_base_url(), item_id, self.token))

    def _report_playback(self, endpoint, item_id, position_ticks):
        url = "%s/Sessions/Playing%s" % (self._build_base_url(), ("/" + endpoint) if endpoint else "")
        payload = json.dumps({
            "ItemId": item_id,
            "PositionTicks": int(position_ticks or 0),
            "IsPaused": False,
            "PlayMethod": "DirectPlay",
        }).encode("utf-8")
        def on_error(err):
            log.warning("Playback Reporting %s fehlgeschlagen: %s", endpoint or "Started", err)
        self._post(url, payload, lambda d: None, on_error)

    def report_playback_started(self, item_id, position_ticks=0):
        self._report_playback("", item_id, position_ticks)

    def report_playback_progress(self, item_id, position_ticks):
        self._report_playback("Progress", item_id, position_ticks)

    def report_playback_stopped(self, item_id, position_ticks):
        self._report_playback("Stopped", item_id, position_ticks)

    def mark_watched(self, item_id, watched=True):
        method = "POST" if watched else "DELETE"
        url = "%s/Users/%s/PlayedItems/%s" % (self._build_base_url(), self.user_id, item_id)
        if method == "POST":
            self._post(url, b"", lambda d: None, lambda e: None)

    # --- Favoriten (r56) --------------------------------------------
    def set_favorite(self, item_id, favorite=True, callback=None, error_callback=None):
        """Setzt/entfernt den Favoritenstatus direkt auf dem Server (Jellyfin/
        Emby FavoriteItems-API), damit er auch in anderen Clients (Web,
        Infuse, Apps) sichtbar ist - statt nur lokal auf der Box."""
        url = "%s/Users/%s/FavoriteItems/%s" % (self._build_base_url(), self.user_id, item_id)
        cb = callback or (lambda d: None)

        def ecb(err):
            log.warning("Favorit %s fuer %s fehlgeschlagen: %s",
                        "setzen" if favorite else "entfernen", item_id, err)
            if error_callback:
                error_callback(err)

        if favorite:
            self._post(url, b"", cb, ecb)
        else:
            self._delete(url, cb, ecb)

    def get_favorites(self, callback, error_callback, limit=500):
        """Alle auf diesem Server als Favorit markierten, abspielbaren Items."""
        url = ("%s/Users/%s/Items?Filters=IsFavorite,IsNotFolder&Recursive=true"
               "&Limit=%d&SortBy=SortName" % (self._build_base_url(), self.user_id, limit))

        def on_items(data):
            try:
                raw_items = [i for i in json.loads(data).get("Items", []) if not i.get("IsFolder")]
                items = [MediaItem.from_jellyfin(i, self) for i in raw_items]
                callback(items)
            except Exception as e:
                error_callback(str(e))

        self._get(url, on_items, error_callback)

    # --- Artwork ----------------------------------------------------
    def get_chapter_image_url(self, item_id, chapter_index):
        """Kleines Kapitelbild fuer Emby/Jellyfin; 404 wird vom ImageCache still toleriert."""
        if not item_id:
            return None
        try:
            index = max(0, int(chapter_index))
        except Exception:
            return None
        token_part = ("&api_key=%s" % quote(self.token)) if self.token else ""
        return ("%s/Items/%s/Images/Chapter/%d?maxWidth=320&maxHeight=180&quality=82%s"
                % (self._build_base_url(), item_id, index, token_part))

    def get_image_url(self, item_id, image_type="Primary"):
        if not item_id:
            return None
        # Enigma2-Boxen sollten niemals die riesigen Original-Artworks laden.
        # Jellyfin/Emby skaliert serverseitig auf eine passende GUI-Groesse.
        # Das reduziert RAM-Spitzen beim ePixmap-Decoding und verhindert
        # verzerrte/unsaubere Poster im Grid.
        if image_type == "Backdrop":
            max_w, max_h = 1920, 1080
        else:
            max_w, max_h = 320, 480
        # r51: api_key als Query-Parameter anhaengen. Der image_cache lädt
        # Cover ueber einen eigenen, von den Clients entkoppelten HTTP-Agent
        # ohne Auth-Header (siehe utils/image_cache.py). Emby-Server mit
        # aktivierter Zugriffsbeschraenkung (und manche Jellyfin-Setups)
        # liefern ohne Token ein HTTP 401 fuer /Images/... zurueck - dadurch
        # blieben Cover schwarz/leer bzw. wurden nur teilweise geladen.
        token_part = ("&api_key=%s" % quote(self.token)) if self.token else ""
        return ("%s/Items/%s/Images/%s?maxWidth=%d&maxHeight=%d&quality=85%s"
                % (self._build_base_url(), item_id, image_type, max_w, max_h, token_part))
