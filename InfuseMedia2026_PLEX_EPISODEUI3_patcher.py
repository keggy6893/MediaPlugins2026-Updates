# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import re
import shutil
import sys

PLUGIN_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026"
EPISODE_REL = "screens/PlexEpisodeBrowser.py"
DETAIL_REL = "screens/MediaDetail.py"
CHILD_REL = "screens/PlexChildrenBrowser.py"
PLEX_REL = "backends/plex_client.py"
MARKER = "# INFUSEMEDIA2026_PLEX_EPISODEUI3"

NEW_EPISODE_BROWSER = '# -*- coding: utf-8 -*-\n# INFUSEMEDIA2026_PLEX_EPISODEUI3\n\nimport os\n\nfrom Screens.Screen import Screen\nfrom Components.ActionMap import ActionMap\nfrom Components.Label import Label\nfrom Components.Pixmap import Pixmap\nfrom enigma import ePoint\n\nfrom ..utils.image_cache import image_cache\nfrom ..utils import log\n\nPAGE_SIZE = 10\nCOLS = 5\nTHUMB_W = 340\nTHUMB_H = 191\nX_POS = (55, 423, 791, 1159, 1527)\nY_POS = (175, 575)\nCARD_POS = [\n    (X_POS[col], Y_POS[row])\n    for row in range(2)\n    for col in range(COLS)\n]\n\n\ndef _build_skin():\n    parts = ["""\n    <screen name="InfuseMedia2026PlexEpisodeBrowser" position="0,0" size="1920,1080"\n            flags="wfNoBorder" backgroundColor="#07131d">\n        <widget name="header" position="55,34" size="1500,52" font="Regular;32"\n                foregroundColor="#f3f6f8" transparent="1" />\n        <widget name="page" position="1600,38" size="265,40" font="Regular;22"\n                foregroundColor="#38bde6" transparent="1" halign="right" />\n        <widget name="subheader" position="55,94" size="1500,36" font="Regular;20"\n                foregroundColor="#38bde6" transparent="1" />\n    """]\n\n    for i, (x, y) in enumerate(CARD_POS):\n        parts.append("""\n        <widget name="thumb%d" position="%d,%d" size="%d,%d"\n                alphatest="on" scale="1" zPosition="2" />\n        <widget name="code%d" position="%d,%d" size="%d,30"\n                font="Regular;19" foregroundColor="#dbe7ef" transparent="1" />\n        <widget name="title%d" position="%d,%d" size="%d,34"\n                font="Regular;21" foregroundColor="#f4f6f8" transparent="1" />\n        <widget name="runtime%d" position="%d,%d" size="%d,30"\n                font="Regular;18" foregroundColor="#8e9ba7" transparent="1" />\n        """ % (\n            i, x, y, THUMB_W, THUMB_H,\n            i, x, y + 204, THUMB_W,\n            i, x, y + 238, THUMB_W,\n            i, x, y + 277, THUMB_W,\n        ))\n\n    parts.append("""\n        <widget name="focus_top" position="49,169" size="352,5"\n                backgroundColor="#f2c400" transparent="0" zPosition="9" />\n        <widget name="focus_bottom" position="49,371" size="352,5"\n                backgroundColor="#f2c400" transparent="0" zPosition="9" />\n        <widget name="focus_left" position="49,169" size="5,207"\n                backgroundColor="#f2c400" transparent="0" zPosition="9" />\n        <widget name="focus_right" position="396,169" size="5,207"\n                backgroundColor="#f2c400" transparent="0" zPosition="9" />\n\n        <widget name="keybar_bg" position="45,960" size="1830,70"\n                backgroundColor="#091b2a" transparent="0" />\n        <widget name="key_red" position="100,980" size="260,32" font="Regular;20"\n                foregroundColor="#f05a5a" transparent="1" text="■  Zurück" />\n        <widget name="key_nav" position="700,980" size="600,32" font="Regular;20"\n                foregroundColor="#d2d8de" transparent="1" halign="center"\n                text="PFEILE   Navigieren      OK   Öffnen" />\n        <widget name="key_blue" position="1570,980" size="245,32" font="Regular;20"\n                foregroundColor="#32b9e8" transparent="1" halign="right"\n                text="■  Merkliste" />\n    </screen>\n    """)\n    return "".join(parts)\n\n\nclass PlexEpisodeBrowser(Screen):\n    skinName = "InfuseMedia2026PlexEpisodeBrowser"\n    skin = _build_skin()\n\n    def __init__(self, session, parent_item, client):\n        Screen.__init__(self, session)\n        self.session = session\n        self.parent_item = parent_item\n        self.client = client\n        self._items = []\n        self._page_items = []\n        self._page_start = 0\n        self._selected = 0\n        self._closing = False\n        self._image_request = 0\n\n        self["header"] = Label("")\n        self["page"] = Label("")\n        self["subheader"] = Label("")\n        self["keybar_bg"] = Label("")\n        self["key_red"] = Label("■  Zurück")\n        self["key_nav"] = Label("PFEILE   Navigieren      OK   Öffnen")\n        self["key_blue"] = Label("■  Merkliste")\n\n        for name in ("focus_top", "focus_bottom", "focus_left", "focus_right"):\n            self[name] = Label("")\n\n        for i in range(PAGE_SIZE):\n            self["thumb%d" % i] = Pixmap()\n            self["code%d" % i] = Label("")\n            self["title%d" % i] = Label("")\n            self["runtime%d" % i] = Label("")\n\n        self["actions"] = ActionMap(\n            ["OkCancelActions", "DirectionActions", "ColorActions"],\n            {\n                "ok": self.keyOpen,\n                "cancel": self.keyCancel,\n                "red": self.keyCancel,\n                "blue": self.keyBlue,\n                "left": self.keyLeft,\n                "right": self.keyRight,\n                "up": self.keyUp,\n                "down": self.keyDown,\n            },\n            -2,\n        )\n\n        self.onClose.append(self._onClose)\n        self.onLayoutFinish.append(self._renderHeader)\n        self.onLayoutFinish.append(self._load)\n\n    def _onClose(self):\n        self._closing = True\n        self._image_request += 1\n\n    def _seriesName(self):\n        return (\n            getattr(self.parent_item, "series_name", "")\n            or getattr(self.parent_item, "title", "")\n            or "Plex"\n        )\n\n    def _seasonNumber(self):\n        try:\n            number = getattr(self.parent_item, "season_number", None)\n            return int(number) if number is not None else None\n        except Exception:\n            return None\n\n    def _renderHeader(self):\n        series = self._seriesName()\n        season = self._seasonNumber()\n        right = (" · STAFFEL %d" % season) if season is not None else ""\n        self["header"].setText("PLEX 2026   |   %s%s" % (series.upper(), right))\n        self._renderPageMeta()\n\n    def _load(self):\n        self.client.get_children(\n            self.parent_item.id,\n            lambda items: log.safe_call(self._onLoaded, items),\n            lambda err: log.safe_call(self._onError, err),\n        )\n\n    def _onLoaded(self, items):\n        if self._closing:\n            return\n        self._items = list(items or [])\n        self._items.sort(\n            key=lambda x: (\n                int(getattr(x, "season_number", 0) or 0),\n                int(getattr(x, "episode_number", 0) or 0),\n                str(getattr(x, "title", "") or "").casefold(),\n            )\n        )\n        self._page_start = 0\n        self._selected = 0\n        self._showPage()\n\n    def _onError(self, err):\n        self._items = []\n        self._page_items = []\n        self["subheader"].setText("Plex-Fehler: %s" % err)\n        self["page"].setText("")\n        self._renderCards()\n\n    def _pageCount(self):\n        return max(1, (len(self._items) + PAGE_SIZE - 1) // PAGE_SIZE)\n\n    def _pageNo(self):\n        return min(self._pageCount(), (self._page_start // PAGE_SIZE) + 1)\n\n    def _renderPageMeta(self):\n        series = self._seriesName()\n        season = self._seasonNumber()\n        bits = [series]\n        if season is not None:\n            bits.append("Staffel %d" % season)\n        bits.append("%d Episoden" % len(self._items))\n        self["subheader"].setText(" · ".join(bits))\n        self["page"].setText("Seite %d / %d" % (self._pageNo(), self._pageCount()))\n\n    def _showPage(self):\n        self._page_items = self._items[self._page_start:self._page_start + PAGE_SIZE]\n        if self._selected >= len(self._page_items):\n            self._selected = max(0, len(self._page_items) - 1)\n        self._renderPageMeta()\n        self._renderCards()\n\n    @staticmethod\n    def _short(text, limit=28):\n        text = str(text or "")\n        if len(text) <= limit:\n            return text\n        return text[:max(1, limit - 3)] + "..."\n\n    @staticmethod\n    def _runtimeText(item):\n        try:\n            ticks = int(getattr(item, "runtime_ticks", 0) or 0)\n        except Exception:\n            ticks = 0\n        if ticks <= 0:\n            return ""\n        minutes = int(ticks // 10000000 // 60)\n        return "%d Min." % minutes if minutes else ""\n\n    @staticmethod\n    def _episodeCode(item):\n        try:\n            season = int(getattr(item, "season_number", 0) or 0)\n        except Exception:\n            season = 0\n        try:\n            episode = int(getattr(item, "episode_number", 0) or 0)\n        except Exception:\n            episode = 0\n        if episode > 0:\n            return "S%02dE%02d" % (season, episode)\n        return ""\n\n    def _renderCards(self):\n        self._image_request += 1\n        rid = self._image_request\n\n        for i in range(PAGE_SIZE):\n            self["code%d" % i].setText("")\n            self["title%d" % i].setText("")\n            self["runtime%d" % i].setText("")\n            try:\n                self["thumb%d" % i].hide()\n            except Exception:\n                pass\n\n        for i, item in enumerate(self._page_items):\n            self["code%d" % i].setText(self._episodeCode(item))\n            self["title%d" % i].setText(self._short(getattr(item, "title", "") or ""))\n            self["runtime%d" % i].setText(self._runtimeText(item))\n\n            url = getattr(item, "poster_url", None)\n            item_id = getattr(item, "id", None)\n            if not url:\n                continue\n\n            cached = image_cache.get_local_path(url)\n            if cached:\n                self._showThumb(i, cached, rid, item_id)\n            else:\n                image_cache.fetch(\n                    url,\n                    lambda path, p=i, r=rid, iid=item_id: self._showThumb(p, path, r, iid),\n                    lambda err, p=i: log.warning("Plex EpisodeUI3 Bild %d: %s", p, err),\n                )\n\n        self._updateFocus()\n\n    def _showThumb(self, pos, path, rid, item_id=None):\n        if self._closing or rid != self._image_request:\n            return False\n        if not (0 <= pos < len(self._page_items)):\n            return False\n        if item_id is not None and getattr(self._page_items[pos], "id", None) != item_id:\n            return False\n        try:\n            if not path or not os.path.isfile(path):\n                return False\n            widget = self["thumb%d" % pos]\n            if widget.instance:\n                widget.instance.setScale(1)\n                widget.instance.setPixmapFromFile(path)\n                widget.show()\n                return True\n        except Exception as exc:\n            log.warning("Plex EpisodeUI3 Bildanzeige %d: %s", pos, exc)\n        return False\n\n    def _showFocus(self, visible):\n        for name in ("focus_top", "focus_bottom", "focus_left", "focus_right"):\n            try:\n                self[name].show() if visible else self[name].hide()\n            except Exception:\n                pass\n\n    def _updateFocus(self):\n        if not self._page_items:\n            self._showFocus(False)\n            return\n        self._showFocus(True)\n        x, y = CARD_POS[self._selected]\n        try:\n            self["focus_top"].instance.move(ePoint(x - 6, y - 6))\n            self["focus_bottom"].instance.move(ePoint(x - 6, y + THUMB_H + 6))\n            self["focus_left"].instance.move(ePoint(x - 6, y - 6))\n            self["focus_right"].instance.move(ePoint(x + THUMB_W + 1, y - 6))\n        except Exception:\n            pass\n\n    def _current(self):\n        if 0 <= self._selected < len(self._page_items):\n            return self._page_items[self._selected]\n        return None\n\n    def _nextPage(self, target_col=0):\n        if self._page_start + PAGE_SIZE >= len(self._items):\n            return False\n        self._page_start += PAGE_SIZE\n        self._page_items = self._items[self._page_start:self._page_start + PAGE_SIZE]\n        self._selected = min(max(0, target_col), len(self._page_items) - 1)\n        self._showPage()\n        return True\n\n    def _prevPage(self, target_col=0):\n        if self._page_start <= 0:\n            return False\n        self._page_start = max(0, self._page_start - PAGE_SIZE)\n        self._page_items = self._items[self._page_start:self._page_start + PAGE_SIZE]\n        target = COLS + target_col if len(self._page_items) > COLS else target_col\n        self._selected = min(max(0, target), len(self._page_items) - 1)\n        self._showPage()\n        return True\n\n    def keyLeft(self):\n        if not self._page_items:\n            return\n        col = self._selected % COLS\n        if col > 0:\n            self._selected -= 1\n            self._updateFocus()\n            return\n        if self._page_start > 0:\n            self._prevPage(COLS - 1)\n\n    def keyRight(self):\n        if not self._page_items:\n            return\n        if self._selected < len(self._page_items) - 1:\n            self._selected += 1\n            self._updateFocus()\n            return\n        self._nextPage(0)\n\n    def keyUp(self):\n        if not self._page_items:\n            return\n        if self._selected >= COLS:\n            self._selected -= COLS\n            self._updateFocus()\n            return\n        col = self._selected % COLS\n        if self._page_start > 0:\n            self._prevPage(col)\n\n    def keyDown(self):\n        if not self._page_items:\n            return\n        target = self._selected + COLS\n        if target < len(self._page_items):\n            self._selected = target\n            self._updateFocus()\n            return\n        col = self._selected % COLS\n        self._nextPage(col)\n\n    def keyOpen(self):\n        item = self._current()\n        if item is None:\n            return\n        from .MediaDetail import MediaDetail\n        self.session.openWithCallback(self._childClosed, MediaDetail, item, self.client)\n\n    def _childClosed(self, *args):\n        if not self._closing:\n            self._renderCards()\n\n    def keyBlue(self):\n        return\n\n    def keyCancel(self):\n        self.close()\n'
OLD_DETAIL = '    def _openChildren(self):\n        if not self._isContainerItem():\n            return False\n        try:\n            from .PlexChildrenBrowser import PlexChildrenBrowser\n            self.session.open(PlexChildrenBrowser, self.item, self.client)\n        except Exception as exc:\n            log.exception("Plex Staffel-/Serienbrowser konnte nicht geöffnet werden: %s", exc)\n            from Screens.MessageBox import MessageBox\n            self.session.open(MessageBox, "Plex-Inhalte konnten nicht geöffnet werden.", MessageBox.TYPE_ERROR)\n        return True\n'
NEW_DETAIL = '    def _openChildren(self):\n        if not self._isContainerItem():\n            return False\n        try:\n            if self._mediaType() == "season":\n                from .PlexEpisodeBrowser import PlexEpisodeBrowser\n                self.session.open(PlexEpisodeBrowser, self.item, self.client)\n            else:\n                from .PlexChildrenBrowser import PlexChildrenBrowser\n                self.session.open(PlexChildrenBrowser, self.item, self.client)\n        except Exception as exc:\n            log.exception("Plex Staffel-/Serienbrowser konnte nicht geöffnet werden: %s", exc)\n            from Screens.MessageBox import MessageBox\n            self.session.open(MessageBox, "Plex-Inhalte konnten nicht geöffnet werden.", MessageBox.TYPE_ERROR)\n        return True\n'
OLD_CHILD = '        kind = self._type(item)\n        if kind in ("show", "season"):\n            self.session.openWithCallback(self._childClosed, PlexChildrenBrowser, item, self.client)\n        else:\n            from .MediaDetail import MediaDetail\n            self.session.openWithCallback(self._childClosed, MediaDetail, item, self.client)\n'
NEW_CHILD = '        kind = self._type(item)\n        if kind == "season":\n            from .PlexEpisodeBrowser import PlexEpisodeBrowser\n            self.session.openWithCallback(self._childClosed, PlexEpisodeBrowser, item, self.client)\n        elif kind == "show":\n            self.session.openWithCallback(self._childClosed, PlexChildrenBrowser, item, self.client)\n        else:\n            from .MediaDetail import MediaDetail\n            self.session.openWithCallback(self._childClosed, MediaDetail, item, self.client)\n'


