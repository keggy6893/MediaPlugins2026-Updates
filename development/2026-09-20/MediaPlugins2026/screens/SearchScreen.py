# -*- coding: utf-8 -*-
# MEDIAPLUGINS2026_SEARCH_AVAILWIDTH1
# INFUSEMEDIA2026_SEARCH_DESCRIPTIONFIT1
# INFUSEMEDIA2026_SEARCH_ENRICH_HISTORY1
# INFUSEMEDIA2026_SEARCH_ZORDER1
# INFUSEMEDIA2026_SEARCH_LABELFIX1
# INFUSEMEDIA2026_SEARCH_DISNEY1
from __future__ import print_function

import json
import os
from datetime import datetime

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Tools.LoadPixmap import LoadPixmap
from enigma import eTimer

from ..config import config_store
from ..utils.image_cache import image_cache
from ..utils.dedupe import normalize_title, provider_key
from ..utils import log


SEARCH_DEBOUNCE_MS = 350
MIN_QUERY_LENGTH = 2
RESULT_COLUMNS = 6
RESULT_VISIBLE_ROWS = 2
RESULT_VISIBLE_COUNT = RESULT_COLUMNS * RESULT_VISIBLE_ROWS

# INFUSEMEDIA2026_SEARCH_ENRICH_HISTORY1
SEARCH_HISTORY_FILE = "/etc/enigma2/mediaplugins2026_unified_search_history.json"
LEGACY_SEARCH_HISTORY_FILE = "/etc/enigma2/infusemedia2026_search_history.json"
SEARCH_HISTORY_MAX = 10
DETAIL_DEBOUNCE_MS = 320

_PROVIDER_ORDER = {"emby": 0, "jellyfin": 1, "plex": 2}
_PROVIDER_NAMES = {"emby": "Emby", "jellyfin": "Jellyfin", "plex": "Plex"}


def _keyboard_layout():
    return [
        ["A", "B", "C", "D", "E", "F"],
        ["G", "H", "I", "J", "K", "L"],
        ["M", "N", "O", "P", "Q", "R"],
        ["S", "T", "U", "V", "W", "X"],
        ["Y", "Z", "0", "1", "2", "3"],
        ["4", "5", "6", "7", "8", "9"],
        ["Ä", "Ö", "Ü", "ß", "<-", "SPACE"],
    ]


_KEYBOARD = _keyboard_layout()
_KEYBOARD_FLAT = [key for row in _KEYBOARD for key in row]


