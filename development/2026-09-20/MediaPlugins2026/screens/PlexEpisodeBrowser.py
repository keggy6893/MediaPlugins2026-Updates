# -*- coding: utf-8 -*-
# INFUSEMEDIA2026_PLEX_EPISODEUI3

import os

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from enigma import ePoint

from ..utils.image_cache import image_cache
from ..utils import log

PAGE_SIZE = 10
COLS = 5
THUMB_W = 340
THUMB_H = 191
X_POS = (55, 423, 791, 1159, 1527)
Y_POS = (175, 575)
CARD_POS = [
    (X_POS[col], Y_POS[row])
    for row in range(2)
    for col in range(COLS)
]


def _build_skin():
    parts = ["""
    <screen name="MediaPlugins2026PlexEpisodeBrowser" position="0,0" size="1920,1080"
            flags="wfNoBorder" backgroundColor="#07131d">
        <widget name="header" position="55,34" size="1500,52" font="Regular;32"
                foregroundColor="#f3f6f8" transparent="1" />
        <widget name="page" position="1600,38" size="265,40" font="Regular;22"
                foregroundColor="#38bde6" transparent="1" halign="right" />
        <widget name="subheader" position="55,94" size="1500,36" font="Regular;20"
                foregroundColor="#38bde6" transparent="1" />
    """]

    for i, (x, y) in enumerate(CARD_POS):
        parts.append("""
        <widget name="thumb%d" position="%d,%d" size="%d,%d"
                alphatest="on" scale="1" zPosition="2" />
        <widget name="code%d" position="%d,%d" size="%d,30"
                font="Regular;19" foregroundColor="#dbe7ef" transparent="1" />
        <widget name="title%d" position="%d,%d" size="%d,34"
                font="Regular;21" foregroundColor="#f4f6f8" transparent="1" />
        <widget name="runtime%d" position="%d,%d" size="%d,30"
                font="Regular;18" foregroundColor="#8e9ba7" transparent="1" />
        """ % (
            i, x, y, THUMB_W, THUMB_H,
            i, x, y + 204, THUMB_W,
            i, x, y + 238, THUMB_W,
            i, x, y + 277, THUMB_W,
        ))

    parts.append("""
        <widget name="focus_top" position="49,169" size="352,5"
                backgroundColor="#f2c400" transparent="0" zPosition="9" />
        <widget name="focus_bottom" position="49,371" size="352,5"
                backgroundColor="#f2c400" transparent="0" zPosition="9" />
        <widget name="focus_left" position="49,169" size="5,207"
                backgroundColor="#f2c400" transparent="0" zPosition="9" />
        <widget name="focus_right" position="396,169" size="5,207"
                backgroundColor="#f2c400" transparent="0" zPosition="9" />

        <widget name="keybar_bg" position="45,960" size="1830,70"
                backgroundColor="#091b2a" transparent="0" />
        <widget name="key_red" position="100,980" size="260,32" font="Regular;20"
                foregroundColor="#f05a5a" transparent="1" text="■  Zurück" />
        <widget name="key_nav" position="700,980" size="600,32" font="Regular;20"
                foregroundColor="#d2d8de" transparent="1" halign="center"
                text="PFEILE   Navigieren      OK   Öffnen" />
        <widget name="key_blue" position="1570,980" size="245,32" font="Regular;20"
                foregroundColor="#32b9e8" transparent="1" halign="right"
                text="■  Merkliste" />
    </screen>
    """)
    return "".join(parts)


