# -*- coding: utf-8 -*-
# MEDIAPLUGINS2026_AUDIOPLAYER_COVERDISC1
# MEDIAPLUGINS2026_AUDIOPLAYER1

import os
import time

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.ServiceEventTracker import ServiceEventTracker
from enigma import eServiceReference, eTimer, iPlayableService

from ..utils.image_cache import image_cache
from ..utils import log


TICKS_PER_SECOND = 10000000
PTS_PER_SECOND = 90000


class MediaPluginsAudioPlayer(Screen):
    """Eigener Audio-/Hoerbuchplayer fuer Media Plugins 2026.

    Direct Play ist formatneutral. Wenn die Box den Originalstream nicht
    starten kann, wird einmalig auf den vom Server erzeugten MP3-Fallback
    gewechselt. Video-Player und Provider-Routing bleiben unangetastet.
    """

    skinName = "MediaPlugins2026AudioPlayer"
    skin = """
    <screen name="MediaPlugins2026AudioPlayer" position="0,0" size="1920,1080"
            flags="wfNoBorder" backgroundColor="#120914" title="Audio Player">
        <widget name="background" position="0,0" size="1920,1080" alphatest="blend" scale="1" zPosition="0" />

        <widget name="brand" position="44,24" size="600,44" font="Regular;28"
                foregroundColor="#ffffff" transparent="1" zPosition="5" />
        <widget name="clock" position="1720,22" size="150,44" font="Regular;28"
                foregroundColor="#ffffff" transparent="1" halign="right" zPosition="5" />

        <widget name="vinyl" position="128,242" size="430,430" alphatest="blend" scale="1" zPosition="2" />
        <widget name="cover" position="151,265" size="384,384" alphatest="blend" scale="1" zPosition="3" />
        <widget name="cover_mask" position="128,242" size="430,430" alphatest="blend" scale="1" zPosition="4" />

        <widget name="title" position="560,310" size="1070,128" font="Regular;47"
                foregroundColor="#ffffff" transparent="1" valign="center" zPosition="5" />
        <widget name="chapter" position="560,450" size="1120,50" font="Regular;27"
                foregroundColor="#4cf2b7" transparent="1" zPosition="5" />
        <widget name="meta" position="560,510" size="1120,40" font="Regular;22"
                foregroundColor="#d8e3e2" transparent="1" zPosition="5" />

        <widget name="wave1" position="560,580" size="10,32" backgroundColor="#ff1698" transparent="0" zPosition="5" />
        <widget name="wave2" position="580,566" size="10,46" backgroundColor="#ff3ca7" transparent="0" zPosition="5" />
        <widget name="wave3" position="600,550" size="10,62" backgroundColor="#4cf2b7" transparent="0" zPosition="5" />
        <widget name="wave4" position="620,574" size="10,38" backgroundColor="#ff1698" transparent="0" zPosition="5" />
        <widget name="wave5" position="640,558" size="10,54" backgroundColor="#ff3ca7" transparent="0" zPosition="5" />
        <widget name="wave6" position="660,544" size="10,68" backgroundColor="#4cf2b7" transparent="0" zPosition="5" />
        <widget name="wave7" position="680,578" size="10,34" backgroundColor="#ff1698" transparent="0" zPosition="5" />
        <widget name="wave8" position="700,562" size="10,50" backgroundColor="#4cf2b7" transparent="0" zPosition="5" />

        <widget name="progress" position="220,812" size="1470,12" borderWidth="0" zPosition="5" />
        <widget name="elapsed" position="220,842" size="260,38" font="Regular;25"
                foregroundColor="#ffffff" transparent="1" zPosition="5" />
        <widget name="remaining" position="1370,842" size="320,38" font="Regular;25"
                foregroundColor="#ffffff" transparent="1" halign="right" zPosition="5" />

        <widget name="seek_back" position="710,900" size="190,70" font="Regular;31"
                foregroundColor="#ffffff" transparent="1" halign="center" valign="center" zPosition="5" />
        <widget name="pause" position="900,886" size="120,96" font="Regular;48"
                foregroundColor="#ffffff" backgroundColor="#8c0b61" transparent="0"
                halign="center" valign="center" zPosition="5" />
        <widget name="seek_fwd" position="1020,900" size="190,70" font="Regular;31"
                foregroundColor="#ffffff" transparent="1" halign="center" valign="center" zPosition="5" />

        <widget name="hint" position="220,1000" size="1470,40" font="Regular;19"
                foregroundColor="#d7e4e1" transparent="1" halign="center" zPosition="5" />
        <widget name="mode" position="1400,1000" size="290,40" font="Regular;18"
                foregroundColor="#8fe6cd" transparent="1" halign="right" zPosition="5" />
    </screen>
    """

    def __init__(self, session, item, client, start_ticks=None):
        Screen.__init__(self, session)
        self.item = item
        self.client = client
        self.start_ticks = max(0, int(start_ticks or 0))
        self.old_service = None
        try:
            self.old_service = session.nav.getCurrentlyPlayingServiceReference()
        except Exception:
            pass

        self._closing = False
        self._started = False
        self._paused = False
        self._fallback_used = False
        self._stream_candidates = []
        self._candidate_index = 0
        self._start_time = 0.0
        self._chapters = []
        self._resume_applied = False
        self._last_report_ticks = -1

        self["background"] = Pixmap()
        self["vinyl"] = Pixmap()
        self["cover"] = Pixmap()
        self["cover_mask"] = Pixmap()
        self["brand"] = Label("MEDIA PLUGINS 2026")
        self["clock"] = Label("")
        self["title"] = Label(str(getattr(item, "title", "") or "Audio"))
        self["chapter"] = Label("HÖRBUCH / AUDIO")
        self["meta"] = Label("")
        self["progress"] = ProgressBar()
        self["elapsed"] = Label("0:00")
        self["remaining"] = Label("GESAMT-REST --:--")
        self["seek_back"] = Label("◀◀  30")
        self["pause"] = Label("II")
        self["seek_fwd"] = Label("30  ▶▶")
        self["hint"] = Label("ROT Zurück   •   OK/GRÜN Pause   •   ◀/▶ ±30 Sek.   •   ▲/▼ Kapitel")
        self["mode"] = Label("")
        for i in range(1, 9):
            self["wave%d" % i] = Label("")

        try:
            self["progress"].setRange((0, 1000))
        except Exception:
            pass

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.togglePause,
                "cancel": self.keyClose,
                "red": self.keyClose,
                "green": self.togglePause,
                "left": lambda: self.seekRelative(-30),
                "right": lambda: self.seekRelative(30),
                "up": self.previousChapter,
                "down": self.nextChapter,
                "yellow": self.nextChapter,
                "blue": lambda: self.seekRelative(30),
            },
            -2,
        )

        self._clock_timer = eTimer()
        self._clock_timer.callback.append(self._updateClock)
        self._progress_timer = eTimer()
        self._progress_timer.callback.append(self._updateProgress)
        self._startup_timer = eTimer()
        self._startup_timer.callback.append(self._startupCheck)
        self._resume_timer = eTimer()
        self._resume_timer.callback.append(self._applyResume)

        self._event_tracker = ServiceEventTracker(
            screen=self,
            eventmap={
                iPlayableService.evStart: self._serviceStarted,
                iPlayableService.evEOF: self._serviceEOF,
            },
        )

        self.onLayoutFinish.append(self._onLayoutReady)
        self.onClose.append(self._onClose)

    @staticmethod
    def _fmt_ticks(ticks):
        try:
            sec = max(0, int(ticks or 0) // TICKS_PER_SECOND)
        except Exception:
            sec = 0
        h, rem = divmod(sec, 3600)
        m, s = divmod(rem, 60)
        if h:
            return "%d:%02d:%02d" % (h, m, s)
        return "%d:%02d" % (m, s)

    @staticmethod
    def _pts_to_ticks(pts):
        try:
            return max(0, int(int(pts) * TICKS_PER_SECOND // PTS_PER_SECOND))
        except Exception:
            return 0

    @staticmethod
    def _ticks_to_pts(ticks):
        try:
            return max(0, int(int(ticks) * PTS_PER_SECOND // TICKS_PER_SECOND))
        except Exception:
            return 0

    def _onLayoutReady(self):
        self._loadStaticArtwork()
        self._loadCover()
        self._updateClock()
        self._clock_timer.start(30000, False)
        self._loadAudioInfo()
        self._startPlayback()

    def _loadStaticArtwork(self):
        root = os.path.dirname(os.path.dirname(__file__))
        for widget_name, filename in (("background", "audio_player_bg.jpg"), ("vinyl", "audio_vinyl.png"), ("cover_mask", "audio_cover_disc_mask.png")):
            path = os.path.join(root, "skin", "audio", filename)
            try:
                if os.path.isfile(path) and self[widget_name].instance:
                    self[widget_name].instance.setScale(1)
                    self[widget_name].instance.setPixmapFromFile(path)
                    self[widget_name].show()
            except Exception:
                pass

    def _loadCover(self):
        url = getattr(self.item, "poster_url", None)
        if not url:
            return
        cached = image_cache.get_local_path(url)
        if cached:
            self._showCover(cached)
            return
        image_cache.fetch(url, self._showCover, lambda err: None)

    def _showCover(self, path):
        if self._closing:
            return
        try:
            if path and os.path.isfile(path) and self["cover"].instance:
                self["cover"].instance.setScale(1)
                self["cover"].instance.setPixmapFromFile(path)
                self["cover"].show()
        except Exception:
            pass

    def _updateClock(self):
        if not self._closing:
            self["clock"].setText(time.strftime("%H:%M"))

    def _loadAudioInfo(self):
        codec = str(getattr(self.item, "audio_codec", "") or "").upper()
        channels = int(getattr(self.item, "audio_channels", 0) or 0)
        container = str(getattr(self.item, "container", "") or "").upper()
        bits = [x for x in (codec, container if container and container != codec else "") if x]
        if channels:
            bits.append("%s.0" % channels if channels <= 2 else "%s.1" % max(1, channels - 1))
        self["meta"].setText("   •   ".join(bits) if bits else "AUDIO")

        getter = getattr(self.client, "get_audio_info", None)
        if callable(getter):
            try:
                getter(self.item.id, self._onAudioInfo, lambda err: None)
            except Exception:
                pass

    def _onAudioInfo(self, info):
        if self._closing or not isinstance(info, dict):
            return
        self._chapters = list(info.get("chapters") or [])
        artist = str(info.get("artist") or "").strip()
        codec = str(info.get("codec") or getattr(self.item, "audio_codec", "") or "").upper()
        container = str(info.get("container") or getattr(self.item, "container", "") or "").upper()
        channels = int(info.get("channels") or getattr(self.item, "audio_channels", 0) or 0)
        bits = []
        if artist:
            bits.append(artist)
        if codec:
            bits.append(codec)
        if container and container != codec:
            bits.append(container)
        if channels:
            bits.append("%s.0" % channels if channels <= 2 else "%s.1" % max(1, channels - 1))
        if bits:
            self["meta"].setText("   •   ".join(bits))
        self._updateChapter(self.start_ticks)

    def _buildCandidates(self):
        getter = getattr(self.client, "get_audio_stream_candidates", None)
        if not callable(getter):
            raise RuntimeError("Audio-Stream-API fehlt im Server-Client")
        candidates = getter(self.item.id, self.item)
        result = []
        for candidate in list(candidates or []):
            if isinstance(candidate, (tuple, list)) and len(candidate) >= 2:
                label, url = candidate[0], candidate[1]
            else:
                label, url = "AUDIO", candidate
            url = str(url or "").strip()
            if url:
                result.append((str(label or "AUDIO"), url))
        if not result:
            raise RuntimeError("Server lieferte keine Audio-Stream-URL")
        return result

    def _startPlayback(self):
        try:
            self._stream_candidates = self._buildCandidates()
            self._candidate_index = 0
            self._playCandidate()
        except Exception as exc:
            log.exception("AudioPlayer Start fehlgeschlagen: %s", exc)
            self.session.open(MessageBox, "Audio konnte nicht gestartet werden.\n\n%s" % exc, MessageBox.TYPE_ERROR, timeout=8)

    def _playCandidate(self):
        if self._closing or self._candidate_index >= len(self._stream_candidates):
            return
        label, url = self._stream_candidates[self._candidate_index]
        self._started = False
        self._resume_applied = False
        self._start_time = time.time()
        self["mode"].setText(label.upper())
        ref = eServiceReference(4097, 0, url)
        try:
            ref.setName(str(getattr(self.item, "title", "") or "Audio"))
        except Exception:
            pass
        log.info("AudioPlayer: starte %s item=%s", label, getattr(self.item, "id", ""))
        self.session.nav.playService(ref)
        self._startup_timer.start(7000, True)

    def _serviceStarted(self):
        if self._closing:
            return
        self._started = True
        try:
            self._startup_timer.stop()
        except Exception:
            pass
        self._progress_timer.start(1000, False)
        self._resume_timer.start(450, True)
        try:
            self.client.report_playback_started(self.item.id, self.start_ticks)
        except Exception:
            pass

    def _startupCheck(self):
        if self._closing or self._started:
            return
        self._tryFallback("kein Service-Start")

    def _serviceEOF(self):
        if self._closing:
            return
        if (time.time() - self._start_time) < 10.0 and self._candidate_index + 1 < len(self._stream_candidates):
            self._tryFallback("fruehes EOF")
            return
        self.keyClose()

    def _tryFallback(self, reason):
        if self._closing:
            return
        if self._candidate_index + 1 >= len(self._stream_candidates):
            log.warning("AudioPlayer: kein Fallback mehr (%s)", reason)
            return
        self._candidate_index += 1
        self._fallback_used = True
        log.warning("AudioPlayer: Direct Play fehlgeschlagen (%s), Fallback %d", reason, self._candidate_index)
        self._playCandidate()

    def _seekable(self):
        try:
            service = self.session.nav.getCurrentService()
            return service.seek() if service else None
        except Exception:
            return None

    def _currentTicks(self):
        seek = self._seekable()
        if not seek:
            return 0
        try:
            err, pts = seek.getPlayPosition()
            if not err:
                return self._pts_to_ticks(pts)
        except Exception:
            pass
        return 0

    def _lengthTicks(self):
        seek = self._seekable()
        if seek:
            try:
                err, pts = seek.getLength()
                if not err and pts > 0:
                    return self._pts_to_ticks(pts)
            except Exception:
                pass
        return int(getattr(self.item, "runtime_ticks", 0) or 0)

    def _applyResume(self):
        if self._closing or self._resume_applied or self.start_ticks <= 0:
            return
        seek = self._seekable()
        if not seek:
            return
        try:
            seek.seekTo(self._ticks_to_pts(self.start_ticks))
            self._resume_applied = True
            log.info("AudioPlayer: Resume bei %.1fs", float(self.start_ticks) / TICKS_PER_SECOND)
        except Exception:
            pass

    def _updateProgress(self):
        if self._closing:
            return
        pos = self._currentTicks()
        total = self._lengthTicks()
        self["elapsed"].setText(self._fmt_ticks(pos))
        if total > 0:
            remain = max(0, total - pos)
            self["remaining"].setText("GESAMT-REST %s" % self._fmt_ticks(remain))
            try:
                self["progress"].setValue(max(0, min(1000, int(float(pos) * 1000.0 / float(total)))))
            except Exception:
                pass
        else:
            self["remaining"].setText("GESAMT-REST --:--")
        self._updateChapter(pos)

        # Nicht sekundenweise den Server belasten: alle ~15 Sekunden melden.
        if pos > 0 and (self._last_report_ticks < 0 or abs(pos - self._last_report_ticks) >= 15 * TICKS_PER_SECOND):
            self._last_report_ticks = pos
            try:
                self.client.report_playback_progress(self.item.id, pos)
            except Exception:
                pass

    def _updateChapter(self, pos_ticks):
        if not self._chapters:
            return
        current = 0
        for idx, chapter in enumerate(self._chapters):
            try:
                if int(chapter.get("start_ticks") or 0) <= int(pos_ticks or 0):
                    current = idx
                else:
                    break
            except Exception:
                pass
        chapter = self._chapters[current]
        name = str(chapter.get("name") or "Kapitel %d" % (current + 1))
        self["chapter"].setText("KAPITEL %d/%d  ·  %s" % (current + 1, len(self._chapters), name.upper()))

    def seekRelative(self, seconds):
        seek = self._seekable()
        if not seek:
            return
        pos = self._currentTicks()
        total = self._lengthTicks()
        target = max(0, pos + int(seconds) * TICKS_PER_SECOND)
        if total > 0:
            target = min(target, max(0, total - TICKS_PER_SECOND))
        try:
            seek.seekTo(self._ticks_to_pts(target))
            self._updateProgress()
        except Exception:
            pass

    def _chapterIndex(self):
        if not self._chapters:
            return -1
        pos = self._currentTicks()
        current = 0
        for idx, chapter in enumerate(self._chapters):
            try:
                if int(chapter.get("start_ticks") or 0) <= pos:
                    current = idx
                else:
                    break
            except Exception:
                pass
        return current

    def previousChapter(self):
        idx = self._chapterIndex()
        if idx < 0:
            self.seekRelative(-30)
            return
        pos = self._currentTicks()
        start = int(self._chapters[idx].get("start_ticks") or 0)
        if pos - start > 5 * TICKS_PER_SECOND:
            target_idx = idx
        else:
            target_idx = max(0, idx - 1)
        self._seekChapter(target_idx)

    def nextChapter(self):
        idx = self._chapterIndex()
        if idx < 0:
            self.seekRelative(30)
            return
        self._seekChapter(min(len(self._chapters) - 1, idx + 1))

    def _seekChapter(self, idx):
        if not (0 <= idx < len(self._chapters)):
            return
        target = int(self._chapters[idx].get("start_ticks") or 0)
        seek = self._seekable()
        if seek:
            try:
                seek.seekTo(self._ticks_to_pts(target))
                self._updateChapter(target)
            except Exception:
                pass

    def togglePause(self):
        try:
            service = self.session.nav.getCurrentService()
            pause = service.pause() if service else None
            if not pause:
                return
            if self._paused:
                pause.unpause()
                self._paused = False
                self["pause"].setText("II")
            else:
                pause.pause()
                self._paused = True
                self["pause"].setText(">")
        except Exception:
            pass

    def keyClose(self):
        if not self._closing:
            self.close()

    def _onClose(self):
        if self._closing:
            return
        self._closing = True
        for timer in (self._clock_timer, self._progress_timer, self._startup_timer, self._resume_timer):
            try:
                timer.stop()
            except Exception:
                pass
        pos = self._currentTicks()
        if pos > 0:
            try:
                self.item.resume_ticks = pos
            except Exception:
                pass
            try:
                self.client.report_playback_stopped(self.item.id, pos)
            except Exception:
                pass
        try:
            self.session.nav.stopService()
        except Exception:
            pass
        if self.old_service:
            try:
                self.session.nav.playService(self.old_service)
            except Exception:
                pass
