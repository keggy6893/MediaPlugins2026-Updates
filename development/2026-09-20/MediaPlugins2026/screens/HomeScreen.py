# -*- coding: utf-8 -*-
# =====================================================================
# MEDIA PLUGINS 2026 - HOMESCREEN FEATURE HISTORY
# =====================================================================
# Snapshot / Cold Start / progressive Home-Ladung
# Poster-Pipeline / Cache / Provider-Rahmen
# Unified Continue / Dedupe / Provider-Filter
# Preview / Availability / Detail-Enrichment / Ambient
# Provider-Wechsel / interne Emby-Jellyfin-Plex-Bibliotheken
# Remote-Navigation / Farbtasten-Shortcuts
#
# Legacy-INFUSEMEDIA-Marker wurden mit CLEANUP1 konsolidiert.
# Aktuelle MEDIAPLUGINS2026-Marker bleiben Release-/Patch-Landmarks.
# =====================================================================
# MEDIAPLUGINS2026_HOMESCREEN_CLEANUP1
# MEDIAPLUGINS2026_HOME_SERVERHEALTH1
# WORKING SNAPSHOT: 2026-09-13 15:45:10 CEST
import time
import io
import json
import os

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Tools.LoadPixmap import LoadPixmap
from enigma import eSize, eTimer

try:
    from skin import parseColor
except Exception:
    parseColor = None

from ..backends.media_item import MediaItem
from ..utils.image_cache import image_cache
from ..utils import log


def _safe_call(fn, *args, **kwargs):
    # Nur fuer unkritische UI-/Timer-Aufrufe; keine Kernlogik verschlucken.
    log_ctx = kwargs.pop("_log_ctx", None)
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        if log_ctx:
            try:
                log.warning("%s: %s", log_ctx, exc)
            except Exception:
                pass
        return None


_PLACEHOLDER_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/skin/icons/poster_placeholder.png"
_DEMO_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/skin/demo"
_PROVIDER_COLORS = {
    "emby": "#37d67a",
    "jellyfin": "#3aa7ff",
    "plex": "#f5b82e",
    "all": "#dbe6ef",
}
_PROVIDER_NAMES = {"all": "Alle", "emby": "Emby", "jellyfin": "Jellyfin", "plex": "Plex"}
_HOME_SLIDESHOW_DELAY_MS = 6000

# Produktiv standardmaessig AUS.
# Fuer Poster-/Pipeline-Diagnose temporaer auf True setzen.
_DEBUG_TIMING = False

_HOME_SNAPSHOT_PATH = "/etc/enigma2/mediaplugins2026_unified_home_snapshot.json"
_HOME_SNAPSHOT_VERSION = 1
_HOME_SNAPSHOT_MAX_AGE = 7 * 24 * 60 * 60
_PIPELINE_TIMING_LOG = "/tmp/mediaplugins2026_unified_home_pipeline.log"


def _pipeline_timing_write(message):
    if not _DEBUG_TIMING:
        return
    try:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with io.open(_PIPELINE_TIMING_LOG, "a", encoding="utf-8") as handle:
            handle.write("%s | %s\n" % (stamp, message))
    except Exception:
        pass
_POSTER_TIMING_LOG = "/tmp/mediaplugins2026_unified_poster_timing.log"


def _poster_timing_log(message):
    """Eigenes Diagnose-Log; niemals Bild-URLs oder Tokens schreiben."""
    if not _DEBUG_TIMING:
        return
    try:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with io.open(_POSTER_TIMING_LOG, "a", encoding="utf-8") as handle:
            handle.write("%s | %s\n" % (stamp, message))
    except Exception:
        pass
_HOME_AMBIENT_DELAY_MS = 180
_HOME_AMBIENT_SHADE_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/skin/home_ambient_shade.png"


class HomeSection(object):
    def __init__(self, title, server_name, items=None):
        self.title = title
        self.server_name = server_name
        self.items = items or []


# =====================================================================
# MEDIA WALL / POSTER PIPELINE
# =====================================================================
class MediaWallRow(object):
    """Horizontale Media-Wall-Reihe mit Fenster-Scrolling.

    Verwendet ausschliesslich Standard-Enigma2-Widgets. Poster werden nur fuer
    das sichtbare Fenster plus kleine Vorladezone angefordert, damit auch sehr
    grosse Favoritenlisten nicht auf einmal hunderte Bildrequests erzeugen.
    """

    def __init__(self, screen, prefix, count=10, progress=False):
        self.screen = screen
        self.prefix = prefix
        self.count = count
        self.progress = progress
        self.items = []
        self.index = 0
        self.offset = 0
        self.focused = False
        self._placeholder = None
        self._poster_generation = 0
        self._poster_inflight = set()
        self._poster_retry_after = {}

        for i in range(count):
            screen["%s_focus_%d" % (prefix, i)] = Label("")
            screen["%s_poster_%d" % (prefix, i)] = Pixmap()
            screen["%s_title_%d" % (prefix, i)] = Label("")
            screen["%s_meta_%d" % (prefix, i)] = Label("")
            screen["%s_provider_top_%d" % (prefix, i)] = Label("")
            screen["%s_provider_bottom_%d" % (prefix, i)] = Label("")
            screen["%s_provider_left_%d" % (prefix, i)] = Label("")
            screen["%s_provider_right_%d" % (prefix, i)] = Label("")
            screen["%s_quality_%d" % (prefix, i)] = Label("")
            if progress:
                screen["%s_progress_bg_%d" % (prefix, i)] = Label("")
                screen["%s_progress_%d" % (prefix, i)] = Label("")

    def setItems(self, items):
        current_key = None
        current = self.getCurrent()
        if current is not None:
            current_key = (
                getattr(current, "server_name", ""),
                getattr(current, "id", ""),
            )

        self._poster_generation += 1
        try:
            self._poster_inflight.clear()
            self._poster_retry_after.clear()
        except Exception:
            pass

        self.items = list(items or [])
        self.index = 0
        if current_key:
            for idx, item in enumerate(self.items):
                if (
                    getattr(item, "server_name", ""),
                    getattr(item, "id", ""),
                ) == current_key:
                    self.index = idx
                    break

        self._ensureVisible()
        self._prefetchVisible()
        self._render()

        try:
            self.screen._schedulePosterRepair(250, reset=True)
        except Exception:
            pass

    def setFocused(self, focused):
        self.focused = bool(focused)
        self._render()

    def getCurrent(self):
        if 0 <= self.index < len(self.items):
            return self.items[self.index]
        return None

    def getCount(self):
        return len(self.items)

    def moveLeft(self):
        if self.index > 0:
            self.index -= 1
            self._ensureVisible()
            self._prefetchVisible()
            self._render()

    def moveRight(self):
        if self.index < len(self.items) - 1:
            self.index += 1
            self._ensureVisible()
            self._prefetchVisible()
            self._render()

    def _ensureVisible(self):
        if self.index < self.offset:
            self.offset = self.index
        elif self.index >= self.offset + self.count:
            self.offset = self.index - self.count + 1
        max_offset = max(0, len(self.items) - self.count)
        self.offset = max(0, min(self.offset, max_offset))

    def _posterTimingState(self, item):
        states = getattr(item, "_mp2026_poster_timing", None)
        if not isinstance(states, dict):
            states = {}
            try:
                item._mp2026_poster_timing = states
            except Exception:
                pass
        state = states.get(self.prefix)
        if state is None:
            now = time.monotonic()
            state = {
                "start": now,
                "ready": None,
                "source": "unknown",
                "request_logged": False,
                "ready_logged": False,
                "visible_logged": False,
            }
            states[self.prefix] = state
        return state

    def _posterTimingContext(self, item):
        provider = (getattr(item, "source_label", "") or "?").strip() or "?"
        server = (getattr(item, "server_name", "") or "?").strip() or "?"
        title = (getattr(item, "title", "") or "?").replace("\n", " ").replace("\r", " ")
        item_id = str(getattr(item, "id", "") or "?")
        return provider, server, title, item_id

    def _posterTimingWrite(self, event, item, state, extra=""):
        if not _DEBUG_TIMING:
            return
        now = time.monotonic()
        provider, server, title, item_id = self._posterTimingContext(item)
        total_ms = max(0.0, (now - state.get("start", now)) * 1000.0)
        home_started = getattr(self.screen, "_timing_load_started", None)
        if home_started is None:
            home_ms = -1.0
        else:
            home_ms = max(0.0, (now - home_started) * 1000.0)
        _poster_timing_log(
            "%s row=%s provider=%s server=%s id=%s source=%s "
            "total_ms=%.1f home_ms=%.1f title=%r%s"
            % (
                event, self.prefix, provider, server, item_id,
                state.get("source", "unknown"), total_ms, home_ms, title,
                (" " + extra) if extra else "",
            )
        )

    # MEDIAPLUGINS2026_POSTER_PIPELINE_HARDEN1_HOME
    @staticmethod
    def _posterItemKey(item):
        return (
            str(getattr(item, "server_name", "") or ""),
            str(getattr(item, "id", "") or ""),
            str(getattr(item, "poster_url", "") or ""),
        )

    def _visiblePosterStats(self):
        total = 0
        ready = 0
        end = min(len(self.items), self.offset + self.count)
        for item in self.items[self.offset:end]:
            total += 1
            path = getattr(item, "local_poster_path", None)
            if path and image_cache.is_valid_path(path):
                ready += 1
        return ready, total

    def _prefetchVisible(self):
        generation = self._poster_generation
        end = min(len(self.items), self.offset + self.count + 3)
        now = time.monotonic()

        for item in self.items[self.offset:end]:
            state = self._posterTimingState(item)
            local_path = getattr(item, "local_poster_path", None)

            if local_path:
                if image_cache.is_valid_path(local_path):
                    if state.get("source") == "unknown":
                        state["source"] = "local"
                        state["ready"] = time.monotonic()
                    if not state.get("ready_logged"):
                        state["ready_logged"] = True
                        self._posterTimingWrite(
                            "READY", item, state, "kind=existing_local"
                        )
                    continue

                try:
                    item.local_poster_path = None
                except Exception:
                    pass
                self._posterTimingWrite(
                    "CACHE_INVALID", item, state, "kind=existing_local"
                )

            url = getattr(item, "poster_url", None)
            lookup_t0 = time.monotonic()
            cached = image_cache.get_local_path(url)
            lookup_ms = (time.monotonic() - lookup_t0) * 1000.0
            if cached:
                item.local_poster_path = cached
                state["source"] = "cache"
                state["ready"] = time.monotonic()
                if not state.get("ready_logged"):
                    state["ready_logged"] = True
                    self._posterTimingWrite(
                        "READY",
                        item,
                        state,
                        "kind=cache lookup_ms=%.1f" % lookup_ms,
                    )
                continue

            if not url:
                state["source"] = "no_url"
                if not state.get("ready_logged"):
                    self._posterTimingWrite(
                        "WAIT_URL", item, state, "reason=no_poster_url"
                    )
                continue

            item_key = self._posterItemKey(item)

            try:
                if item_key in self._poster_inflight:
                    continue
                retry_at = float(self._poster_retry_after.get(item_key, 0.0) or 0.0)
                if retry_at > now:
                    continue
                self._poster_inflight.add(item_key)
            except Exception:
                pass

            state["source"] = "fetch"
            if not state.get("request_logged"):
                state["request_logged"] = True
                self._posterTimingWrite("FETCH_START", item, state)

            try:
                image_cache.fetch(
                    url,
                    lambda path, i=item, g=generation, k=item_key:
                        self._onPosterLoaded(i, path, g, k),
                    lambda err, i=item, g=generation, k=item_key:
                        log.safe_call(self._onPosterFailed, i, err, g, k),
                )
            except Exception as exc:
                try:
                    self._poster_inflight.discard(item_key)
                    self._poster_retry_after[item_key] = time.monotonic() + 2.5
                except Exception:
                    pass
                log.warning(
                    "MediaWall: Poster-Download konnte nicht gestartet werden: %s",
                    exc,
                )
                try:
                    self.screen._schedulePosterRepair(2800)
                except Exception:
                    pass

    def _onPosterLoaded(self, item, path, generation=None, item_key=None):
        if item_key is not None:
            try:
                self._poster_inflight.discard(item_key)
                self._poster_retry_after.pop(item_key, None)
            except Exception:
                pass

        if generation is not None and generation != self._poster_generation:
            state = self._posterTimingState(item)
            self._posterTimingWrite(
                "STALE_CALLBACK", item, state, "reason=generation"
            )
            return

        if item_key is not None and item_key != self._posterItemKey(item):
            state = self._posterTimingState(item)
            self._posterTimingWrite(
                "STALE_CALLBACK", item, state, "reason=item_key"
            )
            return

        if not image_cache.is_valid_path(path):
            state = self._posterTimingState(item)
            self._posterTimingWrite(
                "DECODE_REJECT", item, state, "reason=invalid_cache_file"
            )
            try:
                if item_key is not None:
                    self._poster_retry_after[item_key] = time.monotonic() + 2.5
                self.screen._schedulePosterRepair(2800)
            except Exception:
                pass
            return

        state = self._posterTimingState(item)
        if state.get("source") == "unknown":
            state["source"] = "fetch"
        if state.get("ready") is None:
            state["ready"] = time.monotonic()
        if not state.get("ready_logged"):
            state["ready_logged"] = True
            self._posterTimingWrite("FETCH_DONE", item, state)

        item.local_poster_path = path
        render_t0 = time.monotonic()
        self._render()
        render_ms = (time.monotonic() - render_t0) * 1000.0
        self._posterTimingWrite(
            "ROW_RENDER", item, state, "render_ms=%.1f" % render_ms
        )

        try:
            self.screen._updatePreview()
        except Exception:
            pass

    def _onPosterFailed(self, item, err, generation=None, item_key=None):
        if item_key is not None:
            try:
                self._poster_inflight.discard(item_key)
                self._poster_retry_after[item_key] = time.monotonic() + 3.0
            except Exception:
                pass

        if generation is not None and generation != self._poster_generation:
            return
        if item_key is not None and item_key != self._posterItemKey(item):
            return

        state = self._posterTimingState(item)
        state["source"] = "fetch"
        self._posterTimingWrite(
            "FETCH_FAIL", item, state, "error=%r" % str(err)
        )
        log.warning(
            "MediaWall: Poster '%s' nicht ladbar: %s",
            getattr(item, "title", "?"),
            err,
        )

        try:
            self.screen._schedulePosterRepair(3300)
        except Exception:
            pass

    def _getPlaceholder(self):
        if self._placeholder is None:
            self._placeholder = LoadPixmap(_PLACEHOLDER_PATH)
        return self._placeholder

    @staticmethod
    def _provider(item):
        return (getattr(item, "source_label", "") or "").strip().lower()

    @staticmethod
    def _quality(item):
        width = int(getattr(item, "video_width", 0) or 0)
        height = int(getattr(item, "video_height", 0) or 0)
        if width >= 3800 or height >= 2100:
            return "4K"
        if width >= 1900 or height >= 1050:
            return "1080"
        if width >= 1200 or height >= 700:
            return "HD"
        return ""

    @staticmethod
    def _truncate(text, max_len):
        text = text or ""
        return text if len(text) <= max_len else text[:max_len - 1] + "…"

    def _setProviderColor(self, widget, provider):
        if parseColor is None or widget is None or widget.instance is None:
            return
        try:
            widget.instance.setBackgroundColor(parseColor(_PROVIDER_COLORS.get(provider, "#dbe6ef")))
        except Exception:
            pass

    def _render(self):
        placeholder = self._getPlaceholder()
        for slot in range(self.count):
            absolute = self.offset + slot
            focus_w = self.screen.get("%s_focus_%d" % (self.prefix, slot))
            poster_w = self.screen.get("%s_poster_%d" % (self.prefix, slot))
            title_w = self.screen.get("%s_title_%d" % (self.prefix, slot))
            meta_w = self.screen.get("%s_meta_%d" % (self.prefix, slot))
            provider_ws = [
                self.screen.get("%s_provider_top_%d" % (self.prefix, slot)),
                self.screen.get("%s_provider_bottom_%d" % (self.prefix, slot)),
                self.screen.get("%s_provider_left_%d" % (self.prefix, slot)),
                self.screen.get("%s_provider_right_%d" % (self.prefix, slot)),
            ]
            quality_w = self.screen.get("%s_quality_%d" % (self.prefix, slot))

            if absolute >= len(self.items):
                for w in (focus_w, poster_w, title_w, meta_w, quality_w):
                    if w is not None:
                        w.hide()
                for w in provider_ws:
                    if w is not None:
                        w.hide()
                if self.progress:
                    self.screen["%s_progress_bg_%d" % (self.prefix, slot)].hide()
                    self.screen["%s_progress_%d" % (self.prefix, slot)].hide()
                continue

            item = self.items[absolute]
            if self.focused and absolute == self.index:
                focus_w.show()
            else:
                focus_w.hide()

            poster_w.show()
            title_w.show()
            meta_w.show()
            # Provider-Herkunft als duennen farbigen Rahmen direkt um das Poster.
            # Emby=gruen, Jellyfin=blau, Plex=gelb/orange. Kein Text/Badge/Punkt.

            local_poster_path = getattr(item, "local_poster_path", None)
            pix_t0 = time.monotonic()
            pix = LoadPixmap(local_poster_path) if local_poster_path else placeholder
            pix_ms = (time.monotonic() - pix_t0) * 1000.0
            if pix and poster_w.instance:
                poster_w.instance.setPixmap(pix)
                if local_poster_path:
                    state = self._posterTimingState(item)
                    if not state.get("visible_logged"):
                        state["visible_logged"] = True
                        now = time.monotonic()
                        ready = state.get("ready")
                        ready_to_visible_ms = ((now - ready) * 1000.0) if ready is not None else -1.0
                        self._posterTimingWrite(
                            "VISIBLE", item, state,
                            "pixmap_ms=%.1f ready_to_visible_ms=%.1f slot=%d"
                            % (pix_ms, ready_to_visible_ms, slot),
                        )

            raw_title = getattr(item, "title", "") or ""
            series_name = getattr(item, "series_name", "") or ""
            season_number = getattr(item, "season_number", None)
            episode_number = getattr(item, "episode_number", None)

            # HOME_POLISH1: Plex/Emby koennen in "Neu hinzugefuegt" ganze
            # Staffeln als "Season 1", "Season 2" oder "Specials" liefern.
            # Diese Karten werden nicht mehr wie Filme dargestellt.
            season_card = False
            season_label = ""
            folded = raw_title.strip().casefold()
            if folded in ("specials", "special"):
                season_card = True
                season_label = "Spezialfolgen"
            else:
                for _prefix in ("season ", "staffel "):
                    if folded.startswith(_prefix):
                        _number = raw_title.strip()[len(_prefix):].strip()
                        if _number.isdigit():
                            season_card = True
                            season_label = "Staffel %d" % int(_number)
                        break

            # Oben stehen zwei Titelzeilen zur Verfuegung; die kompakteren
            # unteren Reihen behalten ihre bisherige einzeilige Begrenzung.
            # Alle Home-Reihen nutzen dasselbe zweizeilige Titellimit.
            title_limit = 30
            if season_card:
                title_w.setText(self._truncate(season_label, title_limit))
                # Der Serienname ist Zusatzinfo; bei Plex-Season-Directories
                # ist er oft leer, dann bleibt die zweite Zeile bewusst ruhig.
                meta = self._truncate(series_name, 22) if series_name and series_name.casefold() != raw_title.casefold() else ""
            else:
                title_w.setText(self._truncate(raw_title, title_limit))
                if series_name and season_number is not None:
                    meta = "S%d" % int(season_number)
                    if episode_number is not None:
                        meta += " · F%d" % int(episode_number)
                else:
                    meta = str(getattr(item, "year", "") or "")
            meta_w.setText(meta)

            provider = self._provider(item)
            if provider in ("emby", "jellyfin", "plex"):
                for w in provider_ws:
                    if w is not None:
                        w.setText("")
                        self._setProviderColor(w, provider)
                        w.show()
            else:
                for w in provider_ws:
                    if w is not None:
                        w.setText("")
                        w.hide()

            quality = self._quality(item)
            if quality:
                quality_w.setText(quality)
                quality_w.show()
            else:
                quality_w.setText("")
                quality_w.hide()

            if self.progress:
                bg = self.screen["%s_progress_bg_%d" % (self.prefix, slot)]
                fill = self.screen["%s_progress_%d" % (self.prefix, slot)]
                runtime = int(getattr(item, "runtime_ticks", 0) or 0)
                resume = int(getattr(item, "resume_ticks", 0) or 0)
                if runtime > 0 and resume > 0:
                    pct = max(1, min(100, int((resume * 100.0) / runtime)))
                    bg.show()
                    fill.show()
                    if fill.instance:
                        fill.instance.resize(eSize(max(2, int(145 * pct / 100.0)), 5))
                else:
                    bg.hide()
                    fill.hide()