class PlexEpisodeBrowser(Screen):
    skinName = "MediaPlugins2026PlexEpisodeBrowser"
    skin = _build_skin()

    def __init__(self, session, parent_item, client):
        Screen.__init__(self, session)
        self.session = session
        self.parent_item = parent_item
        self.client = client
        self._items = []
        self._page_items = []
        self._page_start = 0
        self._selected = 0
        self._closing = False
        self._image_request = 0

        self["header"] = Label("")
        self["page"] = Label("")
        self["subheader"] = Label("")
        self["keybar_bg"] = Label("")
        self["key_red"] = Label("■  Zurück")
        self["key_nav"] = Label("PFEILE   Navigieren      OK   Öffnen")
        self["key_blue"] = Label("■  Merkliste")

        for name in ("focus_top", "focus_bottom", "focus_left", "focus_right"):
            self[name] = Label("")

        for i in range(PAGE_SIZE):
            self["thumb%d" % i] = Pixmap()
            self["code%d" % i] = Label("")
            self["title%d" % i] = Label("")
            self["runtime%d" % i] = Label("")

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.keyOpen,
                "cancel": self.keyCancel,
                "red": self.keyCancel,
                "blue": self.keyBlue,
                "left": self.keyLeft,
                "right": self.keyRight,
                "up": self.keyUp,
                "down": self.keyDown,
            },
            -2,
        )

        self.onClose.append(self._onClose)
        self.onLayoutFinish.append(self._renderHeader)
        self.onLayoutFinish.append(self._load)

    def _onClose(self):
        self._closing = True
        self._image_request += 1

    def _seriesName(self):
        return (
            getattr(self.parent_item, "series_name", "")
            or getattr(self.parent_item, "title", "")
            or "Plex"
        )

    def _seasonNumber(self):
        try:
            number = getattr(self.parent_item, "season_number", None)
            return int(number) if number is not None else None
        except Exception:
            return None

    def _renderHeader(self):
        series = self._seriesName()
        season = self._seasonNumber()
        right = (" · STAFFEL %d" % season) if season is not None else ""
        self["header"].setText("PLEX 2026   |   %s%s" % (series.upper(), right))
        self._renderPageMeta()

    def _load(self):
        self.client.get_children(
            self.parent_item.id,
            lambda items: log.safe_call(self._onLoaded, items),
            lambda err: log.safe_call(self._onError, err),
        )

    def _onLoaded(self, items):
        if self._closing:
            return
        self._items = list(items or [])
        self._items.sort(
            key=lambda x: (
                int(getattr(x, "season_number", 0) or 0),
                int(getattr(x, "episode_number", 0) or 0),
                str(getattr(x, "title", "") or "").casefold(),
            )
        )
        self._page_start = 0
        self._selected = 0
        self._showPage()

    def _onError(self, err):
        self._items = []
        self._page_items = []
        self["subheader"].setText("Plex-Fehler: %s" % err)
        self["page"].setText("")
        self._renderCards()

    def _pageCount(self):
        return max(1, (len(self._items) + PAGE_SIZE - 1) // PAGE_SIZE)

    def _pageNo(self):
        return min(self._pageCount(), (self._page_start // PAGE_SIZE) + 1)

    def _renderPageMeta(self):
        series = self._seriesName()
        season = self._seasonNumber()
        bits = [series]
        if season is not None:
            bits.append("Staffel %d" % season)
        bits.append("%d Episoden" % len(self._items))
        self["subheader"].setText(" · ".join(bits))
        self["page"].setText("Seite %d / %d" % (self._pageNo(), self._pageCount()))

    def _showPage(self):
        self._page_items = self._items[self._page_start:self._page_start + PAGE_SIZE]
        if self._selected >= len(self._page_items):
            self._selected = max(0, len(self._page_items) - 1)
        self._renderPageMeta()
        self._renderCards()

    @staticmethod
    def _short(text, limit=28):
        text = str(text or "")
        if len(text) <= limit:
            return text
        return text[:max(1, limit - 3)] + "..."

    @staticmethod
    def _runtimeText(item):
        try:
            ticks = int(getattr(item, "runtime_ticks", 0) or 0)
        except Exception:
            ticks = 0
        if ticks <= 0:
            return ""
        minutes = int(ticks // 10000000 // 60)
        return "%d Min." % minutes if minutes else ""

    @staticmethod
    def _episodeCode(item):
        try:
            season = int(getattr(item, "season_number", 0) or 0)
        except Exception:
            season = 0
        try:
            episode = int(getattr(item, "episode_number", 0) or 0)
        except Exception:
            episode = 0
        if episode > 0:
            return "S%02dE%02d" % (season, episode)
        return ""

    def _renderCards(self):
        self._image_request += 1
        rid = self._image_request

        for i in range(PAGE_SIZE):
            self["code%d" % i].setText("")
            self["title%d" % i].setText("")
            self["runtime%d" % i].setText("")
            try:
                self["thumb%d" % i].hide()
            except Exception:
                pass

        for i, item in enumerate(self._page_items):
            self["code%d" % i].setText(self._episodeCode(item))
            self["title%d" % i].setText(self._short(getattr(item, "title", "") or ""))
            self["runtime%d" % i].setText(self._runtimeText(item))

            url = getattr(item, "poster_url", None)
            item_id = getattr(item, "id", None)
            if not url:
                continue

            cached = image_cache.get_local_path(url)
            if cached:
                self._showThumb(i, cached, rid, item_id)
            else:
                image_cache.fetch(
                    url,
                    lambda path, p=i, r=rid, iid=item_id: self._showThumb(p, path, r, iid),
                    lambda err, p=i: log.warning("Plex EpisodeUI3 Bild %d: %s", p, err),
                )

        self._updateFocus()

    def _showThumb(self, pos, path, rid, item_id=None):
        if self._closing or rid != self._image_request:
            return False
        if not (0 <= pos < len(self._page_items)):
            return False
        if item_id is not None and getattr(self._page_items[pos], "id", None) != item_id:
            return False
        try:
            if not path or not os.path.isfile(path):
                return False
            widget = self["thumb%d" % pos]
            if widget.instance:
                widget.instance.setScale(1)
                widget.instance.setPixmapFromFile(path)
                widget.show()
                return True
        except Exception as exc:
            log.warning("Plex EpisodeUI3 Bildanzeige %d: %s", pos, exc)
        return False

    def _showFocus(self, visible):
        for name in ("focus_top", "focus_bottom", "focus_left", "focus_right"):
            try:
                self[name].show() if visible else self[name].hide()
            except Exception:
                pass

    def _updateFocus(self):
        if not self._page_items:
            self._showFocus(False)
            return
        self._showFocus(True)
        x, y = CARD_POS[self._selected]
        try:
            self["focus_top"].instance.move(ePoint(x - 6, y - 6))
            self["focus_bottom"].instance.move(ePoint(x - 6, y + THUMB_H + 6))
            self["focus_left"].instance.move(ePoint(x - 6, y - 6))
            self["focus_right"].instance.move(ePoint(x + THUMB_W + 1, y - 6))
        except Exception:
            pass

    def _current(self):
        if 0 <= self._selected < len(self._page_items):
            return self._page_items[self._selected]
        return None

    def _nextPage(self, target_col=0):
        if self._page_start + PAGE_SIZE >= len(self._items):
            return False
        self._page_start += PAGE_SIZE
        self._page_items = self._items[self._page_start:self._page_start + PAGE_SIZE]
        self._selected = min(max(0, target_col), len(self._page_items) - 1)
        self._showPage()
        return True

    def _prevPage(self, target_col=0):
        if self._page_start <= 0:
            return False
        self._page_start = max(0, self._page_start - PAGE_SIZE)
        self._page_items = self._items[self._page_start:self._page_start + PAGE_SIZE]
        target = COLS + target_col if len(self._page_items) > COLS else target_col
        self._selected = min(max(0, target), len(self._page_items) - 1)
        self._showPage()
        return True

    def keyLeft(self):
        if not self._page_items:
            return
        col = self._selected % COLS
        if col > 0:
            self._selected -= 1
            self._updateFocus()
            return
        if self._page_start > 0:
            self._prevPage(COLS - 1)

    def keyRight(self):
        if not self._page_items:
            return
        if self._selected < len(self._page_items) - 1:
            self._selected += 1
            self._updateFocus()
            return
        self._nextPage(0)

    def keyUp(self):
        if not self._page_items:
            return
        if self._selected >= COLS:
            self._selected -= COLS
            self._updateFocus()
            return
        col = self._selected % COLS
        if self._page_start > 0:
            self._prevPage(col)

    def keyDown(self):
        if not self._page_items:
            return
        target = self._selected + COLS
        if target < len(self._page_items):
            self._selected = target
            self._updateFocus()
            return
        col = self._selected % COLS
        self._nextPage(col)

    def keyOpen(self):
        item = self._current()
        if item is None:
            return
        from .MediaDetail import MediaDetail
        self.session.openWithCallback(self._childClosed, MediaDetail, item, self.client)

    def _childClosed(self, *args):
        if not self._closing:
            self._renderCards()

    def keyBlue(self):
        return

    def keyCancel(self):
        self.close()
