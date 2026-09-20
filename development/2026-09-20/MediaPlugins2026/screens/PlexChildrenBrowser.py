# -*- coding: utf-8 -*-
# INFUSEMEDIA2026_PLEX_EPISODEUI3
# INFUSEMEDIA2026_PLEX_SEASONUI2

import os

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from enigma import ePoint
from skin import parseColor

from ..utils.image_cache import image_cache
from ..utils import log

PAGE_SIZE = 12
COLS = 6
FILTERS = ["A-Z", "0-9"] + [chr(c) for c in range(ord("A"), ord("Z") + 1)]
POSTER_W = 215
POSTER_H = 300
GRID_X = 220
GRID_Y = (175, 575)
COL_STEP = 250
POSTER_POS = [
    (GRID_X + col * COL_STEP, GRID_Y[row])
    for row in range(2) for col in range(COLS)
]


def _build_skin():
    parts = ["""
    <screen name="MediaPlugins2026PlexChildrenBrowser" position="0,0" size="1920,1080"
            flags="wfNoBorder" backgroundColor="#07131d">
        <widget name="header" position="70,38" size="1500,52" font="Regular;32"
                foregroundColor="#f3f6f8" transparent="1" />
        <widget name="filter_name" position="1660,42" size="180,42" font="Regular;22"
                foregroundColor="#39bce5" transparent="1" halign="right" />
        <widget name="subheader" position="70,98" size="1650,38" font="Regular;20"
                foregroundColor="#36b8e2" transparent="1" />
        <widget name="az" position="82,145" size="95,790" font="Regular;19"
                foregroundColor="#d5dce2" transparent="1" halign="left" valign="top" />
    """]
    for i, (x, y) in enumerate(POSTER_POS):
        parts.append("""
        <widget name="poster%d" position="%d,%d" size="%d,%d"
                alphatest="on" scale="1" zPosition="2" />
        <widget name="title%d" position="%d,%d" size="%d,40"
                font="Regular;18" foregroundColor="#eef2f5" transparent="1" />
        <widget name="year%d" position="%d,%d" size="%d,30"
                font="Regular;17" foregroundColor="#8599aa" transparent="1" />
        """ % (
            i, x, y, POSTER_W, POSTER_H,
            i, x, y + 312, POSTER_W,
            i, x, y + 355, POSTER_W,
        ))
    parts.append("""
        <widget name="focus_top" position="214,169" size="227,5"
                backgroundColor="#f2c400" transparent="0" zPosition="8" />
        <widget name="focus_bottom" position="214,475" size="227,5"
                backgroundColor="#f2c400" transparent="0" zPosition="8" />
        <widget name="focus_left" position="214,169" size="5,311"
                backgroundColor="#f2c400" transparent="0" zPosition="8" />
        <widget name="focus_right" position="436,169" size="5,311"
                backgroundColor="#f2c400" transparent="0" zPosition="8" />
        <widget name="status" position="70,930" size="1550,35" font="Regular;18"
                foregroundColor="#8499aa" transparent="1" />
        <widget name="keybar_bg" position="42,992" size="1835,55"
                backgroundColor="#091b2a" transparent="0" />
        <widget name="keybar" position="45,1004" size="1790,34" font="Regular;19"
                foregroundColor="#cbd4dc" transparent="1" />
    </screen>
    """)
    return "".join(parts)


