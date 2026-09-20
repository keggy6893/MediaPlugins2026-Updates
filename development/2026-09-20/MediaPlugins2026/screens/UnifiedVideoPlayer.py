# -*- coding: utf-8 -*-
# MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER1
# MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER2
# MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER3

from Components.ActionMap import ActionMap

from .InfuseMoviePlayer import InfuseMoviePlayer
from ..utils import log


class MediaPluginsVideoPlayer(InfuseMoviePlayer):
    """Ein gemeinsamer MediaPlugins2026-Player fuer Emby, Jellyfin und Plex."""

    def __init__(self, session, service, playback):
        self.playback = playback
        self._mediaplugins_chapters = list((playback.extra or {}).get("chapters") or [])
        self._mediaplugins_chapters_loading = False

        InfuseMoviePlayer.__init__(
            self,
            session,
            service,
            playback.item,
            playback.client,
            playback.stream_url,
            playback.start_ticks,
        )

        # Farblogik exakt wie im Zielentwurf:
        # ROT Untertitel / GRUEN Audio / GELB Kapitel / BLAU Info.
        self["mediaplugins_unified_actions"] = ActionMap(
            ["OkCancelActions", "InfobarActions", "InfobarEPGActions", "ColorActions"],
            {
                "ok": self._showInfuseOSD,
                "red": self._openSubtitleSelection,
                "green": self._openAudioSelection,
                "yellow": self._openChapterSelection,
                "blue": self._openPlayerInfo,
                "info": self._openPlayerInfo,
                "showEventInfo": self._openPlayerInfo,
            },
            -5,
        )

        try:
            self.onLayoutFinish.append(self._loadUnifiedChapters)
        except Exception:
            pass

        log.info(
            "UnifiedPlayer3 start provider=%s engine=%s title=%r",
            playback.provider,
            playback.engine_label(),
            getattr(playback.item, "title", ""),
        )

    def _loadUnifiedChapters(self):
        if self._mediaplugins_chapters or self._mediaplugins_chapters_loading:
            return
        client = getattr(self.playback, "client", None)
        loader = getattr(client, "get_audio_info", None)
        if not callable(loader):
            return

        item_id = str(getattr(self.playback.item, "id", "") or "")
        if not item_id:
            return

        self._mediaplugins_chapters_loading = True

        def done(info):
            self._mediaplugins_chapters_loading = False
            try:
                chapters = list((info or {}).get("chapters") or [])
            except Exception:
                chapters = []
            if chapters:
                self._mediaplugins_chapters = chapters
                try:
                    self.playback.extra["chapters"] = chapters
                except Exception:
                    pass
                log.info("UnifiedPlayer3 Kapitel geladen: %d", len(chapters))

        def failed(error):
            self._mediaplugins_chapters_loading = False
            log.info("UnifiedPlayer3 Kapitel nicht verfuegbar: %s", error)

        try:
            loader(item_id, done, failed)
        except Exception as error:
            failed(error)

    def _showInfuseOSD(self):
        if self._closing_by_user or self._osd_open:
            return
        try:
            if getattr(self.session, "current_dialog", None) is not self:
                return
        except Exception:
            pass
        try:
            from .InfusePlayerOSD import InfusePlayerOSD
            self._osd_open = True
            self.session.openWithCallback(
                self._onOSDClosed,
                InfusePlayerOSD,
                self,
                self._infuse_item,
            )
        except Exception as error:
            self._osd_open = False
            log.warning("UnifiedPlayer3 OSD konnte nicht geoeffnet werden: %s", error)

    def _onOSDClosed(self, action=None):
        self._osd_open = False
        if action == "stop":
            self._leaveInfusePlayer()
            return
        if action == "audio":
            self._openAudioSelection()
            return
        if action == "subtitle":
            self._openSubtitleSelection()
            return
        if action == "chapters":
            self._openChapterSelection()
            return
        if action == "info":
            self._openPlayerInfo()

    def _openChapterSelection(self):
        if self._closing_by_user:
            return
        try:
            if getattr(self.session, "current_dialog", None) is not self:
                return
        except Exception:
            pass
        self._loadUnifiedChapters()
        try:
            from .UnifiedChapterSelection import MediaPluginsChapterSelection
            self.session.open(MediaPluginsChapterSelection, self)
        except Exception as error:
            log.warning("UnifiedPlayer3 Kapitelmenue konnte nicht geoeffnet werden: %s", error)

    def _openPlayerInfo(self):
        if self._closing_by_user:
            return
        try:
            if getattr(self.session, "current_dialog", None) is not self:
                return
        except Exception:
            pass
        try:
            from .UnifiedPlayerInfo import MediaPluginsPlayerInfo
            self.session.open(MediaPluginsPlayerInfo, self.playback)
        except Exception as error:
            log.warning("UnifiedPlayer3 Medieninfo konnte nicht geoeffnet werden: %s", error)
