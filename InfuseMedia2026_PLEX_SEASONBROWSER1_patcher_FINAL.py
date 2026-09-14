# -*- coding: utf-8 -*-
from __future__ import print_function

import io, os, re, shutil, sys

PLUGIN_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026"
MEDIA_REL = "backends/media_item.py"
PLEX_REL = "backends/plex_client.py"
DETAIL_REL = "screens/MediaDetail.py"
BROWSER_REL = "screens/PlexChildrenBrowser.py"
MARKER = "# INFUSEMEDIA2026_PLEX_SEASONBROWSER1"
NEW_BROWSER = '# -*- coding: utf-8 -*-\n# INFUSEMEDIA2026_PLEX_SEASONBROWSER1\n\nfrom Screens.Screen import Screen\nfrom Components.ActionMap import ActionMap\nfrom Components.Label import Label\nfrom Components.MenuList import MenuList\n\nfrom ..utils import log\n\n\nclass PlexChildrenBrowser(Screen):\n    skinName = "InfuseMedia2026PlexChildrenBrowser"\n    skin = """\n    <screen name="InfuseMedia2026PlexChildrenBrowser" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="#07131d">\n        <widget name="header_bg" position="0,0" size="1920,66" backgroundColor="#07131d" />\n        <widget name="brand1" position="44,15" size="112,40" font="Regular;29" foregroundColor="#ffffff" transparent="1" text="Infuse" />\n        <widget name="brand2" position="158,15" size="150,40" font="Regular;29" foregroundColor="#47badd" transparent="1" text="Media2026" />\n        <widget name="header_sep" position="317,15" size="20,40" font="Regular;27" foregroundColor="#78909c" transparent="1" text="|" />\n        <widget name="header_title" position="347,15" size="500,40" font="Regular;27" foregroundColor="#ffffff" transparent="1" />\n        <widget name="title" position="90,120" size="1500,60" font="Regular;42" foregroundColor="#ffffff" transparent="1" />\n        <widget name="subtitle" position="90,184" size="1500,38" font="Regular;24" foregroundColor="#8fa9b8" transparent="1" />\n        <widget name="list" position="90,260" size="1740,650" font="Regular;29" itemHeight="64" scrollbarMode="showOnDemand" />\n        <widget name="status" position="90,930" size="1000,40" font="Regular;22" foregroundColor="#8fa0a8" transparent="1" />\n        <widget name="key_red" position="100,1025" size="300,35" font="Regular;21" foregroundColor="#e75b55" transparent="1" text="■  Zurück" />\n        <widget name="key_ok" position="760,1025" size="400,35" font="Regular;21" foregroundColor="#32c7ec" transparent="1" halign="center" text="OK  Öffnen" />\n    </screen>\n    """\n\n    def __init__(self, session, parent_item, client):\n        Screen.__init__(self, session)\n        self.session = session\n        self.parent_item = parent_item\n        self.client = client\n        self.items = []\n        self._child_open = False\n        self["header_bg"] = Label("")\n        self["brand1"] = Label("Infuse")\n        self["brand2"] = Label("Media2026")\n        self["header_sep"] = Label("|")\n        self["header_title"] = Label("Plex")\n        self["title"] = Label(self._heading())\n        self["subtitle"] = Label(self._subtitle())\n        self["list"] = MenuList([])\n        self["status"] = Label("Lade …")\n        self["key_red"] = Label("■  Zurück")\n        self["key_ok"] = Label("OK  Öffnen")\n        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {\n            "ok": self.keyOpen, "cancel": self.close, "red": self.close, "green": self.keyOpen,\n        }, -1)\n        self.onLayoutFinish.append(self._load)\n\n    def _type(self, item):\n        kind = str(getattr(item, "media_type", "") or "").strip().lower()\n        if kind:\n            return kind\n        if getattr(item, "season_number", None) is not None and getattr(item, "episode_number", None) is None and not getattr(item, "stream_url", ""):\n            return "season"\n        return ""\n\n    def _heading(self):\n        if self._type(self.parent_item) == "season":\n            return getattr(self.parent_item, "series_name", "") or self.parent_item.title\n        return self.parent_item.title\n\n    def _subtitle(self):\n        kind = self._type(self.parent_item)\n        if kind == "season":\n            number = getattr(self.parent_item, "season_number", None)\n            return ("Staffel %d · Episoden" % int(number)) if number is not None else "Episoden"\n        if kind == "show":\n            return "Staffeln"\n        return ""\n\n    @staticmethod\n    def _runtime_text(item):\n        ticks = int(getattr(item, "runtime_ticks", 0) or 0)\n        if ticks <= 0:\n            return ""\n        minutes = int(ticks // 10000000 // 60)\n        return "%d Min." % minutes if minutes else ""\n\n    def _row_text(self, item):\n        kind = self._type(item)\n        if kind == "season":\n            number = getattr(item, "season_number", None)\n            prefix = ("Staffel %d" % int(number)) if number is not None else "Staffel"\n            title = getattr(item, "title", "") or ""\n            if title.lower().startswith("season ") or title.lower().startswith("staffel "):\n                return prefix\n            return "%s   %s" % (prefix, title)\n        season = getattr(item, "season_number", None)\n        episode = getattr(item, "episode_number", None)\n        prefix = ""\n        if episode is not None:\n            prefix = ("S%02dE%02d" % (int(season), int(episode))) if season is not None else ("E%02d" % int(episode))\n        bits = [x for x in (prefix, getattr(item, "title", "") or "", self._runtime_text(item)) if x]\n        return "   ".join(bits)\n\n    def _load(self):\n        self["status"].setText("Lade Plex-Inhalte …")\n        self.client.get_children(self.parent_item.id, lambda items: log.safe_call(self._onLoaded, items), lambda err: log.safe_call(self._onError, err))\n\n    def _onLoaded(self, items):\n        self.items = list(items or [])\n        self.items.sort(key=lambda x: (int(getattr(x, "season_number", 0) or 0), int(getattr(x, "episode_number", 0) or 0), str(getattr(x, "title", "") or "").casefold()))\n        self["list"].setList([self._row_text(item) for item in self.items])\n        self["status"].setText(("%d Einträge" % len(self.items)) if self.items else "Keine Einträge gefunden")\n\n    def _onError(self, err):\n        self.items = []\n        self["list"].setList([])\n        self["status"].setText("Plex-Fehler: %s" % err)\n\n    def _selected(self):\n        idx = self["list"].getSelectedIndex()\n        return self.items[idx] if 0 <= idx < len(self.items) else None\n\n    def keyOpen(self):\n        if self._child_open:\n            return\n        item = self._selected()\n        if item is None:\n            return\n        kind = self._type(item)\n        self._child_open = True\n        try:\n            if kind in ("show", "season"):\n                child = self.session.open(PlexChildrenBrowser, item, self.client)\n            else:\n                from .MediaDetail import MediaDetail\n                child = self.session.open(MediaDetail, item, self.client)\n            child.onClose.append(self._childClosed)\n        except Exception as exc:\n            self._child_open = False\n            log.exception("PlexChildrenBrowser: Öffnen fehlgeschlagen: %s", exc)\n\n    def _childClosed(self, *args):\n        self._child_open = False\n'
DETAIL_HELPERS = '    # INFUSEMEDIA2026_PLEX_SEASONBROWSER1\n    def _mediaType(self):\n        kind = str(getattr(self.item, "media_type", "") or "").strip().lower()\n        if kind:\n            return kind\n        if self.client.__class__.__name__ == "PlexClient":\n            if getattr(self.item, "season_number", None) is not None and getattr(self.item, "episode_number", None) is None and not getattr(self.item, "stream_url", ""):\n                return "season"\n        return ""\n\n    def _isContainerItem(self):\n        return self.client.__class__.__name__ == "PlexClient" and self._mediaType() in ("show", "season")\n\n    def _containerDisplay(self):\n        kind = self._mediaType()\n        if kind == "season":\n            title = getattr(self.item, "series_name", "") or self.item.title\n            number = getattr(self.item, "season_number", None)\n            subtitle = ("Staffel %d" % int(number)) if number is not None else self.item.title\n            return title, subtitle\n        return self.item.title, (str(self.item.year) if self.item.year else "")\n\n    def _applyContainerMode(self):\n        if not self._isContainerItem():\n            for name in ("progress", "resume", "duration", "last_seen"):\n                try:\n                    self[name].show()\n                except Exception:\n                    pass\n            return False\n        title, subtitle = self._containerDisplay()\n        self["title"].setText(title)\n        self["year"].setText(subtitle)\n        self["quality"].setText("")\n        self["key_green"].setText("")\n        self["key_yellow"].setText("")\n        self["key_blue"].setText("")\n        self["key_ok"].setText("OK  Episoden anzeigen" if self._mediaType() == "season" else "OK  Staffeln anzeigen")\n        for name in ("progress", "resume", "duration", "last_seen"):\n            try:\n                self[name].hide()\n            except Exception:\n                try:\n                    self[name].setText("")\n                except Exception:\n                    pass\n        try:\n            self["progress"].setValue(0)\n        except Exception:\n            pass\n        return True\n\n    def _openChildren(self):\n        if not self._isContainerItem():\n            return False\n        try:\n            from .PlexChildrenBrowser import PlexChildrenBrowser\n            self.session.open(PlexChildrenBrowser, self.item, self.client)\n        except Exception as exc:\n            log.exception("Plex Staffel-/Serienbrowser konnte nicht geöffnet werden: %s", exc)\n            from Screens.MessageBox import MessageBox\n            self.session.open(MessageBox, "Plex-Inhalte konnten nicht geöffnet werden.", MessageBox.TYPE_ERROR)\n        return True\n'
PLEX_NORMALIZE = '        # INFUSEMEDIA2026_PLEX_SEASONBROWSER1\n        media_type = str(a.get("type") or "").strip().lower()\n        if media_type == "season":\n            series_name = a.get("parentTitle") or a.get("grandparentTitle") or series_name or ""\n            try:\n                season_number = int(a.get("index")) if a.get("index") else season_number\n            except Exception:\n                pass\n            episode_number = None\n        elif media_type == "episode":\n            series_name = a.get("grandparentTitle") or a.get("parentTitle") or series_name or ""\n\n'
PLEX_CHILDREN = '    def get_children(self, item_id, callback, error_callback, limit=500):\n        url = ("%s/library/metadata/%s/children?X-Plex-Container-Start=0&X-Plex-Container-Size=%d" % (self._build_base_url(), quote(str(item_id)), int(limit)))\n\n        def done(data):\n            try:\n                root = self._parse_xml(data)\n                callback(self._items_from_root(root))\n            except Exception as exc:\n                error_callback(str(exc))\n\n        self._get(url, done, error_callback)\n\n'


