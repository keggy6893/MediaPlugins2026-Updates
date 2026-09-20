# -*- coding: utf-8 -*-
# MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER1
# MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER3
# MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER4
# MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER5
# MEDIAPLUGINS2026_UNIFIED_OSD_FIX5_PANEL_POLISH
# MEDIAPLUGINS2026_UNIFIED_OSD_FIX6_PANEL_ZORDER
# MEDIAPLUGINS2026_UNIFIED_OSD_FIX7_BOTTOM_ALIGN
# MEDIAPLUGINS2026_UNIFIED_OSD_FIX8_BASE_BOTTOM_PANEL_UP

from enigma import eTimer, iServiceInformation
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Components.Pixmap import Pixmap
from ..utils.image_cache import image_cache

from ..utils import log

try:
    from skin import parseColor
except Exception:
    parseColor = None


class InfusePlayerOSD(Screen):
    """Kompaktes Cinema-OSD ueber dem laufenden Video.

    V4 bleibt absichtlich bei einem kompakten Overlay-Screen. Der Playerkern
    bleibt unangetastet; hier wird nur die Darstellung des OSD verfeinert.
    """

    AUTO_HIDE_MS = 8000
    UPDATE_MS = 1000

    skin = """
    <screen name="InfusePlayerOSD" position="40,580" size="1840,500"
            flags="wfNoBorder" backgroundColor="#C0091622">
        <eLabel position="0,264" size="1840,2" backgroundColor="#18A7E0" zPosition="1" />

        <widget name="title" position="32,277" size="1050,42" font="Bold;34"
                foregroundColor="#FFFFFF" transparent="1" zPosition="3" />
        <widget name="meta" position="32,319" size="1050,27" font="Regular;18"
                foregroundColor="#B8CDD9" transparent="1" />

        <widget name="chapter_bg" position="1200,273" size="420,82" font="Regular;1"
                foregroundColor="#0B1823" backgroundColor="#B80B1823" transparent="0"
                borderWidth="1" borderColor="#2E6683" />
        <widget name="chapter_head" position="1220,283" size="378,20" font="Regular;15"
                foregroundColor="#9FB6C6" transparent="1" halign="right" />
        <widget name="chapter_name" position="1220,305" size="378,25" font="Bold;18"
                foregroundColor="#FFFFFF" transparent="1" halign="right" />
        <widget name="chapter_range" position="1220,331" size="378,19" font="Regular;15"
                foregroundColor="#8CCEF6" transparent="1" halign="right" />

        <widget name="clock" position="1650,281" size="150,30" font="Regular;23"
                foregroundColor="#FFFFFF" transparent="1" halign="right" />
        <widget name="provider_top" position="1650,314" size="150,25" font="Bold;17"
                foregroundColor="#35C96B" transparent="1" halign="right" />

        <widget name="position" position="32,360" size="125,30" font="Regular;21"
                foregroundColor="#FFFFFF" transparent="1" zPosition="3" />
        <widget name="progress" position="160,368" size="1475,14" borderWidth="1"
                borderColor="#49677A" backgroundColor="#172935" foregroundColor="#18A7E0" />
        <widget name="duration" position="1645,360" size="155,30" font="Regular;21"
                foregroundColor="#FFFFFF" transparent="1" halign="right" />

        <eLabel position="32,396" size="1768,1" backgroundColor="#29495D" />

        <widget name="transport" position="32,407" size="225,42" font="Bold;23"
                foregroundColor="#FFFFFF" transparent="1" zPosition="3" />

        <widget name="key_red" position="295,405" size="215,44" font="Regular;19"
                foregroundColor="#F3F7FA" backgroundColor="#121F2A" transparent="0"
                halign="center" valign="center" borderWidth="1" borderColor="#2E6683" />
        <widget name="dot_red" position="312,414" size="24,24" font="Regular;19"
                foregroundColor="#FF4D55" transparent="1" halign="center" />

        <widget name="key_green" position="520,405" size="185,44" font="Regular;19"
                foregroundColor="#F3F7FA" backgroundColor="#121F2A" transparent="0"
                halign="center" valign="center" borderWidth="1" borderColor="#2E6683" />
        <widget name="dot_green" position="536,414" size="24,24" font="Regular;19"
                foregroundColor="#36D46A" transparent="1" halign="center" />

        <widget name="key_yellow" position="715,405" size="185,44" font="Regular;19"
                foregroundColor="#F3F7FA" backgroundColor="#121F2A" transparent="0"
                halign="center" valign="center" borderWidth="1" borderColor="#2E6683" />
        <widget name="dot_yellow" position="731,414" size="24,24" font="Regular;19"
                foregroundColor="#FFC229" transparent="1" halign="center" />

        <widget name="key_blue" position="910,405" size="165,44" font="Regular;19"
                foregroundColor="#F3F7FA" backgroundColor="#121F2A" transparent="0"
                halign="center" valign="center" borderWidth="1" borderColor="#2E6683" />
        <widget name="dot_blue" position="926,414" size="24,24" font="Regular;19"
                foregroundColor="#1EA7FF" transparent="1" halign="center" />

        <widget name="seekhint" position="1100,413" size="700,30" font="Regular;15"
                foregroundColor="#7893A9" transparent="1" halign="right" />

        <widget name="brand" position="32,458" size="520,26" font="Regular;15"
                foregroundColor="#66889C" transparent="1" />

        <widget name="provider_badge" position="1170,452" size="135,32" font="Bold;17"
                foregroundColor="#35C96B" backgroundColor="#101B25" transparent="0"
                halign="center" valign="center" borderWidth="1" borderColor="#315B73" />
        <widget name="mode" position="1315,452" size="140,32" font="Regular;16"
                foregroundColor="#F1F6F9" backgroundColor="#101B25" transparent="0"
                halign="center" valign="center" borderWidth="1" borderColor="#315B73" />
        <widget name="quality" position="1465,452" size="95,32" font="Regular;16"
                foregroundColor="#D8E9F3" backgroundColor="#101B25" transparent="0"
                halign="center" valign="center" borderWidth="1" borderColor="#315B73" />
        <widget name="codec_badge" position="1570,452" size="100,32" font="Regular;16"
                foregroundColor="#D8E9F3" backgroundColor="#101B25" transparent="0"
                halign="center" valign="center" borderWidth="1" borderColor="#315B73" />
        <widget name="bitrate_badge" position="1680,452" size="120,32" font="Regular;16"
                foregroundColor="#D8E9F3" backgroundColor="#101B25" transparent="0"
                halign="center" valign="center" borderWidth="1" borderColor="#315B73" />

        <!-- FIX7: ein ausklappbares Panel statt vier permanenten Spalten -->
        <widget name="panel_bg" position="15,0" size="1810,252" font="Regular;1"
                foregroundColor="#091722" backgroundColor="#E0091722" transparent="0"
                borderWidth="2" borderColor="#2B8CB8" zPosition="0" />
        <widget name="panel_head" position="38,14" size="1745,34" font="Bold;22"
                foregroundColor="#FFFFFF" transparent="1" zPosition="3" />
        <widget name="panel_rule" position="38,52" size="1745,2" font="Regular;1"
                foregroundColor="#18A7E0" backgroundColor="#18A7E0" transparent="0" zPosition="2" />
        <widget name="panel_body" position="42,68" size="1715,165" font="Regular;21"
                foregroundColor="#E5F1F7" transparent="1" zPosition="3" />

        <!-- Kapitel-Vorschau: drei echte Server-Chapter-Images, falls vorhanden -->
        <widget name="chapter_img0" position="70,73" size="300,169" alphatest="blend" scale="1" zPosition="4" />
        <widget name="chapter_img1" position="570,73" size="300,169" alphatest="blend" scale="1" zPosition="4" />
        <widget name="chapter_img2" position="1070,73" size="300,169" alphatest="blend" scale="1" zPosition="4" />
        <widget name="chapter_txt0" position="382,86" size="170,135" font="Regular;20" foregroundColor="#DCEAF2" transparent="1" zPosition="4" />
        <widget name="chapter_txt1" position="882,86" size="170,135" font="Regular;20" foregroundColor="#DCEAF2" transparent="1" zPosition="4" />
        <widget name="chapter_txt2" position="1382,86" size="170,135" font="Regular;20" foregroundColor="#DCEAF2" transparent="1" zPosition="4" />
    </screen>
    """

    PROVIDER_COLORS = {
        "emby": "#35C96B",
        "jellyfin": "#9B5DE5",
        "plex": "#F5B51B",
    }

    def __init__(self, session, player, item):
        Screen.__init__(self, session)
        self.player = player
        self.item = item
        self.playback = getattr(player, "playback", None)
        self._closing = False

        self["title"] = Label(self._displayTitle())
        self["meta"] = Label(self._metaLine())
        self["clock"] = Label("")
        provider_label = self.playback.provider_label() if self.playback else "MEDIA"
        self["provider_top"] = Label(provider_label)

        self["chapter_bg"] = Label("")
        self["chapter_head"] = Label("")
        self["chapter_name"] = Label("")
        self["chapter_range"] = Label("")

        self["position"] = Label("00:00")
        self["duration"] = Label("--:--")
        self["progress"] = ProgressBar()
        self["progress"].setRange((0, 1000))
        self["progress"].setValue(0)
        self["transport"] = Label("◀    II    ▶")

        self["key_red"] = Label("Untertitel")
        self["dot_red"] = Label("●")
        self["key_green"] = Label("Audio")
        self["dot_green"] = Label("●")
        self["key_yellow"] = Label("Kapitel")
        self["dot_yellow"] = Label("●")
        self["key_blue"] = Label("Info")
        self["dot_blue"] = Label("●")
        self["seekhint"] = Label("LEFT/RIGHT 5s   1/3 10s   4/6 30s   7/9 60s")

        self["provider_badge"] = Label(provider_label)
        self["mode"] = Label(self.playback.mode_label() if self.playback else "Stream")
        self["quality"] = Label(self._qualityLabel())
        self["codec_badge"] = Label(self._codecLabel())
        self["bitrate_badge"] = Label(self._bitrateLabel())
        self["brand"] = Label("MediaPlugins2026   •   Ein Player. Alle Provider. Ein Erlebnis.")
        self._panel_mode = None
        self._chapter_selected = 0
        self._chapter_image_generation = 0
        self["panel_bg"] = Label("")
        self["panel_head"] = Label("")
        self["panel_rule"] = Label("")
        self["panel_body"] = Label("")
        for _idx in range(3):
            self["chapter_img%d" % _idx] = Pixmap()
            self["chapter_txt%d" % _idx] = Label("")

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions", "NumberActions", "InfobarActions", "InfobarSeekActions", "InfobarEPGActions"],
            {
                "ok": self.keyOK,
                "cancel": self.close,
                "left": lambda: self._seek(-5),
                "right": lambda: self._seek(5),
                "1": lambda: self._seek(-10),
                "3": lambda: self._seek(10),
                "4": lambda: self._seek(-30),
                "6": lambda: self._seek(30),
                "7": lambda: self._seek(-60),
                "9": lambda: self._seek(60),
                "red": self.keySubtitle,
                "green": self.keyAudio,
                "yellow": self.keyChapters,
                "blue": self.keyInfo,
                "info": self.keyInfo,
                "showEventInfo": self.keyInfo,
                "stop": self.keyStop,
                "playpauseService": self.keyPlayPause,
                "pauseService": self.keyPlayPause,
            },
            -5,
        )

        self._update_timer = eTimer()
        self._update_timer.callback.append(self._updateProgress)
        self._hide_timer = eTimer()
        self._hide_timer.callback.append(self.close)
        self.onLayoutFinish.append(self._onLayout)
        self.onClose.append(self._onClose)

    def _onLayout(self):
        self._applyProviderColor()
        self._hidePanelWidgets()
        self._updateProgress()
        self._update_timer.start(self.UPDATE_MS, False)
        self._restartHideTimer()

    def _applyProviderColor(self):
        if not parseColor:
            return
        provider = str(getattr(self.playback, "provider", "") or "").lower()
        color = self.PROVIDER_COLORS.get(provider, "#1EA7FF")
        for name in ("provider_top", "provider_badge"):
            try:
                if self[name].instance:
                    self[name].instance.setForegroundColor(parseColor(color))
            except Exception:
                pass

    def _displayTitle(self):
        series = getattr(self.item, "series_name", "") or ""
        return series or (getattr(self.item, "title", "") or "")

    def _metaLine(self):
        parts = []
        series = getattr(self.item, "series_name", "") or ""
        if series:
            season = getattr(self.item, "season_number", None)
            episode = getattr(self.item, "episode_number", None)
            if season is not None:
                parts.append("S%s" % season)
            if episode is not None:
                parts.append("E%s" % episode)
            title = getattr(self.item, "title", "") or ""
            if title:
                parts.append(title)
        else:
            year = getattr(self.item, "year", None)
            if year:
                parts.append(str(year))
            genres = list(getattr(self.item, "genres", []) or [])[:2]
            if genres:
                parts.append(" / ".join(str(x) for x in genres if x))

        runtime_ticks = int(getattr(self.item, "runtime_ticks", 0) or 0)
        if runtime_ticks:
            parts.append("%d min" % max(1, int(runtime_ticks // 10000000 // 60)))
        quality = self._qualityLabel()
        if quality and quality != "VIDEO":
            parts.append(quality)
        codec = self._codecLabel()
        if codec and codec != "-":
            parts.append(codec)
        return "  •  ".join(parts)

    def _qualityLabel(self):
        height = int(getattr(self.item, "video_height", 0) or 0)
        if height >= 2160:
            return "4K"
        if height >= 1080:
            return "1080p"
        if height >= 720:
            return "720p"
        if height:
            return "%dp" % height
        try:
            service = self.session.nav.getCurrentService()
            info = service and service.info()
            height = info and info.getInfo(iServiceInformation.sVideoHeight)
            if height and height > 0:
                return "%dp" % int(height)
        except Exception:
            pass
        return "VIDEO"

    def _codecLabel(self):
        codec = (getattr(self.item, "video_codec", "") or "").upper()
        if codec in ("H265", "H.265"):
            codec = "HEVC"
        elif codec in ("H264", "H.264"):
            codec = "H264"
        return codec or "VIDEO"


    def _bitrateLabel(self):
        # Server-Metadaten verwenden, wenn vorhanden; keine erfundene Bitrate.
        for name in ("bitrate", "video_bitrate", "media_bitrate"):
            try:
                value = int(getattr(self.item, name, 0) or 0)
            except Exception:
                value = 0
            if value > 0:
                # Jellyfin/Emby liefern Bitraten ueblicherweise in bit/s.
                if value >= 1000000:
                    return "%.1f Mbps" % (float(value) / 1000000.0)
                if value >= 1000:
                    return "%.1f Mbps" % (float(value) / 1000.0)
        return "— Mbps"


    def _audioPanelText(self):
        lines = []
        try:
            service = self.session.nav.getCurrentService()
            tracks = service and service.audioTracks()
            count = tracks and tracks.getNumberOfTracks() or 0
            current = tracks.getCurrentTrack() if tracks else -1
            for idx in range(min(int(count), 6)):
                info = tracks.getTrackInfo(idx)
                lang = (info.getLanguage() or "Audio").replace("und", "Unbekannt")
                desc = info.getDescription() or ""
                mark = "✓" if idx == current else " "
                lines.append("%s  %-10s  %s" % (mark, lang[:10], desc[:22]))
        except Exception:
            pass
        if not lines:
            lines.append("Keine Trackdaten verfügbar")
        return "\n".join(lines)

    def _subtitlePanelText(self):
        lines = ["○  Aus"]
        try:
            service = self.session.nav.getCurrentService()
            subs = service and service.subtitle()
            entries = list(subs.getSubtitleList() or []) if subs else []
            for entry in entries[:6]:
                lang = str(entry[4] if len(entry) > 4 and entry[4] else "Untertitel")
                lines.append("○  %s" % lang[:30])
        except Exception:
            pass
        return "\n".join(lines)

    def _chapterPanelText(self):
        lines = []
        chapters = list(getattr(self.player, "_mediaplugins_chapters", []) or [])
        pos, _length = self._positions()
        pos_ticks = int(max(0, pos) * 10000000 // 90000)
        current = 0
        for idx, chapter in enumerate(chapters):
            if int(chapter.get("start_ticks") or 0) <= pos_ticks:
                current = idx
        start = max(0, current - 1)
        for idx, chapter in enumerate(chapters[start:start + 6], start):
            mark = "▶" if idx == current else " "
            name = str(chapter.get("name") or ("Kapitel %d" % (idx + 1)))
            tm = self._fmt(int(chapter.get("start_ticks") or 0) // 10000000)
            lines.append("%s %2d. %-19s %s" % (mark, idx + 1, name[:19], tm))
        if not chapters:
            lines.append("Keine Kapiteldaten verfügbar")
        return "\n".join(lines)

    def _infoPanelText(self):
        provider = self.playback.provider_label() if self.playback else "MEDIA"
        title = self._displayTitle()
        return "\n".join([
            "%s" % title[:36],
            "Provider       %s" % provider,
            "Qualität       %s" % self._qualityLabel(),
            "Video          %s" % self._codecLabel(),
            "Wiedergabe     %s" % (self.playback.mode_label() if self.playback else "Stream"),
            "Bitrate        %s" % self._bitrateLabel(),
        ])

    @staticmethod
    def _fmt(seconds):
        try:
            seconds = max(0, int(seconds or 0))
            h, rem = divmod(seconds, 3600)
            m, s = divmod(rem, 60)
            return ("%d:%02d:%02d" % (h, m, s)) if h else ("%02d:%02d" % (m, s))
        except Exception:
            return "00:00"

    def _positions(self):
        try:
            seek = self.player._getSeek()
            if not seek:
                return 0, 0
            err_pos, pos = seek.getPlayPosition()
            err_len, length = seek.getLength()
            if err_pos != 0 or pos is None:
                pos = 0
            if err_len != 0 or length is None:
                length = 0
            return max(0, int(pos)), max(0, int(length))
        except Exception:
            return 0, 0

    def _updateChapter(self, pos_pts, length_pts):
        chapters = list(getattr(self.player, "_mediaplugins_chapters", []) or [])
        names = ("chapter_bg", "chapter_head", "chapter_name", "chapter_range")
        if not chapters:
            for name in names:
                try:
                    self[name].hide()
                except Exception:
                    pass
            return

        pos_ticks = int(max(0, pos_pts) * 10000000 // 90000)
        current = 0
        for idx, chapter in enumerate(chapters):
            try:
                if int(chapter.get("start_ticks") or 0) <= pos_ticks:
                    current = idx
                else:
                    break
            except Exception:
                pass

        chapter = chapters[current]
        start_ticks = int(chapter.get("start_ticks") or 0)
        if current + 1 < len(chapters):
            end_ticks = int(chapters[current + 1].get("start_ticks") or 0)
        else:
            end_ticks = int(max(0, length_pts) * 10000000 // 90000)

        self["chapter_head"].setText("Kapitel %d / %d" % (current + 1, len(chapters)))
        self["chapter_name"].setText(str(chapter.get("name") or ("Kapitel %d" % (current + 1))))
        self["chapter_range"].setText("%s – %s" % (
            self._fmt(start_ticks // 10000000),
            self._fmt(end_ticks // 10000000) if end_ticks else "--:--",
        ))
        for name in names:
            try:
                self[name].show()
            except Exception:
                pass

    def _updateProgress(self):
        if self._closing:
            return
        pos, length = self._positions()
        self["position"].setText(self._fmt(pos // 90000))
        self["duration"].setText(self._fmt(length // 90000) if length else "--:--")
        if length > 0:
            self["progress"].setValue(max(0, min(1000, int(pos * 1000 // length))))
        else:
            self["progress"].setValue(0)
        self._updateChapter(pos, length)
        if self._panel_mode == "chapters":
            self._refreshChapterPanel()
        try:
            import time
            self["clock"].setText(time.strftime("%H:%M"))
        except Exception:
            pass

    def _restartHideTimer(self):
        try:
            self._hide_timer.stop()
            self._hide_timer.start(self.AUTO_HIDE_MS, True)
        except Exception:
            pass

    def _seek(self, seconds):
        if self._panel_mode == "chapters":
            chapters = list(getattr(self.player, "_mediaplugins_chapters", []) or [])
            if chapters:
                step = 1 if seconds > 0 else -1
                self._chapter_selected = max(0, min(len(chapters) - 1, self._chapter_selected + step))
                self._refreshChapterPanel(force_images=True)
            return
        self._restartHideTimer()
        try:
            seek = self.player._getSeek()
            if not seek:
                return
            direction = 1 if seconds >= 0 else -1
            seek.seekRelative(direction, abs(int(seconds)) * 90000)
            self._updateProgress()
        except Exception as error:
            log.warning("UnifiedPlayer5 OSD Seek %ss fehlgeschlagen: %s", seconds, error)

    def _panelNames(self):
        return ["panel_bg", "panel_head", "panel_rule", "panel_body"] + [
            "chapter_img%d" % i for i in range(3)
        ] + ["chapter_txt%d" % i for i in range(3)]

    def _hidePanelWidgets(self):
        for name in self._panelNames():
            try:
                self[name].hide()
            except Exception:
                pass

    def _showBasePanel(self):
        for name in ("panel_bg", "panel_head", "panel_rule", "panel_body"):
            try:
                self[name].show()
            except Exception:
                pass

    def _togglePanel(self, mode):
        if self._panel_mode == mode:
            self._panel_mode = None
            self._hidePanelWidgets()
            self._restartHideTimer()
            return
        self._panel_mode = mode
        try:
            self._hide_timer.stop()
        except Exception:
            pass
        self._hidePanelWidgets()
        self._showBasePanel()
        if mode == "audio":
            self["panel_head"].setText("Audio Auswahl   •   GRÜN zum Einklappen")
            self["panel_body"].setText(self._audioPanelText())
        elif mode == "subtitle":
            self["panel_head"].setText("Untertitel Auswahl   •   ROT zum Einklappen")
            self["panel_body"].setText(self._subtitlePanelText())
        elif mode == "info":
            self["panel_head"].setText("Medieninformationen   •   BLAU zum Einklappen")
            self["panel_body"].setText(self._infoPanelText())
        elif mode == "chapters":
            self["panel_head"].setText("Kapitel   •   LINKS/RECHTS auswählen   •   OK springen   •   GELB einklappen")
            self["panel_body"].hide()
            self._chapter_selected = self._currentChapterIndex()
            self._refreshChapterPanel(force_images=True)

    def _currentChapterIndex(self):
        chapters = list(getattr(self.player, "_mediaplugins_chapters", []) or [])
        if not chapters:
            return 0
        pos, _length = self._positions()
        ticks = int(max(0, pos) * 10000000 // 90000)
        current = 0
        for idx, chapter in enumerate(chapters):
            if int(chapter.get("start_ticks") or 0) <= ticks:
                current = idx
            else:
                break
        return current

    def _chapterImageUrl(self, chapter_index):
        client = getattr(self.playback, "client", None)
        maker = getattr(client, "get_chapter_image_url", None)
        item_id = str(getattr(self.item, "id", "") or "")
        if callable(maker) and item_id:
            try:
                return maker(item_id, chapter_index)
            except Exception:
                return None
        return None

    def _refreshChapterPanel(self, force_images=False):
        if self._panel_mode != "chapters":
            return
        chapters = list(getattr(self.player, "_mediaplugins_chapters", []) or [])
        if not chapters:
            self["panel_body"].setText("Keine Kapiteldaten verfügbar")
            self["panel_body"].show()
            return
        self._chapter_selected = max(0, min(len(chapters) - 1, self._chapter_selected))
        start = max(0, min(len(chapters) - 3, self._chapter_selected - 1))
        visible = list(range(start, min(start + 3, len(chapters))))
        self._chapter_image_generation += 1
        generation = self._chapter_image_generation
        for slot in range(3):
            try:
                self["chapter_img%d" % slot].hide()
                self["chapter_txt%d" % slot].hide()
            except Exception:
                pass
            if slot >= len(visible):
                continue
            idx = visible[slot]
            chapter = chapters[idx]
            mark = "▶ " if idx == self._chapter_selected else ""
            name = str(chapter.get("name") or ("Kapitel %d" % (idx + 1)))
            tm = self._fmt(int(chapter.get("start_ticks") or 0) // 10000000)
            self["chapter_txt%d" % slot].setText("%s%d/%d\n%s\n%s" % (mark, idx + 1, len(chapters), name[:22], tm))
            self["chapter_txt%d" % slot].show()
            url = self._chapterImageUrl(idx)
            if not url:
                continue
            cached = image_cache.get_local_path(url)
            if cached:
                self._setChapterPixmap(slot, cached)
            else:
                def loaded(path, _slot=slot, _gen=generation):
                    if self._panel_mode == "chapters" and _gen == self._chapter_image_generation:
                        self._setChapterPixmap(_slot, path)
                image_cache.fetch(url, loaded, lambda _err: None)

    def _setChapterPixmap(self, slot, path):
        try:
            widget = self["chapter_img%d" % slot]
            if widget.instance and path:
                widget.instance.setPixmapFromFile(path)
                widget.show()
        except Exception as error:
            log.debug("UnifiedPlayer7 Kapitelbild konnte nicht gesetzt werden: %s", error)

    def keyOK(self):
        if self._panel_mode == "chapters":
            chapters = list(getattr(self.player, "_mediaplugins_chapters", []) or [])
            if 0 <= self._chapter_selected < len(chapters):
                try:
                    ticks = int(chapters[self._chapter_selected].get("start_ticks") or 0)
                    seek = self.player._getSeek()
                    if seek:
                        seek.seekTo(int(ticks * 90000 // 10000000))
                        self._updateProgress()
                except Exception as error:
                    log.warning("UnifiedPlayer7 Kapitel-Sprung fehlgeschlagen: %s", error)
            return
        self.close()

    def keyInfo(self):
        self._togglePanel("info")

    def keyPlayPause(self):
        self._restartHideTimer()
        try:
            self.player._callMoviePlayerAction(("playpauseService", "pauseService"))
        except Exception as error:
            log.warning("UnifiedPlayer5 Play/Pause fehlgeschlagen: %s", error)

    def keyAudio(self):
        self._togglePanel("audio")

    def keySubtitle(self):
        self._togglePanel("subtitle")

    def keyChapters(self):
        self._togglePanel("chapters")

    def keyStop(self):
        self.close("stop")

    def _onClose(self):
        self._closing = True
        try:
            self._update_timer.stop()
            self._hide_timer.stop()
        except Exception:
            pass
