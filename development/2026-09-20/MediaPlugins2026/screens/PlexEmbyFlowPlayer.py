# -*- coding: utf-8 -*-
# MEDIAPLUGINS2026_PLEX_EMBYFLOW_BASE2
"""Plex adapter for the proven EmbyFlowE2 player UI.

This intentionally reuses EmbyFlowE2's player/OSD while keeping Plex playback
reporting inside MediaPlugins2026.  No Emby server/token is supplied for Plex.
"""

from Plugins.Extensions.EmbyFlowE2 import plugin as _embyflow


class PlexEmbyFlowMoviePlayer(_embyflow.EmbyFlowMoviePlayer):
    def __init__(self, session, ref, title, playback_info, last_service, plex_client, media_item):
        self._mp2026_plex_client = plex_client
        self._mp2026_media_item = media_item
        _embyflow.EmbyFlowMoviePlayer.__init__(
            self, session, ref, title, playback_info, last_service, False
        )

    def send_emby_playback_report(self, endpoint, position_ticks=0):
        """Translate EmbyFlow's lifecycle callbacks to Plex timeline calls."""
        client = getattr(self, "_mp2026_plex_client", None)
        item = getattr(self, "_mp2026_media_item", None)
        item_id = str(getattr(item, "id", "") or "")
        if not client or not item_id:
            return
        try:
            pos = max(0, int(position_ticks or 0))
            if endpoint == "Playing":
                client.report_playback_started(item_id, pos)
            elif endpoint == "Progress":
                client.report_playback_progress(item_id, pos)
            elif endpoint == "Stopped":
                client.report_playback_stopped(item_id, pos)
        except Exception:
            pass

    def cancel_active_encoding(self, play_session_id=None):
        # BASE2 uses Plex Direct Play only; there is no Emby encoding session.
        return True

    def embyflow_fetch_chapters_remote(self):
        # Never issue Emby /Items requests for a Plex item.  Local chapters are
        # still accepted when the adapter receives them in playback_info.
        try:
            return self.embyflow_extract_local_chapters()
        except Exception:
            return []

    def embyflow_seek_to_chapter(self, target_ticks):
        """Seek inside the active Plex Direct-Play service without Emby restart."""
        try:
            target_ticks = max(0, int(target_ticks or 0))
            service = self.session.nav.getCurrentService()
            seek = service and service.seek()
            if not seek:
                return False
            seek.seekTo(target_ticks)
            try:
                self.send_emby_playback_report("Progress", target_ticks)
            except Exception:
                pass
            return True
        except Exception:
            return False
