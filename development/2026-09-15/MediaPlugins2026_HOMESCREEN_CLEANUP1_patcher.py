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
MARKER = "# MEDIAPLUGINS2026_HOMESCREEN_CLEANUP1"


def read(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def backup(path):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = path + ".before_cleanup1_" + stamp
    shutil.copy2(path, target)
    return target


def replace_once(text, old, new, label, required=True):
    if old not in text:
        if required:
            raise RuntimeError("%s: erwarteter Block nicht gefunden" % label)
        return text
    return text.replace(old, new, 1)


def patch(text):
    if MARKER in text:
        return text, 0

    if "class HomeScreen(Screen):" not in text:
        raise RuntimeError("HomeScreen Klasse nicht gefunden")
    if "class MediaWallRow(object):" not in text:
        raise RuntimeError("MediaWallRow Klasse nicht gefunden")

    # 1) Alte INFUSEMEDIA-Kommentar-Marker konsolidieren.
    lines = []
    removed = 0
    for line in text.splitlines():
        if line.strip().startswith("# INFUSEMEDIA2026_"):
            removed += 1
            continue
        lines.append(line)
    text = "\n".join(lines) + "\n"

    text = re.sub(
        r'(?m)^# Media Plugins 2026 HomeScreen:.*$\n?',
        '',
        text,
        count=1,
    )

    history = '''# =====================================================================
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
'''

    encoding = "# -*- coding: utf-8 -*-\n"
    if text.startswith(encoding):
        text = encoding + history + text[len(encoding):]
    else:
        text = history + text

    # 2) Timing-Logs im Produktivbetrieb abschalten.
    text = replace_once(
        text,
        '_HOME_SLIDESHOW_DELAY_MS = 6000\n',
        '''_HOME_SLIDESHOW_DELAY_MS = 6000

# Produktiv standardmaessig AUS.
# Fuer Poster-/Pipeline-Diagnose temporaer auf True setzen.
_DEBUG_TIMING = False
''',
        "DEBUG_TIMING Flag",
    )

    text = replace_once(
        text,
        '''def _pipeline_timing_write(message):
    try:
''',
        '''def _pipeline_timing_write(message):
    if not _DEBUG_TIMING:
        return
    try:
''',
        "_pipeline_timing_write Guard",
    )

    text = replace_once(
        text,
        'def _poster_timing_log(message):\n    """Eigenes Diagnose-Log; niemals Bild-URLs oder Tokens schreiben."""\n    try:\n',
        'def _poster_timing_log(message):\n    """Eigenes Diagnose-Log; niemals Bild-URLs oder Tokens schreiben."""\n    if not _DEBUG_TIMING:\n        return\n    try:\n',
        "_poster_timing_log Guard",
    )

    text = replace_once(
        text,
        '''    def _posterTimingWrite(self, event, item, state, extra=""):
        now = time.monotonic()
''',
        '''    def _posterTimingWrite(self, event, item, state, extra=""):
        if not _DEBUG_TIMING:
            return
        now = time.monotonic()
''',
        "_posterTimingWrite Guard",
    )

    text = replace_once(
        text,
        '''    def _pipelineTiming(self, event, extra=""):
        try:
''',
        '''    def _pipelineTiming(self, event, extra=""):
        if not _DEBUG_TIMING:
            return
        try:
''',
        "_pipelineTiming Guard",
    )

    # 3) Alte interne Infuse-Namen.
    text = text.replace("_infuse_poster_timing", "_mp2026_poster_timing")
    text = text.replace("brand_infuse", "brand_logo")

    # 4) Kleine Safe-Call-Basis, nur fuer harmlose UI-Aufrufe.
    helper = '''\n\ndef _safe_call(fn, *args, **kwargs):
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
'''
    text = replace_once(
        text,
        'from ..utils import log\n',
        'from ..utils import log\n' + helper,
        "_safe_call Helper",
    )

    text = replace_once(
        text,
        '''        try:
            self.screen._updatePreview()
        except Exception:
            pass
''',
        '''        _safe_call(
            self.screen._updatePreview,
            _log_ctx="MediaWallRow._updatePreview",
        )
''',
        "safe_call UI-Einsatz",
        required=False,
    )

    # 5) Klare Abschnittstrenner.
    sections = (
        (
            'class MediaWallRow(object):\n',
            '''# =====================================================================
# MEDIA WALL / POSTER PIPELINE
# =====================================================================
''',
        ),
        (
            'def _build_skin():\n',
            '''# =====================================================================
# SKIN / LAYOUT
# =====================================================================
''',
        ),
        (
            '    def loadHome(self):\n',
            '''    # =================================================================
    # HOME LOAD / PROVIDER REQUESTS
    # =================================================================
''',
        ),
        (
            '    @staticmethod\n    def _homeSnapshotServerKey(servers):\n',
            '''    # =================================================================
    # SNAPSHOT / COLD START
    # =================================================================
''',
        ),
        (
            '    @staticmethod\n    def _homeVisibleRowSignature(items):\n',
            '''    # =================================================================
    # PROGRESSIVE RENDER / SNAPSHOT SWAP
    # =================================================================
''',
        ),
        (
            '    @staticmethod\n    def _homeNormalizeTitle(value):\n',
            '''    # =================================================================
    # DEDUPE / UNIFIED CONTINUE
    # =================================================================
''',
        ),
        (
            '    def _filteredContinue(self, items, provider):\n',
            '''    # =================================================================
    # FILTER / RENDER / STATUS
    # =================================================================
''',
        ),
        (
            '    def _previewItem(self):\n',
            '''    # =================================================================
    # PREVIEW / AVAILABILITY / DETAIL / AMBIENT
    # =================================================================
''',
        ),
        (
            '    @staticmethod\n    def _serverSwitchProviders():\n',
            '''    # =================================================================
    # PROVIDER SWITCH / INTERNAL LIBRARIES
    # =================================================================
''',
        ),
        (
            '    def _zones(self):\n',
            '''    # =================================================================
    # NAVIGATION / REMOTE KEYS
    # =================================================================
''',
        ),
    )

    for anchor, heading in sections:
        if anchor not in text:
            raise RuntimeError("Abschnittsanker fehlt: %s" % anchor.splitlines()[-1])
        text = text.replace(anchor, heading + anchor, 1)

    text = re.sub(r'\n{4,}', '\n\n\n', text)

    compile(text, "HomeScreen.py", "exec")

    required = (
        MARKER,
        "_DEBUG_TIMING = False",
        "_mp2026_poster_timing",
        'name="brand_logo"',
        'self["brand_logo"]',
        "def _safe_call(fn, *args, **kwargs):",
        "# SNAPSHOT / COLD START",
        "# DEDUPE / UNIFIED CONTINUE",
        "# PREVIEW / AVAILABILITY / DETAIL / AMBIENT",
        "# PROVIDER SWITCH / INTERNAL LIBRARIES",
        "# NAVIGATION / REMOTE KEYS",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise RuntimeError("CLEANUP1 Verifikation fehlt: %r" % missing)

    if "_infuse_poster_timing" in text:
        raise RuntimeError("Legacy _infuse_poster_timing noch vorhanden")
    if "brand_infuse" in text:
        raise RuntimeError("Legacy brand_infuse noch vorhanden")
    if re.search(r'(?m)^\s*# INFUSEMEDIA2026_', text):
        raise RuntimeError("Legacy INFUSEMEDIA-Marker noch verteilt")

    return text, removed


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DEFAULT
    target = os.path.join(root, TARGET_REL)

    if not os.path.isfile(target):
        raise SystemExit("HomeScreen.py fehlt: %s" % target)

    original = read(target)
    patched, removed = patch(original)

    compile(patched, target, "exec")

    backup_path = backup(target)
    write(target, patched)

    verify = read(target)
    compile(verify, target, "exec")

    print("OK MEDIAPLUGINS2026_HOMESCREEN_CLEANUP1")
    print("- Timing-/Poster-Diagnoselogs standardmaessig AUS")
    print("- Diagnose bei Bedarf: _DEBUG_TIMING = True")
    print("- _infuse_poster_timing -> _mp2026_poster_timing")
    print("- brand_infuse -> brand_logo")
    print("- %d alte INFUSEMEDIA-Marker konsolidiert" % removed)
    print("- aktuelle MEDIAPLUGINS2026-Marker bleiben erhalten")
    print("- klare Abschnitte fuer Snapshot / Continue / Preview / Provider / Navigation")
    print("- _safe_call nur fuer unkritische UI-Aufrufe")
    print("- KEINE Provider-/Poster-/Navigation-/Farbtasten-Logik geaendert")
    print("Backup: %s" % backup_path)


if __name__ == "__main__":
    main()