def read(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def backup(path, suffix):
    target = path + suffix
    if not os.path.exists(target):
        shutil.copy2(path, target)
    return target


def add_marker(text):
    if MARKER in text:
        return text
    if text.startswith("# -*- coding: utf-8 -*-"):
        first, rest = text.split("\n", 1)
        return first + "\n" + MARKER + "\n" + rest
    return MARKER + "\n" + text


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError("%s: erwartete genau 1 Fundstelle, gefunden %d" % (label, count))
    return text.replace(old, new, 1)


def patch_detail(text):
    if "PlexEpisodeBrowser" in text:
        return add_marker(text)
    return add_marker(replace_once(text, OLD_DETAIL, NEW_DETAIL, "MediaDetail _openChildren"))


def patch_children(text):
    if "PlexEpisodeBrowser" in text:
        return add_marker(text)
    if "# INFUSEMEDIA2026_PLEX_SEASONUI2" not in text:
        raise RuntimeError("PLEX_SEASONUI2 Basis fehlt im PlexChildrenBrowser")
    return add_marker(replace_once(text, OLD_CHILD, NEW_CHILD, "PlexChildrenBrowser keyOpen"))


def patch_plex(text):
    if "poster_url=poster_url," in text and "640,\n                360" in text:
        return add_marker(text)
    if "# INFUSEMEDIA2026_PLEX_SEASONBROWSER1" not in text:
        raise RuntimeError("PLEX_SEASONBROWSER1 Basis fehlt in plex_client.py")

    item_anchor = "        item = MediaItem(\n"
    if text.count(item_anchor) != 1:
        raise RuntimeError("Plex item = MediaItem: erwartete genau 1 Fundstelle")

    calc = (
        '        if media_type == "episode":\n'
        '            # Episode: echtes 16:9-Still in passender Aufloesung.\n'
        '            poster_url = self._image_url(\n'
        '                a.get("thumb") or a.get("parentThumb") or a.get("grandparentThumb"),\n'
        '                640,\n'
        '                360,\n'
        '            )\n'
        '        else:\n'
        '            # Filme/Serien/Staffeln bleiben Hochformat-Poster.\n'
        '            poster_url = self._image_url(\n'
        '                a.get("thumb") or a.get("parentThumb") or a.get("grandparentThumb"),\n'
        '                320,\n'
        '                480,\n'
        '            )\n\n'
    )
    text = text.replace(item_anchor, calc + item_anchor, 1)

    start = text.index(item_anchor)
    back = text.index("            backdrop_url=", start)
    block = text[start:back]
    block2, n = re.subn(
        r'(?ms)^            poster_url=self\._image_url\(.*?^            \),\n',
        '            poster_url=poster_url,\n',
        block,
        count=1,
    )
    if n == 0:
        block2, n = re.subn(
            r'(?m)^            poster_url=.*?,$',
            '            poster_url=poster_url,',
            block,
            count=1,
        )
    if n != 1:
        raise RuntimeError("Plex poster_url Keyword konnte nicht eindeutig ersetzt werden")
    text = text[:start] + block2 + text[back:]
    return add_marker(text)


def main():
    plugin = sys.argv[1] if len(sys.argv) > 1 else PLUGIN_DEFAULT
    detail = os.path.join(plugin, DETAIL_REL)
    children = os.path.join(plugin, CHILD_REL)
    plex = os.path.join(plugin, PLEX_REL)
    episode = os.path.join(plugin, EPISODE_REL)

    for path in (detail, children, plex):
        if not os.path.isfile(path):
            raise SystemExit("Datei nicht gefunden: %s" % path)

    detail_old = read(detail)
    child_old = read(children)
    plex_old = read(plex)

    if MARKER in detail_old and MARKER in child_old and MARKER in plex_old and os.path.isfile(episode):
        print("PLEX_EPISODEUI3 bereits installiert")
        return

    detail_new = patch_detail(detail_old)
    child_new = patch_children(child_old)
    plex_new = patch_plex(plex_old)

    compile(NEW_EPISODE_BROWSER, episode, "exec")
    compile(detail_new, detail, "exec")
    compile(child_new, children, "exec")
    compile(plex_new, plex, "exec")

    detail_bak = backup(detail, ".before_episodeui3")
    child_bak = backup(children, ".before_episodeui3")
    plex_bak = backup(plex, ".before_episodeui3")
    episode_bak = backup(episode, ".before_episodeui3") if os.path.isfile(episode) else None

    write(detail, detail_new)
    write(children, child_new)
    write(plex, plex_new)
    write(episode, NEW_EPISODE_BROWSER)

    for path in (detail, children, plex, episode):
        compile(read(path), path, "exec")

    ev = read(episode)
    pv = read(plex)
    dv = read(detail)
    cv = read(children)
    checks = [
        (MARKER in ev, "EpisodeBrowser marker"),
        ("PAGE_SIZE = 10" in ev and "COLS = 5" in ev, "5x2 grid"),
        ("THUMB_W = 340" in ev and "THUMB_H = 191" in ev, "16:9 cards"),
        ("A-Z" not in ev, "kein A-Z"),
        ("S%02dE%02d" in ev, "SxxExx"),
        ("640,\n                360" in pv, "Plex 640x360"),
        ("PlexEpisodeBrowser" in dv, "MediaDetail route"),
        ("PlexEpisodeBrowser" in cv, "Children route"),
        (not re.search(r'(?m)^\s*self\.items\s*=', ev), "Screen.items Crashfix"),
    ]
    missing = [name for ok, name in checks if not ok]
    if missing:
        raise RuntimeError("EPISODEUI3 Verifikation fehlgeschlagen: %r" % missing)

    print("OK INFUSEMEDIA2026_PLEX_EPISODEUI3")
    print("- Staffelansicht ohne A-Z")
    print("- 5 x 2 Episoden pro Seite")
    print("- klare 16:9 Plex-Episodenbilder 640x360, nicht verzerrt")
    print("- SxxExx + Titel + Laufzeit")
    print("- Seite x / y oben rechts")
    print("- gelber Fokusrahmen")
    print("- Serien-/Staffelbrowser bleibt separat erhalten")
    print("- Screen.items Crashfix bleibt erhalten")
    print("- keine Login-/Token-/Serverdaten geaendert")
    print("- Detail Backup: %s" % detail_bak)
    print("- Children Backup: %s" % child_bak)
    print("- Plex Backup: %s" % plex_bak)
    if episode_bak:
        print("- Episode Backup: %s" % episode_bak)


if __name__ == "__main__":
    main()
