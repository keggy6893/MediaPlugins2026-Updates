# -*- coding: utf-8 -*-
from Components.GUIComponent import GUIComponent
from enigma import eListbox, eListboxPythonMultiContent, RT_HALIGN_LEFT
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Tools.LoadPixmap import LoadPixmap

from ..utils.image_cache import image_cache

POSTER_W = 180
POSTER_H = 270


class SectionRow(GUIComponent):
    """Eine horizontal scrollbare Poster-Reihe (z.B. 'Neuste Action - Server')."""

    GUI_WIDGET = eListbox

    def __init__(self, title=""):
        GUIComponent.__init__(self)
        self.title = title
        self.l = eListboxPythonMultiContent()
        self.l.setItemHeight(POSTER_H + 50)
        self.l.setBuildFunc(self.buildEntry)
        self.list = []
        self.focused = False

    def postWidgetCreate(self, instance):
        instance.setOrientation(eListbox.orHorizontal)
        instance.setContent(self.l)

    def setItemsList(self, items):
        self.list = [(item,) for item in items]
        self.l.setList(self.list)
        self._prefetchPosters(items)

    def _prefetchPosters(self, items):
        for item in items:
            cached = image_cache.get_local_path(item.poster_url)
            if cached:
                item.local_poster_path = cached
            else:
                item.local_poster_path = None
                image_cache.fetch(
                    item.poster_url,
                    lambda path, i=item: self._onPosterLoaded(i, path)
                )

    def _onPosterLoaded(self, item, local_path):
        item.local_poster_path = local_path
        if self.instance:
            self.l.invalidate()

    def buildEntry(self, item):
        res = [None]
        poster = LoadPixmap(item.local_poster_path) if item.local_poster_path else None
        if poster:
            res.append(MultiContentEntryPixmapAlphaTest(
                pos=(0, 0), size=(POSTER_W, POSTER_H), png=poster
            ))
        res.append(MultiContentEntryText(
            pos=(0, POSTER_H + 4), size=(POSTER_W, 22),
            font=0, flags=RT_HALIGN_LEFT,
            text=self._truncate(item.title, 20)
        ))
        res.append(MultiContentEntryText(
            pos=(0, POSTER_H + 26), size=(POSTER_W, 20),
            font=1, flags=RT_HALIGN_LEFT,
            text=str(item.year) if item.year else ""
        ))
        return res

    def _truncate(self, text, max_len):
        return text if len(text) <= max_len else text[:max_len - 1] + "…"

    def getCurrent(self):
        idx = self.instance.getCurrentIndex()
        if 0 <= idx < len(self.list):
            return self.list[idx][0]
        return None

    def getCount(self):
        return len(self.list)

    def setFocus(self, focused):
        self.focused = focused
        if self.instance:
            self.instance.setSelectionEnable(1 if focused else 0)

    def moveLeft(self):
        if self.instance:
            self.instance.moveSelection(self.instance.moveLeft)

    def moveRight(self):
        if self.instance:
            self.instance.moveSelection(self.instance.moveRight)
