# -*- coding: utf-8 -*-
# MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER1
# MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER4
# MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER5

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label


class MediaPluginsPlayerInfo(Screen):
    skin = """
    <screen name="MediaPluginsPlayerInfo" position="center,center" size="860,540"
            flags="wfNoBorder" backgroundColor="#091722">
        <eLabel position="0,0" size="860,3" backgroundColor="#1EA7FF" />
        <widget name="title" position="30,20" size="800,40" font="Bold;28"
                foregroundColor="#FFFFFF" transparent="1" />
        <widget name="subtitle" position="30,62" size="800,28" font="Regular;18"
                foregroundColor="#9EC8E4" transparent="1" />
        <eLabel position="30,104" size="800,1" backgroundColor="#29495D" />
        <widget name="left" position="40,126" size="215,320" font="Regular;19"
                foregroundColor="#89A8BC" transparent="1" />
        <widget name="right" position="266,126" size="560,320" font="Regular;19"
                foregroundColor="#F1F6F9" transparent="1" />
        <eLabel position="30,462" size="800,1" backgroundColor="#29495D" />
        <widget name="footer" position="30,480" size="800,30" font="Regular;17"
                foregroundColor="#8CCEF6" transparent="1" halign="center" />
    </screen>
    """

    def __init__(self, session, playback):
        Screen.__init__(self, session)
        self.playback = playback
        item = playback.item

        self["title"] = Label(getattr(item, "title", "") or "Medieninformationen")
        self["subtitle"] = Label("%s  •  %s" % (playback.provider_label(), playback.mode_label()))

        labels = [
            "Provider",
            "Player-Engine",
            "Wiedergabe",
            "Auflösung",
            "Video",
            "Audio",
            "Sprache",
            "Container",
            "Server",
            "Item-ID",
        ]
        self["left"] = Label("\n".join(labels))
        self["right"] = Label("\n".join(self._values(item)))
        self["footer"] = Label("OK / EXIT  Zurück")
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {"ok": self.close, "cancel": self.close, "red": self.close},
            -3,
        )

    def _values(self, item):
        width = int(getattr(item, "video_width", 0) or 0)
        height = int(getattr(item, "video_height", 0) or 0)
        resolution = "%d × %d" % (width, height) if width and height else "—"
        video = (getattr(item, "video_codec", "") or "—").upper()
        audio_codec = (getattr(item, "audio_codec", "") or "—").upper()
        channels = int(getattr(item, "audio_channels", 0) or 0)
        channel_text = {1: "1.0", 2: "2.0", 6: "5.1", 8: "7.1"}.get(channels, str(channels) if channels else "")
        audio = (audio_codec + (("  " + channel_text) if channel_text else "")).strip()
        language = (getattr(item, "audio_language", "") or "—").upper()
        container = (getattr(item, "container", "") or "—").upper()
        server = getattr(item, "server_name", "") or "—"
        item_id = str(getattr(item, "id", "") or "—")
        return [
            self.playback.provider_label(),
            self.playback.engine_label(),
            self.playback.mode_label(),
            resolution,
            video,
            audio,
            language,
            container,
            server,
            item_id,
        ]