def read(path):
    with io.open(path, "r", encoding="utf-8") as h:
        return h.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as h:
        h.write(text)


def backup(path, suffix):
    target = path + suffix
    if not os.path.exists(target):
        shutil.copy2(path, target)
    return target


def patch_media_item(text):
    if MARKER in text:
        return text
    old = '                 video_type="", container=""):'
    if old in text:
        text = text.replace(old, '                 video_type="", container="", media_type=""):', 1)
    elif 'media_type=""' not in text:
        raise RuntimeError("MediaItem Signatur nicht erkannt")
    anchor = '        self.container = container or ""\n'
    if 'self.media_type = media_type or ""' not in text:
        if anchor not in text:
            raise RuntimeError("MediaItem container-Anker fehlt")
        text = text.replace(anchor, anchor + '        self.media_type = media_type or ""\n', 1)
    anchor2 = '        detail_container = getattr(detail_item, "container", "") or ""\n'
    if 'detail_media_type = getattr(detail_item, "media_type"' not in text:
        if anchor2 not in text:
            raise RuntimeError("MediaItem Detail-Anker fehlt")
        text = text.replace(anchor2, anchor2 + '        detail_media_type = getattr(detail_item, "media_type", "") or ""\n        if detail_media_type:\n            self.media_type = detail_media_type\n', 1)
    first, rest = text.split("\n", 1)
    return first + "\n" + MARKER + "\n" + rest


