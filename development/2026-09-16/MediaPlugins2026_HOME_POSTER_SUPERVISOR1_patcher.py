# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import re
import shutil
import sys
import time

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
TARGET_REL = "screens/HomeScreen.py"

MARKER = "# MEDIAPLUGINS2026_HOME_POSTER_SUPERVISOR1"
REQUIRED_HARDEN = "MEDIAPLUGINS2026_POSTER_PIPELINE_HARDEN1_HOME"

ROW_SETITEMS = r'''    def setItems(self, items):
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
'''

ROW_PREFETCH = r'''    def _prefetchVisible(self):
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
'''

ROW_LOADED = r'''    def _onPosterLoaded(self, item, path, generation=None, item_key=None):
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
'''

ROW_FAILED = r'''    def _onPosterFailed(self, item, err, generation=None, item_key=None):
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
'''

SCHEDULE = r'''    def _schedulePosterRepair(self, delay_ms=1200, reset=False):
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
'''

REPAIR = r'''    def _repairVisiblePosters(self):
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
'''

def read(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def method_block(text, name):
    pattern = re.compile(
        r"(?ms)^    def %s\(.*?(?=^    def |^    @staticmethod|^    @classmethod|^class |\Z)"
        % re.escape(name)
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(
            "%s: erwartete genau 1 Methode, gefunden %d"
            % (name, len(matches))
        )
    return matches[0]


def replace_method(text, name, replacement):
    m = method_block(text, name)
    return text[:m.start()] + replacement.rstrip() + "\n\n" + text[m.end():]


def patch(text):
    if MARKER in text:
        return text

    if REQUIRED_HARDEN not in text:
        raise RuntimeError(
            "POSTER_PIPELINE_HARDEN1 fehlt. Abbruch ohne Aenderung."
        )

    required_methods = (
        "setItems",
        "_prefetchVisible",
        "_onPosterLoaded",
        "_onPosterFailed",
        "_schedulePosterRepair",
        "_repairVisiblePosters",
        "_homeSwapRowItemsWithoutRender",
    )
    for name in required_methods:
        method_block(text, name)

    init_anchor = "        self._poster_generation = 0\n"
    if init_anchor not in text:
        raise RuntimeError("_poster_generation Init-Anker fehlt")
    if "self._poster_inflight = set()" not in text:
        text = text.replace(
            init_anchor,
            init_anchor
            + "        self._poster_inflight = set()\n"
            + "        self._poster_retry_after = {}\n",
            1,
        )

    home_anchor = "        self._poster_repair_round = 0\n"
    if home_anchor not in text:
        raise RuntimeError("_poster_repair_round Init-Anker fehlt")
    if "self._poster_repair_started = time.monotonic()" not in text:
        text = text.replace(
            home_anchor,
            home_anchor
            + "        self._poster_repair_started = time.monotonic()\n",
            1,
        )

    text = replace_method(text, "setItems", ROW_SETITEMS)
    text = replace_method(text, "_prefetchVisible", ROW_PREFETCH)
    text = replace_method(text, "_onPosterLoaded", ROW_LOADED)
    text = replace_method(text, "_onPosterFailed", ROW_FAILED)
    text = replace_method(text, "_schedulePosterRepair", SCHEDULE)
    text = replace_method(text, "_repairVisiblePosters", REPAIR)

    m = method_block(text, "_homeSwapRowItemsWithoutRender")
    block = m.group(0)
    old = '''        try:
            row._poster_generation += 1
        except Exception:
            pass
'''
    new = '''        try:
            row._poster_generation += 1
            row._poster_inflight.clear()
            row._poster_retry_after.clear()
        except Exception:
            pass
'''
    if old not in block:
        raise RuntimeError(
            "_homeSwapRowItemsWithoutRender Generation-Block nicht erkannt"
        )
    block = block.replace(old, new, 1)

    ensure = "        row._ensureVisible()\n"
    if ensure not in block:
        raise RuntimeError("_homeSwapRowItemsWithoutRender ensureVisible fehlt")
    block = block.replace(
        ensure,
        ensure
        + "        try:\n"
        + "            row.screen._schedulePosterRepair(250, reset=True)\n"
        + "        except Exception:\n"
        + "            pass\n",
        1,
    )
    text = text[:m.start()] + block.rstrip() + "\n\n" + text[m.end():]

    if "def _homePrefetchMissingVisiblePosters" in text:
        m = method_block(text, "_homePrefetchMissingVisiblePosters")
        block = m.group(0)
        if not re.search(
            r"(?m)^(?P<i>\s*)row\._prefetchVisible\(\)\s*\n(?P=i)row\._render\(\)",
            block,
        ):
            block, n = re.subn(
                r"(?m)^(?P<i>\s*)row\._prefetchVisible\(\)\s*$",
                lambda mm: mm.group(0) + "\n" + mm.group("i") + "row._render()",
                block,
                count=1,
            )
            if n != 1:
                raise RuntimeError(
                    "_homePrefetchMissingVisiblePosters Render-Fix nicht eindeutig"
                )
            text = text[:m.start()] + block.rstrip() + "\n\n" + text[m.end():]

    cls = "class HomeScreen(Screen):\n"
    if cls not in text:
        raise RuntimeError("HomeScreen Klassenanker fehlt")
    text = text.replace(cls, MARKER + "\n" + cls, 1)

    compile(text, "HomeScreen.py", "exec")

    verify = (
        MARKER,
        "self._poster_inflight = set()",
        "self._poster_retry_after = {}",
        "Poster-Supervisor beendet",
        "round_no < 24",
        "row.screen._schedulePosterRepair(250, reset=True)",
    )
    missing = [x for x in verify if x not in text]
    if missing:
        raise RuntimeError("Supervisor-Verifikation fehlt: %r" % missing)

    return text


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DEFAULT
    target = os.path.join(root, TARGET_REL)

    if not os.path.isfile(target):
        raise SystemExit("HomeScreen.py fehlt: %s" % target)

    original = read(target)
    patched = patch(original)
    compile(patched, target, "exec")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = target + ".before_home_poster_supervisor1_" + stamp
    shutil.copy2(target, backup)

    write(target, patched)

    verify = read(target)
    compile(verify, target, "exec")
    if MARKER not in verify:
        raise RuntimeError("Marker fehlt nach Schreiben")

    print("OK MEDIAPLUGINS2026_HOME_POSTER_SUPERVISOR1")
    print("- Poster-Reparatur nicht mehr auf nur 4 Runden begrenzt")
    print("- bis zu rund 60 s selbstheilende sichtbare Poster-Aufsicht")
    print("- Live-Item-Wechsel startet Supervisor automatisch neu")
    print("- pro Item nur ein paralleler Poster-Download")
    print("- 3 s Cooldown nach Fehler statt Callback-/Request-Stau")
    print("- synchrone Cache-Treffer werden sofort gerendert")
    print("- Provider / Navigation / Layout / Player unveraendert")
    print("Backup: %s" % backup)


if __name__ == "__main__":
    main()