def _poster_widgets(out, prefix, y, count=10, progress=False, x0=48, step=185):
    """Posterreihe; HOME_POLISH2 erlaubt Vollbreite oder Halbbreite."""
    pw, ph = 145, 190
    title_width = 170 if progress else 160
    # Auch Favoriten/Neu hinzugefuegt erhalten zwei echte Titelzeilen.
    title_height = 41
    # Meta/Jahr beginnt unter der zweiten Titelzeile.
    meta_y_offset = 238
    progress_y_offset = 267 if progress else 250
    for i in range(count):
        x = x0 + i * step
        # Cyan-Fokus liegt aussen, der 2px-Providerrahmen direkt am Poster.
        out.append('<widget name="%s_focus_%d" position="%d,%d" size="153,198" backgroundColor="#20c7ee" transparent="0" zPosition="3" />' % (prefix, i, x - 4, y - 4))
        out.append('<widget name="%s_provider_top_%d" position="%d,%d" size="149,2" backgroundColor="#dbe6ef" transparent="0" zPosition="4" />' % (prefix, i, x - 2, y - 2))
        out.append('<widget name="%s_provider_bottom_%d" position="%d,%d" size="149,2" backgroundColor="#dbe6ef" transparent="0" zPosition="4" />' % (prefix, i, x - 2, y + ph))
        out.append('<widget name="%s_provider_left_%d" position="%d,%d" size="2,190" backgroundColor="#dbe6ef" transparent="0" zPosition="4" />' % (prefix, i, x - 2, y))
        out.append('<widget name="%s_provider_right_%d" position="%d,%d" size="2,190" backgroundColor="#dbe6ef" transparent="0" zPosition="4" />' % (prefix, i, x + pw, y))
        out.append('<widget name="%s_poster_%d" position="%d,%d" size="145,190" alphatest="blend" scale="1" zPosition="5" />' % (prefix, i, x, y))
        out.append('<widget name="%s_quality_%d" position="%d,%d" size="56,22" font="Regular;13" foregroundColor="#ffd34f" backgroundColor="#07111a" transparent="0" halign="center" valign="center" zPosition="7" />' % (prefix, i, x + 84, y + 5))
        out.append('<widget name="%s_title_%d" position="%d,%d" size="%d,%d" font="Regular;17" foregroundColor="#f4f6f8" transparent="1" zPosition="7" />' % (prefix, i, x, y + 197, title_width, title_height))
        out.append('<widget name="%s_meta_%d" position="%d,%d" size="160,23" font="Regular;14" foregroundColor="#8f9aa8" transparent="1" zPosition="7" />' % (prefix, i, x, y + meta_y_offset))
        if progress:
            out.append('<widget name="%s_progress_bg_%d" position="%d,%d" size="145,5" backgroundColor="#34495a" transparent="0" zPosition="6" />' % (prefix, i, x, y + progress_y_offset))
            out.append('<widget name="%s_progress_%d" position="%d,%d" size="145,5" backgroundColor="#20c7ee" transparent="0" zPosition="7" />' % (prefix, i, x, y + progress_y_offset))

def _filter_widgets(out, prefix, y, xs=None, widths=None):
    """Vier kompakte Providerfilter; Cyan = Cursor, Farblinie = aktiver Filter."""
    if widths is None:
        widths = [190, 175, 195, 170]
    if xs is None:
        xs = [250, 455, 645, 855]
    for i, (x, width) in enumerate(zip(xs, widths)):
        out.append('<widget name="%s_filter_focus_%d" position="%d,%d" size="%d,44" backgroundColor="#20c7ee" transparent="0" zPosition="3" />' % (prefix, i, x - 3, y - 3, width + 6))
        out.append('<widget name="%s_filter_%d" position="%d,%d" size="%d,38" font="Regular;16" foregroundColor="#e8edf2" backgroundColor="#16222e" transparent="0" halign="center" valign="center" zPosition="4" />' % (prefix, i, x, y, width))
        out.append('<widget name="%s_filter_selected_%d" position="%d,%d" size="%d,4" backgroundColor="#596b78" transparent="0" zPosition="5" />' % (prefix, i, x, y + 40, width))

# =====================================================================
# SKIN / LAYOUT
# =====================================================================
def _build_skin():
    out = [
        '<screen name="MediaPlugins2026HomeScreen" position="0,0" size="1920,1080" backgroundColor="#07111a" flags="wfNoBorder">',
        '<widget name="brand_logo" position="48,15" size="245,54" font="Regular;35" foregroundColor="#f6f7f8" transparent="1" />',
        '<widget name="brand_media" position="294,15" size="105,54" font="Regular;35" foregroundColor="#63cbe9" transparent="1" />',
        '<widget name="tagline" position="50,62" size="420,28" font="Regular;16" foregroundColor="#a5b1bd" transparent="1" />',
        '<widget name="clock_date" position="1420,15" size="450,28" font="Regular;18" foregroundColor="#dce4eb" transparent="1" halign="right" />',
        '<widget name="clock_time" position="1690,45" size="180,34" font="Regular;25" foregroundColor="#f3f6f8" transparent="1" halign="right" />',
        '<widget name="slogan" position="1240,70" size="630,32" font="Regular;20" foregroundColor="#42bde8" transparent="1" halign="right" />',

        '<widget name="continue_label" position="48,96" size="430,34" font="Regular;28" foregroundColor="#f4f6f8" transparent="1" />',
        '<widget name="continue_empty" position="1180,103" size="690,24" font="Regular;14" foregroundColor="#667585" transparent="1" halign="right" />',

        '<widget name="favorites_panel" position="28,410" size="902,345" backgroundColor="#0b1823" transparent="0" zPosition="0" />',
        '<widget name="latest_panel" position="955,410" size="937,345" backgroundColor="#0b1823" transparent="0" zPosition="0" />',
        '<widget name="favorites_label" position="48,423" size="220,42" font="Regular;28" foregroundColor="#f4f6f8" transparent="1" zPosition="2" />',
        '<widget name="latest_label" position="980,423" size="255,42" font="Regular;28" foregroundColor="#f4f6f8" transparent="1" zPosition="2" />',

        # Gemeinsame Live-Detailzone. Die vier schmalen Labels bilden den
        # Cyan-Rahmen, ohne eine grosse undurchsichtige Ebene vor die Inhalte
        # zu legen (wichtig fuer unterschiedliche Enigma2-Skins).
        '<widget name="preview_panel" position="22,788" size="1120,176" backgroundColor="#0b1823" transparent="0" zPosition="0" />',
        '<widget name="availability_panel" position="1148,788" size="318,176" backgroundColor="#101e2a" transparent="0" zPosition="0" />',
        '<widget name="a11y_panel" position="1472,788" size="426,176" backgroundColor="#101e2a" transparent="0" zPosition="0" />',
        # Die drei bisherigen Panels bleiben als blickdichter Fallback auf
        # Ebene 0. Nur bei einem gueltigen Backdrop liegen Bild und dunkle
        # PNG-Maske darueber. Inhalte/Rahmen bleiben unveraendert obenauf.
        '<widget name="preview_ambient" position="22,788" size="1876,176" alphatest="blend" scale="1" zPosition="1" />',
        '<widget name="preview_ambient_shade" position="22,788" size="1876,176" alphatest="blend" scale="1" zPosition="2" />',
        '<widget name="preview_border_top" position="18,784" size="1884,3" backgroundColor="#20c7ee" transparent="0" zPosition="6" />',
        '<widget name="preview_border_bottom" position="18,965" size="1884,3" backgroundColor="#20c7ee" transparent="0" zPosition="6" />',
        '<widget name="preview_border_left" position="18,784" size="3,184" backgroundColor="#20c7ee" transparent="0" zPosition="6" />',
        '<widget name="preview_border_right" position="1899,784" size="3,184" backgroundColor="#20c7ee" transparent="0" zPosition="6" />',
        '<widget name="preview_separator_1" position="1144,798" size="2,154" backgroundColor="#243744" transparent="0" zPosition="3" />',
        '<widget name="preview_separator_2" position="1468,798" size="2,154" backgroundColor="#243744" transparent="0" zPosition="3" />',

        '<widget name="preview_poster" position="38,799" size="110,148" alphatest="blend" scale="1" zPosition="4" />',
        '<widget name="preview_title" position="170,797" size="597,32" font="Regular;24" foregroundColor="#f4f6f8" transparent="1" zPosition="4" />',
        '<widget name="preview_meta" position="170,831" size="597,23" font="Regular;15" foregroundColor="#d5dde5" transparent="1" zPosition="4" />',
        '<widget name="preview_overview" position="170,857" size="597,50" font="Regular;14" foregroundColor="#d7dfe6" transparent="1" zPosition="4" />',
        '<widget name="preview_badges" position="170,921" size="597,23" font="Regular;15" foregroundColor="#f0c94d" transparent="1" zPosition="4" />',
        '<widget name="preview_source" position="790,798" size="325,25" font="Regular;16" foregroundColor="#aebac5" transparent="1" halign="right" zPosition="4" />',
        '<widget name="preview_progress_text" position="790,832" size="325,22" font="Regular;15" foregroundColor="#b6c2cd" transparent="1" halign="right" zPosition="4" />',
        '<widget name="preview_progress_bg" position="880,859" size="235,7" backgroundColor="#34495a" transparent="0" zPosition="3" />',
        '<widget name="preview_progress" position="880,859" size="235,7" backgroundColor="#20c7ee" transparent="0" zPosition="4" />',
        '<widget name="preview_last_played" position="790,878" size="325,21" font="Regular;14" foregroundColor="#c2ccd5" transparent="1" halign="right" zPosition="4" />',
        '<widget name="preview_remaining" position="790,903" size="325,21" font="Regular;14" foregroundColor="#c2ccd5" transparent="1" halign="right" zPosition="4" />',
        '<widget name="preview_primary_action" position="0,0" size="1,1" font="Regular;1" transparent="1" zPosition="1" />',
        '<widget name="preview_secondary_action" position="0,0" size="1,1" font="Regular;1" transparent="1" zPosition="1" />',

        '<widget name="availability_title" position="1170,798" size="270,26" font="Regular;18" foregroundColor="#f4f6f8" transparent="1" zPosition="5" />',

        '<widget name="server_switch_focus_emby" position="1168,828" size="278,35" backgroundColor="#20c7ee" transparent="0" zPosition="3" />',
        '<widget name="server_switch_row_emby" position="1171,831" size="272,29" backgroundColor="#112535" transparent="0" zPosition="4" />',
        '<widget name="availability_emby_icon" position="1182,838" size="16,16" backgroundColor="#37d67a" transparent="0" zPosition="5" />',
        '<widget name="availability_emby_name" position="1210,833" size="128,24" font="Regular;16" foregroundColor="#37d67a" transparent="1" zPosition="5" />',
        '<widget name="availability_emby_meta" position="1340,833" size="92,24" font="Regular;13" foregroundColor="#aebac5" transparent="1" halign="right" zPosition="5" />',

        '<widget name="server_switch_focus_jelly" position="1168,866" size="278,35" backgroundColor="#20c7ee" transparent="0" zPosition="3" />',
        '<widget name="server_switch_row_jelly" position="1171,869" size="272,29" backgroundColor="#112535" transparent="0" zPosition="4" />',
        '<widget name="availability_jelly_icon" position="1182,876" size="16,16" backgroundColor="#3aa7ff" transparent="0" zPosition="5" />',
        '<widget name="availability_jelly_name" position="1210,871" size="128,24" font="Regular;16" foregroundColor="#3aa7ff" transparent="1" zPosition="5" />',
        '<widget name="availability_jelly_meta" position="1340,871" size="92,24" font="Regular;13" foregroundColor="#aebac5" transparent="1" halign="right" zPosition="5" />',

        '<widget name="server_switch_focus_plex" position="1168,904" size="278,35" backgroundColor="#20c7ee" transparent="0" zPosition="3" />',
        '<widget name="server_switch_row_plex" position="1171,907" size="272,29" backgroundColor="#112535" transparent="0" zPosition="4" />',
        '<widget name="availability_plex_icon" position="1182,914" size="16,16" backgroundColor="#f5b82e" transparent="0" zPosition="5" />',
        '<widget name="availability_plex_name" position="1210,909" size="128,24" font="Regular;16" foregroundColor="#f5b82e" transparent="1" zPosition="5" />',
        '<widget name="availability_plex_meta" position="1340,909" size="92,24" font="Regular;13" foregroundColor="#aebac5" transparent="1" halign="right" zPosition="5" />',

        '<widget name="legend_title" position="1495,958" size="1,1" font="Regular;1" transparent="1" zPosition="1" />',
        '<widget name="legend_emby" position="1495,958" size="1,1" font="Regular;1" transparent="1" zPosition="1" />',
        '<widget name="legend_plex" position="1495,958" size="1,1" font="Regular;1" transparent="1" zPosition="1" />',
        '<widget name="legend_jelly" position="1495,958" size="1,1" font="Regular;1" transparent="1" zPosition="1" />',
        '<widget name="legend_focus" position="1495,958" size="1,1" font="Regular;1" transparent="1" zPosition="1" />',
        '<widget name="a11y_title" position="1495,798" size="360,26" font="Regular;19" foregroundColor="#f4f6f8" transparent="1" zPosition="4" />',
        '<widget name="a11y_line1" position="1495,830" size="385,20" font="Regular;15" foregroundColor="#e8edf2" transparent="1" zPosition="4" />',
        '<widget name="a11y_line2" position="1495,853" size="385,20" font="Regular;15" foregroundColor="#e8edf2" transparent="1" zPosition="4" />',
        '<widget name="a11y_line3" position="1495,876" size="385,20" font="Regular;15" foregroundColor="#e8edf2" transparent="1" zPosition="4" />',
        '<widget name="a11y_line4" position="1495,899" size="385,20" font="Regular;15" foregroundColor="#e8edf2" transparent="1" zPosition="4" />',
        '<widget name="a11y_note" position="1495,925" size="385,31" font="Regular;13" foregroundColor="#9aa9b6" transparent="1" zPosition="4" />',
    ]

    _poster_widgets(out, "continue", 136, count=10, progress=True, x0=48, step=185)

    _filter_widgets(out, "favorites", 425,
                    xs=[285, 430, 560, 705], widths=[135, 120, 135, 120])
    _poster_widgets(out, "favorites", 485, count=5, progress=False, x0=48, step=170)

    _filter_widgets(out, "latest", 425,
                    xs=[1240, 1385, 1515, 1660], widths=[135, 120, 135, 120])
    _poster_widgets(out, "latest", 485, count=5, progress=False, x0=980, step=170)

    out += [
        '<widget name="server_status" position="48,1018" size="880,27" font="Regular;16" foregroundColor="#b4c0cb" transparent="1" />',
        '<widget name="message" position="930,1018" size="350,27" font="Regular;15" foregroundColor="#718191" transparent="1" halign="center" />',
        '<widget name="key_red" position="1285,1018" size="140,27" font="Regular;16" foregroundColor="#f34c52" transparent="1" halign="center" />',
        '<widget name="key_green" position="1420,1018" size="130,27" font="Regular;16" foregroundColor="#50ce75" transparent="1" halign="center" />',
        '<widget name="key_yellow" position="1545,1018" size="130,27" font="Regular;16" foregroundColor="#f3c84f" transparent="1" halign="center" />',
        '<widget name="key_blue" position="1670,1018" size="155,27" font="Regular;16" foregroundColor="#42aaf0" transparent="1" halign="center" />',
        '<widget name="key_menu" position="1825,1018" size="75,27" font="Regular;15" foregroundColor="#c5cbd3" transparent="1" halign="right" />',
        '</screen>',
    ]
    return ''.join(out)