def patch_plex(text):
    if MARKER in text:
        return text
    anchor = '        item = MediaItem(\n'
    if anchor not in text:
        raise RuntimeError("Plex MediaItem-Anker fehlt")
    text = text.replace(anchor, PLEX_NORMALIZE + anchor, 1)
    if '            media_type=media_type,\n' not in text:
        va = '            video_type="VideoFile",\n'
        if va not in text:
            raise RuntimeError("Plex video_type-Anker fehlt")
        text = text.replace(va, '            media_type=media_type,\n' + va, 1)
    item_start = text.index(anchor)
    item_end = text.index('        )\n', item_start)
    if 'parent_id=' not in text[item_start:item_end]:
        ra = '            runtime_ticks=duration_ms * 10000,\n'
        if ra in text:
            text = text.replace(ra, ra + '            parent_id=a.get("parentRatingKey") or a.get("grandparentRatingKey") or "",\n', 1)
    if '    def get_children(self, item_id, callback, error_callback' not in text:
        ga = '    def get_item_by_id(self, item_id, callback, error_callback):\n'
        if ga not in text:
            raise RuntimeError("Plex get_item_by_id-Anker fehlt")
        text = text.replace(ga, PLEX_CHILDREN + ga, 1)
    first, rest = text.split("\n", 1)
    return first + "\n" + MARKER + "\n" + rest


