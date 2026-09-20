# -*- coding: utf-8 -*-
# MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER2
# MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER3
# MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER4
# MEDIAPLUGINS2026_UNIFIED_VIDEO_PLAYER5

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList

from ..utils import log


class MediaPluginsChapterSelection(Screen):
    skin = """
    <screen name="MediaPluginsChapterSelection" position="center,center" size="820,540"
            flags="wfNoBorder" backgroundColor="#091722">
        <eLabel position="0,0" size="820,3" backgroundColor="#FFC229" />
        <widget name="title" position="30,20" size="555,40" font="Bold;28"
                foregroundColor="#FFFFFF" transparent="1" />
        <widget name="count" position="620,24" size="170,28" font="Regular;18"
                foregroundColor="#FFC229" transparent="1" halign="right" />
        <eLabel position="30,72" size="760,1" backgroundColor="#29495D" />
        <widget name="list" position="30,88" size="760,350" font="Regular;22"
                itemHeight="50" scrollbarMode="showOnDemand"
                foregroundColor="#EAF3F8" backgroundColor="#0D1C27"
                selectionForegroundColor="#FFFFFF" selectionBackgroundColor="#1599D6" />
        <eLabel position="30,452" size="760,1" backgroundColor="#29495D" />
        <widget name="red" position="34,470" size="280,30" font="Regular;18"
                foregroundColor="#FF6A71" transparent="1" />
        <widget name="ok" position="430,470" size="358,30" font="Regular;18"
                foregroundColor="#8CCEF6" transparent="1" halign="right" />
    </screen>
    """

    def __init__(self, session, player):
        Screen.__init__(self, session)
        self.player = player
        self.rows = []
        self["title"] = Label("Kapitel / Szenen")
        self["count"] = Label("")
        self["list"] = MenuList([])
        self["red"] = Label("ROT  Zurück")
        self["ok"] = Label("OK  Zu Kapitel springen")
        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.keyOK,
                "cancel": self.close,
                "red": self.close,
                "up": self.keyUp,
                "down": self.keyDown,
            },
            -3,
        )
        try:
            self["list"].onSelectionChanged.append(self._updateCount)
        except Exception:
            pass
        self.onLayoutFinish.append(self._load)

    @staticmethod
    def _fmt_ticks(ticks):
        try:
            seconds = max(0, int(ticks or 0) // 10000000)
            h, rem = divmod(seconds, 3600)
            m, s = divmod(rem, 60)
            return ("%d:%02d:%02d" % (h, m, s)) if h else ("%02d:%02d" % (m, s))
        except Exception:
            return "00:00"

    def _load(self):
        chapters = list(getattr(self.player, "_mediaplugins_chapters", []) or [])
        if not chapters:
            self.rows = []
            self["list"].setList(["Keine Kapitelinformationen verfügbar"])
            self["count"].setText("0/0")
            return

        rows = []
        for idx, chapter in enumerate(chapters):
            start = int(chapter.get("start_ticks") or 0)
            name = str(chapter.get("name") or ("Kapitel %d" % (idx + 1)))
            rows.append({
                "start_ticks": start,
                "label": "%02d.  %-10s   %s" % (idx + 1, self._fmt_ticks(start), name),
            })
        self.rows = rows
        self["list"].setList([row["label"] for row in rows])
        self._selectCurrent()
        self._updateCount()

    def _current_index(self):
        try:
            seek = self.player._getSeek()
            if not seek:
                return 0
            err, pts = seek.getPlayPosition()
            if err != 0 or pts is None:
                return 0
            ticks = int(pts) * 10000000 // 90000
        except Exception:
            return 0
        current = 0
        for idx, row in enumerate(self.rows):
            if int(row.get("start_ticks") or 0) <= ticks:
                current = idx
            else:
                break
        return current

    def _selectCurrent(self):
        if not self.rows:
            return
        try:
            self["list"].moveToIndex(self._current_index())
        except Exception:
            pass

    def _index(self):
        try:
            return self["list"].getSelectedIndex()
        except Exception:
            return 0

    def _updateCount(self):
        total = len(self.rows)
        self["count"].setText("%d/%d" % (self._index() + 1, total) if total else "0/0")

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

    def keyOK(self):
        pos = self._index()
        if not (0 <= pos < len(self.rows)):
            return
        ticks = int(self.rows[pos].get("start_ticks") or 0)
        try:
            seek = self.player._getSeek()
            if not seek:
                return
            seek.seekTo(int(ticks * 90000 // 10000000))
            log.info("UnifiedPlayer5 Kapitel %d angesprungen", pos + 1)
            self.close()
        except Exception as error:
            log.warning("UnifiedPlayer5 Kapitel-Sprung fehlgeschlagen: %s", error)
