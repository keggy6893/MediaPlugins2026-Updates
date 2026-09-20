# -*- coding: utf-8 -*-
import time
from enigma import eTimer, eServiceReference
from Screens.InfoBar import MoviePlayer
from Components.ActionMap import ActionMap

from ..utils import log


class InfuseMoviePlayer(MoviePlayer):
    """MoviePlayer mit Jellyfin/Emby Resume, Reporting und eigenem OSD."""

    REPORT_INTERVAL_MS = 10000
    RESUME_DELAY_MS = 1800
    OSD_START_DELAY_MS = 900

    def __init__(self, session, service, item, client, stream_url=None, start_ticks=None):
        MoviePlayer.__init__(self, session, service, fromMovieSelection=False)

        # MediaPlugins2026 owns the player UI. OpenATV MoviePlayer creates a
        # separate PVRState dialog for play/pause/seek. Its PLAY state is the
        # literal text ">", which otherwise flashes over the video at start.
        # Keep MoviePlayer playback/seek logic, but suppress only that stock
        # PVR-state overlay.
        try:
            pvr_state = getattr(self, "pvrStateDialog", None)
            if pvr_state is not None:
                pvr_state.hide()
                pvr_state.show = lambda *args, **kwargs: None
        except Exception as e:
            log.warning("Standard-PVR-State konnte nicht unterdrueckt werden: %s", e)
        self._infuse_item = item
        self._infuse_client = client
        # r70: URL merken, um sie bei einem moeglichen Fehlschlag direkt in
        # der Bildschirmmeldung anzuzeigen - ohne Log-Datei-Zugriff sofort
        # erkennbar, ob Direct-Play oder Transcoding (master.m3u8) versucht
        # wurde.
        self._stream_url = stream_url or ""
        self._resume_done = False
        if start_ticks is None:
            self._last_ticks = int(getattr(item, "resume_ticks", 0) or 0)
        else:
            self._last_ticks = max(0, int(start_ticks or 0))
        self._stop_reported = False
        self._closing_by_user = False
        self._osd_open = False
        self._player_started_once = False
        # r68: merkt, ob wir dem Decoder je erfolgreich eine gueltige
        # Wiedergabeposition entlocken konnten (seek().getPlayPosition()
        # mit err==0). Bleibt das die ganze Sitzung ueber False, hat der
        # Player nie wirklich zu spielen begonnen - typisches Zeichen fuer
        # ein Format/Codec, das die Box im Direct-Play nicht abspielen
        # kann (Datei bleibt schwarz/eingefroren, bis man Exit drueckt).
        self._got_valid_position = False
        self._start_time = None
        # r90: Stillstands-Erkennung. "_got_valid_position" allein erkennt nur
        # den Fall "nie eine Position bekommen". Es gibt aber auch den Fall,
        # dass der Decoder EINMAL kurz eine Position liefert (z.B. 30s) und
        # danach nie wieder - Bild/Ton bleiben aus, obwohl "_got_valid_position"
        # bereits True ist und die alte Pruefung daher nichts mehr meldet.
        self._stall_last_ticks = None
        self._stall_repeat_count = 0
        self._stall_notified = False

        self._resume_timer = eTimer()
        self._resume_timer.callback.append(self._applyResume)
        self._report_timer = eTimer()
        self._report_timer.callback.append(self._reportProgress)
        self._osd_start_timer = eTimer()
        self._osd_start_timer.callback.append(self._showInfuseOSD)

        # Hohe Prioritaet: OK soll unser OSD zeigen statt das Standard-MoviePlayer-OSD.
        self["infuse_osd_actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "NumberActions", "InfobarActions", "InfobarSeekActions", "ColorActions"],
            {
                "ok": self._showInfuseOSD,
                # SEEK-FIX2: Spulen muss auch funktionieren, wenn das OSD gerade
                # ausgeblendet ist. Die Tasten werden deshalb direkt vom Player
                # abgefangen und nicht nur vom modalen InfusePlayerOSD.
                "left": lambda: self._seekSeconds(-5),
                "right": lambda: self._seekSeconds(5),
                "1": lambda: self._seekSeconds(-10),
                "3": lambda: self._seekSeconds(10),
                "4": lambda: self._seekSeconds(-30),
                "6": lambda: self._seekSeconds(30),
                "7": lambda: self._seekSeconds(-300),
                "9": lambda: self._seekSeconds(300),
                "green": self._openAudioSelection,
                "yellow": self._openSubtitleSelection,
            },
            -3,
        )

        self.onShown.append(self._onInfuseShown)
        self.onClose.append(self._onInfuseClose)

    @staticmethod
    def _ticksToPts(ticks):
        return int(int(ticks or 0) * 9 // 1000)

    @staticmethod
    def _ptsToTicks(pts):
        return int(int(pts or 0) * 1000 // 9)

    def _onInfuseShown(self):
        # onShown wird von Enigma2 auch erneut aufgerufen, wenn ein modaler
        # Kind-Screen (z. B. unser OSD) geschlossen wurde. Die Player-
        # Initialisierung und das automatische OSD duerfen deshalb nur beim
        # allerersten Anzeigen des MoviePlayers laufen.
        if self._player_started_once:
            return
        self._player_started_once = True
        self._start_time = time.time()

        try:
            self._infuse_client.report_playback_started(
                self._infuse_item.id, self._last_ticks
            )
        except Exception as e:
            log.warning("Playback-Start Reporting fehlgeschlagen: %s", e)

        if self._last_ticks > 0 and not self._resume_done:
            self._resume_timer.start(self.RESUME_DELAY_MS, True)
        self._report_timer.start(self.REPORT_INTERVAL_MS, False)
        # MediaPlugins2026 START-ARROW-FIX1:
        # Kein automatisches OSD beim Playerstart. Das verhindert das kurz nach
        # Wiedergabestart eingeblendete Navigationszeichen. OK oeffnet unser OSD
        # weiterhin manuell; Audio-/Untertitel-/Kapitel-UI bleibt unveraendert.

    def _showInfuseOSD(self):
        if self._closing_by_user or self._osd_open:
            return
        # Nur oeffnen, wenn der MoviePlayer selbst gerade der aktive Dialog ist.
        try:
            if getattr(self.session, "current_dialog", None) is not self:
                return
        except Exception:
            pass
        try:
            from .InfusePlayerOSD import InfusePlayerOSD
            self._osd_open = True
            self.session.openWithCallback(self._onOSDClosed, InfusePlayerOSD, self, self._infuse_item)
        except Exception as e:
            self._osd_open = False
            log.warning("Infuse OSD konnte nicht geoeffnet werden: %s", e)

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

    def _openAudioSelection(self):
        """Open Media Plugins 2026's own audio-track selector."""
        if self._closing_by_user:
            return
        try:
            if getattr(self.session, "current_dialog", None) is not self:
                return
        except Exception:
            pass
        try:
            from .InfuseTrackSelection import InfuseAudioSelection
            log.info("Player r50: Infuse-Audioauswahl geoeffnet")
            self.session.open(InfuseAudioSelection, self)
        except Exception as e:
            log.exception("Infuse-Audioauswahl konnte nicht geoeffnet werden: %s", e)

    def _openSubtitleSelection(self):
        """Open Media Plugins 2026's own subtitle selector."""
        if self._closing_by_user:
            return
        try:
            if getattr(self.session, "current_dialog", None) is not self:
                return
        except Exception:
            pass
        try:
            from .InfuseTrackSelection import InfuseSubtitleSelection
            log.info("Player r50: Infuse-Untertitelauswahl geoeffnet")
            self.session.open(InfuseSubtitleSelection, self)
        except Exception as e:
            log.exception("Infuse-Untertitelauswahl konnte nicht geoeffnet werden: %s", e)

    def _callMoviePlayerAction(self, names):
        for name in names:
            fn = getattr(self, name, None)
            if callable(fn):
                try:
                    fn()
                    return True
                except Exception as e:
                    log.warning("MoviePlayer-Aktion %s fehlgeschlagen: %s", name, e)
                    return False
        log.warning("Keine passende MoviePlayer-Aktion gefunden: %s", ", ".join(names))
        return False

    def _getSeek(self):
        try:
            service = self.session.nav.getCurrentService()
            return service and service.seek()
        except Exception:
            return None

    def _seekSeconds(self, seconds):
        """Direktes absolutes Spulen fuer HTTP/Direct-Play."""
        try:
            seek = self._getSeek()
            if not seek:
                return
            err_pos, pos = seek.getPlayPosition()
            if err_pos:
                return
            target = max(0, int(pos) + int(seconds) * 90000)
            try:
                err_len, length = seek.getLength()
                if not err_len and int(length or 0) > 0:
                    target = min(target, max(0, int(length) - 90000))
            except Exception:
                pass
            result = seek.seekTo(target)
            log.info("Player direct seek %ss: %s -> %s (result=%s)",
                     seconds, int(pos), target, result)
            # Jellyfin Direct-Play auf dieser Box liefert bei seekTo() -1.
            # In diesem Fall den HTTP-Stream serverseitig an der Zielposition
            # neu starten. Jellyfin akzeptiert StartTimeTicks am Stream-Endpunkt.
            if result == -1 and "jellyfin" in self._infuse_client.__class__.__name__.lower():
                self._restartJellyfinAtPts(target)
        except Exception as error:
            log.warning("Player direct seek %ss fehlgeschlagen: %s", seconds, error)


    def _restartJellyfinAtPts(self, pts):
        try:
            ticks = self._ptsToTicks(max(0, int(pts or 0)))
            url = str(self._stream_url or "")
            if not url:
                return False
            # Vorhandenen StartTimeTicks-Wert ersetzen, sonst anhaengen.
            parts = url.split("?StartTimeTicks=", 1)
            if len(parts) == 2:
                tail = parts[1]
                rest = tail.split("&", 1)
                url = parts[0] + ("?" + rest[1] if len(rest) == 2 else "")
            else:
                needle = "&StartTimeTicks="
                if needle in url:
                    head, tail = url.split(needle, 1)
                    rest = tail.split("&", 1)
                    url = head + (("&" + rest[1]) if len(rest) == 2 else "")
            sep = "&" if "?" in url else "?"
            url = url + sep + "StartTimeTicks=" + str(ticks)

            old_ref = self.session.nav.getCurrentlyPlayingServiceReference()
            service_type = 4097
            try:
                if old_ref is not None:
                    service_type = int(old_ref.type)
            except Exception:
                pass
            ref = eServiceReference(service_type, 0, url)
            try:
                ref.setName(str(getattr(self._infuse_item, "title", "") or "Jellyfin"))
            except Exception:
                pass

            self._stream_url = url
            self._last_ticks = ticks
            self.session.nav.stopService()
            self.session.nav.playService(ref)
            log.info("Jellyfin server seek: Neustart bei %.1fs", float(ticks) / 10000000.0)
            return True
        except Exception as error:
            log.warning("Jellyfin server seek fehlgeschlagen: %s", error)
            return False

    def _getCurrentTicks(self):
        seek = self._getSeek()
        if not seek:
            return self._last_ticks
        try:
            err, pts = seek.getPlayPosition()
            if err == 0 and pts is not None and pts >= 0:
                self._last_ticks = self._ptsToTicks(pts)
                self._got_valid_position = True
        except Exception:
            pass
        return self._last_ticks

    def _applyResume(self):
        if self._resume_done or self._last_ticks <= 0:
            return
        seek = self._getSeek()
        if not seek:
            self._resume_timer.start(1200, True)
            return
        try:
            pts = self._ticksToPts(self._last_ticks)
            result = seek.seekTo(pts)
            self._resume_done = True
            log.info("Resume angewendet: %s bei %.1f s (seek=%s)",
                     self._infuse_item.title,
                     float(self._last_ticks) / 10000000.0,
                     result)
        except Exception as e:
            log.warning("Resume fehlgeschlagen fuer %s: %s",
                        self._infuse_item.title, e)

    def _reportProgress(self):
        try:
            ticks = self._getCurrentTicks()
            self._checkStalled(ticks)
            self._infuse_client.report_playback_progress(
                self._infuse_item.id, ticks
            )
        except Exception as e:
            log.warning("Playback-Progress Reporting fehlgeschlagen: %s", e)

    def _checkStalled(self, ticks):
        # r90: Wird alle REPORT_INTERVAL_MS (10s) aufgerufen. Bleibt die
        # Position ueber zwei Intervalle hinweg exakt gleich, obwohl der
        # Player laeuft (nicht pausiert/geschlossen), ist das ein starkes
        # Anzeichen fuer ein eingefrorenes Bild/Ton trotz "technisch aktiver"
        # Wiedergabe (haeufig bei nicht unterstuetzten Audio-Codecs wie E-AC3,
        # die die gesamte Pipeline blockieren, waehrend PCR/Position kurz
        # anlief und dann haengen blieb).
        if self._stall_notified or self._closing_by_user:
            return
        try:
            is_paused = bool(getattr(self, "seekstate", 0) == getattr(self, "SEEK_STATE_PAUSE", object()))
        except Exception:
            is_paused = False
        if is_paused:
            self._stall_last_ticks = ticks
            self._stall_repeat_count = 0
            return
        if self._stall_last_ticks is not None and ticks == self._stall_last_ticks:
            self._stall_repeat_count += 1
        else:
            self._stall_repeat_count = 0
        self._stall_last_ticks = ticks
        elapsed = (time.time() - self._start_time) if self._start_time else 0
        if self._stall_repeat_count >= 2 and elapsed >= 15:
            self._stall_notified = True
            log.warning(
                "Player r90: Wiedergabe fuer '%s' seit ueber 20s auf Position "
                "%.1fs eingefroren - Bild/Ton wahrscheinlich haengengeblieben "
                "(moeglicherweise nicht unterstuetzter Audio-/Videocodec)",
                self._infuse_item.title, float(ticks or 0) / 10000000.0,
            )
            self._notifyPlaybackMayHaveFailed()

    def _reportStoppedOnce(self):
        if self._stop_reported:
            return
        self._stop_reported = True
        try:
            self._resume_timer.stop()
            self._report_timer.stop()
            self._osd_start_timer.stop()
        except Exception:
            pass
        ticks = self._getCurrentTicks()
        # RESUME-LOCAL2: denselben MediaItem sofort aktualisieren. Der Detail-Screen
        # bekommt dadurch beim Zurueckkehren die echte Stop-Position, auch wenn
        # Jellyfin/Emby das asynchrone Stopped-Reporting noch nicht verarbeitet hat.
        try:
            self._infuse_item.resume_ticks = max(0, int(ticks or 0))
        except Exception:
            pass
        try:
            self._infuse_client.report_playback_stopped(
                self._infuse_item.id, ticks
            )
            log.info("Wiedergabe beendet: %s bei %.1f s",
                     self._infuse_item.title,
                     float(ticks) / 10000000.0)
        except Exception as e:
            log.warning("Playback-Stop Reporting fehlgeschlagen: %s", e)

        # r68: nie eine gueltige Position vom Decoder erhalten -> die
        # Wiedergabe hat vermutlich nie wirklich begonnen. Deutlich im Log
        # markieren (statt eines unauffaelligen normalen Stopps) und den
        # Nutzer direkt informieren, damit klar ist, dass es sich um ein
        # moegliches Format-/Codec-Problem handelt und nicht um ein
        # gewoehnliches Beenden. Mindestlaufzeit-Schwelle, damit ein sehr
        # schnelles, absichtliches Exit direkt nach Start nicht faelschlich
        # als Fehlschlag gemeldet wird.
        elapsed = (time.time() - self._start_time) if self._start_time else 0
        if not self._got_valid_position and elapsed >= 3:
            log.warning(
                "Player r68: Wiedergabe evtl. fehlgeschlagen fuer '%s' - "
                "nie eine gueltige Position vom Decoder erhalten nach %.1fs "
                "(moeglicherweise nicht unterstuetztes Format/Codec)",
                self._infuse_item.title, elapsed,
            )
            self._notifyPlaybackMayHaveFailed()

    def _notifyPlaybackMayHaveFailed(self):
        try:
            from Tools import Notifications
            from Screens.MessageBox import MessageBox
            # r70: Modus (Transcoding/HLS vs. Direct-Play) und ein Auszug der
            # URL direkt in der Meldung, damit man ohne Log-Zugriff sofort
            # sieht, welcher Wiedergabeweg tatsaechlich versucht wurde.
            if "master.m3u8" in self._stream_url:
                mode = _("Transcoding/HLS")
            elif "stream?static=true" in self._stream_url:
                mode = _("Direct-Play")
            else:
                mode = _("unbekannt")
            url_excerpt = self._stream_url.split("?")[0] if self._stream_url else "?"
            Notifications.AddNotification(
                MessageBox,
                _("Die Wiedergabe von '%s' konnte moeglicherweise nicht gestartet werden.\n"
                  "Das Video-/Audioformat wird von dieser Box eventuell nicht direkt "
                  "unterstuetzt.\n\nModus: %s\nURL: %s") % (
                    self._infuse_item.title, mode, url_excerpt),
                type=MessageBox.TYPE_WARNING,
                timeout=15,
            )
        except Exception as e:
            log.warning("Player r70: Hinweis-Meldung konnte nicht angezeigt werden: %s", e)

    def _leaveInfusePlayer(self):
        if self._closing_by_user:
            return
        self._closing_by_user = True
        log.info("Player beendet per STOP/EXIT: %s", self._infuse_item.title)
        self._reportStoppedOnce()
        self.close()

    def leavePlayer(self):
        self._leaveInfusePlayer()

    def leavePlayerOnExit(self):
        self._leaveInfusePlayer()

    def _onInfuseClose(self):
        self._reportStoppedOnce()