def patch_detail(text):
    if MARKER in text:
        return text
    old = '        self._updateFavoriteLabel()\n        self._updatePlaybackLabels()\n\n    @staticmethod\n'
    new = '        self._updateFavoriteLabel()\n        self._updatePlaybackLabels()\n        if not self._isContainerItem():\n            self["title"].setText(self.item.title)\n            self["year"].setText(str(self.item.year) if self.item.year else "")\n\n    @staticmethod\n'
    if old not in text:
        raise RuntimeError("MediaDetail Detail-Refresh-Anker fehlt")
    text = text.replace(old, new, 1)
    fa = '    @staticmethod\n    def _formatResume(ticks):\n'
    if fa not in text:
        raise RuntimeError("MediaDetail _formatResume-Anker fehlt")
    text = text.replace(fa, DETAIL_HELPERS + "\n" + fa, 1)
    ua = '    def _updatePlaybackLabels(self):\n        resume_ticks = int(getattr(self.item, "resume_ticks", 0) or 0)\n'
    if ua not in text:
        raise RuntimeError("MediaDetail PlaybackLabel-Anker fehlt")
    text = text.replace(ua, '    def _updatePlaybackLabels(self):\n        if self._applyContainerMode():\n            return\n\n        resume_ticks = int(getattr(self.item, "resume_ticks", 0) or 0)\n', 1)
    pa = '    def keyPlay(self):\n        try:\n'
    if pa not in text:
        raise RuntimeError("MediaDetail keyPlay-Anker fehlt")
    text = text.replace(pa, '    def keyPlay(self):\n        if self._openChildren():\n            return\n        try:\n', 1)
    sa = '    def keyPlayFromStart(self):\n        try:\n'
    if sa not in text:
        raise RuntimeError("MediaDetail keyPlayFromStart-Anker fehlt")
    text = text.replace(sa, '    def keyPlayFromStart(self):\n        if self._openChildren():\n            return\n        try:\n', 1)
    ya = '    def keyYellow(self):\n        if self.actionbar_active:\n            return\n'
    if ya in text:
        text = text.replace(ya, '    def keyYellow(self):\n        if self.actionbar_active or self._isContainerItem():\n            return\n', 1)
    oa = '    def keyOptions(self):\n        if self.actionbar_active:\n'
    if oa not in text:
        raise RuntimeError("MediaDetail keyOptions-Anker fehlt")
    text = text.replace(oa, '    def keyOptions(self):\n        if self._isContainerItem():\n            return\n        if self.actionbar_active:\n', 1)
    ta = '    def keyToggleFavorite(self):\n        if self.client.__class__.__name__ == "PlexClient":\n'
    if ta not in text:
        raise RuntimeError("MediaDetail keyToggleFavorite-Anker fehlt")
    text = text.replace(ta, '    def keyToggleFavorite(self):\n        if self._isContainerItem():\n            return\n        if self.client.__class__.__name__ == "PlexClient":\n', 1)
    first, rest = text.split("\n", 1)
    return first + "\n" + MARKER + "\n" + rest