def _build_skin():
    out = [
        '<screen name="MediaPlugins2026SearchDisney1" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="#06131d">',

        # Header
        '<widget name="brand1" position="42,19" size="215,42" font="Regular;29" foregroundColor="#ffffff" transparent="1" text="Media Plugins" />',
        '<widget name="brand2" position="263,19" size="82,42" font="Regular;29" foregroundColor="#47badd" transparent="1" text="2026" />',
        '<widget name="tagline" position="42,62" size="410,27" font="Regular;16" foregroundColor="#8ea1ad" transparent="1" text="Eine App. Alle deine Medien." />',
        '<widget name="date" position="1505,16" size="360,28" font="Regular;19" foregroundColor="#8fcbe0" transparent="1" halign="right" />',
        '<widget name="clock" position="1715,44" size="150,36" font="Regular;30" foregroundColor="#ffffff" transparent="1" halign="right" />',
        '<widget name="slogan" position="1430,82" size="435,28" font="Regular;18" foregroundColor="#47badd" transparent="1" halign="right" text="Filme. Serien. Überall. Zuhause." />',

        # Left search/keyboard panel
        '<widget name="left_panel" position="28,112" size="490,658" backgroundColor="#081923" />',
        '<widget name="search_title" position="48,130" size="410,40" font="Regular;29" foregroundColor="#ffffff" transparent="1" text="Suche" zPosition="20" />',
        '<widget name="query_border" position="47,177" size="423,59" backgroundColor="#33c7eb" />',
        '<widget name="query_box" position="50,180" size="417,53" backgroundColor="#0d2330" />',
        '<widget name="query_input" position="66,188" size="360,38" font="Regular;30" foregroundColor="#ffffff" transparent="1" />',
        '<widget name="query_clear" position="430,188" size="28,36" font="Regular;25" foregroundColor="#9db0bc" transparent="1" halign="center" text="×" />',
        '<widget name="status" position="49,241" size="420,31" font="Regular;18" foregroundColor="#8fa0aa" transparent="1" />',
    ]

    key_w, key_h = 60, 52
    key_x0, key_y0 = 49, 286
    x_step, y_step = 69, 62
    for idx, key in enumerate(_KEYBOARD_FLAT):
        row, col = divmod(idx, 6)
        x = key_x0 + col * x_step
        y = key_y0 + row * y_step
        out += [
            '<widget name="key_focus_%d" position="%d,%d" size="%d,%d" backgroundColor="#35c9ee" zPosition="2" />' %
            (idx, x - 3, y - 3, key_w + 6, key_h + 6),
            '<widget name="key_%d" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#ffffff" backgroundColor="#102532" halign="center" valign="center" zPosition="3" />' %
            (idx, x, y, key_w, key_h, 17 if key == "SPACE" else 24),
        ]

    # Right results panel + filter strip
    out += [
        '<widget name="results_panel" position="536,112" size="1356,658" backgroundColor="#081923" />',
        '<widget name="results_title" position="558,130" size="760,40" font="Regular;28" foregroundColor="#ffffff" transparent="1" />',
        '<widget name="result_count" position="1570,132" size="290,34" font="Regular;19" foregroundColor="#55c8e7" transparent="1" halign="right" />',

        '<widget name="filter_all" position="559,174" size="130,39" font="Regular;19" foregroundColor="#ffffff" backgroundColor="#102532" halign="center" valign="center" />',
        '<widget name="filter_movies" position="699,174" size="140,39" font="Regular;19" foregroundColor="#cbd7de" backgroundColor="#102532" halign="center" valign="center" />',
        '<widget name="filter_series" position="849,174" size="140,39" font="Regular;19" foregroundColor="#cbd7de" backgroundColor="#102532" halign="center" valign="center" />',
        '<widget name="filter_line_all" position="559,211" size="130,4" backgroundColor="#5adcf6" />',
        '<widget name="filter_line_movies" position="699,211" size="140,4" backgroundColor="#5adcf6" />',
        '<widget name="filter_line_series" position="849,211" size="140,4" backgroundColor="#5adcf6" />',

        '<widget name="legend_title" position="1380,179" size="125,28" font="Regular;17" foregroundColor="#aebcc5" transparent="1" text="Verfügbar bei:" zPosition="20" />',
        '<widget name="legend_emby_dot" position="1510,185" size="13,13" backgroundColor="#37d67a" />',
        '<widget name="legend_emby" position="1530,177" size="75,28" font="Regular;17" foregroundColor="#37d67a" transparent="1" text="Emby" zPosition="20" />',
        '<widget name="legend_jelly_dot" position="1610,185" size="13,13" backgroundColor="#3aa7ff" />',
        '<widget name="legend_jelly" position="1630,177" size="90,28" font="Regular;17" foregroundColor="#3aa7ff" transparent="1" text="Jellyfin" zPosition="20" />',
        '<widget name="legend_plex_dot" position="1730,185" size="13,13" backgroundColor="#f5b82e" />',
        '<widget name="legend_plex" position="1750,177" size="70,28" font="Regular;17" foregroundColor="#f5b82e" transparent="1" text="Plex" zPosition="20" />',
    ]

    # SEARCH_ENRICH_HISTORY1: Verlauf belegt den Ergebnisbereich nur,
    # solange noch kein neuer Suchbegriff eingegeben wurde.
    history_x0, history_y0 = 575, 240
    for hidx in range(SEARCH_HISTORY_MAX):
        hcol = hidx // 5
        hrow = hidx % 5
        hx = history_x0 + hcol * 620
        hy = history_y0 + hrow * 82
        out += [
            '<widget name="history_focus_%d" position="%d,%d" size="560,58" backgroundColor="#35c9ee" zPosition="5" />' %
            (hidx, hx - 3, hy - 3),
            '<widget name="history_%d" position="%d,%d" size="554,52" font="Regular;22" foregroundColor="#ffffff" backgroundColor="#102532" valign="center" zPosition="6" />' %
            (hidx, hx, hy),
        ]

    grid_x0, grid_y0 = 552, 232
    card_w, card_h = 216, 258
    poster_w, poster_h = 158, 196
    col_step, row_step = 220, 264
    for slot in range(RESULT_VISIBLE_COUNT):
        row, col = divmod(slot, RESULT_COLUMNS)
        x = grid_x0 + col * col_step
        y = grid_y0 + row * row_step
        px = x + 26
        py = y
        # focus border made of four thin labels
        out += [
            '<widget name="rf_top_%d" position="%d,%d" size="%d,3" backgroundColor="#35d1f5" zPosition="4" />' %
            (slot, px - 3, py - 3, poster_w + 6),
            '<widget name="rf_bottom_%d" position="%d,%d" size="%d,3" backgroundColor="#35d1f5" zPosition="4" />' %
            (slot, px - 3, py + poster_h, poster_w + 6),
            '<widget name="rf_left_%d" position="%d,%d" size="3,%d" backgroundColor="#35d1f5" zPosition="4" />' %
            (slot, px - 3, py - 3, poster_h + 6),
            '<widget name="rf_right_%d" position="%d,%d" size="3,%d" backgroundColor="#35d1f5" zPosition="4" />' %
            (slot, px + poster_w, py - 3, poster_h + 6),
            '<widget name="result_poster_%d" position="%d,%d" size="%d,%d" alphatest="blend" scale="1" zPosition="3" />' %
            (slot, px, py, poster_w, poster_h),
            '<widget name="result_title_%d" position="%d,%d" size="205,29" font="Regular;17" foregroundColor="#ffffff" transparent="1" />' %
            (slot, x + 2, y + 202),
            '<widget name="result_meta_%d" position="%d,%d" size="205,24" font="Regular;15" foregroundColor="#91a2ad" transparent="1" />' %
            (slot, x + 2, y + 229),
            '<widget name="result_emby_%d" position="%d,%d" size="12,12" backgroundColor="#37d67a" />' %
            (slot, x + 4, y + 251),
            '<widget name="result_jelly_%d" position="%d,%d" size="12,12" backgroundColor="#3aa7ff" />' %
            (slot, x + 24, y + 251),
            '<widget name="result_plex_%d" position="%d,%d" size="12,12" backgroundColor="#f5b82e" />' %
            (slot, x + 44, y + 251),
        ]

    # Bottom detail preview
    out += [
        '<widget name="preview_border" position="28,790" size="1864,224" backgroundColor="#36cbed" />',
        '<widget name="preview_panel" position="31,793" size="1858,218" backgroundColor="#081923" />',
        '<widget name="preview_poster" position="45,805" size="112,168" alphatest="blend" scale="1" zPosition="4" />',
        '<widget name="preview_title" position="180,803" size="790,39" font="Regular;29" foregroundColor="#ffffff" transparent="1" />',
        '<widget name="preview_meta" position="180,843" size="790,30" font="Regular;19" foregroundColor="#5ecbea" transparent="1" />',
        '<widget name="preview_overview" position="180,876" size="790,92" font="Regular;18" foregroundColor="#dce5ea" transparent="1" />',
        '<widget name="preview_badges" position="180,974" size="790,27" font="Regular;17" foregroundColor="#e8c558" transparent="1" />',

        '<widget name="availability_sep" position="1002,814" size="2,176" backgroundColor="#294451" />',
        '<widget name="availability_title" position="1030,806" size="260,32" font="Regular;23" foregroundColor="#ffffff" transparent="1" text="Verfügbar bei" zPosition="20" />',

        '<widget name="avail_emby_dot" position="1034,852" size="15,15" backgroundColor="#37d67a" />',
        '<widget name="avail_emby_name" position="1060,843" size="120,34" font="Regular;20" foregroundColor="#37d67a" transparent="1" text="Emby" zPosition="20" />',
        '<widget name="avail_emby_status" position="1160,843" size="280,34" font="Regular;17" foregroundColor="#aebbc3" transparent="1" halign="right" />',

        '<widget name="avail_jelly_dot" position="1034,892" size="15,15" backgroundColor="#3aa7ff" />',
        '<widget name="avail_jelly_name" position="1060,883" size="120,34" font="Regular;20" foregroundColor="#3aa7ff" transparent="1" text="Jellyfin" zPosition="20" />',
        '<widget name="avail_jelly_status" position="1160,883" size="280,34" font="Regular;17" foregroundColor="#aebbc3" transparent="1" halign="right" />',

        '<widget name="avail_plex_dot" position="1034,932" size="15,15" backgroundColor="#f5b82e" />',
        '<widget name="avail_plex_name" position="1060,923" size="120,34" font="Regular;20" foregroundColor="#f5b82e" transparent="1" text="Plex" zPosition="20" />',
        '<widget name="avail_plex_status" position="1160,923" size="280,34" font="Regular;17" foregroundColor="#aebbc3" transparent="1" halign="right" />',

        '<widget name="actions_sep" position="1460,814" size="2,176" backgroundColor="#294451" />',
        '<widget name="actions_title" position="1490,806" size="340,32" font="Regular;23" foregroundColor="#ffffff" transparent="1" text="Aktionen" zPosition="20" />',
        '<widget name="action_open" position="1490,850" size="350,32" font="Regular;19" foregroundColor="#dfe8ed" transparent="1" text="OK   Details öffnen" zPosition="20" />',
        '<widget name="action_keyboard" position="1490,890" size="350,32" font="Regular;19" foregroundColor="#dfe8ed" transparent="1" text="GELB   Zur Tastatur" zPosition="20" />',
        '<widget name="action_favorite" position="1490,930" size="350,32" font="Regular;19" foregroundColor="#dfe8ed" transparent="1" text="GRÜN   Favorit" zPosition="20" />',
        '<widget name="action_filter" position="1490,970" size="350,32" font="Regular;19" foregroundColor="#dfe8ed" transparent="1" text="BLAU   Alle / Filme / Serien" zPosition="20" />',

        # Footer
        '<widget name="key_red" position="42,1033" size="240,30" font="Regular;18" foregroundColor="#ee5a5c" transparent="1" text="■  Zurück" />',
        '<widget name="key_green" position="300,1033" size="240,30" font="Regular;18" foregroundColor="#55d67c" transparent="1" text="■  Favorit" />',
        '<widget name="key_yellow" position="555,1033" size="240,30" font="Regular;18" foregroundColor="#e5bd44" transparent="1" text="■  Tastatur" />',
        '<widget name="key_blue" position="810,1033" size="240,30" font="Regular;18" foregroundColor="#49aef0" transparent="1" text="■  Filter" />',
        '<widget name="footer_hint" position="1180,1033" size="700,30" font="Regular;17" foregroundColor="#8fa0aa" transparent="1" halign="right" text="Pfeile: Navigieren   OK: Zeichen / Öffnen" />',
        '</screen>',
    ]
    return "".join(out)


