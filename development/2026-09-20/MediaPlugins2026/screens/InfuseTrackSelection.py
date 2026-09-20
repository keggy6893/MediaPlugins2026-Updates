# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList

from ..utils import log

try:
    from Tools.ISO639 import LanguageCodes
except Exception:
    LanguageCodes = {}


def _language_name(code):
    raw = (code or "").strip()
    if not raw:
        return _("Nicht definiert")
    first = raw.split("/")[0].strip()
    aliases = {
        "de": "Deutsch", "deu": "Deutsch", "ger": "Deutsch",
        "en": "Englisch", "eng": "Englisch",
        "fr": "Französisch", "fra": "Französisch", "fre": "Französisch",
        "es": "Spanisch", "spa": "Spanisch",
        "it": "Italienisch", "ita": "Italienisch",
        "nl": "Niederländisch", "nld": "Niederländisch", "dut": "Niederländisch",
        "ar": "Arabisch", "ara": "Arabisch",
        "und": _("Nicht definiert"),
    }
    low = first.lower()
    if low in aliases:
        return aliases[low]
    try:
        if first in LanguageCodes:
            return _(LanguageCodes[first][0])
        if low in LanguageCodes:
            return _(LanguageCodes[low][0])
    except Exception:
        pass
    return first


def _codec_from_description(description):
    d = (description or "").strip()
    u = d.upper()
    mapping = (
        ("E-AC-3", "E-AC3"), ("EAC3", "E-AC3"),
        ("DOLBY DIGITAL PLUS", "E-AC3"), ("DOLBY DIGITAL", "AC3"),
        ("AC-3", "AC3"), ("DTS-HD MA", "DTS-HD MA"),
        ("DTS-HD", "DTS-HD"), ("TRUEHD", "TrueHD"),
        ("AAC", "AAC"), ("FLAC", "FLAC"), ("OPUS", "Opus"),
        ("MP3", "MP3"), ("PCM", "PCM"), ("DTS", "DTS"),
    )
    for needle, label in mapping:
        if needle in u:
            return label
    return d[:18] if d else ""


def _channels_from_description(description):
    d = (description or "").lower()
    for token, label in (
        ("7.1", "7.1"), ("8 channels", "7.1"),
        ("5.1", "5.1"), ("6 channels", "5.1"),
        ("stereo", "2.0"), ("2 channels", "2.0"),
        ("mono", "1.0"),
    ):
        if token in d:
            return label
    return ""


class InfuseTrackSelectionBase(Screen):
    # MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER1
    # MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER4
    # MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER5
    skin = """
    <screen name="InfuseTrackSelectionBase" position="center,center" size="760,540"
            flags="wfNoBorder" backgroundColor="#091722" title="">
        <eLabel position="0,0" size="760,3" backgroundColor="#18A7E0" />
        <widget name="title" position="30,20" size="555,40" font="Bold;28"
                foregroundColor="#FFFFFF" transparent="1" />
        <widget name="count" position="602,24" size="128,28" font="Regular;18"
                foregroundColor="#8CCEF6" transparent="1" halign="right" />
        <eLabel position="30,72" size="700,1" backgroundColor="#29495D" />
        <widget name="list" position="30,88" size="700,350" font="Regular;22"
                itemHeight="50" scrollbarMode="showOnDemand"
                foregroundColor="#EAF3F8" backgroundColor="#0D1C27"
                selectionForegroundColor="#FFFFFF" selectionBackgroundColor="#1599D6" />
        <eLabel position="30,452" size="700,1" backgroundColor="#29495D" />
        <widget name="red" position="34,468" size="270,30" font="Regular;18"
                foregroundColor="#FF6A71" transparent="1" />
        <widget name="ok" position="438,468" size="290,30" font="Regular;18"
                foregroundColor="#8CCEF6" transparent="1" halign="right" />
        <widget name="hint" position="34,508" size="694,22" font="Regular;15"
                foregroundColor="#6E8B9E" transparent="1" halign="center" />
    </screen>
    """

    def __init__(self, session, player, title):
        Screen.__init__(self, session)
        self.player_ref = player
        self.track_rows = []
        self["title"] = Label(title)
        self["count"] = Label("")
        self["list"] = MenuList([])
        self["red"] = Label(_("ROT  Zurück"))
        self["ok"] = Label(_("OK  Auswählen"))
        self["hint"] = Label(_("▲/▼ navigieren"))
        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.keyOK,
                "cancel": self.keyCancel,
                "red": self.keyCancel,
                "up": self.keyUp,
                "down": self.keyDown,
            },
            -2
        )
        try:
            self["list"].onSelectionChanged.append(self._updateCount)
        except Exception:
            pass

    def _setRows(self, rows, selected=0):
        self.track_rows = rows or []
        self["list"].setList([r["label"] for r in self.track_rows])
        if self.track_rows:
            selected = max(0, min(int(selected or 0), len(self.track_rows)-1))
            try:
                self["list"].moveToIndex(selected)
            except Exception:
                pass
        self._updateCount()

    def _index(self):
        try:
            return self["list"].getSelectedIndex()
        except Exception:
            return 0

    def _updateCount(self):
        total = len(self.track_rows)
        self["count"].setText("%d/%d" % (self._index()+1, total) if total else "0/0")

    def keyUp(self):
        try:
            self["list"].up()
        except Exception:
            pass
        self._updateCount()

    def keyDown(self):
        try:
            self["list"].down()
        except Exception:
            pass
        self._updateCount()

    def keyCancel(self):
        self.close()

    def keyOK(self):
        pass


