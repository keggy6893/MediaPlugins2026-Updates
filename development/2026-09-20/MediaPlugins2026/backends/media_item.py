# -*- coding: utf-8 -*-
# INFUSEMEDIA2026_PLEX_SEASONBROWSER1

class MediaItem(object):
    """Backend-unabhängige Repräsentation eines Mediums (Film/Serie/Episode)."""

    def __init__(self, item_id, title, server_name, year=None, overview="",
                 genres=None, rating=None, poster_url=None, backdrop_url=None,
                 stream_url=None, resume_ticks=0, played=False, last_played_date="", date_created="",
                 series_name="", season_number=None, episode_number=None,
                 video_codec="", video_width=0, video_height=0,
                 audio_codec="", audio_channels=0, audio_language="",
                 runtime_ticks=0, parent_id="", provider_ids=None, is_favorite=False,
                 video_type="", container="", media_type=""):
        self.id = item_id
        self.title = title
        self.server_name = server_name
        self.year = year
        self.overview = overview
        self.genres = genres or []
        self.rating = rating
        self.poster_url = poster_url
        self.backdrop_url = backdrop_url
        self.stream_url = stream_url
        self.local_poster_path = None
        self.resume_ticks = int(resume_ticks or 0)
        self.played = bool(played)
        self.last_played_date = last_played_date or ""
        self.date_created = date_created or ""
        self.series_name = series_name or ""
        self.season_number = season_number
        self.episode_number = episode_number
        self.video_codec = video_codec or ""
        self.video_width = int(video_width or 0)
        self.video_height = int(video_height or 0)
        self.audio_codec = audio_codec or ""
        self.audio_channels = int(audio_channels or 0)
        self.audio_language = audio_language or ""
        self.runtime_ticks = int(runtime_ticks or 0)
        self.parent_id = parent_id or ""
        # r51: Provider-IDs (imdb/tmdb/tvdb, klein geschrieben) fuer
        # zuverlaessige serveruebergreifende Duplikaterkennung.
        self.provider_ids = provider_ids or {}
        # r56: Serverseitiger Favoritenstatus (Jellyfin/Emby UserData.IsFavorite).
        # Ersetzt die bisherige rein lokale Favoritenliste.
        self.is_favorite = bool(is_favorite)
        # r69: VideoType ("VideoFile"/"Iso"/"Dvd"/"BluRay") und Container
        # ("iso" u.a.) - noetig um zu erkennen, ob eine Datei eine
        # vollstaendige Disc-Struktur ist, die nicht direkt streambar ist
        # (siehe get_stream_url() im jeweiligen Backend-Client).
        self.video_type = video_type or ""
        self.container = container or ""
        self.media_type = media_type or ""
        # Optional UI-only provider label (EMBY/JELLYFIN/PLEX).
        self.source_label = ""

    def update_from_detail(self, detail_item):
        self.overview = detail_item.overview or self.overview
        self.genres = detail_item.genres or self.genres
        self.rating = detail_item.rating or self.rating
        self.resume_ticks = int(getattr(detail_item, "resume_ticks", 0) or self.resume_ticks or 0)
        self.played = bool(getattr(detail_item, "played", self.played))
        detail_provider_ids = getattr(detail_item, "provider_ids", None) or {}
        if detail_provider_ids:
            self.provider_ids = dict(self.provider_ids, **detail_provider_ids)
        self.is_favorite = bool(getattr(detail_item, "is_favorite", self.is_favorite))
        detail_stream_url = getattr(detail_item, "stream_url", "") or ""
        if detail_stream_url:
            self.stream_url = detail_stream_url
        detail_poster_url = getattr(detail_item, "poster_url", None)
        if detail_poster_url:
            self.poster_url = detail_poster_url
        detail_backdrop_url = getattr(detail_item, "backdrop_url", None)
        if detail_backdrop_url:
            self.backdrop_url = detail_backdrop_url
        detail_source_label = getattr(detail_item, "source_label", "") or ""
        if detail_source_label:
            self.source_label = detail_source_label
        detail_video_type = getattr(detail_item, "video_type", "") or ""
        if detail_video_type:
            self.video_type = detail_video_type
        detail_container = getattr(detail_item, "container", "") or ""
        detail_media_type = getattr(detail_item, "media_type", "") or ""
        if detail_media_type:
            self.media_type = detail_media_type
        if detail_container:
            self.container = detail_container
        for attr in ("series_name", "season_number", "episode_number", "video_codec",
                     "video_width", "video_height", "audio_codec", "audio_channels", "audio_language", "runtime_ticks"):
            value = getattr(detail_item, attr, None)
            if value not in (None, "", 0):
                setattr(self, attr, value)

    # r89: Jellyfin/Emby "Type"-Werte, die eindeutig Audioinhalte kennzeichnen.
    # Wird gebraucht, weil embettete Cover-Art (mjpeg/png) in MediaStreams
    # sonst als "Video" durchgeht und Hoerbuecher faelschlich als Video
    # erkannt werden (siehe from_jellyfin unten).
    _JELLYFIN_AUDIO_TYPES = ("audio", "audiobook", "musicalbum")
    _ATTACHMENT_VIDEO_CODECS = ("mjpeg", "png", "bmp", "gif", "jpg", "jpeg")

    @classmethod
    def from_jellyfin(cls, raw, client):
        streams = raw.get("MediaStreams") or []
        if not streams:
            sources = raw.get("MediaSources") or []
            if sources:
                streams = (sources[0] or {}).get("MediaStreams") or []

        def _is_real_video_stream(s):
            if (s.get("Type") or "").lower() != "video":
                return False
            if s.get("IsAttachment"):
                return False
            codec = (s.get("Codec") or "").lower()
            if codec in cls._ATTACHMENT_VIDEO_CODECS:
                return False
            # Embedded cover art typically has no frame rate / very few frames;
            # a real video track always reports one. When Codec is ambiguous
            # but no frame rate is present at all, treat it as artwork too.
            if not codec and not s.get("RealFrameRate") and not s.get("AverageFrameRate"):
                return False
            return True

        video = next((s for s in streams if _is_real_video_stream(s)), {})
        audio = next((s for s in streams if (s.get("Type") or "").lower() == "audio"), {})

        # r89: Jellyfin/Emby liefern den zuverlaessigsten Hinweis direkt im
        # eigenen "Type"-Feld des Items (z. B. "Audio", "AudioBook"). Das
        # wurde bisher komplett ignoriert, wodurch media_type fuer JEDES
        # Jellyfin/Emby-Item leer blieb und _is_audio_item() sich allein auf
        # die (durch Cover-Art verfaelschte) Codec-Heuristik verlassen musste.
        raw_type = str(raw.get("Type") or "").strip().lower()
        media_type = raw_type if raw_type in cls._JELLYFIN_AUDIO_TYPES else ""

        raw_provider_ids = raw.get("ProviderIds") or {}
        provider_ids = {}
        for key, value in raw_provider_ids.items():
            if value:
                provider_ids[(key or "").strip().lower()] = str(value).strip()
        return cls(
            item_id=raw.get("Id"),
            title=raw.get("Name", "?"),
            server_name=client.server_name,
            year=raw.get("ProductionYear"),
            overview=raw.get("Overview", ""),
            genres=raw.get("Genres", []),
            rating=raw.get("CommunityRating"),
            poster_url=client.get_image_url(raw.get("Id"), "Primary"),
            backdrop_url=client.get_image_url(raw.get("Id"), "Backdrop"),
            resume_ticks=(raw.get("UserData") or {}).get("PlaybackPositionTicks", 0),
            played=(raw.get("UserData") or {}).get("Played", False),
            last_played_date=(raw.get("UserData") or {}).get("LastPlayedDate", ""),
            date_created=raw.get("DateCreated", ""),
            series_name=raw.get("SeriesName", ""),
            season_number=raw.get("ParentIndexNumber"),
            episode_number=raw.get("IndexNumber"),
            video_codec=video.get("Codec", ""),
            video_width=video.get("Width", 0),
            video_height=video.get("Height", 0),
            audio_codec=audio.get("Codec", ""),
            audio_channels=audio.get("Channels", 0),
            audio_language=audio.get("Language", ""),
            runtime_ticks=raw.get("RunTimeTicks", 0),
            parent_id=raw.get("ParentId", ""),
            provider_ids=provider_ids,
            is_favorite=(raw.get("UserData") or {}).get("IsFavorite", False),
            video_type=raw.get("VideoType", ""),
            container=raw.get("Container", ""),
            media_type=media_type,
        )

    @classmethod
    def from_emby(cls, raw, client):
        # Emby-API ist strukturell fast identisch zu Jellyfin
        return cls.from_jellyfin(raw, client)