class PlexChildrenBrowser(Screen):
    skinName = "MediaPlugins2026PlexChildrenBrowser"
    skin = _build_skin()

    def __init__(self, session, parent_item, client):
        Screen.__init__(self, session)
        self.session = session
        self.parent_item = parent_item
        self.client = client

        # Screen besitzt bereits items(); daher bewusst _items verwenden.
        self._items = []
        self._filtered = []
        self._page_items = []
        self._selected = 0
        self._page_start = 0
        self._filter_index = 0
        self._focus_area = "grid"
        self._closing = False
        self._image_request = 0

        self["header"] = Label("")
        self["filter_name"] = Label("A-Z")
        self["subheader"] = Label("")
        self["az"] = Label("")
        self["status"] = Label("Lade Plex-Inhalte …")
        self["keybar_bg"] = Label("")
        self["keybar"] = Label(
            "PFEILE  Treffer wählen     OK  Öffnen     EXIT  Zurück     BLAU  Merkliste"
        )

        for name in ("focus_top", "focus_bottom", "focus_left", "focus_right"):
            self[name] = Label("")

        for i in range(PAGE_SIZE):
            self["poster%d" % i] = Pixmap()
            self["title%d" % i] = Label("")
            self["year%d" % i] = Label("")

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.keyOpen,
                "cancel": self.keyCancel,
                "red": self.keyCancel,
                "blue": self.keyBlue,
                "up": self.keyUp,
                "down": self.keyDown,
                "left": self.keyLeft,
                "right": self.keyRight,
            },
            -2,
        )

        self.onClose.append(self._onClose)
        self.onLayoutFinish.append(self._renderHeader)
        self.onLayoutFinish.append(self._renderAz)
        self.onLayoutFinish.append(self._load)

    def _onClose(self):
        self._closing = True
        self._image_request += 1

    def _type(self, item):
        kind = str(getattr(item, "media_type", "") or "").strip().lower()
        if kind:
            return kind
        if (
            getattr(item, "season_number", None) is not None
            and getattr(item, "episode_number", None) is None
            and not getattr(item, "stream_url", "")
        ):
            return "season"
        return ""

    def _seriesName(self):
        if self._type(self.parent_item) == "season":
            return (
                getattr(self.parent_item, "series_name", "")
                or getattr(self.parent_item, "title", "")
                or "Plex"
            )
        return getattr(self.parent_item, "title", "") or "Plex"

    def _seasonText(self):
        number = getattr(self.parent_item, "season_number", None)
        if number is None:
            return ""
        try:
            return "Staffel %d" % int(number)
        except Exception:
            return ""

    def _renderHeader(self):
        series = self._seriesName()
        season = self._seasonText()
        suffix = (" · " + season.upper()) if season else ""
        self["header"].setText("PLEX 2026   |   %s%s" % (series.upper(), suffix))

    def _renderAz(self):
        lines = []
        for idx, value in enumerate(FILTERS):
            lines.append(("▶ " if self._focus_area == "az" and idx == self._filter_index else "  ") + value)
        self["az"].setText("\n".join(lines))
        self["filter_name"].setText(FILTERS[self._filter_index])
        try:
            color = "#f2c400" if self._focus_area == "az" else "#d5dce2"
            self["az"].instance.setForegroundColor(parseColor(color))
        except Exception:
            pass

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
        self._applyFilter()

    def _onError(self, err):
        self._items = []
        self._filtered = []
        self._page_items = []
        self["status"].setText("Plex-Fehler: %s" % err)
        self._renderPage()

    @staticmethod
    def _matchesFilter(item, active):
        if active == "A-Z":
            return True
        title = (getattr(item, "title", "") or "").strip()
        if not title:
            return False
        first = title[0].upper()
        if active == "0-9":
            return first.isdigit()
        return first == active

    def _applyFilter(self):
        active = FILTERS[self._filter_index]
        self._filtered = [item for item in self._items if self._matchesFilter(item, active)]
        self._page_start = 0
        self._selected = 0
        self._showPage()

    def _pageCount(self):
        return max(1, (len(self._filtered) + PAGE_SIZE - 1) // PAGE_SIZE)

    def _pageNo(self):
        return min(self._pageCount(), (self._page_start // PAGE_SIZE) + 1)

    def _showPage(self):
        self._page_items = self._filtered[self._page_start:self._page_start + PAGE_SIZE]
        if self._selected >= len(self._page_items):
            self._selected = max(0, len(self._page_items) - 1)

        count_name = "Episoden" if self._type(self.parent_item) == "season" else "Einträge"
        bits = [self._seriesName()]
        season = self._seasonText()
        if season:
            bits.append(season)
        bits.append("%d %s" % (len(self._filtered), count_name))
        bits.append("Seite %d / %d" % (self._pageNo(), self._pageCount()))
        self["subheader"].setText(" · ".join(bits))
        self["status"].setText("%d %s" % (len(self._filtered), count_name))

        self._renderPage()
        self._renderAz()

    @staticmethod
    def _short(text, limit=23):
        text = str(text or "")
        return text if len(text) <= limit else text[:limit - 3] + "..."

    def _labelFor(self, item):
        if self._type(item) == "season":
            number = getattr(item, "season_number", None)
            if number is not None:
                return "Staffel %d" % int(number)
        return self._short(getattr(item, "title", "") or "")

    def _renderPage(self):
        self._image_request += 1
        rid = self._image_request

        for i in range(PAGE_SIZE):
            self["title%d" % i].setText("")
            self["year%d" % i].setText("")
            try:
                self["poster%d" % i].hide()
            except Exception:
                pass

        for i, item in enumerate(self._page_items):
            self["title%d" % i].setText(self._labelFor(item))
            year = getattr(item, "year", None)
            self["year%d" % i].setText(str(year) if year else "")

            url = getattr(item, "poster_url", None)
            item_id = getattr(item, "id", None)
            if not url:
                continue
            cached = image_cache.get_local_path(url)
            if cached:
                self._showPoster(i, cached, rid, item_id)
            else:
                image_cache.fetch(
                    url,
                    lambda path, p=i, r=rid, iid=item_id: self._showPoster(p, path, r, iid),
                    lambda err, p=i: log.warning("Plex SeasonUI2 Poster %d: %s", p, err),
                )
        self._updateFocus()

    def _showPoster(self, pos, path, rid, item_id=None):
        if self._closing or rid != self._image_request or not (0 <= pos < len(self._page_items)):
            return False
        if item_id is not None and getattr(self._page_items[pos], "id", None) != item_id:
            return False
        try:
            if not path or not os.path.isfile(path):
                return False
            widget = self["poster%d" % pos]
            if widget.instance:
                widget.instance.setScale(1)
                widget.instance.setPixmapFromFile(path)
                widget.show()
                return True
        except Exception as exc:
            log.warning("Plex SeasonUI2 Posteranzeige %d: %s", pos, exc)
        return False

    def _showFocus(self, visible):
        for name in ("focus_top", "focus_bottom", "focus_left", "focus_right"):
            try:
                self[name].show() if visible else self[name].hide()
            except Exception:
                pass

    def _updateFocus(self):
        if self._focus_area == "az":
            self._showFocus(False)
            self._renderAz()
            return
        self._renderAz()
        if not self._page_items:
            self._showFocus(False)
            return
        self._showFocus(True)
        x, y = POSTER_POS[self._selected]
        try:
            self["focus_top"].instance.move(ePoint(x - 6, y - 6))
            self["focus_bottom"].instance.move(ePoint(x - 6, y + POSTER_H + 6))
            self["focus_left"].instance.move(ePoint(x - 6, y - 6))
            self["focus_right"].instance.move(ePoint(x + POSTER_W + 1, y - 6))
        except Exception:
            pass

    def _current(self):
        if 0 <= self._selected < len(self._page_items):
            return self._page_items[self._selected]
        return None

    def _prevPage(self, col=0):
        if self._page_start <= 0:
            return False
        self._page_start = max(0, self._page_start - PAGE_SIZE)
        self._page_items = self._filtered[self._page_start:self._page_start + PAGE_SIZE]
        target = COLS + col if len(self._page_items) > COLS else col
        self._selected = min(max(0, target), len(self._page_items) - 1)
        self._showPage()
        return True

    def _nextPage(self, col=0):
        if self._page_start + PAGE_SIZE >= len(self._filtered):
            return False
        self._page_start += PAGE_SIZE
        self._page_items = self._filtered[self._page_start:self._page_start + PAGE_SIZE]
        self._selected = min(max(0, col), len(self._page_items) - 1)
        self._showPage()
        return True

    def keyLeft(self):
        if self._focus_area == "az":
            return
        if not self._page_items:
            self._focus_area = "az"
            self._updateFocus()
            return
        col = self._selected % COLS
        if col > 0:
            self._selected -= 1
            self._updateFocus()
        elif self._page_start > 0:
            self._prevPage(COLS - 1)
        else:
            self._focus_area = "az"
            self._updateFocus()

    def keyRight(self):
        if self._focus_area == "az":
            self._focus_area = "grid"
            self._selected = 0
            self._updateFocus()
            return
        if not self._page_items:
            return
        if self._selected < len(self._page_items) - 1:
            self._selected += 1
            self._updateFocus()
        else:
            self._nextPage(0)

    def keyUp(self):
        if self._focus_area == "az":
            if self._filter_index > 0:
                self._filter_index -= 1
                self._applyFilter()
                self._focus_area = "az"
                self._updateFocus()
            return
        if self._selected >= COLS:
            self._selected -= COLS
            self._updateFocus()
            return
        col = self._selected % COLS
        if self._page_start > 0:
            self._prevPage(col)

    def keyDown(self):
        if self._focus_area == "az":
            if self._filter_index < len(FILTERS) - 1:
                self._filter_index += 1
                self._applyFilter()
                self._focus_area = "az"
                self._updateFocus()
            return
        if not self._page_items:
            return
        target = self._selected + COLS
        if target < len(self._page_items):
            self._selected = target
            self._updateFocus()
        else:
            self._nextPage(self._selected % COLS)

    def keyOpen(self):
        if self._focus_area == "az":
            self._focus_area = "grid"
            self._selected = 0
            self._updateFocus()
            return
        item = self._current()
        if item is None:
            return
        kind = self._type(item)
        if kind == "season":
            from .PlexEpisodeBrowser import PlexEpisodeBrowser
            self.session.openWithCallback(self._childClosed, PlexEpisodeBrowser, item, self.client)
        elif kind == "show":
            self.session.openWithCallback(self._childClosed, PlexChildrenBrowser, item, self.client)
        else:
            from .MediaDetail import MediaDetail
            self.session.openWithCallback(self._childClosed, MediaDetail, item, self.client)

    def _childClosed(self, *args):
        if not self._closing:
            self._renderPage()

    def keyBlue(self):
        self["status"].setText("Plex-Merkliste folgt in einer späteren Version.")

    def keyCancel(self):
        self.close()
