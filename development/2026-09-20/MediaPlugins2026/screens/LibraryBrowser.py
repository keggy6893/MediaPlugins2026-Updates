# MEDIAPLUGINS2026_LIBRARY_CINEMA_UI1
# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from enigma import ePoint, eTimer
from skin import parseColor
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap

import os

from ..config import config_store
from ..utils.image_cache import image_cache
from ..utils.dedupe import dedupe_items
from ..utils import log

PAGE_SIZE = 8
COLS = 4
MAX_LIBRARY_ITEMS = 3000
LETTERS = ["0-9"] + [chr(c) for c in range(ord("A"), ord("Z") + 1)]


# MEDIAPLUGINS2026_LIBRARY_AZ_FULLLOAD1
class LibraryBrowser(Screen):
    """r53: Posteransicht mit echter A-Z-Navigation und Detailbereich."""

    skinName = "MediaPlugins2026LibraryBrowser"
    skin = """
    <screen name="MediaPlugins2026LibraryBrowser" position="0,0" size="1920,1080"
            flags="wfNoBorder" backgroundColor="#03101a" title="Bibliothek">
        <widget name="cinema_bg" position="0,0" size="1920,1080" alphatest="blend" scale="1" zPosition="0" />

        <widget name="provider_icon" position="30,14" size="58,58" alphatest="blend" scale="1" zPosition="4" />
        <widget name="provider_mark" position="30,16" size="58,58" font="Regular;46"
                foregroundColor="#20c8f4" transparent="1" halign="center" valign="center" zPosition="4" />
        <widget name="header_provider" position="102,18" size="600,50" font="Regular;34"
                foregroundColor="#ffffff" transparent="1" zPosition="4" />
        <widget name="server_alias" position="102,59" size="600,27" font="Regular;17"
                foregroundColor="#20c8f4" transparent="1" zPosition="4" />
        <widget name="brand" position="1435,18" size="350,38" font="Regular;27"
                foregroundColor="#e4edf3" transparent="1" halign="right" zPosition="4" />
        <widget name="clock" position="1800,15" size="100,42" font="Regular;30"
                foregroundColor="#ffffff" transparent="1" halign="right" zPosition="4" />
        <widget name="brand_sub" position="1340,57" size="445,26" font="Regular;15"
                foregroundColor="#8599a7" transparent="1" halign="right" zPosition="4" />

        <widget name="title" position="78,86" size="560,55" font="Regular;38"
                foregroundColor="#ffffff" transparent="1" zPosition="4" />
        <widget name="count" position="645,96" size="300,35" font="Regular;22"
                foregroundColor="#aab9c4" transparent="1" zPosition="4" />
        <widget name="page" position="805,96" size="260,35" font="Regular;22"
                foregroundColor="#aab9c4" transparent="1" halign="right" zPosition="4" />

        <widget name="az" position="10,145" size="46,745" font="Regular;20"
                foregroundColor="#9aaab5" transparent="1" halign="center" valign="top" zPosition="4" />

        <widget name="poster0" position="78,150" size="210,315" alphatest="blend" scale="1" zPosition="2" />
        <widget name="poster1" position="318,150" size="210,315" alphatest="blend" scale="1" zPosition="2" />
        <widget name="poster2" position="558,150" size="210,315" alphatest="blend" scale="1" zPosition="2" />
        <widget name="poster3" position="798,150" size="210,315" alphatest="blend" scale="1" zPosition="2" />
        <widget name="poster4" position="78,535" size="210,315" alphatest="blend" scale="1" zPosition="2" />
        <widget name="poster5" position="318,535" size="210,315" alphatest="blend" scale="1" zPosition="2" />
        <widget name="poster6" position="558,535" size="210,315" alphatest="blend" scale="1" zPosition="2" />
        <widget name="poster7" position="798,535" size="210,315" alphatest="blend" scale="1" zPosition="2" />

        <widget name="title0" position="68,470" size="230,58" font="Regular;20" foregroundColor="#eef3f6" transparent="1" halign="center" valign="top" zPosition="4" />
        <widget name="title1" position="308,470" size="230,58" font="Regular;20" foregroundColor="#eef3f6" transparent="1" halign="center" valign="top" zPosition="4" />
        <widget name="title2" position="548,470" size="230,58" font="Regular;20" foregroundColor="#eef3f6" transparent="1" halign="center" valign="top" zPosition="4" />
        <widget name="title3" position="788,470" size="230,58" font="Regular;20" foregroundColor="#eef3f6" transparent="1" halign="center" valign="top" zPosition="4" />
        <widget name="title4" position="68,855" size="230,58" font="Regular;20" foregroundColor="#eef3f6" transparent="1" halign="center" valign="top" zPosition="4" />
        <widget name="title5" position="308,855" size="230,58" font="Regular;20" foregroundColor="#eef3f6" transparent="1" halign="center" valign="top" zPosition="4" />
        <widget name="title6" position="548,855" size="230,58" font="Regular;20" foregroundColor="#eef3f6" transparent="1" halign="center" valign="top" zPosition="4" />
        <widget name="title7" position="788,855" size="230,58" font="Regular;20" foregroundColor="#eef3f6" transparent="1" halign="center" valign="top" zPosition="4" />

        <widget name="focus_top" position="72,144" size="222,5" backgroundColor="#20c8f4" transparent="0" zPosition="8" />
        <widget name="focus_bottom" position="72,465" size="222,5" backgroundColor="#20c8f4" transparent="0" zPosition="8" />
        <widget name="focus_left" position="72,144" size="5,326" backgroundColor="#20c8f4" transparent="0" zPosition="8" />
        <widget name="focus_right" position="289,144" size="5,326" backgroundColor="#20c8f4" transparent="0" zPosition="8" />

        <widget name="detail_bg" position="1058,112" size="820,800" backgroundColor="#071723" transparent="0" zPosition="1" />
        <widget name="detail_border_top" position="1058,112" size="820,2" backgroundColor="#173f55" transparent="0" zPosition="5" />
        <widget name="detail_border_bottom" position="1058,910" size="820,2" backgroundColor="#173f55" transparent="0" zPosition="5" />
        <widget name="detail_border_left" position="1058,112" size="2,800" backgroundColor="#173f55" transparent="0" zPosition="5" />
        <widget name="detail_border_right" position="1876,112" size="2,800" backgroundColor="#173f55" transparent="0" zPosition="5" />

        <widget name="detail_poster" position="1076,132" size="330,495" alphatest="blend" scale="1" zPosition="3" />
        <widget name="detail_title" position="1438,140" size="410,98" font="Regular;32" foregroundColor="#ffffff" transparent="1" zPosition="4" />
        <widget name="detail_meta" position="1438,245" size="410,44" font="Regular;21" foregroundColor="#b8c6d0" transparent="1" zPosition="4" />
        <widget name="detail_genres" position="1438,290" size="410,50" font="Regular;21" foregroundColor="#b8c6d0" transparent="1" zPosition="4" />
        <widget name="detail_rating" position="1438,340" size="410,42" font="Regular;23" foregroundColor="#f2c94c" transparent="1" zPosition="4" />
        <widget name="overview" position="1438,392" size="410,235" font="Regular;21" foregroundColor="#d2dbe1" transparent="1" zPosition="4" />
        <widget name="tech" position="1076,642" size="772,46" font="Regular;22" foregroundColor="#dbe6ec" backgroundColor="#0b2231" transparent="0" valign="center" zPosition="4" />

        <widget name="similar_label" position="1076,704" size="300,36" font="Regular;24" foregroundColor="#ffffff" transparent="1" zPosition="4" />
        <widget name="similar0" position="1076,748" size="132,150" alphatest="blend" scale="1" zPosition="4" />
        <widget name="similar1" position="1224,748" size="132,150" alphatest="blend" scale="1" zPosition="4" />
        <widget name="similar2" position="1372,748" size="132,150" alphatest="blend" scale="1" zPosition="4" />
        <widget name="similar3" position="1520,748" size="132,150" alphatest="blend" scale="1" zPosition="4" />
        <widget name="similar4" position="1668,748" size="132,150" alphatest="blend" scale="1" zPosition="4" />

        <widget name="similar_focus_top" position="1070,742" size="144,5"
                backgroundColor="#20c8f4" transparent="0" zPosition="9" />
        <widget name="similar_focus_bottom" position="1070,899" size="144,5"
                backgroundColor="#20c8f4" transparent="0" zPosition="9" />
        <widget name="similar_focus_left" position="1070,742" size="5,162"
                backgroundColor="#20c8f4" transparent="0" zPosition="9" />
        <widget name="similar_focus_right" position="1209,742" size="5,162"
                backgroundColor="#20c8f4" transparent="0" zPosition="9" />

        <widget name="key_red_box" position="48,985" size="34,34" backgroundColor="#ef3340" transparent="0" zPosition="4" />
        <widget name="key_red" position="94,980" size="130,42" font="Regular;22" foregroundColor="#ffffff" transparent="1" valign="center" zPosition="4" />
        <widget name="key_green_box" position="285,985" size="34,34" backgroundColor="#19c979" transparent="0" zPosition="4" />
        <widget name="key_green" position="331,980" size="130,42" font="Regular;22" foregroundColor="#ffffff" transparent="1" valign="center" zPosition="4" />
        <widget name="key_yellow_box" position="540,985" size="34,34" backgroundColor="#f0c51d" transparent="0" zPosition="4" />
        <widget name="key_yellow" position="586,980" size="150,42" font="Regular;22" foregroundColor="#ffffff" transparent="1" valign="center" zPosition="4" />
        <widget name="key_blue_box" position="790,985" size="34,34" backgroundColor="#26a7ef" transparent="0" zPosition="4" />
        <widget name="key_blue" position="836,980" size="150,42" font="Regular;22" foregroundColor="#ffffff" transparent="1" valign="center" zPosition="4" />
        <widget name="hint" position="1450,980" size="390,42" font="Regular;21" foregroundColor="#9aabb6" transparent="1" valign="center" halign="right" zPosition="4" />
    </screen>
    """
    POSTER_POS = [
        (78,150), (318,150), (558,150), (798,150),
        (78,535), (318,535), (558,535), (798,535),
    ]

    def __init__(self, session, server_name, library_id, library_title, client=None):
        Screen.__init__(self, session)
        self.server_name = server_name
        self.library_id = library_id
        self.library_title = library_title
        self.client = client or self._createClient()

        self["cinema_bg"] = Pixmap()
        self["provider_icon"] = Pixmap()
        self["provider_mark"] = Label("◆")
        self["header_provider"] = Label("")
        self["server_alias"] = Label("")
        self["brand"] = Label("Media Plugins 2026")
        self["clock"] = Label("")
        self["brand_sub"] = Label(_("Filme. Serien. Musik. Alles in einer Oberfläche."))
        self["title"] = Label(library_title)
        self["az"] = Label("")
        self["detail_bg"] = Label("")
        self["detail_border_top"] = Label("")
        self["detail_border_bottom"] = Label("")
        self["detail_border_left"] = Label("")
        self["detail_border_right"] = Label("")
        self["detail_poster"] = Pixmap()
        self["detail_title"] = Label("")
        self["detail_meta"] = Label("")
        self["detail_genres"] = Label("")
        self["detail_rating"] = Label("")
        self["tech"] = Label("")
        self["overview"] = Label("")
        self["similar_label"] = Label(_("Ähnliche Titel"))
        for i in range(5):
            self["similar%d" % i] = Pixmap()
        for name in (
            "similar_focus_top", "similar_focus_bottom",
            "similar_focus_left", "similar_focus_right",
        ):
            self[name] = Label("")
        self["count"] = Label("")
        self["page"] = Label("")
        # r66: farbige Tasten-Legende statt reinem Fliesstext.
        self["key_red_box"] = Label("")
        self["key_green_box"] = Label("")
        self["key_yellow_box"] = Label("")
        self["key_blue_box"] = Label("")
        self["key_red"] = Label(_("Zurück"))
        self["key_green"] = Label(_("Öffnen"))
        self["key_yellow"] = Label(_("Details"))
        self["key_blue"] = Label(_("Favorit"))
        self["hint"] = Label(_("◀ A-Z   ▶ Ähnliche Titel"))

        for name in ("focus_top","focus_bottom","focus_left","focus_right"):
            self[name] = Label("")
        for i in range(PAGE_SIZE):
            self["poster%d" % i] = Pixmap()
            self["title%d" % i] = Label("")

        self.all_media = []
        self.filtered_media = []
        self.media_items = []
        self.start_index = 0
        self.total_count = 0
        self.selected = 0
        self.focus_area = "grid"
        self.az_index = 0
        self.active_letter = None
        self._closing = False
        self._child_open = False
        self._image_request = 0
        self._detail_request = 0
        self._similar_request = 0
        self._similar_items = []
        self._similar_selected = 0
        self._similar_origin_selected = 0
        self._server_display_request = 0
        # MEDIAPLUGINS2026_LIBRARY_SERVER_AZ1
        self._library_request = 0
        self._library_total_count = 0

        self._clock_timer = eTimer()
        self._clock_timer.callback.append(self._updateClock)
        self._detail_timer = eTimer()
        self._detail_timer.callback.append(self._loadSelectedDetail)

        self["actions"] = ActionMap(
            ["OkCancelActions","DirectionActions","ColorActions"],
            {
                "ok": self.keyOpen, "cancel": self.keyCancel,
                "up": self.keyUp, "down": self.keyDown,
                "left": self.keyLeft, "right": self.keyRight,
                "red": self.keyCancel, "green": self.keyOpen,
                "yellow": self.keyOpen, "blue": self.keyToggleFavorite,
            }, -2
        )
        self.onClose.append(self._onClose)
        self.onLayoutFinish.append(self._applyCinemaBrand)
        self.onLayoutFinish.append(self._startClock)
        self.onLayoutFinish.append(self._renderAz)
        self.onLayoutFinish.append(self.loadLibrary)

    # MEDIAPLUGINS2026_LIBRARY_CINEMA_UI1
    def _providerInfo(self):
        cfg = next(
            (s for s in config_store.get_servers() if s.name == self.server_name),
            None,
        )
        protocol = (getattr(cfg, "protocol", "") or "").strip().lower() if cfg else ""
        names = {
            "emby": "Emby",
            "jellyfin": "Jellyfin",
            "plex": "Plex",
        }
        return protocol, names.get(protocol, self.server_name or "Medienserver")

    # MEDIAPLUGINS2026_SERVER_ALIAS_LABELS1_LIBRARY
    def _applyCinemaBrand(self):
        protocol, provider_name = self._providerInfo()
        self["header_provider"].setText("%s – Bibliothek" % provider_name)

        self["server_alias"].setText(_("Server: wird ermittelt …"))
        self._resolveActiveServerDisplayName()

        try:
            root = os.path.dirname(os.path.dirname(__file__))
            bg = os.path.join(root, "skin", "library_theme", "library_browser_bg.jpg")
            if os.path.isfile(bg) and self["cinema_bg"].instance:
                self["cinema_bg"].instance.setScale(1)
                self["cinema_bg"].instance.setPixmapFromFile(bg)
                self["cinema_bg"].show()
        except Exception:
            pass

        try:
            root = os.path.dirname(os.path.dirname(__file__))
            icon = os.path.join(root, "skin", "icons", "provider_%s.png" % protocol)
            if protocol and os.path.isfile(icon) and self["provider_icon"].instance:
                self["provider_icon"].instance.setScale(1)
                self["provider_icon"].instance.setPixmapFromFile(icon)
                self["provider_icon"].show()
                self["provider_mark"].hide()
            else:
                self["provider_icon"].hide()
                self["provider_mark"].show()
        except Exception:
            try:
                self["provider_icon"].hide()
                self["provider_mark"].show()
            except Exception:
                pass

    # MEDIAPLUGINS2026_REMOTE_SERVERNAME1_LIBRARY
    def _resolveActiveServerDisplayName(self):
        self._server_display_request += 1
        request = self._server_display_request

        getter = getattr(self.client, "get_server_display_name", None)
        if not callable(getter):
            self._onActiveServerDisplayNameError(
                "Displayname-API nicht verfügbar",
                request,
            )
            return

        try:
            getter(
                lambda name, req=request:
                    self._onActiveServerDisplayName(name, req),
                lambda err, req=request:
                    self._onActiveServerDisplayNameError(err, req),
            )
        except Exception as exc:
            self._onActiveServerDisplayNameError(str(exc), request)

    def _onActiveServerDisplayName(self, display_name, request):
        if self._closing or request != self._server_display_request:
            return
        display_name = str(display_name or "").strip()
        if not display_name:
            self._onActiveServerDisplayNameError(
                "leerer Servername",
                request,
            )
            return
        self["server_alias"].setText(_("Server: %s") % display_name)

    def _onActiveServerDisplayNameError(self, err, request):
        if self._closing or request != self._server_display_request:
            return
        fallback = str(self.server_name or "").strip()
        if fallback:
            self["server_alias"].setText(_("Server: %s") % fallback)
        else:
            self["server_alias"].setText(_("Server: Unbekannt"))
        log.debug(
            "LibraryBrowser Servername nicht lesbar (%s): %s",
            self.server_name,
            err,
        )

    def _startClock(self):
        self._updateClock()
        try:
            self._clock_timer.start(30000, False)
        except Exception:
            pass

    def _updateClock(self):
        if self._closing:
            return
        try:
            import time
            self["clock"].setText(time.strftime("%H:%M"))
        except Exception:
            pass

    def _clearSimilar(self):
        self._similar_request += 1
        self._similar_items = []
        self._similar_selected = 0
        self._showSimilarFocus(False)
        for i in range(5):
            try:
                self["similar%d" % i].hide()
            except Exception:
                pass

    # MEDIAPLUGINS2026_LIBRARY_SIMILAR_PROVIDER1
    # MEDIAPLUGINS2026_LIBRARY_SIMILAR_NAV1
    def _showSimilarFocus(self, visible):
        for name in (
            "similar_focus_top", "similar_focus_bottom",
            "similar_focus_left", "similar_focus_right",
        ):
            try:
                self[name].show() if visible else self[name].hide()
            except Exception:
                pass

    def _updateSimilarFocus(self):
        if self.focus_area != "similar" or not self._similar_items:
            self._showSimilarFocus(False)
            return

        positions = (
            (1076, 748), (1224, 748), (1372, 748),
            (1520, 748), (1668, 748),
        )
        self._similar_selected = max(
            0, min(self._similar_selected, len(self._similar_items) - 1)
        )
        x, y = positions[self._similar_selected]
        self._showSimilarFocus(True)
        try:
            self["similar_focus_top"].instance.move(ePoint(x - 6, y - 6))
            self["similar_focus_bottom"].instance.move(ePoint(x - 6, y + 151))
            self["similar_focus_left"].instance.move(ePoint(x - 6, y - 6))
            self["similar_focus_right"].instance.move(ePoint(x + 133, y - 6))
        except Exception:
            pass

    def _enterSimilar(self):
        if not self._similar_items:
            return False
        self._similar_origin_selected = self.selected
        self._similar_selected = 0
        self.focus_area = "similar"
        self._updateFocus()
        return True

    def _leaveSimilar(self):
        self.focus_area = "grid"
        if self.media_items:
            self.selected = max(
                0, min(self._similar_origin_selected, len(self.media_items) - 1)
            )
        self._updateFocus()
        self._scheduleDetail()

    def _renderSimilar(self, selected_item):
        self._similar_request += 1
        request = self._similar_request
        self._similar_items = []
        self._similar_selected = 0
        self._showSimilarFocus(False)

        for i in range(5):
            try:
                self["similar%d" % i].hide()
            except Exception:
                pass

        if selected_item is None:
            return

        selected_id = str(getattr(selected_item, "id", "") or "")
        if not selected_id:
            self._renderSimilarFallback(selected_item, request, [])
            return

        getter = getattr(self.client, "get_similar_items", None)
        if not callable(getter):
            self._renderSimilarFallback(selected_item, request, [])
            return

        try:
            getter(
                selected_id,
                lambda items, req=request, current_id=selected_id:
                    self._onSimilarProviderLoaded(items, req, current_id),
                lambda err, req=request, target=selected_item:
                    self._onSimilarProviderError(err, target, req),
                limit=5,
            )
        except Exception as exc:
            log.debug("LibraryBrowser Similar Provider Start fehlgeschlagen: %s", exc)
            self._renderSimilarFallback(selected_item, request, [])

    def _onSimilarProviderLoaded(self, items, request, selected_id):
        if self._closing or request != self._similar_request:
            return

        current = self._current()
        if current is None or str(getattr(current, "id", "") or "") != selected_id:
            return

        clean = []
        seen = set([selected_id])
        for item in list(items or []):
            iid = str(getattr(item, "id", "") or "")
            if not iid or iid in seen or not getattr(item, "poster_url", None):
                continue
            seen.add(iid)
            clean.append(item)
            if len(clean) >= 5:
                break

        if len(clean) < 5:
            self._renderSimilarFallback(current, request, clean)
            return

        self._renderSimilarItems(clean[:5], request)

    def _onSimilarProviderError(self, err, selected_item, request):
        if self._closing or request != self._similar_request:
            return
        log.debug("LibraryBrowser Similar Provider fehlgeschlagen: %s", err)
        self._renderSimilarFallback(selected_item, request, [])

    def _renderSimilarFallback(self, selected_item, request, prefix):
        if self._closing or request != self._similar_request:
            return

        selected_id = str(getattr(selected_item, "id", "") or "")
        selected_year = int(getattr(selected_item, "year", 0) or 0)
        selected_genres = set(
            str(x).strip().lower()
            for x in (getattr(selected_item, "genres", None) or [])
            if str(x).strip()
        )

        used = set(
            str(getattr(x, "id", "") or "")
            for x in list(prefix or [])
        )
        used.add(selected_id)

        scored = []
        for index, candidate in enumerate(self.all_media):
            iid = str(getattr(candidate, "id", "") or "")
            if not iid or iid in used or not getattr(candidate, "poster_url", None):
                continue

            genres = set(
                str(x).strip().lower()
                for x in (getattr(candidate, "genres", None) or [])
                if str(x).strip()
            )
            overlap = len(selected_genres.intersection(genres))

            year = int(getattr(candidate, "year", 0) or 0)
            year_distance = abs(selected_year - year) if selected_year and year else 9999
            id_mix = sum(ord(ch) for ch in (selected_id + iid)) % 997

            score = (
                overlap * 100000
                - min(year_distance, 100) * 100
                - id_mix
                - (index % 31)
            )
            scored.append((score, candidate))

        scored.sort(key=lambda pair: pair[0], reverse=True)

        combined = list(prefix or [])
        for _score, candidate in scored:
            iid = str(getattr(candidate, "id", "") or "")
            if iid in used:
                continue
            used.add(iid)
            combined.append(candidate)
            if len(combined) >= 5:
                break

        self._renderSimilarItems(combined[:5], request)

    def _renderSimilarItems(self, candidates, request):
        if self._closing or request != self._similar_request:
            return

        self._similar_items = [
            candidate
            for candidate in list(candidates or [])[:5]
            if getattr(candidate, "poster_url", None)
        ]
        if self._similar_selected >= len(self._similar_items):
            self._similar_selected = 0

        for pos, candidate in enumerate(self._similar_items):
            url = getattr(candidate, "poster_url", None)
            item_id = getattr(candidate, "id", None)
            path = image_cache.get_local_path(url)
            if path:
                self._showSimilar(pos, path, request, item_id)
            else:
                image_cache.fetch(
                    url,
                    lambda p, slot=pos, req=request, iid=item_id:
                        self._showSimilar(slot, p, req, iid),
                    lambda err: None,
                )

        if self.focus_area == "similar":
            if self._similar_items:
                self._updateSimilarFocus()
            else:
                self._leaveSimilar()

    def _showSimilar(self, pos, path, request, item_id):
        if self._closing or request != self._similar_request:
            return
        try:
            if not path or not os.path.isfile(path):
                return
            widget = self["similar%d" % pos]
            if widget.instance:
                widget.instance.setScale(1)
                widget.instance.setPixmapFromFile(path)
                widget.show()
        except Exception as exc:
            log.debug("LibraryBrowser Cinema Similar %d: %s", pos, exc)

    def _renderAz(self):
        lines = []
        active = LETTERS[self.az_index] if self.focus_area == "az" else None
        for letter in LETTERS:
            if letter == active:
                lines.append("▶ " + letter)
            else:
                lines.append("  " + letter)
        self["az"].setText("\n".join(lines))
        try:
            if self.focus_area == "az":
                self["az"].instance.setForegroundColor(parseColor("#20c8f4"))
            else:
                self["az"].instance.setForegroundColor(parseColor("#a8abb0"))
        except Exception:
            pass

    def _createClient(self):
        cfg = next((s for s in config_store.get_servers() if s.name == self.server_name), None)
        if not cfg:
            return None
        from ..backends.factory import create_client_for_server
        return create_client_for_server(cfg)

    def loadLibrary(self):
        if not self.client:
            self["detail_title"].setText(_("Server nicht gefunden"))
            return
        log.info("LibraryBrowser SERVER_AZ1: lade Bibliothek %s", self.library_id)
        if getattr(self.client,"token",None) and getattr(self.client,"user_id",None):
            self._fetchAll()
        else:
            self.client.login(
                lambda token,uid: self._fetchAll(),
                lambda err: self["detail_title"].setText(_("Verbindungsfehler: %s") % err)
            )

    # MEDIAPLUGINS2026_LIBRARY_SERVER_AZ1
    def _usesServerPaging(self):
        protocol, _provider_name = self._providerInfo()
        return protocol in ("emby", "jellyfin")

    def _fetchAll(self):
        # Emby/Jellyfin: nur die sichtbare Seite laden. Bei sehr grossen
        # Bibliotheken verhindert das das alte harte 3000er-Limit.
        if self._usesServerPaging():
            self.active_letter = None
            self.start_index = 0
            self._requestServerPage(0, None)
            return
        self._fetchAllLegacy()

    def _fetchAllLegacy(self):
        # Plex bleibt absichtlich auf dem bisherigen, bewaehrten Pfad.
        page_size = 300
        collected = []
        expected_total = [None]
        seen_pages = set()

        def finish():
            if self._closing:
                return
            total = expected_total[0]
            if total is None:
                total = len(collected)
            self._onLibraryLoaded(collected[:MAX_LIBRARY_ITEMS], total)

        def failed(err):
            if self._closing:
                return
            if collected:
                log.warning("LibraryBrowser Legacy Paging nach %d Titeln abgebrochen: %s", len(collected), err)
                finish()
            else:
                self._onFetchError(err)

        def page_loaded(start_index, media, server_total):
            if self._closing:
                return
            page = list(media or [])
            if expected_total[0] is None:
                try:
                    expected_total[0] = int(server_total or 0)
                except Exception:
                    expected_total[0] = 0
            first_id = str(getattr(page[0], "id", "")) if page else ""
            last_id = str(getattr(page[-1], "id", "")) if page else ""
            signature = (len(page), first_id, last_id)
            if page and signature in seen_pages:
                log.warning("LibraryBrowser Legacy Paging: wiederholte Seite bei StartIndex=%d; Abbruch nach %d Titeln", start_index, len(collected))
                finish()
                return
            if page:
                seen_pages.add(signature)
                collected.extend(page)
            target = min(int(expected_total[0] or len(collected)), MAX_LIBRARY_ITEMS)
            if not page or len(collected) >= target:
                finish()
                return
            next_index = start_index + len(page)
            if next_index <= start_index:
                finish()
                return
            fetch_page(next_index)

        def fetch_page(start_index):
            if self._closing:
                return
            remaining = MAX_LIBRARY_ITEMS - len(collected)
            if remaining <= 0:
                finish()
                return
            self.client.get_items(
                self.library_id,
                lambda media, total, start=start_index: page_loaded(start, media, total),
                failed,
                start_index=start_index,
                limit=min(page_size, remaining),
                sort_by="SortName",
            )

        fetch_page(0)

    def _requestServerPage(self, start_index, letter=None, select_last=False):
        if self._closing:
            return
        self._library_request += 1
        request = self._library_request
        try:
            start_index = max(0, int(start_index or 0))
        except Exception:
            start_index = 0

        self.active_letter = letter
        self.start_index = start_index

        kwargs = {}
        if letter == "0-9":
            # Emby stellt NameLessThan offiziell bereit. Damit bleibt der
            # Sonderzeichen/Ziffern-Bucket klein, ohne 28k Titel zu laden.
            kwargs["name_less_than"] = "A"
        elif letter:
            kwargs["name_starts_with"] = letter

        log.info(
            "LibraryBrowser SERVER_AZ1: Start=%d Limit=%d Buchstabe=%s",
            start_index, PAGE_SIZE, letter or "ALLE"
        )

        self.client.get_items(
            self.library_id,
            lambda media, total, req=request, target_letter=letter, last=select_last:
                self._onServerPageLoaded(media, total, req, target_letter, last),
            lambda err, req=request: self._onServerPageError(err, req),
            start_index=start_index,
            limit=PAGE_SIZE,
            sort_by="SortName",
            **kwargs
        )

    def _onServerPageLoaded(self, media, server_total, request, letter, select_last=False):
        if self._closing or request != self._library_request:
            return

        unique, duplicates = dedupe_items(media)
        try:
            query_total = int(server_total or 0)
        except Exception:
            query_total = len(unique)

        if letter is None:
            self._library_total_count = query_total

        self.active_letter = letter
        self.total_count = query_total
        self.media_items = list(unique)
        # Provider-Similar ist primaer. Der lokale Similar-Fallback darf bei
        # Server-Paging bewusst nur die aktuell geladene Seite verwenden.
        self.all_media = list(unique)
        self.filtered_media = list(unique)
        self.selected = max(0, len(self.media_items) - 1) if (select_last and self.media_items) else 0

        log.info(
            "LibraryBrowser SERVER_AZ1: Buchstabe=%s Server=%d Seite=%d Dubletten=%d",
            letter or "ALLE", query_total, len(self.media_items), duplicates
        )
        self._showServerPage()
        self._updateFocus()
        if self.focus_area == "grid":
            self._scheduleDetail()

    def _onServerPageError(self, err, request):
        if self._closing or request != self._library_request:
            return
        log.error("LibraryBrowser SERVER_AZ1: Laden fehlgeschlagen: %s", err)
        self["detail_title"].setText(_("Fehler beim Laden: %s") % err)

    def _showServerPage(self):
        shown_total = self._library_total_count
        if shown_total <= 0 and self.active_letter is None:
            shown_total = self.total_count

        if self.active_letter:
            self["count"].setText(
                _("%d Einträge • %s: %d")
                % (shown_total, self.active_letter, self.total_count)
            )
        else:
            self["count"].setText(_("%d Einträge") % shown_total)

        if self.total_count <= 0 or not self.media_items:
            self["page"].setText(_("Seite 0/0"))
            self._clearDetail()
        else:
            pages = max(1, (self.total_count + PAGE_SIZE - 1) // PAGE_SIZE)
            page_no = min(pages, (self.start_index // PAGE_SIZE) + 1)
            self["page"].setText(_("Seite %d/%d") % (page_no, pages))
        self._renderPage()

    def _onLibraryLoaded(self, media, server_total):
        if self._closing:
            return
        unique, duplicates = dedupe_items(media)

        self.all_media = unique
        log.info("LibraryBrowser r53: Server=%d, eindeutig=%d, Dubletten=%d",
                 int(server_total or len(media or [])), len(unique), duplicates)
        self.active_letter = None
        self.start_index = 0
        self.filtered_media = list(self.all_media)
        self._showLocalPage()

    def _onFetchError(self, err):
        if not self._closing:
            log.error("LibraryBrowser r53: Laden fehlgeschlagen: %s", err)
            self["detail_title"].setText(_("Fehler beim Laden: %s") % err)

    def _matchesLetter(self, item, letter):
        title = (getattr(item, "title", "") or "").strip()
        if not title:
            return False
        first = title[0].upper()
        if letter == "0-9":
            return first.isdigit()
        return first == letter

    def _applyLetterFilter(self):
        letter = LETTERS[self.az_index]
        if self._usesServerPaging():
            self.active_letter = letter
            self.start_index = 0
            self.selected = 0
            self._requestServerPage(0, letter)
            return

        self.active_letter = letter
        self.filtered_media = [x for x in self.all_media if self._matchesLetter(x, letter)]
        self.start_index = 0
        self.selected = 0
        self._showLocalPage()

    def _showLocalPage(self):
        if self._usesServerPaging():
            self._showServerPage()
            return

        source = self.filtered_media if self.active_letter else self.all_media
        self.total_count = len(source)
        self.media_items = source[self.start_index:self.start_index + PAGE_SIZE]
        self.selected = 0
        shown_total = len(self.all_media)
        if self.active_letter:
            self["count"].setText(_("%d Einträge • %s: %d") % (shown_total, self.active_letter, self.total_count))
        else:
            self["count"].setText(_("%d Einträge") % shown_total)
        if self.total_count <= 0:
            self["page"].setText(_("Seite 0/0"))
            self._clearDetail()
        else:
            pages = max(1, (self.total_count + PAGE_SIZE - 1) // PAGE_SIZE)
            page_no = min(pages, (self.start_index // PAGE_SIZE) + 1)
            self["page"].setText(_("Seite %d/%d") % (page_no, pages))
        self._renderPage()

    @staticmethod
    def _buildLabel(item):
        title = getattr(item, "title", "") or ""
        year = getattr(item, "year", None)
        # r56: Herz-Kennzeichen fuer serverseitig markierte Favoriten.
        heart = "♥ " if getattr(item, "is_favorite", False) else ""
        return heart + title + (("\n(%s)" % year) if year else "")

    def _refreshTitleLabels(self):
        """Nur die Titel-Labels aktualisieren (z.B. nach Favoriten-Toggle),
        ohne die Poster erneut anzufordern."""
        for i, item in enumerate(self.media_items):
            self["title%d" % i].setText(self._buildLabel(item))

    def _renderPage(self):
        self._image_request += 1
        rid = self._image_request

        for i in range(PAGE_SIZE):
            self["title%d" % i].setText("")
            try:
                self["poster%d" % i].hide()
            except Exception:
                pass

        for i, item in enumerate(self.media_items):
            self["title%d" % i].setText(self._buildLabel(item))

            url = getattr(item, "poster_url", None)
            item_id = getattr(item, "id", None)
            if not url:
                continue

            cached = image_cache.get_local_path(url)
            if cached:
                self._showPoster(i, cached, rid, item_id)
                continue

            # r52: alle Poster der Seite sofort anfordern statt nacheinander
            # ueber eine eigene Warteschlange mit Zwischenpausen. image_cache
            # bringt bereits eine eigene, auf mehrere parallele Downloads
            # begrenzte Warteschlange mit (siehe utils/image_cache.py) - die
            # zusaetzliche Serialisierung hier sorgte dafuer, dass 8 Poster
            # nacheinander statt in parallelen Wellen geladen wurden und die
            # Seite spuerbar langsam wirkte.
            self._fetchPoster(i, url, rid, item_id, 0)

        self._updateFocus()
        self._scheduleDetail()

    def _fetchPoster(self, pos, url, rid, item_id, attempt):
        image_cache.fetch(
            url,
            lambda path, p=pos, u=url, r=rid, iid=item_id, a=attempt:
                self._posterFetched(p, u, r, iid, a, path),
            lambda err, p=pos, u=url, r=rid, iid=item_id, a=attempt:
                self._posterFetchError(p, u, r, iid, a, err)
        )

    def _showPoster(self, pos, path, rid, item_id=None):
        if self._closing or rid != self._image_request:
            return False
        if not (0 <= pos < len(self.media_items)):
            return False

        current_id = getattr(self.media_items[pos], "id", None)
        if item_id is not None and current_id != item_id:
            log.debug("LibraryBrowser r53: veraltetes Poster ignoriert pos=%d", pos)
            return False

        try:
            import os
            if not path or not os.path.isfile(path) or os.path.getsize(path) < 128:
                return False

            w = self["poster%d" % pos]
            if w.instance:
                w.instance.setScale(1)
                w.instance.setPixmapFromFile(path)
                w.show()
                return True
        except Exception as e:
            log.warning("LibraryBrowser r53 Poster %d konnte nicht angezeigt werden: %s", pos, e)
        return False

    def _posterFetched(self, pos, url, rid, item_id, attempt, path):
        if self._closing or rid != self._image_request:
            return

        ok = self._showPoster(pos, path, rid, item_id)
        if not ok and attempt < 1:
            log.warning("LibraryBrowser r53: Poster Retry %d fuer %s", pos, item_id)
            self._fetchPoster(pos, url, rid, item_id, attempt + 1)

    def _posterFetchError(self, pos, url, rid, item_id, attempt, err):
        if self._closing or rid != self._image_request:
            return

        if attempt < 1:
            log.warning("LibraryBrowser r53: Poster-Download Retry %d: %s", pos, err)
            self._fetchPoster(pos, url, rid, item_id, attempt + 1)
        else:
            log.warning("LibraryBrowser r53: Poster-Download fehlgeschlagen %d: %s", pos, err)

    def _current(self):
        if 0 <= self.selected < len(self.media_items):
            return self.media_items[self.selected]
        return None

    def _showGridFocus(self, visible):
        for name in ("focus_top","focus_bottom","focus_left","focus_right"):
            try:
                self[name].show() if visible else self[name].hide()
            except Exception:
                pass

    def _updateFocus(self):
        if self.focus_area == "az":
            self._showGridFocus(False)
            self._showSimilarFocus(False)
            self._renderAz()
            return

        if self.focus_area == "similar":
            self._showGridFocus(False)
            self._renderAz()
            self._updateSimilarFocus()
            return

        self._showSimilarFocus(False)
        self._renderAz()
        if not self.media_items:
            self._showGridFocus(False)
            return
        self._showGridFocus(True)
        x,y = self.POSTER_POS[self.selected]
        try:
            self["focus_top"].instance.move(ePoint(x-6,y-6))
            self["focus_bottom"].instance.move(ePoint(x-6,y+315))
            self["focus_left"].instance.move(ePoint(x-6,y-6))
            self["focus_right"].instance.move(ePoint(x+211,y-6))
        except Exception:
            pass

    def _scheduleDetail(self):
        if self.focus_area != "grid":
            return
        try:
            self._detail_timer.stop()
        except Exception:
            pass
        self._detail_timer.start(220, True)

    def _loadSelectedDetail(self):
        if self._closing or self.focus_area != "grid":
            return
        item = self._current()
        if not item:
            self._clearDetail()
            return

        # Show the data already available immediately.
        self._renderDetail(item)

        if getattr(item, "_infuse_detail_loaded", False):
            return

        self._detail_request += 1
        request = self._detail_request
        item_id = getattr(item, "id", None)
        if not item_id:
            return

        self.client.get_item_detail(
            item_id,
            lambda detail, rid=request, target=item: self._onDetailLoaded(detail, rid, target),
            lambda err, rid=request: self._onDetailError(err, rid)
        )

    def _onDetailLoaded(self, detail, request, target):
        if self._closing or request != self._detail_request:
            return
        try:
            target.update_from_detail(detail)
            target._infuse_detail_loaded = True
        except Exception as e:
            log.warning("LibraryBrowser r53: Detail-Update fehlgeschlagen: %s", e)
        if target is self._current():
            self._renderDetail(target)

    def _onDetailError(self, err, request):
        if not self._closing and request == self._detail_request:
            log.warning("LibraryBrowser r53: Detaildaten fehlgeschlagen: %s", err)

    def _formatDuration(self, ticks):
        seconds = int(int(ticks or 0) / 10000000)
        if seconds <= 0:
            return ""
        hours, rem = divmod(seconds, 3600)
        minutes = rem // 60
        if hours:
            return _("%d Std. %02d Min.") % (hours, minutes)
        return _("%d Min.") % minutes

    def _renderDetail(self,item):
        if not item:
            self._clearDetail()
            return
        title = getattr(item,"title","") or ""
        year = getattr(item,"year",None)
        self["detail_title"].setText(title + ((" (%s)" % year) if year else ""))

        resume = int(getattr(item,"resume_ticks",0) or 0)
        runtime = int(getattr(item,"runtime_ticks",0) or 0)
        pct = int(resume*100/runtime) if runtime > 0 and resume > 0 else 0
        duration = self._formatDuration(runtime)
        meta = [str(year) if year else "", duration, ("▶ %d%%" % pct) if pct else ""]
        self["detail_meta"].setText("  •  ".join(x for x in meta if x))

        genres = getattr(item,"genres",None) or []
        self["detail_genres"].setText("  •  ".join(genres[:4]))

        rating = getattr(item, "rating", None)
        if rating not in (None, "", 0):
            try:
                self["detail_rating"].setText("★ %.1f / 10" % float(rating))
            except Exception:
                self["detail_rating"].setText("★ %s" % rating)
        else:
            self["detail_rating"].setText("")

        height = int(getattr(item,"video_height",0) or 0)
        resolution = "2160p" if height >= 2160 else ("1080p" if height >= 1080 else ("720p" if height >= 720 else ""))
        vcodec = (getattr(item,"video_codec","") or "").upper()
        acodec = (getattr(item,"audio_codec","") or "").upper()
        channels = int(getattr(item,"audio_channels",0) or 0)
        ch = "7.1" if channels >= 8 else ("5.1" if channels >= 6 else ("2.0" if channels == 2 else ""))
        lang = (getattr(item,"audio_language","") or "").upper()
        tags = [x for x in (resolution,vcodec,acodec,ch,lang) if x]
        self["tech"].setText("  ".join("[%s]" % x for x in tags))
        self["overview"].setText(getattr(item,"overview","") or "")
        self._renderSimilar(item)

        url = getattr(item,"poster_url",None)
        if url:
            rid=self._image_request
            cached=image_cache.get_local_path(url)
            if cached:
                self._showDetailPoster(cached,rid)
            else:
                image_cache.fetch(
                    url,
                    lambda path,req=rid:self._showDetailPoster(path,req),
                    lambda err,req=rid:None
                )

    def _clearDetail(self):
        for name in ("detail_title","detail_meta","detail_genres","detail_rating","tech","overview"):
            self[name].setText("")
        self._clearSimilar()
        try:
            self["detail_poster"].hide()
        except Exception:
            pass

    def _showDetailPoster(self,path,rid):
        if self._closing or rid != self._image_request:
            return
        try:
            if self["detail_poster"].instance:
                self["detail_poster"].instance.setScale(1)
                self["detail_poster"].instance.setPixmapFromFile(path)
                self["detail_poster"].show()
        except Exception as e:
            log.warning("LibraryBrowser r53 Detailposter: %s", e)

    def _syncAzToCurrent(self):
        item = self._current()
        if not item:
            return
        title = (getattr(item, "title", "") or "").strip()
        if not title:
            return
        first = title[0].upper()
        target = "0-9" if first.isdigit() else first
        if target in LETTERS:
            self.az_index = LETTERS.index(target)

    def keyLeft(self):
        if self.focus_area == "similar":
            if self._similar_selected > 0:
                self._similar_selected -= 1
                self._updateSimilarFocus()
            else:
                self._leaveSimilar()
            return

        if self.focus_area == "az":
            return
        if self.selected % COLS > 0:
            self.selected -= 1
            self._updateFocus()
            self._scheduleDetail()
            return

        if self.start_index > 0:
            # SERVER_AZ1: bei Emby/Jellyfin die vorherige Seite direkt vom
            # Server holen; Plex behaelt das bisherige lokale Paging.
            previous = max(0, self.start_index - PAGE_SIZE)
            if self._usesServerPaging():
                self._requestServerPage(previous, self.active_letter, select_last=True)
            else:
                self.start_index = previous
                self._showLocalPage()
                self.selected = max(0, len(self.media_items) - 1)
                self._updateFocus()
                self._scheduleDetail()
            return

        # From the first poster column enter the A-Z bar.
        self._syncAzToCurrent()
        self.focus_area = "az"
        self._updateFocus()

    def keyRight(self):
        if self.focus_area == "similar":
            if self._similar_selected + 1 < len(self._similar_items):
                self._similar_selected += 1
                self._updateSimilarFocus()
                return

            # Hinter der letzten Empfehlung bleibt Seitenwechsel erreichbar.
            if self.start_index + PAGE_SIZE < self.total_count:
                self.focus_area = "grid"
                next_start = self.start_index + PAGE_SIZE
                if self._usesServerPaging():
                    self._requestServerPage(next_start, self.active_letter)
                else:
                    self.start_index = next_start
                    self.selected = 0
                    self._showLocalPage()
                    self._updateFocus()
                    self._scheduleDetail()
            return

        if self.focus_area == "az":
            self.focus_area = "grid"
            if not self.media_items:
                self.selected = 0
            self._updateFocus()
            self._scheduleDetail()
            return

        if self.selected % COLS < COLS-1 and self.selected+1 < len(self.media_items):
            self.selected += 1
            self._updateFocus()
            self._scheduleDetail()
            return

        # Rechte Grid-Kante -> Empfehlungen.
        if self._enterSimilar():
            return

        if self.start_index + PAGE_SIZE < self.total_count:
            next_start = self.start_index + PAGE_SIZE
            if self._usesServerPaging():
                self._requestServerPage(next_start, self.active_letter)
            else:
                self.start_index = next_start
                self.selected = 0
                self._showLocalPage()
                self._updateFocus()
                self._scheduleDetail()

    def keyUp(self):
        if self.focus_area == "similar":
            self._leaveSimilar()
            return

        if self.focus_area == "az":
            self.az_index = (self.az_index - 1) % len(LETTERS)
            self._applyLetterFilter()
            self.focus_area = "az"
            self._updateFocus()
            return
        if self.selected >= COLS:
            self.selected -= COLS
            self._updateFocus()
            self._scheduleDetail()

    def keyDown(self):
        if self.focus_area == "similar":
            return

        if self.focus_area == "az":
            self.az_index = (self.az_index + 1) % len(LETTERS)
            self._applyLetterFilter()
            self.focus_area = "az"
            self._updateFocus()
            return
        if self.selected + COLS < len(self.media_items):
            self.selected += COLS
            self._updateFocus()
            self._scheduleDetail()

    def keyOpen(self):
        if self.focus_area == "az":
            # Up/Down startet bei SERVER_AZ1 bereits die passende
            # Serverabfrage. OK wechselt deshalb nur noch ins Grid, sofern
            # derselbe Buchstabe aktiv ist; sonst wird genau einmal geladen.
            letter = LETTERS[self.az_index]
            if (not self._usesServerPaging()) or self.active_letter != letter:
                self._applyLetterFilter()
            self.focus_area = "grid"
            self._updateFocus()
            self._scheduleDetail()
            return

        if self._child_open:
            return

        if self.focus_area == "similar":
            if not self._similar_items:
                return
            item = self._similar_items[self._similar_selected]
        else:
            item = self._current()

        if not item:
            return

        from .MediaDetail import MediaDetail
        self._child_open=True
        try:
            child=self.session.open(MediaDetail,item,self.client)
            child.onClose.append(self._childClosed)
        except Exception as e:
            self._child_open=False
            log.exception("LibraryBrowser r53 Detailfehler: %s",e)

    def _childClosed(self,*args):
        self._child_open=False

    def keyToggleFavorite(self):
        if self.focus_area != "grid":
            return
        item=self._current()
        if not item:
            return
        # r56: Favoritenstatus direkt auf dem Server setzen/entfernen
        # (Jellyfin/Emby FavoriteItems-API) statt nur lokal auf der Box -
        # damit er auch in anderen Clients (Web, Infuse, Apps) sichtbar ist.
        new_state = not getattr(item, "is_favorite", False)
        item.is_favorite = new_state
        self.client.set_favorite(item.id, new_state)
        self._refreshTitleLabels()

    def keyCancel(self):
        if self._closing or self._child_open:
            return
        self._closing=True
        self._image_request += 1
        self._detail_request += 1
        self._similar_request += 1
        self._server_display_request += 1
        self._similar_items = []
        self._showSimilarFocus(False)
        try:
            self._clock_timer.stop()
        except Exception:
            pass
        try:
            self._detail_timer.stop()
        except Exception:
            pass
        try:
            self["actions"].setEnabled(False)
        except Exception:
            pass
        self.close()

    def _onClose(self):
        self._closing=True
        self._image_request += 1
        self._detail_request += 1
        self._similar_request += 1
        self._server_display_request += 1
        self._similar_items = []
        self._showSimilarFocus(False)
        try:
            self._clock_timer.stop()
        except Exception:
            pass
        try:
            self._detail_timer.stop()
        except Exception:
            pass