class SearchScreen(Screen):
    skinName = "MediaPlugins2026SearchDisney1"

    def __init__(self, session):
        self.skin = _build_skin()
        Screen.__init__(self, session)
        self.session = session
        self._closing = False

        # Search/runtime state
        self.query = ""
        self.clients = {}
        self.server_configs = {}
        self._client_protocol = {}
        self._login_state = {}
        self._login_requested = {}
        self._search_generation = 0
        self._raw_results = []
        self.results_all = []
        self.results_display = []
        self.pending_searches = 0
        self.search_filter = "all"

        # Navigation state
        self.focus_area = "keyboard"  # keyboard | results
        self.keyboard_index = 0
        self.result_index = 0
        self.result_offset = 0
        self._slot_items = [None] * RESULT_VISIBLE_COUNT
        self._render_token = 0

        # SEARCH_ENRICH_HISTORY1: lokale Suchhistorie.
        self.search_history = []
        self.history_index = 0

        # Detaildaten nur für den Treffer, auf dem der Fokus stehenbleibt.
        self._detail_cache = {}
        self._detail_failed = set()
        self._detail_inflight = {}
        self._detail_pending = None
        self._detail_serial = 0

        # INFUSEMEDIA2026_SEARCH_VERSIONS1_COMPAT
        # Weitere Versionen eines gruppierten Treffers werden erst nach dem
        # Fokus-Debounce nachgeladen, nicht fuer die komplette Trefferliste.
        self._variant_detail_inflight = set()

        # Static caches
        self._placeholder_path = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/skin/icons/poster_placeholder.png"
        try:
            self._placeholder_pix = LoadPixmap(self._placeholder_path)
        except Exception:
            self._placeholder_pix = None

        # Header and structural widgets
        for name, text in (
            ("brand1", "Media Plugins"),
            ("brand2", "2026"),
            ("tagline", "Eine App. Alle deine Medien."),
            ("slogan", "Filme. Serien. Überall. Zuhause."),
            ("search_title", "Suche"),
            ("query_clear", "×"),
            ("legend_title", "Verfügbar bei:"),
            ("legend_emby", "Emby"),
            ("legend_jelly", "Jellyfin"),
            ("legend_plex", "Plex"),
            ("availability_title", "Verfügbar bei"),
            ("avail_emby_name", "Emby"),
            ("avail_jelly_name", "Jellyfin"),
            ("avail_plex_name", "Plex"),
            ("actions_title", "Aktionen"),
            ("action_open", "OK   Details öffnen"),
            ("action_keyboard", "GELB   Zur Tastatur"),
            ("action_favorite", "GRÜN   Favorit"),
            ("action_filter", "BLAU   Alle / Filme / Serien"),
            ("key_red", "■  Zurück"),
            ("key_green", "■  Favorit"),
            ("key_yellow", "■  Tastatur"),
            ("key_blue", "■  Filter"),
            ("footer_hint", "Pfeile: Navigieren   OK: Zeichen / Öffnen"),
        ):
            self[name] = Label(text)

        for name in (
            "left_panel", "query_border", "query_box", "results_panel",
            "filter_line_all", "filter_line_movies", "filter_line_series",
            "legend_emby_dot", "legend_jelly_dot", "legend_plex_dot",
            "preview_border", "preview_panel", "availability_sep",
            "avail_emby_dot", "avail_jelly_dot", "avail_plex_dot", "actions_sep",
        ):
            self[name] = Label("")

        self["date"] = Label("")
        self["clock"] = Label("")
        self["query_input"] = Label("")
        self["status"] = Label("2+ Zeichen für Ergebnisse")
        self["results_title"] = Label("Ergebnisse")
        self["result_count"] = Label("")
        self["filter_all"] = Label("Alle (0)")
        self["filter_movies"] = Label("Filme (0)")
        self["filter_series"] = Label("Serien (0)")

        # Keyboard widgets
        for idx, key in enumerate(_KEYBOARD_FLAT):
            self["key_focus_%d" % idx] = Label("")
            display = "Leer" if key == "SPACE" else key
            self["key_%d" % idx] = Label(display)

        # Result slots
        for slot in range(RESULT_VISIBLE_COUNT):
            for edge in ("top", "bottom", "left", "right"):
                self["rf_%s_%d" % (edge, slot)] = Label("")
            self["result_poster_%d" % slot] = Pixmap()
            self["result_title_%d" % slot] = Label("")
            self["result_meta_%d" % slot] = Label("")
            self["result_emby_%d" % slot] = Label("")
            self["result_jelly_%d" % slot] = Label("")
            self["result_plex_%d" % slot] = Label("")

        # Search history widgets
        for hidx in range(SEARCH_HISTORY_MAX):
            self["history_focus_%d" % hidx] = Label("")
            self["history_%d" % hidx] = Label("")

        # Bottom preview
        self["preview_poster"] = Pixmap()
        self["preview_title"] = Label("")
        self["preview_meta"] = Label("")
        self["preview_overview"] = Label("")
        self["preview_badges"] = Label("")
        self["avail_emby_status"] = Label("–")
        self["avail_jelly_status"] = Label("–")
        self["avail_plex_status"] = Label("–")

        self._debounce_timer = eTimer()
        self._debounce_timer.callback.append(self._doSearch)

        self._detail_timer = eTimer()
        self._detail_timer.callback.append(self._requestPreviewDetail)

        self._clock_timer = eTimer()
        self._clock_timer.callback.append(self._updateClock)

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.keyOK,
                "cancel": self.keyCancel,
                "red": self.keyCancel,
                "green": self.keyGreen,
                "yellow": self.keyYellow,
                "blue": self.keyBlue,
                "up": self.keyUp,
                "down": self.keyDown,
                "left": self.keyLeft,
                "right": self.keyRight,
            },
            -1
        )

        self.onLayoutFinish.append(self._onLayout)
        self.onClose.append(self._onClose)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def _onLayout(self):
        # INFUSEMEDIA2026_SEARCH_LABELFIX1
        # Einige Enigma2-Skins initialisieren statische Label-Texte beim
        # Skin-Aufbau leer. Nach onLayoutFinish deshalb bewusst erneut setzen
        # und sichtbar machen.
        self._restoreStaticLabels()
        self._updateClock()
        self._clock_timer.start(30000, False)
        self._loadSearchHistory()
        self._renderKeyboard()
        self._updateQueryLabel()
        self._renderFilters()
        self._renderResults()
        self._renderHistory()
        self._updatePreview()
        self._prepareClients()

    def _restoreStaticLabels(self):
        static_labels = (
            ("search_title", "Suche"),
            ("legend_title", "Verfügbar bei:"),
            ("legend_emby", "Emby"),
            ("legend_jelly", "Jellyfin"),
            ("legend_plex", "Plex"),
            ("availability_title", "Verfügbar bei"),
            ("avail_emby_name", "Emby"),
            ("avail_jelly_name", "Jellyfin"),
            ("avail_plex_name", "Plex"),
            ("actions_title", "Aktionen"),
            ("action_open", "OK   Details öffnen"),
            ("action_keyboard", "GELB   Zur Tastatur"),
            ("action_favorite", "GRÜN   Favorit"),
            ("action_filter", "BLAU   Alle / Filme / Serien"),
        )
        for name, text in static_labels:
            try:
                self[name].setText(text)
                self[name].show()
            except Exception:
                pass

    def _onClose(self):
        self._closing = True
        try:
            self._debounce_timer.stop()
        except Exception:
            pass
        try:
            self._clock_timer.stop()
        except Exception:
            pass
        try:
            self._detail_timer.stop()
        except Exception:
            pass

    def _updateClock(self):
        now = datetime.now()
        weekdays = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
        months = ("Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
                  "Jul", "Aug", "Sep", "Okt", "Nov", "Dez")
        self["date"].setText("%s, %d. %s %d" % (
            weekdays[now.weekday()], now.day, months[now.month - 1], now.year
        ))
        self["clock"].setText(now.strftime("%H:%M"))

    # ------------------------------------------------------------------
    # Search history
    # ------------------------------------------------------------------
    def _loadSearchHistory(self):
        self.search_history = []
        try:
            history_path = SEARCH_HISTORY_FILE
            if not os.path.isfile(history_path) and os.path.isfile(LEGACY_SEARCH_HISTORY_FILE):
                history_path = LEGACY_SEARCH_HISTORY_FILE
            with open(history_path, "r", encoding="utf-8", errors="replace") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                items = data.get("items", [])
            elif isinstance(data, list):
                items = data
            else:
                items = []
            seen = set()
            for value in items:
                term = str(value or "").strip()
                folded = term.casefold()
                if len(term) < MIN_QUERY_LENGTH or not folded or folded in seen:
                    continue
                seen.add(folded)
                self.search_history.append(term[:80])
                if len(self.search_history) >= SEARCH_HISTORY_MAX:
                    break
        except Exception:
            self.search_history = []
        self.history_index = 0

    def _writeSearchHistory(self):
        try:
            directory = os.path.dirname(SEARCH_HISTORY_FILE)
            if directory and not os.path.isdir(directory):
                os.makedirs(directory)
            tmp = SEARCH_HISTORY_FILE + ".tmp"
            payload = {"version": 1, "items": self.search_history[:SEARCH_HISTORY_MAX]}
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(tmp, SEARCH_HISTORY_FILE)
        except Exception as error:
            log.warning("SearchDisney1 Verlauf konnte nicht gespeichert werden: %s", error)

    def _rememberSearchTerm(self):
        term = self.query.strip()
        # Keine Tastatur-Zwischenstände und keine erfolglosen Suchfragmente.
        if len(term) < MIN_QUERY_LENGTH or not self.results_all:
            return
        folded = term.casefold()
        cleaned = [old for old in self.search_history
                   if (old or "").strip().casefold() != folded]
        self.search_history = [term[:80]] + cleaned
        self.search_history = self.search_history[:SEARCH_HISTORY_MAX]
        self.history_index = 0
        self._writeSearchHistory()

    def _historyVisible(self):
        return not self.query.strip() and bool(self.search_history)

    def _renderHistory(self):
        visible = self._historyVisible()
        for idx in range(SEARCH_HISTORY_MAX):
            focus = self["history_focus_%d" % idx]
            label = self["history_%d" % idx]
            if visible and idx < len(self.search_history):
                label.setText("  %d.  %s" % (idx + 1, self.search_history[idx]))
                label.show()
                if self.focus_area == "history" and idx == self.history_index:
                    focus.show()
                else:
                    focus.hide()
            else:
                focus.hide()
                label.hide()

        # Verlauf und Ergebnisfilter teilen sich bewusst dieselbe Fläche.
        filter_widgets = (
            "filter_all", "filter_movies", "filter_series",
            "filter_line_all", "filter_line_movies", "filter_line_series",
            "legend_title", "legend_emby_dot", "legend_emby",
            "legend_jelly_dot", "legend_jelly",
            "legend_plex_dot", "legend_plex",
        )
        if visible:
            for name in filter_widgets:
                self[name].hide()
            self["results_title"].setText("Letzte Suchen")
            self["result_count"].setText("%d gespeichert" % len(self.search_history))
        else:
            for name in ("filter_all", "filter_movies", "filter_series",
                         "legend_title", "legend_emby_dot", "legend_emby",
                         "legend_jelly_dot", "legend_jelly",
                         "legend_plex_dot", "legend_plex"):
                self[name].show()
            self._renderFilters()

    def _selectedHistoryTerm(self):
        if not self._historyVisible():
            return None
        if not self.search_history:
            return None
        self.history_index = max(0, min(self.history_index, len(self.search_history) - 1))
        return self.search_history[self.history_index]

    def _openHistoryTerm(self):
        term = self._selectedHistoryTerm()
        if not term:
            return
        self.query = term
        self.focus_area = "keyboard"
        self._updateQueryLabel()
        self._renderKeyboard()
        self._renderHistory()
        self._triggerSearch()

    # ------------------------------------------------------------------
    # Clients + live search
    # ------------------------------------------------------------------
    def _prepareClients(self):
        from ..backends.factory import create_client_for_server
        try:
            config_store.auto_import_existing()
        except Exception:
            pass

        for server_cfg in config_store.get_servers():
            try:
                client = create_client_for_server(server_cfg)
            except Exception as e:
                log.warning("SearchDisney1: Client %s konnte nicht erstellt werden: %s",
                            getattr(server_cfg, "name", "?"), e)
                continue
            name = server_cfg.name
            protocol = (getattr(server_cfg, "protocol", "") or "").lower()
            self.clients[name] = client
            self.server_configs[name] = server_cfg
            self._client_protocol[name] = protocol
            self._login_state[name] = "idle"

        if not self.clients:
            self["status"].setText("Kein Server konfiguriert")

    def _triggerSearch(self):
        try:
            self._debounce_timer.stop()
        except Exception:
            pass
        if len(self.query.strip()) < MIN_QUERY_LENGTH:
            self._search_generation += 1
            self._raw_results = []
            self.results_all = []
            self.results_display = []
            self.pending_searches = 0
            self.result_index = 0
            self.result_offset = 0
            self._cancelPreviewDetail()
            if not self.query.strip():
                self["status"].setText("2+ Zeichen für Ergebnisse")
                self["results_title"].setText("Letzte Suchen" if self.search_history else "Ergebnisse")
            else:
                self["status"].setText("Noch 1 Zeichen für Ergebnisse")
                self["results_title"].setText("Ergebnisse")
            if self.focus_area == "history" and not self._historyVisible():
                self.focus_area = "keyboard"
            self._renderFilters()
            self._renderResults()
            self._renderHistory()
            self._renderKeyboard()
            self._updatePreview()
            return
        self._renderHistory()
        self._debounce_timer.start(SEARCH_DEBOUNCE_MS, True)

    def _doSearch(self):
        query = self.query.strip()
        if len(query) < MIN_QUERY_LENGTH or self._closing:
            return

        self._search_generation += 1
        generation = self._search_generation
        self._raw_results = []
        self.results_all = []
        self.results_display = []
        self.pending_searches = len(self.clients)
        self.result_index = 0
        self.result_offset = 0

        self["status"].setText("Suche läuft …")
        self["results_title"].setText('Ergebnisse für „%s“' % query)
        self._renderHistory()
        self._renderFilters()
        self._renderResults()
        self._updatePreview()

        if not self.clients:
            self["status"].setText("Kein Server konfiguriert")
            return

        for server_name, client in self.clients.items():
            self._ensureClientSearch(server_name, client, generation, query)

    def _ensureClientSearch(self, server_name, client, generation, query):
        state = self._login_state.get(server_name, "idle")
        if state == "ready":
            self._searchOnClient(server_name, client, generation, query)
            return

        self._login_requested[server_name] = (generation, query)
        if state == "pending":
            return

        self._login_state[server_name] = "pending"

        def on_login(token, uid):
            if self._closing:
                return
            self._login_state[server_name] = "ready"
            request = self._login_requested.get(server_name)
            if not request:
                return
            req_generation, req_query = request
            if req_generation != self._search_generation:
                return
            self._searchOnClient(server_name, client, req_generation, req_query)

        def on_error(err):
            if self._closing:
                return
            self._login_state[server_name] = "idle"
            request = self._login_requested.get(server_name)
            if not request:
                return
            req_generation, req_query = request
            if req_generation == self._search_generation:
                self._onSearchDone(req_generation, server_name, [], err)

        try:
            client.login(on_login, on_error)
        except Exception as e:
            on_error(str(e))

    def _searchOnClient(self, server_name, client, generation, query):
        if generation != self._search_generation or self._closing:
            return
        try:
            client.search(
                query,
                lambda items, g=generation, s=server_name: self._onSearchDone(g, s, items, None),
                lambda err, g=generation, s=server_name: self._onSearchDone(g, s, [], err)
            )
        except Exception as e:
            self._onSearchDone(generation, server_name, [], str(e))

    def _onSearchDone(self, generation, server_name, items, err):
        if generation != self._search_generation or self._closing:
            return

        if err:
            log.warning("SearchDisney1 Suchfehler bei %s: %s", server_name, err)
        else:
            protocol = self._client_protocol.get(server_name, "")
            provider_name = _PROVIDER_NAMES.get(protocol, protocol.capitalize() or "Server")
            for item in items or []:
                try:
                    item.source_label = provider_name
                except Exception:
                    pass
                self._raw_results.append((server_name, protocol, item))

        self.pending_searches = max(0, self.pending_searches - 1)
        self._rebuildGroupedResults()

        # First completed server should already produce visible results.
        if self.pending_searches > 0:
            if self.results_all:
                self["status"].setText("%d Treffer · weitere Server werden durchsucht …" %
                                       len(self.results_all))
            else:
                self["status"].setText("Suche läuft …")
        else:
            if self.results_all:
                self["status"].setText("%d Treffer" % len(self.results_all))
            else:
                self["status"].setText("Keine Ergebnisse für '%s'" % self.query.strip())

    # ------------------------------------------------------------------
    # Cross-provider grouping
    # ------------------------------------------------------------------
    @staticmethod
    def _year(item):
        try:
            return int(getattr(item, "year", 0) or 0)
        except Exception:
            return 0

    @staticmethod
    def _compatible_year(a, b):
        return a == 0 or b == 0 or a == b

    def _sameMedium(self, group, item):
        pkey = provider_key(item)
        title = normalize_title(getattr(item, "title", "") or "")
        year = self._year(item)

        if pkey and pkey in group["provider_keys"]:
            return True

        if title != group["title_key"]:
            return False

        for seen_year in group["years"]:
            if self._compatible_year(seen_year, year):
                return True
        return False

    def _rebuildGroupedResults(self):
        old_key = None
        if self.results_display and 0 <= self.result_index < len(self.results_display):
            old_key = getattr(self.results_display[self.result_index], "_search_group_key", None)

        groups = []
        for server_name, protocol, item in self._raw_results:
            group = None
            for candidate in groups:
                if self._sameMedium(candidate, item):
                    group = candidate
                    break

            if group is None:
                title_key = normalize_title(getattr(item, "title", "") or "")
                year = self._year(item)
                group = {
                    "title_key": title_key,
                    "years": [year],
                    "provider_keys": set(),
                    "variants": [],
                }
                groups.append(group)
            else:
                year = self._year(item)
                if year not in group["years"]:
                    group["years"].append(year)

            pkey = provider_key(item)
            if pkey:
                group["provider_keys"].add(pkey)
            group["variants"].append((server_name, protocol, item))

        query_cf = self.query.strip().casefold()
        built = []
        for group in groups:
            variants = sorted(
                group["variants"],
                key=lambda entry: (_PROVIDER_ORDER.get(entry[1], 99),
                                   (getattr(entry[2], "title", "") or "").casefold())
            )
            if not variants:
                continue
            server_name, protocol, primary = variants[0]

            protocols = []
            variant_map = {}
            for v_server, v_protocol, v_item in variants:
                if v_protocol and v_protocol not in protocols:
                    protocols.append(v_protocol)
                variant_map.setdefault(v_protocol, []).append(v_item)

            protocols.sort(key=lambda p: _PROVIDER_ORDER.get(p, 99))
            primary.search_provider_protocols = tuple(protocols)
            primary.search_variants = variant_map
            primary._search_group_key = (
                group["title_key"],
                self._year(primary),
                tuple(sorted(group["provider_keys"])),
            )
            built.append(primary)

        built.sort(key=lambda item: (
            query_cf not in (getattr(item, "title", "") or "").casefold(),
            not (getattr(item, "title", "") or "").casefold().startswith(query_cf),
            (getattr(item, "title", "") or "").casefold(),
            self._year(item),
        ))
        self.results_all = built
        self._applyFilter(old_key)

    def _mediaKind(self, item):
        media_type = (getattr(item, "media_type", "") or "").lower()
        if media_type in ("show", "series", "season", "episode"):
            return "series"
        if media_type in ("movie", "film"):
            return "movie"
        if getattr(item, "series_name", ""):
            return "series"
        if getattr(item, "season_number", None) is not None:
            return "series"
        # Search backends mainly return movies/shows; unknowns remain in "Alle"
        return "movie"

    def _applyFilter(self, preserve_key=None):
        if self.search_filter == "movie":
            display = [i for i in self.results_all if self._mediaKind(i) == "movie"]
        elif self.search_filter == "series":
            display = [i for i in self.results_all if self._mediaKind(i) == "series"]
        else:
            display = list(self.results_all)

        self.results_display = display
        self.result_index = 0
        self.result_offset = 0

        if preserve_key:
            for idx, item in enumerate(display):
                if getattr(item, "_search_group_key", None) == preserve_key:
                    self.result_index = idx
                    break

        self._ensureResultVisible()
        self._renderFilters()
        self._renderResults()
        self._updatePreview()

    # ------------------------------------------------------------------
    # Grouped search versions
    # ------------------------------------------------------------------
    def _searchVersionsByProvider(self, item):
        result = {"emby": [], "jellyfin": [], "plex": []}
        variants = getattr(item, "search_variants", None) or {}

        seen = set()
        for protocol, members in variants.items():
            protocol = (protocol or "").lower()
            if protocol not in result:
                continue
            for member in members or []:
                identity = (
                    protocol,
                    str(getattr(member, "server_name", "") or ""),
                    str(getattr(member, "id", "") or ""),
                )
                if identity in seen:
                    continue
                seen.add(identity)
                result[protocol].append(member)

        if not any(result.values()) and item is not None:
            cfg = self.server_configs.get(getattr(item, "server_name", ""))
            protocol = (getattr(cfg, "protocol", "") or "").lower() if cfg else ""
            if protocol in result:
                result[protocol].append(item)

        return result

    @staticmethod
    def _searchQuality(item):
        width = int(getattr(item, "video_width", 0) or 0)
        height = int(getattr(item, "video_height", 0) or 0)
        if height >= 2000 or width >= 3800:
            return "4K"
        if height >= 1000 or width >= 1900:
            return "1080p"
        if height >= 700 or width >= 1200:
            return "HD"
        return ""

    def _searchQualitySummary(self, items):
        labels = []
        for candidate in items or []:
            label = self._searchQuality(candidate)
            if label and label not in labels:
                labels.append(label)
        order = {"4K": 0, "1080p": 1, "HD": 2}
        labels.sort(key=lambda value: order.get(value, 9))
        return labels

    def _searchVersionStatus(self, items):
        count = len(items or [])
        if not count:
            return "–"
        parts = []
        if count > 1:
            parts.append("%d Versionen" % count)
        parts.extend(self._searchQualitySummary(items))
        return " · ".join(parts) if parts else "Verfügbar"

    def _searchAllVariants(self, item):
        versions = self._searchVersionsByProvider(item)
        result = []
        seen = set()
        for protocol in ("emby", "jellyfin", "plex"):
            for candidate in versions.get(protocol, []):
                key = self._previewDetailKey(candidate)
                if key is None or key in seen:
                    continue
                seen.add(key)
                result.append(candidate)
        return result

    def _prepareVariantDetails(self, item):
        if item is None or self._closing:
            return

        group_key = getattr(item, "_search_group_key", None)
        primary_key = self._previewDetailKey(item)

        for candidate in self._searchAllVariants(item):
            key = self._previewDetailKey(candidate)
            if key is None or key == primary_key:
                continue

            cached = self._detail_cache.get(key)
            if cached is not None:
                self._mergePreviewDetail(candidate, cached)
                continue

            if (
                key in self._detail_failed
                or key in self._detail_inflight
                or key in self._variant_detail_inflight
            ):
                continue

            client = self.clients.get(getattr(candidate, "server_name", ""))
            if client is None or not hasattr(client, "get_item_detail"):
                continue

            self._variant_detail_inflight.add(key)
            try:
                client.get_item_detail(
                    getattr(candidate, "id", ""),
                    lambda detail, k=key, target=candidate, group=group_key:
                        self._variantDetailLoaded(k, target, group, detail),
                    lambda error, k=key, group=group_key:
                        self._variantDetailFailed(k, group, error),
                )
            except Exception as error:
                self._variantDetailFailed(key, group_key, error)

    def _variantDetailLoaded(self, key, target, group_key, detail):
        self._variant_detail_inflight.discard(key)
        if self._closing or detail is None:
            return

        self._detail_cache[key] = detail
        self._mergePreviewDetail(target, detail)

        current = self._selectedItem()
        if current is not None and getattr(current, "_search_group_key", None) == group_key:
            self._updatePreview()

    def _variantDetailFailed(self, key, group_key, error):
        self._variant_detail_inflight.discard(key)
        if self._closing:
            return
        self._detail_failed.add(key)
        log.warning(
            "SearchDisney1 Variantendetails nicht ladbar (%s/%s): %s",
            key[0], key[1], error
        )

    # ------------------------------------------------------------------
    # Focused-result detail enrichment
    # ------------------------------------------------------------------
    def _previewDetailKey(self, item):
        if item is None:
            return None
        server_name = getattr(item, "server_name", "") or ""
        item_id = getattr(item, "id", "") or ""
        if not server_name or not item_id:
            return None
        return (server_name, str(item_id))

    def _cancelPreviewDetail(self):
        self._detail_pending = None
        self._detail_serial += 1
        try:
            self._detail_timer.stop()
        except Exception:
            pass

    def _mergePreviewDetail(self, item, detail):
        if item is None or detail is None:
            return
        try:
            updater = getattr(item, "update_from_detail", None)
            if callable(updater):
                updater(detail)
        except Exception:
            pass

        for attr in (
            "year", "overview", "genres", "rating", "series_name",
            "season_number", "episode_number", "video_codec",
            "video_width", "video_height", "audio_codec",
            "audio_channels", "audio_language", "runtime_ticks",
            "provider_ids", "poster_url", "backdrop_url",
        ):
            value = getattr(detail, attr, None)
            if value not in (None, "", 0, [], {}):
                try:
                    setattr(item, attr, value)
                except Exception:
                    pass

    def _preparePreviewDetail(self, item):
        key = self._previewDetailKey(item)
        if key is None:
            self._cancelPreviewDetail()
            return

        cached = self._detail_cache.get(key)
        if cached is not None:
            self._mergePreviewDetail(item, cached)
            self._prepareVariantDetails(item)
            return

        if key in self._detail_failed or key in self._detail_inflight:
            return
        if self._detail_pending is not None and self._detail_pending[1] == key:
            return

        client = self.clients.get(getattr(item, "server_name", ""))
        if client is None or not hasattr(client, "get_item_detail"):
            return

        self._detail_serial += 1
        serial = self._detail_serial
        self._detail_pending = (serial, key, item)
        try:
            self._detail_timer.stop()
            self._detail_timer.start(DETAIL_DEBOUNCE_MS, True)
        except Exception:
            self._requestPreviewDetail()

    def _requestPreviewDetail(self):
        pending = self._detail_pending
        self._detail_pending = None
        if pending is None or self._closing:
            return

        serial, key, item = pending
        current = self._selectedItem()
        if serial != self._detail_serial or self._previewDetailKey(current) != key:
            return

        client = self.clients.get(getattr(item, "server_name", ""))
        if client is None or not hasattr(client, "get_item_detail"):
            return

        self._detail_inflight[key] = serial

        # SEARCH_VERSIONS1_COMPAT: nach demselben Fokus-Debounce auch die
        # weiteren Varianten dieses einen gruppierten Titels anreichern.
        self._prepareVariantDetails(item)

        try:
            client.get_item_detail(
                getattr(item, "id", ""),
                lambda detail, s=serial, k=key, target=item:
                    self._previewDetailLoaded(s, k, target, detail),
                lambda error, s=serial, k=key:
                    self._previewDetailFailed(s, k, error),
            )
        except Exception as error:
            self._previewDetailFailed(serial, key, error)

    def _previewDetailLoaded(self, serial, key, target, detail):
        if self._detail_inflight.get(key) != serial:
            return
        self._detail_inflight.pop(key, None)
        if self._closing or detail is None:
            return

        self._detail_cache[key] = detail
        self._mergePreviewDetail(target, detail)

        current = self._selectedItem()
        if self._previewDetailKey(current) == key:
            self._mergePreviewDetail(current, detail)
            self._updatePreview()

    def _previewDetailFailed(self, serial, key, error):
        if self._detail_inflight.get(key) != serial:
            return
        self._detail_inflight.pop(key, None)
        if not self._closing:
            self._detail_failed.add(key)
            log.warning("SearchDisney1 Vorschaudetails nicht ladbar (%s/%s): %s",
                        key[0], key[1], error)
            current = self._selectedItem()
            if self._previewDetailKey(current) == key:
                self._updatePreview()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _updateQueryLabel(self):
        if self.query:
            self["query_input"].setText(self.query + "|")
        else:
            self["query_input"].setText("Suchbegriff …")

    def _renderKeyboard(self):
        for idx in range(len(_KEYBOARD_FLAT)):
            focus = self["key_focus_%d" % idx]
            if self.focus_area == "keyboard" and idx == self.keyboard_index:
                focus.show()
            else:
                focus.hide()

    def _renderFilters(self):
        movies = len([i for i in self.results_all if self._mediaKind(i) == "movie"])
        series = len([i for i in self.results_all if self._mediaKind(i) == "series"])
        self["filter_all"].setText("Alle (%d)" % len(self.results_all))
        self["filter_movies"].setText("Filme (%d)" % movies)
        self["filter_series"].setText("Serien (%d)" % series)

        states = (
            ("filter_line_all", self.search_filter == "all"),
            ("filter_line_movies", self.search_filter == "movie"),
            ("filter_line_series", self.search_filter == "series"),
        )
        for name, active in states:
            if active:
                self[name].show()
            else:
                self[name].hide()

    def _resultMeta(self, item):
        year = str(getattr(item, "year", "") or "")
        kind = "Serie" if self._mediaKind(item) == "series" else "Film"
        if year:
            return "%s · %s" % (year, kind)
        return kind

    @staticmethod
    def _short(text, limit):
        text = (text or "").strip()
        if len(text) <= limit:
            return text
        return text[:max(0, limit - 3)].rstrip() + "..."

    def _hideResultSlot(self, slot):
        self._slot_items[slot] = None
        self["result_poster_%d" % slot].hide()
        self["result_title_%d" % slot].setText("")
        self["result_meta_%d" % slot].setText("")
        for edge in ("top", "bottom", "left", "right"):
            self["rf_%s_%d" % (edge, slot)].hide()
        for provider in ("emby", "jelly", "plex"):
            self["result_%s_%d" % (provider, slot)].hide()

    def _renderResults(self):
        self._render_token += 1
        token = self._render_token

        for slot in range(RESULT_VISIBLE_COUNT):
            absolute = self.result_offset + slot
            if absolute >= len(self.results_display):
                self._hideResultSlot(slot)
                continue

            item = self.results_display[absolute]
            self._slot_items[slot] = item
            self["result_title_%d" % slot].setText(
                self._short(getattr(item, "title", "") or "", 24)
            )
            self["result_meta_%d" % slot].setText(self._resultMeta(item))

            selected = (absolute == self.result_index and self.focus_area == "results")
            for edge in ("top", "bottom", "left", "right"):
                widget = self["rf_%s_%d" % (edge, slot)]
                if selected:
                    widget.show()
                else:
                    widget.hide()

            protocols = set(getattr(item, "search_provider_protocols", ()) or ())
            provider_widgets = {
                "emby": self["result_emby_%d" % slot],
                "jellyfin": self["result_jelly_%d" % slot],
                "plex": self["result_plex_%d" % slot],
            }
            for protocol, widget in provider_widgets.items():
                if protocol in protocols:
                    widget.show()
                else:
                    widget.hide()

            poster = self["result_poster_%d" % slot]
            path = getattr(item, "local_poster_path", None)
            if not path:
                path = image_cache.get_local_path(getattr(item, "poster_url", None))
                if path:
                    item.local_poster_path = path

            pix = None
            if path:
                try:
                    pix = LoadPixmap(path)
                except Exception:
                    pix = None
            if pix is None:
                pix = self._placeholder_pix

            if pix is not None and poster.instance:
                poster.instance.setPixmap(pix)
                poster.show()
            else:
                poster.hide()

            poster_url = getattr(item, "poster_url", None)
            if poster_url and not path:
                image_cache.fetch(
                    poster_url,
                    lambda loaded, i=item, s=slot, t=token: self._onResultPosterLoaded(i, s, t, loaded),
                    lambda err: None
                )

        total = len(self.results_display)
        if total:
            page = (self.result_offset // RESULT_COLUMNS) + 1
            total_rows = (total + RESULT_COLUMNS - 1) // RESULT_COLUMNS
            max_first_row = max(0, total_rows - RESULT_VISIBLE_ROWS)
            pages = max(1, max_first_row + 1)
            self["result_count"].setText("%d Treffer" % total)
        else:
            self["result_count"].setText("")

    def _onResultPosterLoaded(self, item, slot, token, path):
        if self._closing or token != self._render_token:
            return
        if slot < 0 or slot >= RESULT_VISIBLE_COUNT:
            return
        if self._slot_items[slot] is not item:
            return
        item.local_poster_path = path
        try:
            pix = LoadPixmap(path)
        except Exception:
            pix = None
        widget = self["result_poster_%d" % slot]
        if pix is not None and widget.instance:
            widget.instance.setPixmap(pix)
            widget.show()

    def _selectedItem(self):
        if not self.results_display:
            return None
        idx = max(0, min(self.result_index, len(self.results_display) - 1))
        return self.results_display[idx]

    def _updatePreview(self):
        item = self._selectedItem()

        if item is None:
            self._cancelPreviewDetail()
            history_term = self._selectedHistoryTerm() if self.focus_area == "history" else None
            if history_term:
                self["preview_title"].setText(history_term)
                self["preview_meta"].setText("Letzte Suche")
                self["preview_overview"].setText(
                    "OK startet diesen Suchbegriff sofort erneut."
                )
            else:
                self["preview_title"].setText("Noch keine Auswahl")
                self["preview_meta"].setText("")
                self["preview_overview"].setText(
                    "Gib mindestens zwei Buchstaben oder Zahlen ein. "
                    "Die ersten Treffer erscheinen rechts automatisch."
                )
            self["preview_badges"].setText("")
            self["preview_poster"].hide()
            self._renderAvailability(())
            return

        self["preview_title"].setText(getattr(item, "title", "") or "")

        meta = []
        year = getattr(item, "year", None)
        if year:
            meta.append(str(year))
        meta.append("Serie" if self._mediaKind(item) == "series" else "Film")
        runtime = int(getattr(item, "runtime_ticks", 0) or 0)
        if runtime > 0:
            minutes = int(round(runtime / 600000000.0))
            if minutes > 0:
                meta.append("%d Min." % minutes)
        genres = getattr(item, "genres", None) or []
        if genres:
            meta.append(", ".join(genres[:3]))
        self["preview_meta"].setText("  |  ".join(meta))

        overview = (getattr(item, "overview", "") or "").strip()
        detail_key = self._previewDetailKey(item)
        if not overview:
            if detail_key in self._detail_failed:
                overview = "Keine Beschreibung verfügbar."
            else:
                overview = "Details werden geladen …"
        # INFUSEMEDIA2026_SEARCH_DESCRIPTIONFIT1
        # Die Vorschau hat Platz fuer ca. vier saubere Zeilen. Ein bewusst
        # kuerzeres Limit verhindert, dass Text unter die Technik-Badges laeuft.
        self["preview_overview"].setText(self._short(overview, 250))

        badges = []
        rating = getattr(item, "rating", None)
        if rating not in (None, "", 0):
            try:
                badges.append("★ %.1f" % float(rating))
            except Exception:
                badges.append("★ %s" % rating)

        versions_by_provider = self._searchVersionsByProvider(item)
        all_versions = []
        for _provider in ("emby", "jellyfin", "plex"):
            all_versions.extend(versions_by_provider.get(_provider, []))

        version_count = len(all_versions)
        if version_count > 1:
            badges.append("%d Versionen" % version_count)

        qualities = self._searchQualitySummary(all_versions)
        if qualities:
            badges.extend(qualities)
        else:
            primary_quality = self._searchQuality(item)
            if primary_quality:
                badges.append(primary_quality)

        codecs = []
        for candidate in all_versions or [item]:
            codec = str(getattr(candidate, "video_codec", "") or "").upper()
            if codec and codec not in codecs:
                codecs.append(codec)
        badges.extend(codecs[:2])

        self["preview_badges"].setText("  |  ".join(badges))

        protocols = getattr(item, "search_provider_protocols", ()) or ()
        self._renderAvailability(protocols, item)

        path = getattr(item, "local_poster_path", None)
        if not path:
            path = image_cache.get_local_path(getattr(item, "poster_url", None))
            if path:
                item.local_poster_path = path
        pix = None
        if path:
            try:
                pix = LoadPixmap(path)
            except Exception:
                pix = None
        if pix is None:
            pix = self._placeholder_pix
        if pix is not None and self["preview_poster"].instance:
            self["preview_poster"].instance.setPixmap(pix)
            self["preview_poster"].show()
        else:
            self["preview_poster"].hide()

        poster_url = getattr(item, "poster_url", None)
        if poster_url and not path:
            image_cache.fetch(
                poster_url,
                lambda loaded, i=item: self._onPreviewPosterLoaded(i, loaded),
                lambda err: None
            )

        # Suchtreffer bleiben leichtgewichtig; vollständige Metadaten werden
        # nur für den tatsächlich fokussierten Treffer nachgeladen.
        self._preparePreviewDetail(item)

    def _onPreviewPosterLoaded(self, item, path):
        if self._closing or self._selectedItem() is not item:
            return
        item.local_poster_path = path
        try:
            pix = LoadPixmap(path)
        except Exception:
            pix = None
        if pix is not None and self["preview_poster"].instance:
            self["preview_poster"].instance.setPixmap(pix)
            self["preview_poster"].show()

    def _renderAvailability(self, protocols, item=None):
        protocols = set(protocols or ())
        versions = self._searchVersionsByProvider(item) if item is not None else {
            "emby": [], "jellyfin": [], "plex": []
        }
        mapping = (
            ("emby", "avail_emby_dot", "avail_emby_status"),
            ("jellyfin", "avail_jelly_dot", "avail_jelly_status"),
            ("plex", "avail_plex_dot", "avail_plex_status"),
        )
        for protocol, dot_name, status_name in mapping:
            members = versions.get(protocol, [])
            if protocol in protocols or members:
                self[dot_name].show()
                self[status_name].setText(self._searchVersionStatus(members))
            else:
                self[dot_name].hide()
                self[status_name].setText("–")

    # ------------------------------------------------------------------
    # Result navigation
    # ------------------------------------------------------------------
    def _ensureResultVisible(self):
        if not self.results_display:
            self.result_index = 0
            self.result_offset = 0
            return
        self.result_index = max(0, min(self.result_index, len(self.results_display) - 1))

        row = self.result_index // RESULT_COLUMNS
        first_row = self.result_offset // RESULT_COLUMNS
        if row < first_row:
            self.result_offset = row * RESULT_COLUMNS
        elif row > first_row + RESULT_VISIBLE_ROWS - 1:
            self.result_offset = (row - RESULT_VISIBLE_ROWS + 1) * RESULT_COLUMNS

    def _moveResultHorizontal(self, delta):
        if not self.results_display:
            return
        col = self.result_index % RESULT_COLUMNS
        row = self.result_index // RESULT_COLUMNS
        target_col = col + delta
        if target_col < 0:
            self.focus_area = "keyboard"
            self._renderKeyboard()
            self._renderResults()
            return
        if target_col >= RESULT_COLUMNS:
            return
        target = row * RESULT_COLUMNS + target_col
        if target >= len(self.results_display):
            return
        self.result_index = target
        self._ensureResultVisible()
        self._renderResults()
        self._updatePreview()

    def _moveResultVertical(self, delta):
        if not self.results_display:
            return
        row = self.result_index // RESULT_COLUMNS
        col = self.result_index % RESULT_COLUMNS
        target_row = row + delta
        if target_row < 0:
            return
        row_start = target_row * RESULT_COLUMNS
        if row_start >= len(self.results_display):
            return
        target = min(row_start + col, len(self.results_display) - 1)
        self.result_index = target
        self._ensureResultVisible()
        self._renderResults()
        self._updatePreview()

    # ------------------------------------------------------------------
    # Keyboard + actions
    # ------------------------------------------------------------------
    def _keyboardRowCol(self):
        return divmod(self.keyboard_index, 6)

    def _setKeyboardIndex(self, row, col):
        row = max(0, min(row, len(_KEYBOARD) - 1))
        col = max(0, min(col, len(_KEYBOARD[row]) - 1))
        self.keyboard_index = row * 6 + col
        self._renderKeyboard()

    def _insertKeyboardKey(self):
        key = _KEYBOARD_FLAT[self.keyboard_index]
        if key == "<-":
            self.query = self.query[:-1]
        elif key == "SPACE":
            if self.query and not self.query.endswith(" "):
                self.query += " "
        else:
            self.query += key
        self._updateQueryLabel()
        self._triggerSearch()

    def keyOK(self):
        if self.focus_area == "keyboard":
            self._insertKeyboardKey()
            return
        if self.focus_area == "history":
            self._openHistoryTerm()
            return
        self.keyOpen()

    def keyLeft(self):
        if self.focus_area == "results":
            self._moveResultHorizontal(-1)
            return
        if self.focus_area == "history":
            if self.history_index >= 5:
                self.history_index -= 5
                self._renderHistory()
                self._updatePreview()
            else:
                self.focus_area = "keyboard"
                self._renderHistory()
                self._renderKeyboard()
                self._updatePreview()
            return
        row, col = self._keyboardRowCol()
        if col > 0:
            self._setKeyboardIndex(row, col - 1)

    def keyRight(self):
        if self.focus_area == "results":
            self._moveResultHorizontal(1)
            return
        if self.focus_area == "history":
            target = self.history_index + 5
            if self.history_index < 5 and target < len(self.search_history):
                self.history_index = target
                self._renderHistory()
                self._updatePreview()
            return
        row, col = self._keyboardRowCol()
        if col < len(_KEYBOARD[row]) - 1:
            self._setKeyboardIndex(row, col + 1)
            return
        if self._historyVisible():
            self.focus_area = "history"
            self.history_index = min(self.history_index, len(self.search_history) - 1)
            self._renderKeyboard()
            self._renderHistory()
            self._updatePreview()
            return
        if self.results_display:
            self.focus_area = "results"
            self._ensureResultVisible()
            self._renderKeyboard()
            self._renderResults()
            self._updatePreview()

    def keyUp(self):
        if self.focus_area == "results":
            self._moveResultVertical(-1)
            return
        if self.focus_area == "history":
            if self.history_index % 5 > 0:
                self.history_index -= 1
                self._renderHistory()
                self._updatePreview()
            return
        row, col = self._keyboardRowCol()
        if row > 0:
            self._setKeyboardIndex(row - 1, col)

    def keyDown(self):
        if self.focus_area == "results":
            self._moveResultVertical(1)
            return
        if self.focus_area == "history":
            target = self.history_index + 1
            same_column = (target // 5) == (self.history_index // 5)
            if same_column and target < len(self.search_history):
                self.history_index = target
                self._renderHistory()
                self._updatePreview()
            return
        row, col = self._keyboardRowCol()
        if row < len(_KEYBOARD) - 1:
            self._setKeyboardIndex(row + 1, col)

    def keyYellow(self):
        self.focus_area = "keyboard"
        self._renderKeyboard()
        self._renderResults()
        self._renderHistory()
        self._updatePreview()

    def keyBlue(self):
        if len(self.query.strip()) < MIN_QUERY_LENGTH:
            return
        order = ("all", "movie", "series")
        try:
            idx = order.index(self.search_filter)
        except ValueError:
            idx = 0
        self.search_filter = order[(idx + 1) % len(order)]
        self._applyFilter()
        if self.results_display:
            self["status"].setText("%d Treffer" % len(self.results_display))

    def keyGreen(self):
        if self.focus_area == "history":
            return
        item = self._selectedItem()
        if item is None:
            return
        client = self.clients.get(getattr(item, "server_name", ""))
        if not client:
            return
        if client.__class__.__name__ == "PlexClient":
            self["status"].setText("Plex-Watchlist wird in diesem Build noch nicht geschrieben")
            return
        new_state = not bool(getattr(item, "is_favorite", False))
        item.is_favorite = new_state
        try:
            client.set_favorite(item.id, new_state)
            self["status"].setText("Favorit gesetzt" if new_state else "Favorit entfernt")
        except Exception as e:
            self["status"].setText("Favorit konnte nicht geändert werden")
            log.warning("SearchDisney1 Favorit: %s", e)
        self._updatePreview()

    def keyOpen(self):
        item = self._selectedItem()
        if item is None:
            return
        client = self.clients.get(getattr(item, "server_name", ""))
        if client is None:
            return
        self._rememberSearchTerm()
        try:
            from .MediaDetail import MediaDetail
            self.session.open(MediaDetail, item, client)
        except Exception as e:
            log.exception("SearchDisney1 Details konnten nicht geöffnet werden: %s", e)

    def keyCancel(self):
        self._rememberSearchTerm()
        self.close()
