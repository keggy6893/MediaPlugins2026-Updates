# -*- coding: utf-8 -*-
from Components.Pixmap import Pixmap
from Components.Label import Label
from Tools.LoadPixmap import LoadPixmap

from ..utils.image_cache import image_cache
from ..utils import log

_PLACEHOLDER_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/skin/icons/poster_placeholder.png"
_placeholder_pixmap_cache = None


def _get_placeholder_pixmap():
    global _placeholder_pixmap_cache
    if _placeholder_pixmap_cache is None:
        _placeholder_pixmap_cache = LoadPixmap(_PLACEHOLDER_PATH)
    return _placeholder_pixmap_cache


class PosterRow(object):
    """Robuste Posterreihe aus Standard-Pixmap/Label-Widgets.

    Leere Zellen werden komplett ausgeblendet. Nur vorhandene Eintraege zeigen
    waehrend des Downloads einen Platzhalter. Das verhindert die grossen grauen
    Leerflaechen der bisherigen Startseite.
    """

    def __init__(self, screen, prefix, count=6):
        self.screen = screen
        self.prefix = prefix
        self.count = count
        self.items = []
        self.index = 0
        self.focused = False

        for i in range(count):
            screen["%s_focus_%d" % (prefix, i)] = Label("")
            screen["%s_poster_%d" % (prefix, i)] = Pixmap()
            screen["%s_title_%d" % (prefix, i)] = Label("")
            screen["%s_year_%d" % (prefix, i)] = Label("")

    def setItems(self, items):
        self.items = list(items)[:self.count]
        self.index = 0
        self._render()
        self._prefetchPosters()

    def setFocused(self, focused):
        self.focused = bool(focused)
        self._render()

    def _prefetchPosters(self):
        for item in self.items:
            cached = image_cache.get_local_path(item.poster_url)
            if cached:
                item.local_poster_path = cached
            else:
                item.local_poster_path = None
                image_cache.fetch(
                    item.poster_url,
                    lambda path, i=item: self._onPosterLoaded(i, path),
                    lambda err, i=item: log.safe_call(self._onPosterFailed, i, err)
                )

    def _onPosterLoaded(self, item, path):
        item.local_poster_path = path
        self._render()

    def _onPosterFailed(self, item, err):
        log.warning("Poster fuer '%s' nicht ladbar: %s", item.title, err)

    def _render(self):
        placeholder = _get_placeholder_pixmap()
        for i in range(self.count):
            focus_w = self.screen.get("%s_focus_%d" % (self.prefix, i))
            poster_w = self.screen.get("%s_poster_%d" % (self.prefix, i))
            title_w = self.screen.get("%s_title_%d" % (self.prefix, i))
            year_w = self.screen.get("%s_year_%d" % (self.prefix, i))
            if focus_w is None or poster_w is None or title_w is None or year_w is None:
                continue

            if i >= len(self.items):
                focus_w.hide()
                poster_w.hide()
                title_w.setText("")
                title_w.hide()
                year_w.setText("")
                year_w.hide()
                continue

            if self.focused and i == self.index:
                focus_w.show()
            else:
                focus_w.hide()
            poster_w.show()
            title_w.show()
            year_w.show()
            item = self.items[i]
            pix = LoadPixmap(item.local_poster_path) if item.local_poster_path else placeholder
            if pix and poster_w.instance:
                poster_w.instance.setPixmap(pix)

            marker = "▶ " if self.focused and i == self.index else ""
            heart = "♥ " if getattr(item, "is_favorite", False) else ""
            max_len = 31 if self.prefix == "hero" else 24
            title_w.setText(marker + heart + self._truncate(item.title, max_len))
            year = str(item.year) if item.year else ""
            source = (getattr(item, "source_label", "") or "").upper()
            if source:
                year_w.setText((year + "  ·  " if year else "") + source)
            else:
                year_w.setText(year)

    def _truncate(self, text, max_len):
        text = text or ""
        return text if len(text) <= max_len else text[:max_len - 1] + "…"

    def getCurrent(self):
        if 0 <= self.index < len(self.items):
            return self.items[self.index]
        return None

    def getCount(self):
        return len(self.items)

    def moveLeft(self):
        if self.items and self.index > 0:
            self.index -= 1
            self._render()

    def moveRight(self):
        if self.items and self.index < len(self.items) - 1:
            self.index += 1
            self._render()