# MEDIAPLUGINS2026_POSTER_PIPELINE_STARTFIX2_HOME
# MEDIAPLUGINS2026_HOME_POSTER_SUPERVISOR1
class HomeScreen(Screen):
    skinName = "MediaPlugins2026HomeScreen"

    def __init__(self, session):
        self.skin = _build_skin()
        Screen.__init__(self, session)
        self.session = session

        self.sections = []
        self.continue_items = []
        self.latest_items = []
        self.favorite_items = []
        self._all_continue_items = []
        self._all_latest_items = []
        self._all_favorite_items = []
        self.clients = {}
        self.server_configs = {}
        self.server_libraries = {}
        self.server_status = {}
        self.pending_requests = 0
        self._server_results_pending = {}
        self._child_open = False
        self._home_snapshot_active = False
        self._home_snapshot_loaded_at = 0.0

        self._preview_detail_cache = {}
        self._preview_detail_failed = set()
        self._preview_detail_inflight = {}
        self._preview_detail_pending = None
        self._preview_detail_serial = 0
        self._preview_detail_closed = False
        self._preview_detail_timer = eTimer()
        self._preview_detail_timer.callback.append(self._requestPreviewDetail)
        self.onClose.append(self._closePreviewDetail)

        self._home_slideshow_closed = False
        self._home_slideshow_timer = eTimer()
        self._home_slideshow_timer.callback.append(self._advanceHomeSlideshow)
        self.onClose.append(self._closeHomeSlideshow)

        # HOME_AMBIENT1 besitzt einen eigenen kurzen Entprelltimer. Die
        # Seriennummer verhindert, dass ein altes Bild nach einem schnellen
        # Fokuswechsel in die jetzt aktive Detailzone geschrieben wird.
        self._home_ambient_closed = False
        self._home_ambient_serial = 0
        self._home_ambient_key = None
        self._home_ambient_pending = None
        self._home_ambient_timer = eTimer()
        self._home_ambient_timer.callback.append(self._requestHomeAmbient)
        self.onClose.append(self._closeHomeAmbient)

        self.continue_filter = "all"
        self.favorites_filter = "all"
        self.latest_filter = "all"
        self.favorite_filter_index = 0
        self.latest_filter_index = 0
        self.zone = "continue"  # continue | fav_filter | favorites | latest_filter | latest | server_switch
        self.server_switch_index = 0
        self._server_switch_item = None

        self["brand_logo"] = Label("Media Plugins")
        self["brand_media"] = Label("2026")
        self["tagline"] = Label("Eine App. Alle deine Medien.")
        self["clock_date"] = Label("")
        self["clock_time"] = Label("")

        # Die Home-Uhr wird sekündlich aus der lokalen Box-Zeit aktualisiert.
        # Vorher wurde sie nur einmal bei onLayoutFinish gesetzt.
        self._clock_timer = eTimer()
        try:
            self._clock_timer.callback.append(self._updateClock)
        except Exception:
            try:
                self._clock_timer.timeout.connect(self._updateClock)
            except Exception:
                pass

        self["slogan"] = Label("Filme. Serien. Überall. Zuhause.")
        self["continue_label"] = Label("Weiterschauen")
        self["continue_empty"] = Label("")
        self["favorites_panel"] = Label("")
        self["latest_panel"] = Label("")
        self["favorites_label"] = Label("Favoriten")
        self["latest_label"] = Label("Neu hinzugefügt")
        self["preview_panel"] = Label("")
        self["availability_panel"] = Label("")
        self["preview_ambient"] = Pixmap()
        self["preview_ambient_shade"] = Pixmap()
        self["preview_border_top"] = Label("")
        self["preview_border_bottom"] = Label("")
        self["preview_border_left"] = Label("")
        self["preview_border_right"] = Label("")
        self["preview_separator_1"] = Label("")
        self["preview_separator_2"] = Label("")
        self["preview_poster"] = Pixmap()
        self["preview_title"] = Label("")
        self["preview_meta"] = Label("")
        self["preview_overview"] = Label("")
        self["preview_badges"] = Label("")
        self["preview_source"] = Label("")
        self["preview_progress_text"] = Label("")
        self["preview_progress_bg"] = Label("")
        self["preview_progress"] = Label("")
        self["preview_last_played"] = Label("")
        self["preview_remaining"] = Label("")
        self["preview_primary_action"] = Label("")
        self["preview_secondary_action"] = Label("Details anzeigen")
        self["availability_title"] = Label("Zu Server wechseln")
        self["server_switch_focus_emby"] = Label("")
        self["server_switch_row_emby"] = Label("")
        self["server_switch_focus_jelly"] = Label("")
        self["server_switch_row_jelly"] = Label("")
        self["server_switch_focus_plex"] = Label("")
        self["server_switch_row_plex"] = Label("")
        self["availability_emby_icon"] = Label("")
        self["availability_emby_name"] = Label("Emby")
        self["availability_emby_meta"] = Label("")
        self["availability_plex_icon"] = Label("")
        self["availability_plex_name"] = Label("Plex")
        self["availability_plex_meta"] = Label("")
        self["availability_jelly_icon"] = Label("")
        self["availability_jelly_name"] = Label("Jellyfin")
        self["availability_jelly_meta"] = Label("")
        self["server_status"] = Label("")
        self["message"] = Label("")
        self["a11y_panel"] = Label("")
        self["a11y_title"] = Label("Hinweis")
        self["a11y_line1"] = Label("✓ Cyan zeigt die aktuelle Auswahl")
        self["a11y_line2"] = Label("✓ 2 px Provider-Rahmen")
        self["a11y_line3"] = Label("✓ Providerfarben = Herkunft")
        self["a11y_line4"] = Label("✓ Fokus bleibt providerunabhängig")
        self["a11y_note"] = Label("Doppelte 1080p/4K-Versionen werden pro Anbieter nur einmal angezeigt.")
        self["legend_title"] = Label("Provider-Rahmen")
        self["legend_emby"] = Label("■  Grün     Emby")
        self["legend_plex"] = Label("■  Orange   Plex")
        self["legend_jelly"] = Label("■  Blau     Jellyfin")
        self["legend_focus"] = Label("■  Cyan     Auswahl / Fokus")
        self["key_red"] = Label("■ Beenden")
        self["key_green"] = Label("■ Emby")
        self["key_yellow"] = Label("■ Plex")
        self["key_blue"] = Label("■ Jellyfin")
        self["key_menu"] = Label("MENU")

        for prefix in ("favorites", "latest"):
            for i in range(4):
                self["%s_filter_focus_%d" % (prefix, i)] = Label("")
                self["%s_filter_%d" % (prefix, i)] = Label("")
                self["%s_filter_selected_%d" % (prefix, i)] = Label("")

        self.continueRow = MediaWallRow(self, "continue", count=10, progress=True)
        self.favoritesRow = MediaWallRow(self, "favorites", count=5, progress=False)
        self.latestRow = MediaWallRow(self, "latest", count=5, progress=False)

        self._poster_repair_closed = False
        self._poster_repair_round = 0
        self._poster_repair_started = time.monotonic()
        self._poster_repair_timer = eTimer()
        self._poster_repair_timer.callback.append(self._repairVisiblePosters)
        self.onClose.append(self._closePosterRepair)

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions"],
            {
                "ok": self.keyOk,
                "cancel": self.keyCancel,
                "up": self.keyUp,
                "down": self.keyDown,
                "left": self.keyLeft,
                "right": self.keyRight,
                "red": self.keyCancel,
                "green": self.keyOpenEmbyLibraries,
                "yellow": self.keyOpenPlexLibraries,
                "blue": self.keyOpenJellyfinLibraries,
                "menu": self.keyOpenSettings,
            }, -1
        )
        self.onLayoutFinish.append(self._onLayoutFinish)
        try:
            self.onClose.append(self._stopClockTimer)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Laden / Backend
    # ------------------------------------------------------------------
    def _onLayoutFinish(self):
        self._updateClock()
        self._refreshFocus()
        log.safe_call(self.loadHome)

    def _updateClock(self):
        try:
            now = time.localtime()
            self["clock_date"].setText(
                time.strftime("%a, %d. %b %Y", now)
            )
            self["clock_time"].setText(
                time.strftime("%H:%M", now)
            )
        except Exception:
            pass

        # Single-shot bewusst selbst wieder starten: damit funktioniert die
        # Uhr auf unterschiedlichen Enigma2/eTimer-Implementierungen stabil.
        try:
            self._clock_timer.start(1000, True)
        except Exception:
            pass

    def _stopClockTimer(self):
        try:
            self._clock_timer.stop()
        except Exception:
            pass

    # MEDIAPLUGINS2026_POSTER_PIPELINE_HARDEN1_HOME
    def _schedulePosterRepair(self, delay_ms=1200, reset=False):
        if self._poster_repair_closed:
            return
        if reset:
            self._poster_repair_round = 0
            self._poster_repair_started = time.monotonic()

        try:
            self._poster_repair_timer.stop()
        except Exception:
            pass
        try:
            self._poster_repair_timer.start(max(100, int(delay_ms)), True)
        except Exception:
            pass

    def _repairVisiblePosters(self):
        if self._poster_repair_closed:
            return

        self._poster_repair_round += 1
        ready = 0
        total = 0

        for row in (self.continueRow, self.favoritesRow, self.latestRow):
            try:
                row._prefetchVisible()
                row._render()
                row_ready, row_total = row._visiblePosterStats()
                ready += row_ready
                total += row_total
            except Exception as exc:
                log.warning("Poster-Supervisor row fehlgeschlagen: %s", exc)

        if total <= 0 or ready >= total:
            return

        round_no = int(self._poster_repair_round or 0)
        if round_no < 6:
            delay = 1200
        elif round_no < 14:
            delay = 2500
        elif round_no < 24:
            delay = 5000
        else:
            log.warning(
                "Poster-Supervisor beendet nach %d Runden: sichtbar %d/%d",
                round_no, ready, total,
            )
            return

        self._schedulePosterRepair(delay)

    def _closePosterRepair(self):
        self._poster_repair_closed = True
        try:
            self._poster_repair_timer.stop()
        except Exception:
            pass

    # =================================================================
    # HOME LOAD / PROVIDER REQUESTS
    # =================================================================
    def loadHome(self):
        from ..config import get_configured_servers, config_store
        from ..backends.factory import create_client_for_server

        self.sections = []
        self.continue_items = []
        self.latest_items = []
        self.favorite_items = []
        self._all_continue_items = []
        self._all_latest_items = []
        self._all_favorite_items = []
        self.clients = {}
        self.server_configs = {}
        self.server_libraries = {}
        self.server_status = {}
        self._server_results_pending = {}
        self.server_switch_index = 0
        self._server_switch_item = None
        if self.zone == "server_switch":
            self.zone = "continue"
        try:
            self._home_slideshow_timer.stop()
        except Exception:
            pass
        self._home_ambient_serial += 1
        self._home_ambient_key = None
        self._home_ambient_pending = None
        try:
            self._home_ambient_timer.stop()
        except Exception:
            pass
        self._hideHomeAmbient()
        # Server/Anmeldung koennen sich nach den Einstellungen geaendert
        # haben; deshalb keine alten Detailobjekte in den neuen Lauf tragen.
        self._preview_detail_cache.clear()
        self._preview_detail_failed.clear()
        self._preview_detail_inflight.clear()
        self._preview_detail_pending = None
        self._preview_detail_serial += 1
        try:
            self._preview_detail_timer.stop()
        except Exception:
            pass
        self._timing_load_started = time.monotonic()
        self._pipelineTiming("HOME_START")
        _poster_timing_log("=== HOME_LOAD_START ===")
        self._timing_login_started = {}
        self._timing_sub_started = {}
        self.continueRow.setItems([])
        self.favoritesRow.setItems([])
        self.latestRow.setItems([])
        self["message"].setText("Lade Inhalte …")
        self._renderFilters()
        self._renderStatus()

        # r8: vor dem Laden noch einmal nach bereits eingerichteten
        # Einzelplugins suchen. So muss niemand Emby/Jellyfin/Plex doppelt
        # eingeben; die Fremdkonfiguration bleibt unangetastet.
        imported = config_store.auto_import_existing()
        servers = get_configured_servers()
        log.info("TIMING HOME +%.3fs START providers=%s", time.monotonic() - self._timing_load_started, ",".join((getattr(x, "protocol", "?") or "?") for x in servers))
        if imported:
            self["message"].setText("Zugaenge uebernommen: %s" % ", ".join(sorted(set(p.capitalize() for p in imported))))
        if not servers:
            # R6: echte Layout-Vorschau auch ohne Server. Die Dummy-Eintraege
            # sind rein lokal, werden nie abgespielt und verschwinden sofort,
            # sobald mindestens ein echter Server eingerichtet ist.
            self._loadDemoPreview()
            return

        # HOME_SNAPSHOT1: alten, bereits vollstaendig gerenderten Home-Stand
        # sofort anzeigen. Die echten Serverrequests starten danach unveraendert.
        self._restoreHomeSnapshot(servers)
        self._schedulePosterRepair(900, reset=True)
        self["continue_empty"].setText("")
        self.pending_requests = len(servers)
        for server_cfg in servers:
            self.server_configs[server_cfg.name] = server_cfg
            self.server_status[server_cfg.name] = "connecting"
            try:
                client = create_client_for_server(server_cfg)
            except Exception as e:
                log.exception("Client fuer %s konnte nicht erstellt werden: %s", server_cfg.name, e)
                self._onServerError(server_cfg, str(e))
                continue
            self.clients[server_cfg.name] = client
            self._timing_login_started[server_cfg.name] = time.monotonic()
            self._pipelineTiming("LOGIN_START", "server=%r provider=%s" % (server_cfg.name, getattr(server_cfg, "protocol", "?")))
            log.info("TIMING HOME +%.3fs %s LOGIN start protocol=%s", time.monotonic() - self._timing_load_started, server_cfg.name, getattr(server_cfg, "protocol", "?"))
            client.login(
                lambda token, uid, s=server_cfg, c=client: log.safe_call(self._onLogin, s, c),
                lambda err, s=server_cfg: log.safe_call(self._onServerError, s, err),
            )
        self._renderStatus()

    def _onLogin(self, server_cfg, client):
        now = time.monotonic()
        login_started = self._timing_login_started.get(server_cfg.name, now)
        log.info("TIMING HOME +%.3fs %s LOGIN ok in %.3fs", now - self._timing_load_started, server_cfg.name, now - login_started)
        self._pipelineTiming("LOGIN_OK", "server=%r provider=%s login_ms=%.1f" % (server_cfg.name, getattr(server_cfg, "protocol", "?"), (now - login_started) * 1000.0))
        # Erfolgreich verwendete/importierte Tokens lokal merken. Das spart
        # auch bei kuenftigen Starts eine erneute Passwort-Anmeldung.
        try:
            from ..config import config_store
            config_store.update_server_auth(server_cfg.name, getattr(client, "token", ""), getattr(client, "user_id", ""))
            if ((getattr(server_cfg, "protocol", "") or "").lower() == "plex" and
                    (getattr(server_cfg, "address", "") or "").rstrip("/").lower() == "plex://account-discovery"):
                discovered = getattr(client, "_active_base_url", "") or ""
                if discovered.startswith(("http://", "https://")):
                    config_store.update_server_endpoint(server_cfg.name, discovered)
                    server_cfg.address = discovered
        except Exception:
            pass
        self.server_status[server_cfg.name] = "online"
        self._server_results_pending[server_cfg.name] = 3
        self._renderStatus()
        self._timing_sub_started[(server_cfg.name, "Home")] = time.monotonic()
        self._timing_sub_started[(server_cfg.name, "Libraries")] = time.monotonic()
        self._timing_sub_started[(server_cfg.name, "Favorites")] = time.monotonic()
        log.info("TIMING HOME +%.3fs %s subrequests START Home,Libraries,Favorites", time.monotonic() - self._timing_load_started, server_cfg.name)
        self._pipelineTiming("SUBREQ_START", "server=%r names=Home,Libraries,Favorites" % server_cfg.name)
        client.get_home_sections(
            lambda sections, s=server_cfg: log.safe_call(self._onSectionsLoaded, s, sections),
            lambda err, s=server_cfg: log.safe_call(self._onSubRequestError, s, "Home", err),
        )
        client.get_libraries(
            lambda libs, s=server_cfg, c=client: log.safe_call(self._onLibrariesLoaded, s, c, libs),
            lambda err, s=server_cfg: log.safe_call(self._onSubRequestError, s, "Libraries", err),
        )
        try:
            client.get_favorites(
                lambda items, s=server_cfg: log.safe_call(self._onFavoritesLoaded, s, items),
                lambda err, s=server_cfg: log.safe_call(self._onSubRequestError, s, "Favorites", err),
                limit=300,
            )
        except TypeError:
            client.get_favorites(
                lambda items, s=server_cfg: log.safe_call(self._onFavoritesLoaded, s, items),
                lambda err, s=server_cfg: log.safe_call(self._onSubRequestError, s, "Favorites", err),
            )
        except Exception as e:
            self._onSubRequestError(server_cfg, "Favorites", str(e))

    def _tagItems(self, server_cfg, items):
        provider = (getattr(server_cfg, "protocol", "") or "").upper()
        for item in items or []:
            item.source_label = provider
        return items or []

    def _pipelineTiming(self, event, extra=""):
        if not _DEBUG_TIMING:
            return
        try:
            started = getattr(self, "_timing_load_started", None)
            if started is None:
                elapsed_ms = -1.0
            else:
                elapsed_ms = max(0.0, (time.monotonic() - started) * 1000.0)
            suffix = (" " + str(extra)) if extra else ""
            _pipeline_timing_write("%s home_ms=%.1f%s" % (event, elapsed_ms, suffix))
        except Exception:
            pass

    # =================================================================
    # SNAPSHOT / COLD START
    # =================================================================
    @staticmethod
    def _homeSnapshotServerKey(servers):
        return sorted([
            [str(getattr(server, "name", "") or ""), str(getattr(server, "protocol", "") or "").lower()]
            for server in (servers or [])
        ])

    @staticmethod
    def _homeSnapshotItemData(item):
        # Absichtlich keine poster_url/backdrop_url/stream_url: diese koennen
        # Auth-Tokens enthalten. Fuer den Sofortstart reicht der lokale
        # Poster-Cache plus die UI-Metadaten.
        local_path = str(getattr(item, "local_poster_path", "") or "")
        if local_path and not os.path.isfile(local_path):
            local_path = ""
        return {
            "id": str(getattr(item, "id", "") or ""),
            "title": str(getattr(item, "title", "") or ""),
            "server_name": str(getattr(item, "server_name", "") or ""),
            "source_label": str(getattr(item, "source_label", "") or ""),
            "year": getattr(item, "year", None),
            "overview": str(getattr(item, "overview", "") or ""),
            "genres": list(getattr(item, "genres", None) or []),
            "rating": getattr(item, "rating", None),
            "resume_ticks": int(getattr(item, "resume_ticks", 0) or 0),
            "played": bool(getattr(item, "played", False)),
            "last_played_date": str(getattr(item, "last_played_date", "") or ""),
            "date_created": str(getattr(item, "date_created", "") or ""),
            "series_name": str(getattr(item, "series_name", "") or ""),
            "season_number": getattr(item, "season_number", None),
            "episode_number": getattr(item, "episode_number", None),
            "video_codec": str(getattr(item, "video_codec", "") or ""),
            "video_width": int(getattr(item, "video_width", 0) or 0),
            "video_height": int(getattr(item, "video_height", 0) or 0),
            "audio_codec": str(getattr(item, "audio_codec", "") or ""),
            "audio_channels": int(getattr(item, "audio_channels", 0) or 0),
            "runtime_ticks": int(getattr(item, "runtime_ticks", 0) or 0),
            "provider_ids": dict(getattr(item, "provider_ids", None) or {}),
            "is_favorite": bool(getattr(item, "is_favorite", False)),
            "video_type": str(getattr(item, "video_type", "") or ""),
            "container": str(getattr(item, "container", "") or ""),
            "parent_id": str(getattr(item, "parent_id", "") or ""),
            "local_poster_path": local_path,
        }

    @staticmethod
    def _homeSnapshotItemFromData(raw):
        if not isinstance(raw, dict):
            return None
        item_id = str(raw.get("id") or "")
        title = str(raw.get("title") or "")
        server_name = str(raw.get("server_name") or "")
        if not item_id or not server_name:
            return None
        item = MediaItem(item_id=item_id, title=title, server_name=server_name)
        for attr in (
            "source_label", "year", "overview", "genres", "rating",
            "resume_ticks", "played", "last_played_date", "date_created",
            "series_name", "season_number", "episode_number", "video_codec",
            "video_width", "video_height", "audio_codec", "audio_channels",
            "runtime_ticks", "provider_ids", "is_favorite", "video_type",
            "container", "parent_id",
        ):
            if attr in raw:
                try:
                    setattr(item, attr, raw.get(attr))
                except Exception:
                    pass
        local_path = str(raw.get("local_poster_path") or "")
        if local_path and os.path.isfile(local_path):
            item.local_poster_path = local_path
        item._infuse_home_snapshot = True
        return item

    @staticmethod
    def _homeSnapshotRowSignature(items):
        return tuple(
            (
                str(getattr(item, "server_name", "") or ""),
                str(getattr(item, "id", "") or ""),
                str(getattr(item, "title", "") or ""),
                int(getattr(item, "resume_ticks", 0) or 0),
                str(getattr(item, "date_created", "") or ""),
                str(getattr(item, "last_played_date", "") or ""),
            )
            for item in (items or [])
        )

    def _restoreHomeSnapshot(self, servers):
        self._home_snapshot_active = False
        try:
            if not os.path.isfile(_HOME_SNAPSHOT_PATH):
                self._pipelineTiming("SNAPSHOT_MISS", "reason=no_file")
                return False
            with open(_HOME_SNAPSHOT_PATH, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict) or int(payload.get("version") or 0) != _HOME_SNAPSHOT_VERSION:
                self._pipelineTiming("SNAPSHOT_MISS", "reason=version")
                return False
            if payload.get("servers") != self._homeSnapshotServerKey(servers):
                self._pipelineTiming("SNAPSHOT_MISS", "reason=server_set")
                return False
            saved_at = float(payload.get("saved_at") or 0.0)
            if saved_at <= 0 or (time.time() - saved_at) > _HOME_SNAPSHOT_MAX_AGE:
                self._pipelineTiming("SNAPSHOT_MISS", "reason=age")
                return False

            rows = payload.get("rows") or {}
            continue_items = [self._homeSnapshotItemFromData(x) for x in (rows.get("continue") or [])]
            favorite_items = [self._homeSnapshotItemFromData(x) for x in (rows.get("favorites") or [])]
            latest_items = [self._homeSnapshotItemFromData(x) for x in (rows.get("latest") or [])]
            continue_items = [x for x in continue_items if x is not None]
            favorite_items = [x for x in favorite_items if x is not None]
            latest_items = [x for x in latest_items if x is not None]
            if not (continue_items or favorite_items or latest_items):
                self._pipelineTiming("SNAPSHOT_MISS", "reason=empty")
                return False

            self._all_continue_items = continue_items
            self._all_favorite_items = favorite_items
            self._all_latest_items = latest_items
            self._home_snapshot_active = True
            self._home_snapshot_loaded_at = time.monotonic()
            self._applyFilters()
            self["message"].setText("Aktualisiere Inhalte …")
            self._refreshFocus()
            self._pipelineTiming(
                "SNAPSHOT_HIT",
                "continue=%d favorites=%d latest=%d" %
                (len(continue_items), len(favorite_items), len(latest_items)),
            )
            return True
        except Exception as exc:
            self._pipelineTiming("SNAPSHOT_MISS", "reason=error error=%r" % (str(exc),))
            return False

    def _saveHomeSnapshot(self):
        try:
            payload = {
                "version": _HOME_SNAPSHOT_VERSION,
                "saved_at": time.time(),
                "servers": self._homeSnapshotServerKey(list(self.server_configs.values())),
                "rows": {
                    "continue": [self._homeSnapshotItemData(x) for x in self._all_continue_items],
                    "favorites": [self._homeSnapshotItemData(x) for x in self._all_favorite_items],
                    "latest": [self._homeSnapshotItemData(x) for x in self._all_latest_items],
                },
            }
            directory = os.path.dirname(_HOME_SNAPSHOT_PATH)
            if directory and not os.path.isdir(directory):
                os.makedirs(directory)
            tmp_path = _HOME_SNAPSHOT_PATH + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            try:
                os.chmod(tmp_path, 0o600)
            except Exception:
                pass
            os.replace(tmp_path, _HOME_SNAPSHOT_PATH)
            try:
                os.chmod(_HOME_SNAPSHOT_PATH, 0o600)
            except Exception:
                pass
            self._pipelineTiming(
                "SNAPSHOT_SAVE",
                "continue=%d favorites=%d latest=%d" %
                (len(self._all_continue_items), len(self._all_favorite_items), len(self._all_latest_items)),
            )
        except Exception as exc:
            self._pipelineTiming("SNAPSHOT_SAVE_FAIL", "error=%r" % (str(exc),))

    def _loadDemoPreview(self):
        """Lokale Dummy-Media-Wall fuer die Designkontrolle ohne Server.

        Keine Netzwerkzugriffe, keine Fake-Logins und keine Wiedergabe. Sobald
        ein Server konfiguriert ist, wird diese Vorschau nicht mehr verwendet.
        """
        specs = [
            ("Nordlicht", 2026, "emby", 3840, 2160),
            ("Neon City", 2025, "jellyfin", 1920, 1080),
            ("Red Horizon", 2024, "plex", 1280, 720),
            ("After Midnight", 2026, "emby", 1920, 1080),
            ("Deep Signal", 2023, "jellyfin", 3840, 2160),
            ("Paper Moon", 2025, "plex", 1920, 1080),
            ("Cold Harbour", 2024, "emby", 1280, 720),
            ("Electric Summer", 2026, "jellyfin", 1920, 1080),
            ("Night Train", 2022, "plex", 3840, 2160),
            ("Blue Hour", 2025, "emby", 1920, 1080),
            ("Last Orbit", 2026, "jellyfin", 1280, 720),
            ("Golden Dust", 2023, "plex", 1920, 1080),
        ]
        items = []
        for idx, (title, year, provider, width, height) in enumerate(specs, 1):
            runtime = (82 + idx * 5) * 60 * 10000000
            resume = int(runtime * (0.12 + ((idx * 7) % 62) / 100.0))
            item = MediaItem(
                item_id="demo-%02d" % idx,
                title=title,
                server_name="demo-%s" % provider,
                year=year,
                video_width=width,
                video_height=height,
                runtime_ticks=runtime,
                resume_ticks=resume,
                date_created="2026-09-%02dT12:00:00Z" % max(1, 13 - idx),
                last_played_date="2026-09-%02dT20:00:00Z" % max(1, 13 - idx),
                is_favorite=(idx <= 9),
            )
            item.source_label = provider.upper()
            item.local_poster_path = "%s/demo_%02d.png" % (_DEMO_DIR, idx)
            item.is_demo = True
            items.append(item)

        self._all_continue_items = list(items[:8])
        self._all_favorite_items = list(items[1:10])
        self._all_latest_items = list(reversed(items[2:12]))
        self.continue_items = list(self._all_continue_items)
        self.favorite_items = list(self._all_favorite_items)
        self.latest_items = list(self._all_latest_items)
        self.continue_filter = "all"
        self.favorites_filter = "all"
        self.latest_filter = "all"
        self.favorite_filter_index = 0
        self.latest_filter_index = 0
        self.zone = "continue"
        self.server_switch_index = 0
        self._server_switch_item = None
        self._applyFilters()
        self["continue_empty"].setText("Demo · BLAU: Server einrichten")
        self["message"].setText("Demo")
        self["server_status"].setText("Demoansicht:   ● Emby   ● Jellyfin   ● Plex   · noch nicht verbunden")
        self._refreshFocus()

    def _onSectionsLoaded(self, server_cfg, raw_sections):
        now = time.monotonic()
        started = self._timing_sub_started.get((server_cfg.name, "Home"), now)
        section_counts = [(r.get("title", "?"), len(r.get("items") or [])) for r in (raw_sections or [])]
        log.info("TIMING HOME +%.3fs %s Home ok in %.3fs sections=%s", now - self._timing_load_started, server_cfg.name, now - started, section_counts)
        self._pipelineTiming("HOME_OK", "server=%r request_ms=%.1f sections=%r" % (server_cfg.name, (now - started) * 1000.0, section_counts))
        for raw in raw_sections or []:
            items = self._tagItems(server_cfg, raw.get("items") or [])
            if raw.get("is_resume"):
                self.continue_items.extend(items)
            else:
                self.sections.append(HomeSection(raw.get("title", ""), server_cfg.name, items))
                # Funktionale Erkennung ueber eine stabile technische ID;
                # der sichtbare/uebersetzbare Titel ist nur noch Darstellung.
                if raw.get("section_id") == "latest":
                    self.latest_items.extend(items)

        # r16 fast-home: nicht mehr auf alle Server/Unterabfragen warten.
        # Sobald z.B. Emby seine Home-Reihen geliefert hat, werden sie sofort
        # sichtbar. Ein langsamer/offliner Plex darf die komplette Media-Wall
        # nicht mehr bis zum Netzwerk-Timeout leer halten.
        self._refreshProgressiveLayout()
        self._subRequestFinished(server_cfg)

    def _onFavoritesLoaded(self, server_cfg, items):
        now = time.monotonic()
        started = self._timing_sub_started.get((server_cfg.name, "Favorites"), now)
        log.info("TIMING HOME +%.3fs %s Favorites ok in %.3fs count=%d", now - self._timing_load_started, server_cfg.name, now - started, len(items or []))
        self._pipelineTiming("FAVORITES_OK", "server=%r request_ms=%.1f count=%d" % (server_cfg.name, (now - started) * 1000.0, len(items or [])))
        tagged = self._tagItems(server_cfg, items or [])
        for item in tagged:
            item.is_favorite = True
        self.favorite_items.extend(tagged)
        self._refreshProgressiveLayout()
        self._subRequestFinished(server_cfg)

    def _onLibrariesLoaded(self, server_cfg, client, raw_libraries):
        now = time.monotonic()
        started = self._timing_sub_started.get((server_cfg.name, "Libraries"), now)
        log.info("TIMING HOME +%.3fs %s Libraries ok in %.3fs count=%d", now - self._timing_load_started, server_cfg.name, now - started, len(raw_libraries or []))
        self._pipelineTiming("LIBRARIES_OK", "server=%r request_ms=%.1f count=%d" % (server_cfg.name, (now - started) * 1000.0, len(raw_libraries or [])))
        libs = []
        for raw in raw_libraries or []:
            lib_id = raw.get("Id")
            if not lib_id:
                continue
            item = MediaItem(
                item_id=lib_id,
                title=raw.get("Name") or "Bibliothek",
                server_name=server_cfg.name,
                poster_url=client.get_image_url(lib_id, "Primary"),
            )
            item.is_library = True
            item.library_id = lib_id
            item.source_label = (getattr(server_cfg, "protocol", "") or "").upper()
            libs.append(item)
        self.server_libraries[server_cfg.name] = libs
        self._subRequestFinished(server_cfg)

    def _onSubRequestError(self, server_cfg, request_name, err):
        now = time.monotonic()
        started = self._timing_sub_started.get((server_cfg.name, request_name), now)
        log.warning("TIMING HOME +%.3fs %s %s FAIL in %.3fs: %s", now - self._timing_load_started, server_cfg.name, request_name, now - started, err)
        self._pipelineTiming("SUBREQ_FAIL", "server=%r name=%s request_ms=%.1f error=%r" % (server_cfg.name, request_name, (now - started) * 1000.0, str(err)))
        log.warning("MediaWall %s fuer %s fehlgeschlagen: %s", request_name, server_cfg.name, err)
        self._subRequestFinished(server_cfg)

    def _subRequestFinished(self, server_cfg):
        name = server_cfg.name
        left = self._server_results_pending.get(name, 1) - 1
        self._server_results_pending[name] = left
        self._pipelineTiming("SUBREQ_DONE", "server=%r remaining=%d" % (name, left))
        if left <= 0:
            self._requestFinished()

    @staticmethod
    def _classifyServerFailure(err):
        text = (str(err or "")).strip().lower()
        auth_markers = (
            "401", "403", "unauthorized", "forbidden",
            "authentication", "auth failed", "login failed",
            "invalid token", "expired token", "token expired",
            "invalid credentials", "access denied", "not authorized",
            "account locked", "locked out", "account disabled",
            "account suspended",
        )
        if any(marker in text for marker in auth_markers):
            return "auth"

        offline_markers = (
            "timeout", "timed out", "connection refused",
            "connection reset", "connection aborted", "network is unreachable",
            "no route to host", "name or service not known",
            "temporary failure in name resolution", "dns",
            "host unreachable", "server unreachable",
        )
        if any(marker in text for marker in offline_markers):
            return "offline"
        return "error"

    def _onServerError(self, server_cfg, err):
        now = time.monotonic()
        started = self._timing_login_started.get(server_cfg.name, now)
        log.warning("TIMING HOME +%.3fs %s LOGIN FAIL in %.3fs: %s", now - self._timing_load_started, server_cfg.name, now - started, err)
        self._pipelineTiming("LOGIN_FAIL", "server=%r login_ms=%.1f error=%r" % (server_cfg.name, (now - started) * 1000.0, str(err)))
        state = self._classifyServerFailure(err)
        self.server_status[server_cfg.name] = state
        log.warning("Server %s status=%s: %s", server_cfg.name, state, err)
        self._renderStatus()
        self._renderServerSwitch()
        self._requestFinished()

    def _requestFinished(self):
        self.pending_requests -= 1
        self._pipelineTiming("PROVIDER_DONE", "providers_remaining=%d" % self.pending_requests)
        if self.pending_requests <= 0:
            self._buildLayout()

    def _refreshProgressiveLayout(self):
        """Zeigt bereits eingetroffene Provider-Daten sofort an.

        Die Netzabfragen bleiben asynchron aktiv. Die endgueltige Sortierung
        erfolgt weiterhin in _buildLayout(), sobald alle Provider fertig sind.
        Dadurch blockiert ein langsamer/offliner Server nicht mehr den ersten
        sichtbaren Aufbau der Startseite.
        """
        refresh_t0 = time.monotonic()
        self._pipelineTiming(
            "REFRESH_START",
            "raw_continue=%d raw_favorites=%d raw_latest=%d" %
            (len(self.continue_items), len(self.favorite_items), len(self.latest_items)),
        )
        if self._home_snapshot_active:
            self._pipelineTiming(
                "REFRESH_DEFERRED_SNAPSHOT",
                "raw_continue=%d raw_favorites=%d raw_latest=%d" %
                (len(self.continue_items), len(self.favorite_items), len(self.latest_items)),
            )
            return
        self._all_continue_items = self._homeDedupe(self._interleaveByServer(list(self.continue_items), "last_played_date"), "last_played_date")
        self._all_latest_items = self._homeDedupe(self._interleaveByServer(list(self.latest_items), "date_created"), "date_created")
        self._all_favorite_items = self._homeDedupe(self._interleaveByServer(list(self.favorite_items), "date_created"), "date_created")
        self._applyFilters()
        if self._all_continue_items or self._all_latest_items or self._all_favorite_items:
            self["message"].setText("")
        self._renderStatus()
        self._refreshFocus()
        self._pipelineTiming(
            "REFRESH_DONE",
            "cost_ms=%.1f continue=%d favorites=%d latest=%d visible_continue=%d visible_favorites=%d visible_latest=%d" %
            (
                (time.monotonic() - refresh_t0) * 1000.0,
                len(self._all_continue_items), len(self._all_favorite_items), len(self._all_latest_items),
                self.continueRow.getCount(), self.favoritesRow.getCount(), self.latestRow.getCount(),
            ),
        )

    # =================================================================
    # PROGRESSIVE RENDER / SNAPSHOT SWAP
    # =================================================================
    @staticmethod
    def _homeVisibleRowSignature(items):
        return tuple(
            (
                str(getattr(item, "server_name", "") or ""),
                str(getattr(item, "id", "") or ""),
                str(getattr(item, "title", "") or ""),
                str(getattr(item, "source_label", "") or ""),
                getattr(item, "year", None),
                int(getattr(item, "resume_ticks", 0) or 0),
                int(getattr(item, "runtime_ticks", 0) or 0),
                str(getattr(item, "series_name", "") or ""),
                getattr(item, "season_number", None),
                getattr(item, "episode_number", None),
                int(getattr(item, "video_width", 0) or 0),
                int(getattr(item, "video_height", 0) or 0),
            )
            for item in (items or [])
        )

    @staticmethod
    def _homeRenderedCardSignature(item, progress=False):
        raw_title = str(getattr(item, "title", "") or "")
        series_name = str(getattr(item, "series_name", "") or "")
        season_number = getattr(item, "season_number", None)
        episode_number = getattr(item, "episode_number", None)

        season_card = False
        season_label = ""
        folded = raw_title.strip().casefold()
        if folded in ("specials", "special"):
            season_card = True
            season_label = "Spezialfolgen"
        else:
            for prefix in ("season ", "staffel "):
                if folded.startswith(prefix):
                    number = raw_title.strip()[len(prefix):].strip()
                    if number.isdigit():
                        season_card = True
                        season_label = "Staffel %d" % int(number)
                    break

        title_limit = 30 if progress else 22
        if season_card:
            visible_title = season_label
            visible_meta = series_name if series_name and series_name.casefold() != raw_title.casefold() else ""
        else:
            visible_title = raw_title
            if series_name and season_number is not None:
                visible_meta = "S%d" % int(season_number)
                if episode_number is not None:
                    visible_meta += " · F%d" % int(episode_number)
            else:
                visible_meta = str(getattr(item, "year", "") or "")

        def trunc(value, limit):
            value = value or ""
            return value if len(value) <= limit else value[:limit - 1] + "…"

        visible_title = trunc(visible_title, title_limit)
        visible_meta = trunc(visible_meta, 22) if season_card else visible_meta

        provider = str(getattr(item, "source_label", "") or "").strip().lower()
        if provider not in ("emby", "jellyfin", "plex"):
            provider = ""

        width = int(getattr(item, "video_width", 0) or 0)
        height = int(getattr(item, "video_height", 0) or 0)
        if width >= 3800 or height >= 2100:
            quality = "4K"
        elif width >= 1900 or height >= 1050:
            quality = "1080"
        elif width >= 1200 or height >= 700:
            quality = "HD"
        else:
            quality = ""

        progress_pct = 0
        if progress:
            runtime = int(getattr(item, "runtime_ticks", 0) or 0)
            resume = int(getattr(item, "resume_ticks", 0) or 0)
            if runtime > 0 and resume > 0:
                progress_pct = max(1, min(100, int((resume * 100.0) / runtime)))

        return (
            str(getattr(item, "server_name", "") or ""),
            str(getattr(item, "id", "") or ""),
            visible_title,
            visible_meta,
            provider,
            quality,
            progress_pct,
        )

    @classmethod
    def _homeVisibleWindowMatches(cls, row, live_items, progress=False):
        live_items = list(live_items or [])
        offset = int(getattr(row, "offset", 0) or 0)
        count = int(getattr(row, "count", 0) or 0)

        old_visible = list((getattr(row, "items", None) or [])[offset:offset + count])
        new_visible = live_items[offset:offset + count]

        old_sig = tuple(cls._homeRenderedCardSignature(x, progress) for x in old_visible)
        new_sig = tuple(cls._homeRenderedCardSignature(x, progress) for x in new_visible)
        if old_sig != new_sig:
            return False

        old_current = row.getCurrent()
        if old_current is None:
            return True
        current_key = (
            str(getattr(old_current, "server_name", "") or ""),
            str(getattr(old_current, "id", "") or ""),
        )
        idx = int(getattr(row, "index", 0) or 0)
        if idx < 0 or idx >= len(live_items):
            return False
        live_key = (
            str(getattr(live_items[idx], "server_name", "") or ""),
            str(getattr(live_items[idx], "id", "") or ""),
        )
        return current_key == live_key

    @staticmethod
    def _homeCarrySnapshotPosterPaths(snapshot_items, live_items):
        paths = {}
        for item in (snapshot_items or []):
            path = str(getattr(item, "local_poster_path", "") or "")
            if path and os.path.isfile(path):
                key = (str(getattr(item, "server_name", "") or ""), str(getattr(item, "id", "") or ""))
                paths[key] = path
        for item in (live_items or []):
            if getattr(item, "local_poster_path", None):
                continue
            key = (str(getattr(item, "server_name", "") or ""), str(getattr(item, "id", "") or ""))
            path = paths.get(key)
            if path:
                item.local_poster_path = path

    # MEDIAPLUGINS2026_POSTER_PIPELINE_HOTFIX1_HOME
    @staticmethod
    def _homeSwapRowItemsWithoutRender(row, items):
        current = row.getCurrent()
        current_key = None
        if current is not None:
            current_key = (
                str(getattr(current, "server_name", "") or ""),
                str(getattr(current, "id", "") or ""),
            )

        # Laufende Download-Callbacks gehoeren zur alten Item-Generation.
        try:
            row._poster_generation += 1
            row._poster_inflight.clear()
            row._poster_retry_after.clear()
        except Exception:
            pass

        row.items = list(items or [])
        if not row.items:
            row.index = 0
            row.offset = 0
            return

        if current_key:
            for idx, item in enumerate(row.items):
                key = (
                    str(getattr(item, "server_name", "") or ""),
                    str(getattr(item, "id", "") or ""),
                )
                if key == current_key:
                    row.index = idx
                    break
            else:
                row.index = min(row.index, len(row.items) - 1)
        else:
            row.index = min(row.index, len(row.items) - 1)
        row._ensureVisible()
        try:
            row.screen._schedulePosterRepair(250, reset=True)
        except Exception:
            pass

    # MEDIAPLUGINS2026_HOME_SNAPSHOT_CACHE_RENDERFIX1

    def _homePrefetchMissingVisiblePosters(self):
        # Snapshot-Schnellpfad tauscht Live-Items absichtlich ohne Komplett-Render.
        # Neue Live-Items muessen trotzdem ihre Poster laden duerfen.
        for row in (self.continueRow, self.favoritesRow, self.latestRow):
            try:
                row._prefetchVisible()
                row._render()
                # Snapshot-Reuse: synchrone Cache-Treffer muessen sofort in die Pixmap-Widgets gerendert werden.
                row._render()
            except Exception as exc:
                log.warning("Home Poster-Prefetch nach Snapshot-Reuse fehlgeschlagen: %s", exc)

    def _buildLayout(self):
        build_t0 = time.monotonic()
        self._pipelineTiming("FINAL_BUILD_START", "continue=%d favorites=%d latest=%d" % (len(self.continue_items), len(self.favorite_items), len(self.latest_items)))
        log.info("TIMING HOME +%.3fs ALL provider requests finished continue=%d favorites=%d latest=%d", time.monotonic() - self._timing_load_started, len(self.continue_items), len(self.favorite_items), len(self.latest_items))

        live_continue = self._homeDedupe(self._interleaveByServer(self.continue_items, "last_played_date"), "last_played_date")
        live_latest = self._homeDedupe(self._interleaveByServer(self.latest_items, "date_created"), "date_created")
        live_favorites = self._homeDedupe(self._interleaveByServer(self.favorite_items, "date_created"), "date_created")

        # HOME_SNAPSHOT_SKIPFINAL1: Snapshot steht bereits sichtbar auf dem
        # Bildschirm. Wenn der komplette Live-Stand fuer die drei Posterreihen
        # identisch ist, sparen wir den dreifachen setItems/_render-Zyklus.
        # SKIPFINAL2 muss dieselbe Unified-Continue-Sicht verwenden wie _applyFilters.
        live_continue_filtered = self._filteredContinue(live_continue, self.continue_filter)
        live_favorites_filtered = self._filtered(live_favorites, self.favorites_filter)
        live_latest_filtered = self._filtered(live_latest, self.latest_filter)

        continue_same = bool(self._home_snapshot_active) and self._homeVisibleWindowMatches(
            self.continueRow, live_continue_filtered, True
        )
        favorites_same = bool(self._home_snapshot_active) and self._homeVisibleWindowMatches(
            self.favoritesRow, live_favorites_filtered, False
        )
        latest_same = bool(self._home_snapshot_active) and self._homeVisibleWindowMatches(
            self.latestRow, live_latest_filtered, False
        )
        same_visible = continue_same and favorites_same and latest_same

        self._pipelineTiming(
            "FINAL_BUILD_VISIBLE_COMPARE",
            "continue=%d favorites=%d latest=%d" %
            (1 if continue_same else 0, 1 if favorites_same else 0, 1 if latest_same else 0),
        )

        if same_visible:
            # Die bereits sichtbaren lokalen Poster auf die echten Live-Items
            # uebertragen. Danach koennen Rows/Preview/Playback mit aktuellen
            # Serverobjekten arbeiten, ohne dass die Poster erneut gezeichnet
            # werden muessen.
            self._homeCarrySnapshotPosterPaths(self._all_continue_items, live_continue)
            self._homeCarrySnapshotPosterPaths(self._all_favorite_items, live_favorites)
            self._homeCarrySnapshotPosterPaths(self._all_latest_items, live_latest)

            self.continue_items = list(live_continue)
            self.favorite_items = list(live_favorites)
            self.latest_items = list(live_latest)
            self._all_continue_items = list(live_continue)
            self._all_favorite_items = list(live_favorites)
            self._all_latest_items = list(live_latest)
            self._home_snapshot_active = False

            self._homeSwapRowItemsWithoutRender(
                self.continueRow,
                live_continue_filtered,
            )
            self._homeSwapRowItemsWithoutRender(
                self.favoritesRow,
                live_favorites_filtered,
            )
            self._homeSwapRowItemsWithoutRender(
                self.latestRow,
                live_latest_filtered,
            )

            self._homePrefetchMissingVisiblePosters()

            self["message"].setText("")
            self._renderStatus()
            # Nur die zentrale Vorschau einmal auf das frische Live-Item
            # umstellen. Die drei Posterreihen bleiben unangetastet.
            try:
                self._updatePreview()
            except Exception:
                pass
            self._armHomeSlideshow()
            self._saveHomeSnapshot()
            self._pipelineTiming(
                "FINAL_BUILD_REUSE_VISIBLE",
                "cost_ms=%.1f visible_continue=%d visible_favorites=%d visible_latest=%d" %
                ((time.monotonic() - build_t0) * 1000.0, self.continueRow.getCount(), self.favoritesRow.getCount(), self.latestRow.getCount()),
            )
            self._pipelineTiming(
                "FINAL_BUILD_DONE",
                "cost_ms=%.1f visible_continue=%d visible_favorites=%d visible_latest=%d" %
                ((time.monotonic() - build_t0) * 1000.0, self.continueRow.getCount(), self.favoritesRow.getCount(), self.latestRow.getCount()),
            )
            return

        # Sichtbarer Live-Stand hat sich geaendert: normaler, sicherer
        # Komplett-Refresh bleibt exakt wie bisher erhalten.
        self.continue_items = live_continue
        self.latest_items = live_latest
        self.favorite_items = live_favorites
        self._all_continue_items = list(self.continue_items)
        self._all_latest_items = list(self.latest_items)
        self._all_favorite_items = list(self.favorite_items)
        self._home_snapshot_active = False
        self._applyFilters()
        self["message"].setText("")
        self._renderStatus()
        self._refreshFocus()
        self._saveHomeSnapshot()
        self._pipelineTiming(
            "FINAL_BUILD_DONE",
            "cost_ms=%.1f visible_continue=%d visible_favorites=%d visible_latest=%d" %
            ((time.monotonic() - build_t0) * 1000.0, self.continueRow.getCount(), self.favoritesRow.getCount(), self.latestRow.getCount()),
        )

    @staticmethod
    def _interleaveByServer(items, date_attr):
        by_server, order = {}, []
        for item in items or []:
            name = getattr(item, "server_name", "") or ""
            if name not in by_server:
                by_server[name] = []
                order.append(name)
            by_server[name].append(item)
        for name in order:
            by_server[name].sort(key=lambda i: getattr(i, date_attr, "") or "", reverse=True)
        result, pos = [], 0
        while True:
            added = False
            for name in order:
                bucket = by_server[name]
                if pos < len(bucket):
                    result.append(bucket[pos])
                    added = True
            if not added:
                break
            pos += 1
        return result

    # =================================================================
    # DEDUPE / UNIFIED CONTINUE
    # =================================================================
    @staticmethod
    def _homeNormalizeTitle(value):
        value = (value or "").strip().casefold()
        return " ".join("".join(ch if ch.isalnum() else " " for ch in value).split())

    def _homeDuplicateKey(self, item):
        provider = self._providerForItem(item)
        title = self._homeNormalizeTitle(getattr(item, "title", ""))
        series = self._homeNormalizeTitle(getattr(item, "series_name", ""))
        season = getattr(item, "season_number", None)
        episode = getattr(item, "episode_number", None)
        parent_id = str(getattr(item, "parent_id", "") or "").strip()

        # Episoden nur dann zusammenfassen, wenn Serie + S/F eindeutig sind.
        if series and season is not None and episode is not None:
            return (provider, "episode", series, int(season), int(episode))

        # Generische Staffel-Titel wie "Season 1" duerfen niemals zwei
        # verschiedene Serien miteinander verschmelzen. Ohne Parent/Serie
        # gibt es deshalb absichtlich keinen Dedupe-Key.
        folded = (getattr(item, "title", "") or "").strip().casefold()
        is_generic_season = folded in ("specials", "special") or folded.startswith("season ") or folded.startswith("staffel ")
        if is_generic_season:
            if series:
                return (provider, "season", series, title)
            if parent_id:
                return (provider, "season", parent_id, title)
            return None

        # Filme/Serien: Provider-ID ist am sichersten. Fehlt sie, werden
        # gleicher Provider + Titel + grober Laufzeit-Bucket verwendet. Damit
        # kollabieren 1080p/4K-Versionen auch dann, wenn bei einer Karte das
        # Produktionsjahr fehlt.
        if not title:
            return None
        provider_ids = getattr(item, "provider_ids", None) or {}
        for _id_name in ("imdb", "tmdb", "tvdb"):
            _id_value = str(provider_ids.get(_id_name, "") or "").strip().lower()
            if _id_value:
                return (provider, "provider-id", _id_name, _id_value)
        runtime = int(getattr(item, "runtime_ticks", 0) or 0)
        if runtime > 0:
            # 5-Minuten-Bucket toleriert kleine Editions-/Metadatenabweichungen.
            runtime_minutes = int(round(runtime / 600000000.0))
            runtime_bucket = int(round(runtime_minutes / 5.0) * 5)
            return (provider, "title-runtime", title, runtime_bucket)
        year = int(getattr(item, "year", 0) or 0)
        return (provider, "title-year", title, year) if year else (provider, "title", title)

    @staticmethod
    def _homeRepresentativeScore(item, date_attr):
        # Neuester Datensatz zuerst, danach vorhandener Resume-Punkt und
        # Bildqualitaet. Bei 1080/4K-Doppelungen bleibt damit i.d.R. die
        # bessere Version sichtbar, ohne den aktuellen Wiedergabestand zu
        # verlieren.
        date_value = str(getattr(item, date_attr, "") or "")
        resume = int(getattr(item, "resume_ticks", 0) or 0)
        width = int(getattr(item, "video_width", 0) or 0)
        height = int(getattr(item, "video_height", 0) or 0)
        area = width * height
        runtime = int(getattr(item, "runtime_ticks", 0) or 0)
        return (area, 1 if resume > 0 else 0, date_value, resume, runtime)

    def _homeDedupe(self, items, date_attr):
        result = []
        positions = {}
        variants = {}
        for item in items or []:
            key = self._homeDuplicateKey(item)
            if key is None:
                result.append(item)
                continue
            if key not in positions:
                positions[key] = len(result)
                variants[key] = [item]
                result.append(item)
                continue

            variants[key].append(item)
            pos = positions[key]
            current = result[pos]
            if self._homeRepresentativeScore(item, date_attr) > self._homeRepresentativeScore(current, date_attr):
                result[pos] = item

        # Varianten bleiben am Repraesentanten erreichbar. Das veraendert
        # noch keine Detail-/Playback-Logik, erlaubt spaeter aber einen
        # gezielten Versionsdialog ohne erneute Serversuche.
        for key, members in variants.items():
            if len(members) > 1:
                try:
                    result[positions[key]].ui_variants = list(members)
                    result[positions[key]].ui_variant_count = len(members)
                except Exception:
                    pass
        return result

    @staticmethod
    def _continueProviderIds(item):
        raw = getattr(item, "provider_ids", None) or {}
        result = {}
        try:
            iterator = raw.items()
        except Exception:
            iterator = ()
        for key, value in iterator:
            key = str(key or "").strip().lower()
            value = str(value or "").strip().lower()
            if key and value:
                result[key] = value
        return result

    def _continueUnifiedAliases(self, item):
        """Alle sicheren Cross-Provider-Identitaeten eines Continue-Eintrags.

        Ein Film darf gleichzeitig IMDb/TMDb/TVDb UND Titel+Jahr besitzen.
        So koennen zwei Server trotz unterschiedlicher externer ID-Typen ueber
        Titel+Jahr zusammenfinden. Episoden verwenden zusaetzlich die stabile
        Serie+Staffel+Folge-Identitaet.
        """
        aliases = []

        series = self._homeNormalizeTitle(getattr(item, "series_name", ""))
        season = getattr(item, "season_number", None)
        episode = getattr(item, "episode_number", None)
        is_episode = False

        if series and season is not None and episode is not None:
            try:
                aliases.append(
                    ("episode", series, int(season), int(episode))
                )
                is_episode = True
            except Exception:
                pass

        ids = self._continueProviderIds(item)
        for key in ("imdb", "tmdb", "tvdb"):
            value = ids.get(key, "")
            if value:
                aliases.append(("provider-id", key, value))

        title = self._homeNormalizeTitle(getattr(item, "title", ""))
        if title and not is_episode:
            year = int(getattr(item, "year", 0) or 0)
            if year:
                aliases.append(("title-year", title, year))

            runtime = int(getattr(item, "runtime_ticks", 0) or 0)
            if runtime > 0:
                runtime_minutes = int(round(runtime / 600000000.0))
                runtime_bucket = int(round(runtime_minutes / 5.0) * 5)
                aliases.append(
                    ("title-runtime", title, runtime_bucket)
                )

        # Reihenfolge stabil halten, Dubletten entfernen.
        result = []
        seen = set()
        for alias in aliases:
            if alias in seen:
                continue
            seen.add(alias)
            result.append(alias)
        return tuple(result)

    def _continueUnifiedKey(self, item):
        """Kompatibilitaets-Helfer fuer eventuell vorhandene Aufrufer."""
        aliases = self._continueUnifiedAliases(item)
        return aliases[0] if aliases else None

    @staticmethod
    def _continueProgressRatio(item):
        resume = max(0, int(getattr(item, "resume_ticks", 0) or 0))
        runtime = max(0, int(getattr(item, "runtime_ticks", 0) or 0))
        if runtime > 0:
            return min(1.0, max(0.0, float(resume) / float(runtime)))
        return 0.0

    @staticmethod
    def _continueLastPlayedKey(item):
        """Nur echte Datum-/Zeitwerte fuer die Resume-Auswahl akzeptieren.

        Erwartete Serverformate sind ISO-aehnlich, z.B.
        2026-09-14T08:43:11Z oder 2026-09-14 08:43:11.
        Rein numerische/zero-padded Rohwerte werden absichtlich ignoriert.
        """
        value = str(getattr(item, "last_played_date", "") or "").strip()
        if not value:
            return 0

        # Rohwerte wie 00000000001788888651 duerfen nicht lexikographisch
        # gegen echte Datumswerte gewinnen.
        if value.isdigit():
            return 0

        # ISO YYYY-MM-DD[ T]HH:MM[:SS][...]
        try:
            if (
                len(value) >= 10
                and value[4:5] == "-"
                and value[7:8] == "-"
            ):
                year = int(value[0:4])
                month = int(value[5:7])
                day = int(value[8:10])

                hour = 0
                minute = 0
                second = 0

                if len(value) >= 16 and value[10:11] in ("T", " "):
                    hour = int(value[11:13])
                    minute = int(value[14:16])
                    if len(value) >= 19 and value[16:17] == ":":
                        second = int(value[17:19])

                if not (1 <= month <= 12 and 1 <= day <= 31):
                    return 0
                if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
                    return 0

                return (
                    year * 10000000000
                    + month * 100000000
                    + day * 1000000
                    + hour * 10000
                    + minute * 100
                    + second
                )
        except Exception:
            return 0

        return 0

    def _continueUnifiedScore(self, item):
        last_played_key = self._continueLastPlayedKey(item)
        resume = max(0, int(getattr(item, "resume_ticks", 0) or 0))
        width = max(0, int(getattr(item, "video_width", 0) or 0))
        height = max(0, int(getattr(item, "video_height", 0) or 0))

        # Reihenfolge:
        # 1. echtes Datum vorhanden
        # 2. bei echten Daten: neuester Zeitpunkt
        # 3. sonst bzw. bei Gleichstand: hoechster Fortschritt
        # 4. absolute Resume-Position
        # 5. Aufloesung als letzter Tie-Breaker
        return (
            1 if last_played_key else 0,
            last_played_key,
            self._continueProgressRatio(item),
            resume,
            width * height,
        )

    def _unifyContinueAcrossProviders(self, items):
        """Vereinigt Eintraege, sobald mindestens EINE sichere Identitaet passt.

        Union-Find macht die Zuordnung auch transitiv stabil:
        A teilt IMDb mit B, B teilt Titel+Jahr mit C -> A/B/C bleiben ein
        gemeinsames Medium, ohne dass ein bestimmter ID-Typ bevorzugt wird.
        """
        items = list(items or [])
        if not items:
            return []

        parent = list(range(len(items)))
        rank = [0] * len(items)
        alias_owner = {}

        def find(index):
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left, right):
            left = find(left)
            right = find(right)
            if left == right:
                return left
            if rank[left] < rank[right]:
                left, right = right, left
            parent[right] = left
            if rank[left] == rank[right]:
                rank[left] += 1
            return left

        for index, item in enumerate(items):
            aliases = self._continueUnifiedAliases(item)
            for alias in aliases:
                owner = alias_owner.get(alias)
                if owner is None:
                    alias_owner[alias] = index
                    continue
                union(index, owner)

        groups = {}
        order = []
        for index, item in enumerate(items):
            root = find(index)
            if root not in groups:
                groups[root] = []
                order.append(root)
            groups[root].append(item)

        result = []
        merged = 0

        for root in order:
            members = groups[root]

            # Der zuletzt abgespielte Stand bleibt der sichtbare Repraesentant.
            representative = max(
                members,
                key=self._continueUnifiedScore,
            )

            physical = []
            seen = set()
            providers = []

            for member in members:
                variants = list(
                    getattr(member, "ui_variants", None) or [member]
                )
                for variant in variants:
                    identity = (
                        str(getattr(variant, "server_name", "") or ""),
                        str(getattr(variant, "id", "") or ""),
                    )
                    if identity in seen:
                        continue
                    seen.add(identity)
                    physical.append(variant)

                    provider = self._providerForItem(variant)
                    if provider and provider not in providers:
                        providers.append(provider)

            if len(members) > 1:
                merged += 1
                try:
                    representative.ui_variants = physical
                    representative.ui_variant_count = len(physical)
                    representative.ui_unified_continue = True
                    representative.ui_unified_providers = tuple(providers)
                    representative.ui_unified_provider_count = len(providers)
                    representative.ui_unified_resume_provider = (
                        self._providerForItem(representative)
                    )
                except Exception:
                    pass

            result.append(representative)

        if merged:
            try:
                log.info(
                    "UNIFIED_CONTINUE2 groups=%d input=%d output=%d",
                    merged,
                    len(items),
                    len(result),
                )
            except Exception:
                pass

        return result

    # =================================================================
    # FILTER / RENDER / STATUS
    # =================================================================
    def _filteredContinue(self, items, provider):
        if provider == "all":
            return self._unifyContinueAcrossProviders(items)

        result = []
        seen = set()

        for item in items or []:
            variants = list(getattr(item, "ui_variants", None) or [item])
            candidates = [
                variant for variant in variants
                if self._providerForItem(variant) == provider
            ]
            if not candidates:
                continue

            best = max(candidates, key=self._continueUnifiedScore)
            identity = (
                str(getattr(best, "server_name", "") or ""),
                str(getattr(best, "id", "") or ""),
            )
            if identity in seen:
                continue
            seen.add(identity)
            result.append(best)

        return result

    def _providerForItem(self, item):
        label = (getattr(item, "source_label", "") or "").strip().lower()
        if label in ("emby", "jellyfin", "plex"):
            return label
        cfg = self.server_configs.get(getattr(item, "server_name", ""))
        return (getattr(cfg, "protocol", "") or "").lower()

    def _filtered(self, items, provider):
        if provider == "all":
            return list(items)
        return [i for i in items if self._providerForItem(i) == provider]

    def _applyFilters(self):
        self.continueRow.setItems(self._filteredContinue(self._all_continue_items, self.continue_filter))
        self.favoritesRow.setItems(self._filtered(self._all_favorite_items, self.favorites_filter))
        self.latestRow.setItems(self._filtered(self._all_latest_items, self.latest_filter))
        self["continue_empty"].setText("Keine Einträge für diese Quelle" if not self.continueRow.getCount() else "")
        self._renderFilters()

    # ------------------------------------------------------------------
    # Filter / Status / Fokus
    # ------------------------------------------------------------------
    def _countByProvider(self, items, provider):
        if provider == "all":
            return len(items)
        return sum(1 for item in items if self._providerForItem(item) == provider)

    def _setWidgetColor(self, widget, color):
        if parseColor is None or widget is None or widget.instance is None:
            return
        try:
            widget.instance.setForegroundColor(parseColor(color))
        except Exception:
            pass

    def _setWidgetBackground(self, widget, color):
        if parseColor is None or widget is None or widget.instance is None:
            return
        try:
            widget.instance.setBackgroundColor(parseColor(color))
        except Exception:
            pass

    def _renderFilters(self):
        providers = ["all", "emby", "jellyfin", "plex"]
        for prefix, items, selected, index in (
            ("favorites", self._all_favorite_items, self.favorites_filter, self.favorite_filter_index),
            ("latest", self._all_latest_items, self.latest_filter, self.latest_filter_index),
        ):
            active_zone = (self.zone == "fav_filter" and prefix == "favorites") or (self.zone == "latest_filter" and prefix == "latest")
            for i, provider in enumerate(providers):
                chip = self["%s_filter_%d" % (prefix, i)]
                focus = self["%s_filter_focus_%d" % (prefix, i)]
                selected_bar = self["%s_filter_selected_%d" % (prefix, i)]
                count = self._countByProvider(items, provider)
                if provider == "all":
                    text = "Alle (%d)" % count
                else:
                    text = "%s (%d)" % (_PROVIDER_NAMES[provider], count)
                chip.setText(text)
                provider_color = _PROVIDER_COLORS.get(provider, "#e8edf2")
                self._setWidgetColor(chip, provider_color)

                # Nur der Cursor in der aktuell bedienten Filterzeile bekommt
                # den Cyan-Fokusrahmen. Ein bereits aktiver Filter wird nicht
                # mehr faelschlich als zweiter Fokus gezeichnet.
                if active_zone and i == index:
                    focus.show()
                else:
                    focus.hide()

                # Der angewendete Filter bleibt durch eine duenne Unterlinie
                # sichtbar - in seiner Providerfarbe, nicht als Cyan-Fokus.
                if provider == selected:
                    self._setWidgetBackground(selected_bar, provider_color)
                    selected_bar.show()
                else:
                    selected_bar.hide()

    @staticmethod
    def _healthStatusText(state, compact=False):
        labels = {
            "online": "✓ Online",
            "auth": "! Login nötig",
            "offline": "× Offline",
            "error": "! Fehler",
            "connecting": "… Prüfe",
            "–": "– Nicht aktiv",
        }
        text = labels.get(state, labels["–"])
        if compact and text == "– Nicht aktiv":
            return "–"
        return text

    def _protocolHealthState(self, provider):
        states = []
        for name, cfg in self.server_configs.items():
            if (getattr(cfg, "protocol", "") or "").lower() == provider:
                states.append(self.server_status.get(name, "connecting"))

        if not states:
            return "–"
        for state in ("online", "auth", "error", "offline", "connecting"):
            if state in states:
                return state
        return "error"

    def _renderStatus(self):
        emby = self._healthStatusText(self._protocolHealthState("emby"))
        jelly = self._healthStatusText(self._protocolHealthState("jellyfin"))
        plex = self._healthStatusText(self._protocolHealthState("plex"))
        self["server_status"].setText(
            "Serverstatus:   Emby %s     Jellyfin %s     Plex %s" %
            (emby, jelly, plex)
        )
        self._renderServerSwitch()

    # =================================================================
    # PREVIEW / AVAILABILITY / DETAIL / AMBIENT
    # =================================================================
    def _previewItem(self):
        if self.zone == "server_switch" and self._server_switch_item is not None:
            return self._server_switch_item
        if self.zone == "continue":
            return self.continueRow.getCurrent()
        if self.zone in ("favorites", "fav_filter"):
            return self.favoritesRow.getCurrent()
        if self.zone in ("latest", "latest_filter"):
            return self.latestRow.getCurrent()
        return self.continueRow.getCurrent() or self.favoritesRow.getCurrent() or self.latestRow.getCurrent()

    @staticmethod
    def _previewText(value, max_len):
        value = " ".join((value or "").split())
        return value if len(value) <= max_len else value[:max_len - 1] + "…"

    @staticmethod
    def _previewDuration(ticks):
        seconds = max(0, int(int(ticks or 0) / 10000000))
        hours, rest = divmod(seconds, 3600)
        minutes, seconds = divmod(rest, 60)
        if hours:
            return "%d:%02d:%02d" % (hours, minutes, seconds)
        return "%d:%02d" % (minutes, seconds)

    @staticmethod
    def _previewMinutes(ticks):
        minutes = int(round(int(ticks or 0) / 600000000.0))
        return "%d Min." % minutes if minutes > 0 else ""

    @staticmethod
    def _previewDate(value):
        """Nur echte Datum-/Zeitwerte in der Home-Detailleiste anzeigen."""
        value = str(value or "").strip()
        if not value:
            return ""

        # Server-Rohwerte wie 00000000001787574043 sind keine nutzbare
        # Datumsanzeige und sollen nicht im UI erscheinen.
        if value.isdigit():
            return ""

        # Erwartetes ISO-aehnliches Format: YYYY-MM-DD[ T]HH:MM...
        if len(value) >= 10 and value[4:5] == "-" and value[7:8] == "-":
            try:
                year = int(value[0:4])
                month = int(value[5:7])
                day = int(value[8:10])
                if not (1 <= month <= 12 and 1 <= day <= 31):
                    return ""

                result = "%02d.%02d.%04d" % (day, month, year)

                if len(value) >= 16 and value[10:11] in ("T", " "):
                    hour = int(value[11:13])
                    minute = int(value[14:16])
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        result += ", %02d:%02d" % (hour, minute)
                return result
            except Exception:
                return ""

        # Unbekannte Formate nicht ungeprueft ins UI durchreichen.
        return ""

    def _previewCrossKey(self, item):
        provider_ids = getattr(item, "provider_ids", None) or {}
        for key in ("imdb", "tmdb", "tvdb"):
            value = str(provider_ids.get(key, "") or "").strip().lower()
            if value:
                return ("id", key, value)
        title = self._homeNormalizeTitle(getattr(item, "title", ""))
        if not title:
            return None
        year = int(getattr(item, "year", 0) or 0)
        return ("title", title, year) if year else ("title", title)

    def _previewAvailabilityTitleAliases(self, item):
        """Sichere Titel-Aliase nur fuer die Verfuegbarkeitsanzeige."""
        raw = str(getattr(item, "title", "") or "").strip()
        result = []

        def add(value):
            value = self._homeNormalizeTitle(value)
            if value and len(value) >= 4 and value not in result:
                result.append(value)

        add(raw)

        # Beispiel:
        # "James Bond 007 - Skyfall" -> zusaetzlicher Alias "skyfall".
        # Nur klare Trennzeichen verwenden; kein aggressives Wort-Loeschen.
        for separator in (" - ", " – ", " — "):
            if separator in raw:
                tail = raw.rsplit(separator, 1)[-1].strip()
                add(tail)

        return tuple(result)

    @staticmethod
    def _previewAvailabilityRuntimeClose(left, right):
        left = int(getattr(left, "runtime_ticks", 0) or 0)
        right = int(getattr(right, "runtime_ticks", 0) or 0)
        if left <= 0 or right <= 0:
            return False
        # Maximal 10 Minuten Differenz: verschiedene Encodes/Cuts duerfen
        # leicht abweichen, deutlich andere Filme aber nicht.
        return abs(left - right) <= (10 * 60 * 10000000)

    def _previewAvailabilityMatch(self, selected, candidate):
        """Strenger Cross-Provider-Match fuer 'Verfuegbar bei'."""
        if selected is None or candidate is None:
            return False

        # 1. Externe IDs sind der staerkste Treffer.
        left_ids = self._continueProviderIds(selected) if hasattr(self, "_continueProviderIds") else {}
        right_ids = self._continueProviderIds(candidate) if hasattr(self, "_continueProviderIds") else {}
        for key in ("imdb", "tmdb", "tvdb"):
            if left_ids.get(key) and left_ids.get(key) == right_ids.get(key):
                return True

        # 2. Titel bzw. sicherer Suffix-Alias muss uebereinstimmen.
        left_titles = set(self._previewAvailabilityTitleAliases(selected))
        right_titles = set(self._previewAvailabilityTitleAliases(candidate))
        if not left_titles or not right_titles or not (left_titles & right_titles):
            return False

        left_year = int(getattr(selected, "year", 0) or 0)
        right_year = int(getattr(candidate, "year", 0) or 0)

        # Wenn beide Jahre bekannt sind, muessen sie identisch sein.
        if left_year and right_year:
            return left_year == right_year

        # Fehlt auf mindestens einer Seite das Jahr, dient die Laufzeit als
        # Sicherheitsnetz. Damit matchen gleiche Encodes trotz Metadatenluecke.
        return self._previewAvailabilityRuntimeClose(selected, candidate)

    def _previewAvailabilityQuery(self, item):
        raw = str(getattr(item, "title", "") or "").strip()
        for separator in (" - ", " – ", " — "):
            if separator in raw:
                tail = raw.rsplit(separator, 1)[-1].strip()
                if len(tail) >= 4:
                    return tail
        return raw

    def _previewAvailabilityState(self):
        if not hasattr(self, "_preview_availability_cache"):
            self._preview_availability_cache = {}
        if not hasattr(self, "_preview_availability_done"):
            self._preview_availability_done = set()
        if not hasattr(self, "_preview_availability_inflight"):
            self._preview_availability_inflight = set()
        return (
            self._preview_availability_cache,
            self._preview_availability_done,
            self._preview_availability_inflight,
        )

    def _requestPreviewAvailability(self, selected):
        """Andere Provider asynchron suchen; keinerlei Resume-Daten schreiben."""
        key = self._previewDetailKey(selected)
        if key is None or getattr(selected, "is_demo", False):
            return

        query = self._previewAvailabilityQuery(selected)
        if len(query) < 2:
            return

        cache, done, inflight = self._previewAvailabilityState()
        cache.setdefault(key, [])

        selected_provider = self._providerForItem(selected)

        for server_name, client in self.clients.items():
            cfg = self.server_configs.get(server_name)
            provider = str(getattr(cfg, "protocol", "") or "").lower()
            if provider not in ("emby", "jellyfin", "plex"):
                continue

            # Der Provider des echten Resume-Eintrags ist bereits bekannt.
            if provider == selected_provider:
                continue

            request_key = (key, server_name)
            if request_key in done or request_key in inflight:
                continue
            if not hasattr(client, "search"):
                done.add(request_key)
                continue

            inflight.add(request_key)

            def on_items(items, rk=request_key, target=selected, target_key=key):
                _cache, _done, _inflight = self._previewAvailabilityState()
                _inflight.discard(rk)
                _done.add(rk)

                existing = {
                    (
                        str(getattr(x, "server_name", "") or ""),
                        str(getattr(x, "id", "") or ""),
                    )
                    for x in _cache.setdefault(target_key, [])
                }

                for candidate in items or []:
                    try:
                        if not self._previewAvailabilityMatch(target, candidate):
                            continue
                        identity = (
                            str(getattr(candidate, "server_name", "") or ""),
                            str(getattr(candidate, "id", "") or ""),
                        )
                        if identity in existing:
                            continue
                        existing.add(identity)
                        _cache[target_key].append(candidate)
                    except Exception:
                        continue

                current = self._previewItem()
                if self._previewDetailKey(current) == target_key:
                    self._updatePreview()

            def on_error(error, rk=request_key, target_key=key):
                _cache, _done, _inflight = self._previewAvailabilityState()
                _inflight.discard(rk)
                _done.add(rk)
                try:
                    log.warning(
                        "Home-Verfuegbarkeitssuche fehlgeschlagen (%s): %s",
                        rk[1], error,
                    )
                except Exception:
                    pass

            try:
                client.search(query, on_items, on_error)
            except Exception as error:
                on_error(error)

    def _previewVersionsByProvider(self, selected):
        result = {"emby": [], "plex": [], "jellyfin": []}
        selected_key = self._previewCrossKey(selected)
        selected_identity = (
            str(getattr(selected, "server_name", "") or ""),
            str(getattr(selected, "id", "") or ""),
        )
        seen = set()
        pools = self._all_continue_items + self._all_favorite_items + self._all_latest_items

        for candidate in pools:
            if selected_key is None:
                candidate_identity = (
                    str(getattr(candidate, "server_name", "") or ""),
                    str(getattr(candidate, "id", "") or ""),
                )
                if candidate_identity != selected_identity:
                    continue
            elif self._previewCrossKey(candidate) != selected_key:
                # Der alte Home-Pool-Match bleibt absichtlich konservativ.
                continue

            members = list(getattr(candidate, "ui_variants", None) or [candidate])
            for member in members:
                provider = self._providerForItem(member)
                identity = (
                    provider,
                    str(getattr(member, "server_name", "") or ""),
                    str(getattr(member, "id", "") or ""),
                )
                if provider not in result or identity in seen:
                    continue
                seen.add(identity)
                result[provider].append(member)

        # Zusaetzliche Suchtreffer anderer Provider NUR fuer die Anzeige.
        cache, _done, _inflight = self._previewAvailabilityState()
        availability_key = self._previewDetailKey(selected)
        for member in cache.get(availability_key, []):
            provider = self._providerForItem(member)
            identity = (
                provider,
                str(getattr(member, "server_name", "") or ""),
                str(getattr(member, "id", "") or ""),
            )
            if provider not in result or identity in seen:
                continue
            seen.add(identity)
            result[provider].append(member)

        # Der fokussierte echte Eintrag muss sicher erscheinen.
        provider = self._providerForItem(selected)
        if provider in result and not result[provider]:
            result[provider] = list(getattr(selected, "ui_variants", None) or [selected])

        return result

    @staticmethod
    def _previewQualitySummary(items):
        labels = []
        for candidate in items:
            quality = MediaWallRow._quality(candidate)
            if quality and quality not in labels:
                labels.append(quality)
        order = {"4K": 0, "1080": 1, "HD": 2}
        labels.sort(key=lambda value: order.get(value, 9))
        return " · ".join(labels) if labels else ("Verfügbar" if items else "–")

    @staticmethod
    def _previewDetailKey(item):
        if item is None:
            return None
        server_name = str(getattr(item, "server_name", "") or "")
        item_id = str(getattr(item, "id", "") or "")
        return (server_name, item_id) if server_name and item_id else None

    @staticmethod
    def _mergePreviewDetail(item, detail):
        if item is None or detail is None:
            return
        try:
            item.update_from_detail(detail)
        except Exception:
            pass

        # MediaItem.update_from_detail behaelt bewusst einige Listendaten.
        # Fuer die Vorschau duerfen die vollstaendigeren Detailwerte diese
        # Luecken auffuellen, ohne Resume/Progress mit Null zu ueberschreiben.
        for attr in (
            "year", "overview", "genres", "rating", "last_played_date",
            "series_name", "season_number", "episode_number", "video_codec",
            "video_width", "video_height", "audio_codec", "audio_channels",
            "audio_language", "runtime_ticks", "provider_ids",
        ):
            value = getattr(detail, attr, None)
            if value not in (None, "", 0, [], {}):
                try:
                    setattr(item, attr, value)
                except Exception:
                    pass

    def _preparePreviewDetail(self, item):
        key = self._previewDetailKey(item)
        if key is None or getattr(item, "is_demo", False):
            self._preview_detail_pending = None
            self._preview_detail_serial += 1
            try:
                self._preview_detail_timer.stop()
            except Exception:
                pass
            return

        cached = self._preview_detail_cache.get(key)
        if cached is not None:
            self._mergePreviewDetail(item, cached)
            # Erst mit angereicherten Details auf anderen Providern suchen.
            self._requestPreviewAvailability(item)
            return
        if key in self._preview_detail_failed or key in self._preview_detail_inflight:
            return
        if self._preview_detail_pending is not None and self._preview_detail_pending[1] == key:
            return

        client = self.clients.get(getattr(item, "server_name", ""))
        if client is None or not hasattr(client, "get_item_detail"):
            return

        self._preview_detail_serial += 1
        serial = self._preview_detail_serial
        self._preview_detail_pending = (serial, key, item)
        try:
            self._preview_detail_timer.stop()
            # Kurze Entprellung: Pfeiltasten bleiben fluessig und nur die
            # Karte, auf der der Fokus stehenbleibt, erzeugt einen Request.
            self._preview_detail_timer.start(320, True)
        except Exception:
            self._requestPreviewDetail()

    # MEDIAPLUGINS2026_POSTER_PIPELINE_FINALIZE1_HOME
    def _ensureHomeAsyncRuntimeState(self):
        if not hasattr(self, "_preview_detail_cache"):
            self._preview_detail_cache = {}
        if not hasattr(self, "_preview_detail_failed"):
            self._preview_detail_failed = set()
        if not hasattr(self, "_preview_detail_inflight"):
            self._preview_detail_inflight = {}
        if not hasattr(self, "_preview_detail_pending"):
            self._preview_detail_pending = None
        if not hasattr(self, "_preview_detail_serial"):
            self._preview_detail_serial = 0
        if not hasattr(self, "_preview_detail_closed"):
            self._preview_detail_closed = False
        if not hasattr(self, "_preview_detail_timer"):
            self._preview_detail_timer = eTimer()
            try:
                self._preview_detail_timer.callback.append(self._requestPreviewDetail)
            except Exception:
                pass

        if not hasattr(self, "_home_ambient_closed"):
            self._home_ambient_closed = False
        if not hasattr(self, "_home_ambient_serial"):
            self._home_ambient_serial = 0
        if not hasattr(self, "_home_ambient_key"):
            self._home_ambient_key = None
        if not hasattr(self, "_home_ambient_pending"):
            self._home_ambient_pending = None
        if not hasattr(self, "_home_ambient_timer"):
            self._home_ambient_timer = eTimer()
            try:
                self._home_ambient_timer.callback.append(self._requestHomeAmbient)
            except Exception:
                pass

    def _requestPreviewDetail(self):
        self._ensureHomeAsyncRuntimeState()
        pending = self._preview_detail_pending
        self._preview_detail_pending = None
        if pending is None or self._preview_detail_closed:
            return
        serial, key, item = pending
        current = self._previewItem()
        if serial != self._preview_detail_serial or self._previewDetailKey(current) != key:
            return

        client = self.clients.get(getattr(item, "server_name", ""))
        if client is None or not hasattr(client, "get_item_detail"):
            return
        self._preview_detail_inflight[key] = serial
        try:
            client.get_item_detail(
                getattr(item, "id", ""),
                lambda detail, s=serial, k=key, target=item: self._previewDetailLoaded(s, k, target, detail),
                lambda error, s=serial, k=key: self._previewDetailFailed(s, k, error),
            )
        except Exception as error:
            self._previewDetailFailed(serial, key, error)

    def _previewDetailLoaded(self, serial, key, target, detail):
        self._ensureHomeAsyncRuntimeState()
        if self._preview_detail_inflight.get(key) != serial:
            return
        self._preview_detail_inflight.pop(key, None)
        if self._preview_detail_closed or detail is None:
            return
        self._preview_detail_cache[key] = detail
        self._mergePreviewDetail(target, detail)

        # Resume bleibt am echten Continue-Item; andere Provider liefern
        # ausschliesslich Verfuegbarkeits-/Qualitaetsinformationen.
        self._requestPreviewAvailability(target)

        # Die Antwort darf nur die Karte aktualisieren, die jetzt noch im
        # Fokus steht. Beim Zuruecknavigieren greift stattdessen der Cache.
        current = self._previewItem()
        if self._previewDetailKey(current) == key:
            self._mergePreviewDetail(current, detail)
            self._updatePreview()

    def _previewDetailFailed(self, serial, key, error):
        self._ensureHomeAsyncRuntimeState()
        if self._preview_detail_inflight.get(key) != serial:
            return
        self._preview_detail_inflight.pop(key, None)
        if not self._preview_detail_closed:
            # Pro Screen-Lauf nur ein Fehlversuch je Karte; so entsteht bei
            # einem offline Provider keine Request-Schleife beim Navigieren.
            self._preview_detail_failed.add(key)
            log.warning("Home-Vorschaudetails nicht ladbar (%s/%s): %s", key[0], key[1], error)

    def _closePreviewDetail(self):
        self._ensureHomeAsyncRuntimeState()
        self._preview_detail_closed = True
        self._preview_detail_serial += 1
        self._preview_detail_pending = None
        try:
            self._preview_detail_timer.stop()
        except Exception:
            pass

    @staticmethod
    def _homeAmbientKey(item):
        if item is None:
            return None
        url = str(getattr(item, "backdrop_url", "") or "")
        if not url:
            return None
        return (
            str(getattr(item, "server_name", "") or ""),
            str(getattr(item, "id", "") or ""),
            url,
        )

    def _hideHomeAmbient(self):
        try:
            self["preview_ambient"].hide()
            self["preview_ambient_shade"].hide()
        except Exception:
            pass

    def _updateHomeAmbient(self, item):
        self._ensureHomeAsyncRuntimeState()
        key = self._homeAmbientKey(item)
        if key == self._home_ambient_key:
            return

        self._home_ambient_serial += 1
        serial = self._home_ambient_serial
        self._home_ambient_key = key
        self._home_ambient_pending = None
        try:
            self._home_ambient_timer.stop()
        except Exception:
            pass

        # Niemals das Bild des vorherigen Titels unter dem neuen Text stehen
        # lassen. Ohne Bild bleiben die vorhandenen dunklen Panels sichtbar.
        self._hideHomeAmbient()
        if key is None or self._home_ambient_closed:
            return

        url = key[2]
        cached = image_cache.get_local_path(url)
        if cached:
            self._homeAmbientLoaded(serial, key, cached)
            return

        self._home_ambient_pending = (serial, key, url)
        try:
            self._home_ambient_timer.start(_HOME_AMBIENT_DELAY_MS, True)
        except Exception:
            self._requestHomeAmbient()

    def _requestHomeAmbient(self):
        self._ensureHomeAsyncRuntimeState()
        pending = self._home_ambient_pending
        self._home_ambient_pending = None
        if pending is None or self._home_ambient_closed:
            return
        serial, key, url = pending
        if serial != self._home_ambient_serial or key != self._homeAmbientKey(self._previewItem()):
            return
        try:
            image_cache.fetch(
                url,
                lambda path, s=serial, k=key: self._homeAmbientLoaded(s, k, path),
                lambda error, s=serial, k=key: self._homeAmbientFailed(s, k),
            )
        except Exception:
            self._homeAmbientFailed(serial, key)

    def _homeAmbientLoaded(self, serial, key, path):
        self._ensureHomeAsyncRuntimeState()
        if self._home_ambient_closed or serial != self._home_ambient_serial:
            return
        if key != self._home_ambient_key or key != self._homeAmbientKey(self._previewItem()):
            return
        backdrop = LoadPixmap(path) if path else None
        shade = LoadPixmap(_HOME_AMBIENT_SHADE_PATH)
        if not backdrop or not shade:
            self._homeAmbientFailed(serial, key)
            return
        if self["preview_ambient"].instance:
            self["preview_ambient"].instance.setPixmap(backdrop)
        if self["preview_ambient_shade"].instance:
            self["preview_ambient_shade"].instance.setPixmap(shade)
        self["preview_ambient"].show()
        self["preview_ambient_shade"].show()

    def _homeAmbientFailed(self, serial, key):
        if serial != self._home_ambient_serial or key != self._home_ambient_key:
            return
        self._hideHomeAmbient()

    def _closeHomeAmbient(self):
        self._ensureHomeAsyncRuntimeState()
        self._home_ambient_closed = True
        self._home_ambient_serial += 1
        self._home_ambient_key = None
        self._home_ambient_pending = None
        try:
            self._home_ambient_timer.stop()
        except Exception:
            pass

    def _updatePreview(self):
        self._ensureHomeAsyncRuntimeState()
        item = self._previewItem()
        self._preparePreviewDetail(item)
        self._updateHomeAmbient(item)
        poster = self["preview_poster"]
        availability = ("emby", "plex", "jelly")
        if item is None:
            poster.hide()
            self["preview_title"].setText("Keine Auswahl")
            for name in ("preview_meta", "preview_overview", "preview_badges", "preview_source",
                         "preview_progress_text", "preview_last_played", "preview_remaining",
                         "preview_primary_action"):
                self[name].setText("")
            self["preview_secondary_action"].setText("")
            self["preview_progress_bg"].hide()
            self["preview_progress"].hide()
            self._renderServerSwitch()
            return

        path = getattr(item, "local_poster_path", None)
        pix = LoadPixmap(path) if path else LoadPixmap(_PLACEHOLDER_PATH)
        if pix and poster.instance:
            poster.instance.setPixmap(pix)
        poster.show()

        title = getattr(item, "title", "") or ""
        folded = title.strip().casefold()
        if folded in ("specials", "special"):
            title = "Spezialfolgen"
        else:
            for prefix in ("season ", "staffel "):
                if folded.startswith(prefix):
                    number = title.strip()[len(prefix):].strip()
                    if number.isdigit():
                        title = "Staffel %d" % int(number)
                    break
        self["preview_title"].setText(self._previewText(title, 46))

        meta = []
        if getattr(item, "year", None):
            meta.append(str(item.year))
        runtime_text = self._previewMinutes(getattr(item, "runtime_ticks", 0))
        if runtime_text:
            meta.append(runtime_text)
        genres = [str(value) for value in (getattr(item, "genres", None) or []) if value]
        if genres:
            meta.append(", ".join(genres[:3]))
        if getattr(item, "series_name", "") and getattr(item, "season_number", None) is not None:
            episode = "S%d" % int(item.season_number)
            if getattr(item, "episode_number", None) is not None:
                episode += " · F%d" % int(item.episode_number)
            meta.insert(0, episode)
        self["preview_meta"].setText(self._previewText("   |   ".join(meta), 74))

        overview = getattr(item, "overview", "") or ""
        if not overview:
            if folded.startswith("season ") or folded.startswith("staffel ") or folded in ("specials", "special"):
                overview = "Staffel-/Serieninhalt aus %s." % _PROVIDER_NAMES.get(self._providerForItem(item), "dieser Quelle")
            else:
                overview = "Keine Kurzbeschreibung für diesen Eintrag verfügbar."
        self["preview_overview"].setText(self._previewText(overview, 205))

        badges = []
        rating = getattr(item, "rating", None)
        try:
            if rating is not None and float(rating) > 0:
                badges.append("★ %.1f" % float(rating))
        except Exception:
            pass
        quality = MediaWallRow._quality(item)
        if quality:
            badges.append(quality)
        video_codec = str(getattr(item, "video_codec", "") or "").upper()
        if video_codec:
            badges.append(video_codec)
        audio_codec = str(getattr(item, "audio_codec", "") or "").upper()
        channels = int(getattr(item, "audio_channels", 0) or 0)
        if audio_codec:
            channel_label = {1: "1.0", 2: "2.0", 6: "5.1", 8: "7.1"}.get(channels, "%d ch" % channels if channels else "")
            badges.append(audio_codec + ((" " + channel_label) if channel_label else ""))

        provider = self._providerForItem(item)
        provider_name = _PROVIDER_NAMES.get(provider, provider.capitalize() if provider else "Quelle")
        variants = list(getattr(item, "ui_variants", None) or [item])
        if len(variants) > 1:
            badges.append("%d Versionen verfügbar" % len(variants))
        self["preview_badges"].setText(self._previewText("   |   ".join(badges), 76))

        # Quellenzeile aus der tatsaechlich erkannten Verfuegbarkeit bauen.
        # Resume/Fortschritt bleiben weiterhin am ausgewaehlten Provider.
        availability_versions = self._previewVersionsByProvider(item)
        available_provider_names = []
        for availability_provider in ("emby", "jellyfin", "plex"):
            if availability_versions.get(availability_provider):
                available_provider_names.append(
                    _PROVIDER_NAMES.get(
                        availability_provider,
                        availability_provider.capitalize(),
                    )
                )

        source_text = " · ".join(available_provider_names) if available_provider_names else provider_name
        if len(variants) > 1:
            source_text += " · %d Versionen" % len(variants)

        self["preview_source"].setText(source_text)
        self._setWidgetColor(self["preview_source"], _PROVIDER_COLORS.get(provider, "#aebac5"))
        self["preview_primary_action"].setText("")
        self["preview_secondary_action"].setText("")

        runtime = int(getattr(item, "runtime_ticks", 0) or 0)
        resume = int(getattr(item, "resume_ticks", 0) or 0)
        if runtime > 0 and resume > 0:
            pct = max(1, min(100, int((resume * 100.0) / runtime)))
            self["preview_progress_text"].setText("Fortschritt: %d%%" % pct)
            self["preview_progress_bg"].show()
            self["preview_progress"].show()
            if self["preview_progress"].instance:
                self["preview_progress"].instance.resize(eSize(max(2, int(235 * pct / 100.0)), 7))
            self["preview_remaining"].setText("Verbleibend: %s" % self._previewDuration(max(0, runtime - resume)))
        else:
            self["preview_progress_text"].setText("Noch nicht begonnen" if runtime > 0 else "")
            self["preview_progress_bg"].hide()
            self["preview_progress"].hide()
            self["preview_remaining"].setText("")

        last_played = self._previewDate(getattr(item, "last_played_date", ""))
        self["preview_last_played"].setText("Letzte Wiedergabe: %s" % last_played if last_played else "")

        self._renderServerSwitch()

    # =================================================================
    # PROVIDER SWITCH / INTERNAL LIBRARIES
    # =================================================================
    @staticmethod
    def _serverSwitchProviders():
        return ("emby", "jellyfin", "plex")

    def _serverSwitchProvider(self):
        providers = self._serverSwitchProviders()
        return providers[max(0, min(len(providers) - 1, self.server_switch_index))]

    def _serverSwitchStatus(self, provider):
        return self._healthStatusText(
            self._protocolHealthState(provider),
            compact=True,
        )

    def _renderServerSwitch(self):
        status_names = {
            "emby": "availability_emby_meta",
            "jellyfin": "availability_jelly_meta",
            "plex": "availability_plex_meta",
        }
        focus_names = {
            "emby": "server_switch_focus_emby",
            "jellyfin": "server_switch_focus_jelly",
            "plex": "server_switch_focus_plex",
        }
        selected = self._serverSwitchProvider()
        for provider in self._serverSwitchProviders():
            self[status_names[provider]].setText(self._serverSwitchStatus(provider))
            focus = self[focus_names[provider]]
            if self.zone == "server_switch" and provider == selected:
                focus.show()
            else:
                focus.hide()

    def _syncServerSwitchToItem(self, item):
        provider = self._providerForItem(item) if item is not None else ""
        providers = self._serverSwitchProviders()
        if provider in providers:
            self.server_switch_index = providers.index(provider)
        else:
            self.server_switch_index = 0

    def _refreshFocus(self):
        self.continueRow.setFocused(self.zone == "continue")
        self.favoritesRow.setFocused(self.zone == "favorites")
        self.latestRow.setFocused(self.zone == "latest")
        self._renderFilters()
        self._updatePreview()
        self._renderServerSwitch()
        self._armHomeSlideshow()

    def _homeSlideshowRow(self):
        if self.zone == "continue":
            return self.continueRow
        if self.zone == "favorites":
            return self.favoritesRow
        if self.zone == "latest":
            return self.latestRow
        return None

    def _armHomeSlideshow(self):
        try:
            self._home_slideshow_timer.stop()
        except Exception:
            pass
        if self._home_slideshow_closed or self._child_open:
            return
        row = self._homeSlideshowRow()
        if row is None or row.getCount() <= 1:
            return
        try:
            self._home_slideshow_timer.start(_HOME_SLIDESHOW_DELAY_MS, True)
        except Exception:
            pass

    def _touchHomeSlideshow(self):
        # Jede Navigation beginnt die sechs Sekunden Wartezeit von vorn.
        self._armHomeSlideshow()

    def _advanceHomeSlideshow(self):
        if self._home_slideshow_closed or self._child_open:
            return
        row = self._homeSlideshowRow()
        if row is None or row.getCount() <= 1:
            return

        if row.index < row.getCount() - 1:
            row.moveRight()
        else:
            row.index = 0
            row._ensureVisible()
            row._prefetchVisible()
            row._render()
        # Genau derselbe Vorschauweg wie bei manueller Navigation: Fokus,
        # Poster und komplette Detailzone bleiben dadurch synchron.
        self._updatePreview()
        self._armHomeSlideshow()

    def _closeHomeSlideshow(self):
        self._home_slideshow_closed = True
        try:
            self._home_slideshow_timer.stop()
        except Exception:
            pass

    # =================================================================
    # NAVIGATION / REMOTE KEYS
    # =================================================================
    def _zones(self):
        # Normale vertikale Navigation folgt nur sichtbaren Medienreihen.
        # Filter werden bewusst nur ueber GELB betreten.
        zones = []
        if self.continueRow.getCount() > 0:
            zones.append("continue")
        if self.favoritesRow.getCount() > 0:
            zones.append("favorites")
        if self.latestRow.getCount() > 0:
            zones.append("latest")
        zones.append("server_switch")
        return zones

    def _moveZone(self, delta):
        zones = self._zones()
        if not zones:
            return
        try:
            idx = zones.index(self.zone)
        except ValueError:
            idx = 0

        old_zone = self.zone
        old_item = self._previewItem()
        idx = max(0, min(len(zones) - 1, idx + delta))
        new_zone = zones[idx]

        if new_zone == "server_switch" and old_zone != "server_switch":
            self._enterServerSwitch(old_item, old_zone)
            return

        if old_zone == "server_switch" and new_zone != "server_switch":
            self._server_switch_item = None

        self.zone = new_zone
        self._refreshFocus()

    def _enterServerSwitch(self, item=None, return_zone=None):
        # Serverliste fokussieren, ohne das aktuell angezeigte Medium zu verlieren.
        if item is None:
            item = self._previewItem()
        self._server_switch_item = item
        self._server_switch_return_zone = return_zone or self.zone
        self._syncServerSwitchToItem(item)
        self.zone = "server_switch"
        self._refreshFocus()
        self._renderServerSwitch()

    def _leaveServerSwitch(self):
        # Zur Medienzeile zurueckkehren, aus der der Serverbereich betreten wurde.
        target = getattr(self, "_server_switch_return_zone", "")
        valid = [z for z in self._zones() if z != "server_switch"]
        if target not in valid:
            target = valid[-1] if valid else "continue"
        self._server_switch_item = None
        self.zone = target
        self._refreshFocus()

    def keyUp(self):
        self._touchHomeSlideshow()

        if self.zone == "server_switch":
            if self.server_switch_index > 0:
                self.server_switch_index -= 1
                self._renderServerSwitch()
            else:
                self._leaveServerSwitch()
            return

        # Pfeil HOCH betritt zuerst die sichtbare Filterleiste der jeweiligen
        # unteren Posterreihe. Ein weiteres HOCH geht zur vorherigen Medienreihe.
        if self.zone == "latest":
            self.zone = "latest_filter"
            self._refreshFocus()
            return

        if self.zone == "favorites":
            self.zone = "fav_filter"
            self._refreshFocus()
            return

        if self.zone == "latest_filter":
            if self.favoritesRow.getCount() > 0:
                self.zone = "favorites"
            elif self.continueRow.getCount() > 0:
                self.zone = "continue"
            self._refreshFocus()
            return

        if self.zone == "fav_filter":
            if self.continueRow.getCount() > 0:
                self.zone = "continue"
                self._refreshFocus()
            return

        self._moveZone(-1)

    def keyDown(self):
        self._touchHomeSlideshow()

        if self.zone == "server_switch":
            providers = self._serverSwitchProviders()
            if self.server_switch_index < len(providers) - 1:
                self.server_switch_index += 1
                self._renderServerSwitch()
            return

        # Filter sind ein eigener GELB-Modus. RUNTER verlaesst den Filter
        # direkt in die zugehoerige Posterreihe.
        if self.zone == "fav_filter":
            if self.favoritesRow.getCount() > 0:
                self.zone = "favorites"
                self._refreshFocus()
            return

        if self.zone == "latest_filter":
            if self.latestRow.getCount() > 0:
                self.zone = "latest"
                self._refreshFocus()
            return

        # Sichtbare Reihenfolge:
        # Weiterschauen -> Favoriten -> Neu hinzugefuegt -> Serverwechsel
        self._moveZone(1)

    def keyLeft(self):
        self._touchHomeSlideshow()

        # Untere Bereiche horizontal wie eine zusammenhaengende Reihe.
        if self.zone == "latest" and self.latestRow.index <= 0:
            if self.favoritesRow.getCount() > 0:
                self.zone = "favorites"
                self.favoritesRow.index = self.favoritesRow.getCount() - 1
                self.favoritesRow._ensureVisible()
                self.favoritesRow._prefetchVisible()
                self.favoritesRow._render()
                self._refreshFocus()
                self._updatePreview()
                return
        if self.zone == "continue":
            self.continueRow.moveLeft()
        elif self.zone == "favorites":
            self.favoritesRow.moveLeft()
        elif self.zone == "latest":
            self.latestRow.moveLeft()
        elif self.zone == "fav_filter":
            self.favorite_filter_index = max(0, self.favorite_filter_index - 1)
            self._renderFilters()
        elif self.zone == "latest_filter":
            # Linker Rand von "Neu hinzugefuegt" -> rechter Rand "Favoriten".
            if self.latest_filter_index <= 0:
                self.zone = "fav_filter"
                self.favorite_filter_index = 3
                self._refreshFocus()
                return
            self.latest_filter_index = max(0, self.latest_filter_index - 1)
            self._renderFilters()
        self._updatePreview()

    def keyRight(self):
        self._touchHomeSlideshow()

        # Letztes Favoriten-Poster -> erstes "Neu hinzugefuegt"-Poster.
        if (
            self.zone == "favorites"
            and self.favoritesRow.getCount() > 0
            and self.favoritesRow.index >= self.favoritesRow.getCount() - 1
        ):
            if self.latestRow.getCount() > 0:
                self.zone = "latest"
                self.latestRow.index = 0
                self.latestRow._ensureVisible()
                self.latestRow._prefetchVisible()
                self.latestRow._render()
                self._refreshFocus()
                self._updatePreview()
                return
        if self.zone == "continue":
            self.continueRow.moveRight()
        elif self.zone == "favorites":
            self.favoritesRow.moveRight()
        elif self.zone == "latest":
            self.latestRow.moveRight()
        elif self.zone == "fav_filter":
            # Rechter Rand "Favoriten" -> linker Rand "Neu hinzugefuegt".
            if self.favorite_filter_index >= 3:
                self.zone = "latest_filter"
                self.latest_filter_index = 0
                self._refreshFocus()
                return
            self.favorite_filter_index = min(3, self.favorite_filter_index + 1)
            self._renderFilters()
        elif self.zone == "latest_filter":
            self.latest_filter_index = min(3, self.latest_filter_index + 1)
            self._renderFilters()
        self._updatePreview()

    def keyOk(self):
        self._touchHomeSlideshow()
        providers = ["all", "emby", "jellyfin", "plex"]
        if self.zone == "fav_filter":
            self.favorites_filter = providers[self.favorite_filter_index]
            self.favoritesRow.setItems(self._filtered(self._all_favorite_items, self.favorites_filter))
            self._renderFilters()
            if self.favoritesRow.getCount() > 0:
                self.zone = "favorites"
                self._refreshFocus()
            elif self.favorites_filter != "all" and not any(
                    (getattr(c, "protocol", "") or "").lower() == self.favorites_filter
                    for c in self.server_configs.values()):
                self.keyOpenSettings()
            return
        if self.zone == "latest_filter":
            self.latest_filter = providers[self.latest_filter_index]
            self.latestRow.setItems(self._filtered(self._all_latest_items, self.latest_filter))
            self._renderFilters()
            if self.latestRow.getCount() > 0:
                self.zone = "latest"
                self._refreshFocus()
            elif self.latest_filter != "all" and not any(
                    (getattr(c, "protocol", "") or "").lower() == self.latest_filter
                    for c in self.server_configs.values()):
                self.keyOpenSettings()
            return

        if self.zone == "server_switch":
            # MEDIAPLUGINS2026_PROVIDER_LIBRARIES_INTERNAL1
            self._openProviderLibraries(self._serverSwitchProvider())
            return

        item = self._selectedItem()
        if item and getattr(item, "is_demo", False):
            self.keyOpenSettings()
            return
        if item:
            self._openDetail(item)
        elif not self.server_configs:
            self.keyOpenSettings()

    def keyDetailsCurrent(self):
        self._touchHomeSlideshow()
        item = self._previewItem()
        if item is None:
            return
        if getattr(item, "is_demo", False):
            self.keyOpenSettings()
            return
        self._openDetail(item)

    def _openProviderLibraries(self, provider):
        # MEDIAPLUGINS2026_PROVIDER_LIBRARIES_INTERNAL1
        # Der Home-Serverwechsel bleibt komplett innerhalb Media Plugins 2026:
        # Anbieter -> dessen konfigurierte Server -> dessen Bibliotheken ->
        # vorhandener interner LibraryBrowser.
        provider = (provider or "").strip().lower()
        provider_name = _PROVIDER_NAMES.get(
            provider,
            provider.capitalize() if provider else "Quelle",
        )
        if provider not in ("emby", "jellyfin", "plex"):
            return

        matching = []
        for name, cfg in self.server_configs.items():
            if (getattr(cfg, "protocol", "") or "").strip().lower() == provider:
                matching.append(name)

        if not matching:
            self.session.open(
                MessageBox,
                "%s ist in Media Plugins 2026 nicht eingerichtet." % provider_name,
                MessageBox.TYPE_INFO,
                timeout=5,
            )
            return

        online = [
            name for name in matching
            if self.server_status.get(name) == "online"
        ]
        if not online:
            pending = any(
                int(self._server_results_pending.get(name, 0) or 0) > 0
                for name in matching
            )
            if pending:
                message = "%s wird noch geladen. Bitte gleich noch einmal versuchen." % provider_name
            else:
                message = "%s ist derzeit offline." % provider_name
            self.session.open(
                MessageBox,
                message,
                MessageBox.TYPE_INFO,
                timeout=5,
            )
            return

        # Nur Server dieses Providers an den internen Ordnerbrowser geben.
        # ServerFolderBrowser liest daraus ausschließlich deren Libraries.
        provider_libraries = {}
        ready_names = []
        for name in online:
            libs = list(self.server_libraries.get(name, []) or [])
            if libs:
                provider_libraries[name] = libs
                ready_names.append(name)

        if not ready_names:
            pending = any(
                int(self._server_results_pending.get(name, 0) or 0) > 0
                for name in online
            )
            if pending:
                message = "%s-Bibliotheken werden noch geladen." % provider_name
            else:
                message = "Für %s wurden keine Bibliotheken gefunden." % provider_name
            self.session.open(
                MessageBox,
                message,
                MessageBox.TYPE_INFO,
                timeout=5,
            )
            return

        try:
            self._home_slideshow_timer.stop()
        except Exception:
            pass

        if self._child_open:
            return

        from .ServerFolderBrowser import ServerFolderBrowser

        title = "%s – Bibliotheken" % provider_name
        self._child_open = True
        log.info(
            "Home interne Provider-Bibliotheken: provider=%s server=%s libraries=%d",
            provider,
            ",".join(ready_names),
            sum(len(provider_libraries.get(name, [])) for name in ready_names),
        )
        try:
            child = self.session.open(
                ServerFolderBrowser,
                title,
                ready_names,
                provider_libraries,
                self.clients,
            )
            child.onClose.append(self._childClosed)
        except Exception as exc:
            self._child_open = False
            log.exception(
                "Interne %s-Bibliotheken konnten nicht geoeffnet werden: %s",
                provider_name,
                exc,
            )
            self.session.open(
                MessageBox,
                "%s-Bibliotheken konnten nicht geöffnet werden." % provider_name,
                MessageBox.TYPE_ERROR,
                timeout=6,
            )

    @staticmethod
    def _providerPluginAliases(provider):
        provider = (provider or "").strip().lower()
        if provider == "emby":
            return ("embyflowe2", "embyflow e2", "emby")
        if provider == "plex":
            return ("plex2026", "plex 2026", "plex")
        if provider == "jellyfin":
            return ("jellyfin", "jellyfin2026", "jellyfin 2026")
        return ()

    def _findProviderPlugin(self, provider):
        # Originalplugin in der bereits geladenen Enigma2-Pluginliste suchen.
        try:
            from Components.PluginComponent import plugins
            from Plugins.Plugin import PluginDescriptor
        except Exception as e:
            log.warning("Serverwechsel: PluginComponent nicht verfuegbar: %s", e)
            return None

        descriptors = []
        seen = set()
        where_values = [
            PluginDescriptor.WHERE_PLUGINMENU,
            getattr(PluginDescriptor, "WHERE_EXTENSIONSMENU", None),
            getattr(PluginDescriptor, "WHERE_MENU", None),
        ]
        for where in where_values:
            if where is None:
                continue
            try:
                rows = plugins.getPlugins(where) or []
            except Exception:
                rows = []
            for descriptor in rows:
                ident = id(descriptor)
                if ident in seen:
                    continue
                seen.add(ident)
                descriptors.append(descriptor)

        aliases = self._providerPluginAliases(provider)
        for alias in aliases:
            for descriptor in descriptors:
                name = str(getattr(descriptor, "name", "") or "").strip().lower()
                if name == alias:
                    return descriptor

        provider = (provider or "").strip().lower()
        candidates = []
        seen_names = set()
        for descriptor in descriptors:
            name = str(getattr(descriptor, "name", "") or "").strip()
            folded = name.lower()
            if not folded or "infusemedia" in folded:
                continue
            matched = bool(provider and provider in folded)
            if provider == "emby" and "embyflow" in folded:
                matched = True
            if provider == "plex" and "plex2026" in folded:
                matched = True
            if matched and folded not in seen_names:
                seen_names.add(folded)
                candidates.append(descriptor)

        return candidates[0] if candidates else None

    def _openProviderPluginDirect(self, provider):
        # Fallback fuer Images, deren PluginComponent den Ziel-Descriptor nicht liefert.
        import importlib

        known = {
            "emby": ("Plugins.Extensions.EmbyFlowE2.plugin",),
            "plex": ("Plugins.Extensions.Plex2026.plugin",),
            "jellyfin": (
                "Plugins.Extensions.Jellyfin.plugin",
                "Plugins.Extensions.Jellyfin2026.plugin",
            ),
        }

        module_names = list(known.get(provider, ()))
        ext_dir = "/usr/lib/enigma2/python/Plugins/Extensions"
        try:
            for entry in os.listdir(ext_dir):
                folded = entry.lower()
                if folded in ("infusemedia2026", "mediaplugins2026"):

                    continue
                if provider == "emby":
                    match = "emby" in folded
                elif provider == "plex":
                    match = "plex" in folded
                elif provider == "jellyfin":
                    match = "jelly" in folded
                else:
                    match = False
                if match:
                    modname = "Plugins.Extensions.%s.plugin" % entry
                    if modname not in module_names:
                        module_names.append(modname)
        except Exception:
            pass

        errors = []
        for module_name in module_names:
            try:
                module = importlib.import_module(module_name)
            except Exception as e:
                errors.append("%s import: %s" % (module_name, e))
                continue

            fn = getattr(module, "main", None)
            if callable(fn):
                try:
                    fn(self.session)
                    log.info("Home Serverwechsel direkt: provider=%s module=%s", provider, module_name)
                    return True
                except TypeError:
                    try:
                        fn(session=self.session)
                        log.info("Home Serverwechsel direkt: provider=%s module=%s", provider, module_name)
                        return True
                    except Exception as e:
                        errors.append("%s main(session=): %s" % (module_name, e))
                except Exception as e:
                    errors.append("%s main: %s" % (module_name, e))

            plugins_fn = getattr(module, "Plugins", None)
            if callable(plugins_fn):
                try:
                    rows = plugins_fn() or []
                    if not isinstance(rows, (list, tuple)):
                        rows = [rows]
                    for descriptor in rows:
                        name = str(getattr(descriptor, "name", "") or "")
                        if "infusemedia" in name.lower():
                            continue
                        try:
                            descriptor(session=self.session)
                            log.info(
                                "Home Serverwechsel direkt: provider=%s module=%s descriptor=%s",
                                provider, module_name, name,
                            )
                            return True
                        except Exception as e:
                            errors.append("%s descriptor %s: %s" % (module_name, name, e))
                except Exception as e:
                    errors.append("%s Plugins(): %s" % (module_name, e))

        if errors:
            log.warning(
                "Serverwechsel direkte Fallbacks fehlgeschlagen (%s): %s",
                provider, " | ".join(errors[-4:]),
            )
        return False

    def _openProviderPlugin(self, provider):
        provider = (provider or "").strip().lower()
        provider_name = _PROVIDER_NAMES.get(
            provider,
            provider.capitalize() if provider else "Quelle",
        )

        if provider not in ("emby", "jellyfin", "plex"):
            return

        try:
            self._home_slideshow_timer.stop()
        except Exception:
            pass

        descriptor = self._findProviderPlugin(provider)
        if descriptor is not None:
            try:
                log.info(
                    "Home Serverwechsel: provider=%s plugin=%s",
                    provider,
                    getattr(descriptor, "name", "?"),
                )
                descriptor(session=self.session)
                return
            except TypeError:
                try:
                    descriptor(self.session)
                    return
                except Exception as e:
                    log.warning("Serverwechsel Descriptor %s fehlgeschlagen: %s", provider_name, e)
            except Exception as e:
                log.warning("Serverwechsel Descriptor %s fehlgeschlagen: %s", provider_name, e)

        if self._openProviderPluginDirect(provider):
            return

        self.session.open(
            MessageBox,
            "%s konnte nicht geoeffnet werden.\n\nBitte pruefen, ob das %s-Plugin installiert ist."
            % (provider_name, provider_name),
            MessageBox.TYPE_ERROR,
            timeout=7,
        )

    # MEDIAPLUGINS2026_HOME_PROVIDER_COLORKEYS1
    def _openProviderByColorKey(self, provider):
        # Direkter Farbtasten-Shortcut in die internen Provider-Bibliotheken.
        self._touchHomeSlideshow()
        try:
            self._home_slideshow_timer.stop()
        except Exception:
            pass
        self._openProviderLibraries(provider)

    def keyOpenEmbyLibraries(self):
        self._openProviderByColorKey("emby")

    def keyOpenPlexLibraries(self):
        self._openProviderByColorKey("plex")

    def keyOpenJellyfinLibraries(self):
        self._openProviderByColorKey("jellyfin")

    def keyFilter(self):
        self._touchHomeSlideshow()
        # Gelb springt zum Filter der aktuellen Sektion. In Weiterschauen
        # wird die Quelle direkt durchgeschaltet, da dort bewusst keine
        # zusaetzliche Chipzeile Platz beansprucht.
        if self.zone == "continue":
            available = ["all"] + [p for p in ("emby", "jellyfin", "plex")
                                     if any((getattr(c, "protocol", "") or "").lower() == p
                                            for c in self.server_configs.values())]
            if len(available) <= 1:
                self.keyOpenSettings()
                return
            try:
                pos = available.index(self.continue_filter)
            except ValueError:
                pos = 0
            self.continue_filter = available[(pos + 1) % len(available)]
            self.continueRow.setItems(self._filteredContinue(self._all_continue_items, self.continue_filter))
            self["message"].setText("Weiterschauen: %s" % _PROVIDER_NAMES.get(self.continue_filter, self.continue_filter))
            self._refreshFocus()
        elif self.zone in ("favorites", "fav_filter"):
            self.zone = "fav_filter"
            self._refreshFocus()
        else:
            self.zone = "latest_filter"
            self._refreshFocus()

    def keyCancel(self):
        self._closeHomeSlideshow()
        self.close()

    # ------------------------------------------------------------------
    # Oeffnen / Player
    # ------------------------------------------------------------------
    def _selectedItem(self):
        if self.zone == "continue":
            return self.continueRow.getCurrent()
        if self.zone == "favorites":
            return self.favoritesRow.getCurrent()
        if self.zone == "latest":
            return self.latestRow.getCurrent()
        return None

    def keyPlayCurrent(self):
        item = self._selectedItem()
        if item is None:
            return
        if getattr(item, "is_demo", False):
            self.keyOpenSettings()
            return

        client = self.clients.get(item.server_name)
        if not client:
            return

        try:
            # MEDIAPLUGINS2026_PROVIDERPLAYER_RESTORE1
            from .ProviderPlayerBridge import open_provider_player

            if open_provider_player(
                self.session,
                item,
                client,
                start_ticks=int(getattr(item, "resume_ticks", 0) or 0),
            ):
                return

            from enigma import eServiceReference
            from .InfuseMoviePlayer import InfuseMoviePlayer

            url = client.get_stream_url(item.id, item)
            ref = eServiceReference(4097, 0, url)
            ref.setName(item.title)
            self.session.open(
                InfuseMoviePlayer,
                ref,
                item,
                client,
                url,
            )

        except Exception as e:
            log.exception("MediaWall-Wiedergabe fehlgeschlagen: %s", e)
            self.session.open(
                MessageBox,
                "Wiedergabe fehlgeschlagen.",
                MessageBox.TYPE_ERROR,
            )

    def _openDetail(self, item):
        if not item or self._child_open:
            return
        client = self.clients.get(item.server_name)
        if not client:
            return
        try:
            from .MediaDetail import MediaDetail
            self._child_open = True
            child = self.session.open(MediaDetail, item, client)
            child.onClose.append(self._childClosed)
        except Exception as e:
            self._child_open = False
            log.exception("Details konnten nicht geoeffnet werden: %s", e)

    def _childClosed(self, *args):
        self._child_open = False
        self._armHomeSlideshow()

    def keyOpenSettings(self):
        try:
            self._home_slideshow_timer.stop()
        except Exception:
            pass
        from .Settings import Settings
        self.session.openWithCallback(self._settingsClosed, Settings)

    def _settingsClosed(self, *args):
        self.loadHome()

    def keyOpenSearch(self):
        try:
            self._home_slideshow_timer.stop()
        except Exception:
            pass
        from .SearchScreen import SearchScreen
        self.session.openWithCallback(self._searchClosed, SearchScreen)

    def _searchClosed(self, *args):
        self._armHomeSlideshow()