class InfuseAudioSelection(InfuseTrackSelectionBase):
    skinName = "InfuseTrackSelectionBase"

    def __init__(self, session, player):
        InfuseTrackSelectionBase.__init__(self, session, player, _("Audio Auswahl"))
        self.audio_tracks = None
        self.onLayoutFinish.append(self._load)

    def _load(self):
        try:
            service = self.session.nav.getCurrentService()
            self.audio_tracks = service and service.audioTracks()
            count = self.audio_tracks and self.audio_tracks.getNumberOfTracks() or 0
            current = self.audio_tracks.getCurrentTrack() if count else 0
            rows = []
            for idx in range(count):
                info = self.audio_tracks.getTrackInfo(idx)
                language = _language_name(info.getLanguage())
                desc = info.getDescription() or ""
                codec = _codec_from_description(desc)
                channels = _channels_from_description(desc)
                active = idx == current
                details = "   ".join(x for x in (codec, channels) if x)
                label = "%s  %s%s" % (
                    "✓" if active else " ",
                    language,
                    ("     " + details) if details else ""
                )
                rows.append({"label": label, "track_index": idx})
            if not rows:
                rows = [{"label": _("Keine Audiospuren gefunden"), "track_index": None}]
            self._setRows(rows, current)
        except Exception as e:
            log.exception("Audioauswahl konnte nicht aufgebaut werden: %s", e)
            self._setRows([{"label": _("Audioauswahl nicht verfügbar"), "track_index": None}], 0)

    def keyOK(self):
        pos = self._index()
        if not (0 <= pos < len(self.track_rows)):
            return
        track = self.track_rows[pos].get("track_index")
        if track is None:
            return
        try:
            self.audio_tracks.selectTrack(int(track))
            log.info("Player r50: Audiospur %d ausgewaehlt", int(track))
            self.close()
        except Exception as e:
            log.warning("Audiospur konnte nicht umgeschaltet werden: %s", e)


class InfuseSubtitleSelection(InfuseTrackSelectionBase):
    skinName = "InfuseTrackSelectionBase"

    EXT_TYPES = {
        0: "SUB", 1: "Embedded", 2: "SSA", 3: "ASS",
        4: "SRT", 5: "VOB", 6: "PGS", 7: "WebVTT",
    }

    def __init__(self, session, player):
        InfuseTrackSelectionBase.__init__(self, session, player, _("Untertitel Auswahl"))
        self.onLayoutFinish.append(self._load)

    def _enabled(self):
        try:
            return bool(self.player_ref.subtitle_window.shown)
        except Exception:
            return getattr(self.player_ref, "selected_subtitle", None) is not None

    def _load(self):
        try:
            service = self.session.nav.getCurrentService()
            subtitle = service and service.subtitle()
            entries = subtitle and subtitle.getSubtitleList() or []
            current = getattr(self.player_ref, "selected_subtitle", None)
            enabled = self._enabled()

            rows = [{
                "label": "%s  %s" % ("✓" if not enabled else " ", _("Untertitel aus")),
                "subtitle_value": None
            }]
            selected = 0

            for pos, sub in enumerate(entries, 1):
                try:
                    stype = int(sub[0])
                except Exception:
                    stype = -1

                lang = _language_name(sub[4] if len(sub) > 4 else "")
                if stype == 0:
                    codec = "DVB"
                elif stype == 1:
                    codec = "TTX"
                elif stype == 2:
                    try:
                        codec = self.EXT_TYPES.get(int(sub[2]), "EXT")
                    except Exception:
                        codec = "EXT"
                else:
                    codec = "SUB"

                flags = []
                if len(sub) > 5 and isinstance(sub[5], str):
                    low = sub[5].lower()
                    if "forced" in low or "erz" in low:
                        flags.append(_("Erzw."))
                    if "hearing" in low or "sdh" in low or "hoh" in low:
                        flags.append("SDH")

                active = bool(enabled and current and tuple(sub[:4]) == tuple(current[:4]))
                if active:
                    selected = pos
                details = "   ".join([codec] + flags)
                label = "%s  %s     %s" % ("✓" if active else " ", lang, details)
                rows.append({"label": label, "subtitle_value": sub})

            self._setRows(rows, selected)
        except Exception as e:
            log.exception("Untertitelauswahl konnte nicht aufgebaut werden: %s", e)
            self._setRows([{"label": _("Untertitelauswahl nicht verfügbar"), "subtitle_value": "invalid"}], 0)

    def keyOK(self):
        pos = self._index()
        if not (0 <= pos < len(self.track_rows)):
            return
        sub = self.track_rows[pos].get("subtitle_value")
        if sub == "invalid":
            return

        try:
            if sub is None:
                fn = getattr(self.player_ref, "disableSubtitles", None)
                if not callable(fn):
                    log.warning("Player besitzt keine disableSubtitles()-Methode")
                    return
                fn()
                try:
                    self.player_ref.selected_subtitle = None
                except Exception:
                    pass
                log.info("Player r50: Untertitel ausgeschaltet")
            else:
                fn = getattr(self.player_ref, "enableSubtitle", None)
                if not callable(fn):
                    log.warning("Player besitzt keine enableSubtitle()-Methode")
                    return
                fn(sub)
                try:
                    self.player_ref.selected_subtitle = sub
                except Exception:
                    pass
                log.info("Player r50: Untertitel ausgewaehlt: %s", sub)
            self.close()
        except Exception as e:
            log.warning("Untertitel konnten nicht umgeschaltet werden: %s", e)
