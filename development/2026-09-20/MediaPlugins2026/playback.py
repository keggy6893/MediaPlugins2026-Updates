# -*- coding: utf-8 -*-
# MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER1


class PlaybackContext(object):
    """Provider-neutral playback state used by the shared MediaPlugins2026 player."""

    def __init__(self, provider, item, client, stream_url, start_ticks=0,
                 service_type=4097, extra=None):
        self.provider = str(provider or "").strip().lower()
        self.item = item
        self.client = client
        self.stream_url = str(stream_url or "")
        self.start_ticks = max(0, int(start_ticks or 0))
        self.service_type = int(service_type or 4097)
        self.extra = dict(extra or {})

    def provider_label(self):
        return {
            "emby": "EMBY",
            "jellyfin": "JELLYFIN",
            "plex": "PLEX",
        }.get(self.provider, (self.provider or "MEDIA").upper())

    def mode_label(self):
        url = self.stream_url.lower()
        if "master.m3u8" in url or ".m3u8" in url:
            return "HLS / Transcoding"
        if "static=true" in url:
            return "Direct Play"
        if "transcode" in url or "/stream.ts" in url:
            return "Transcoding"
        return "Stream"

    def engine_label(self):
        names = {
            4097: "Enigma2",
            5001: "GstPlayer",
            5002: "ExtEplayer3",
        }
        return "%s (%d)" % (names.get(self.service_type, "Service"), self.service_type)