def main():
    plugin = sys.argv[1] if len(sys.argv) > 1 else PLUGIN_DEFAULT
    media_path = os.path.join(plugin, MEDIA_REL)
    plex_path = os.path.join(plugin, PLEX_REL)
    detail_path = os.path.join(plugin, DETAIL_REL)
    browser_path = os.path.join(plugin, BROWSER_REL)
    for path in (media_path, plex_path, detail_path):
        if not os.path.isfile(path):
            raise SystemExit("Datei nicht gefunden: %s" % path)
    mo, po, do = read(media_path), read(plex_path), read(detail_path)
    if MARKER in mo and MARKER in po and MARKER in do and os.path.isfile(browser_path):
        print("PLEX_SEASONBROWSER1 bereits installiert")
        return
    mn, pn, dn = patch_media_item(mo), patch_plex(po), patch_detail(do)
    compile(mn, media_path, "exec")
    compile(pn, plex_path, "exec")
    compile(dn, detail_path, "exec")
    compile(NEW_BROWSER, browser_path, "exec")
    mb = backup(media_path, ".before_seasonbrowser1")
    pb = backup(plex_path, ".before_seasonbrowser1")
    db = backup(detail_path, ".before_seasonbrowser1")
    bb = backup(browser_path, ".before_seasonbrowser1") if os.path.isfile(browser_path) else None
    write(media_path, mn); write(plex_path, pn); write(detail_path, dn); write(browser_path, NEW_BROWSER)
    for path in (media_path, plex_path, detail_path, browser_path):
        compile(read(path), path, "exec")
    pv, dv, mv = read(plex_path), read(detail_path), read(media_path)
    checks = [
        (MARKER in mv, "MediaItem marker"),
        ("self.media_type = media_type" in mv, "MediaItem media_type"),
        ("def get_children(self, item_id" in pv, "Plex get_children"),
        ("media_type=media_type" in pv, "Plex media_type"),
        ("def _isContainerItem(self):" in dv, "Detail container"),
        ("OK  Episoden anzeigen" in dv, "Detail episodes"),
        ("PlexChildrenBrowser" in dv, "Detail browser"),
    ]
    missing = [n for ok,n in checks if not ok]
    if missing:
        raise RuntimeError("Verifikation fehlgeschlagen: %r" % missing)
    print("OK INFUSEMEDIA2026_PLEX_SEASONBROWSER1")
    print("- Plex season/show werden als Container erkannt")
    print("- Detail zeigt Serienname + Staffel statt nur Season 1")
    print("- Staffel: OK -> Episoden anzeigen, kein Playback-Versuch")
    print("- Serie: OK -> Staffeln anzeigen")
    print("- Episodenbrowser nutzt /library/metadata/<id>/children")
    print("- Episode/Film -> bestehende Detailseite + Player")
    print("- keine Server-/Login-/Token-Daten geaendert")
    print("- MediaItem Backup: %s" % mb)
    print("- Plex Backup: %s" % pb)
    print("- Detail Backup: %s" % db)
    if bb:
        print("- Browser Backup: %s" % bb)


if __name__ == "__main__":
    main()
