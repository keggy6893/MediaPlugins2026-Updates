# -*- coding: utf-8 -*-
from __future__ import print_function

import ast
import io
import os
import re
import shutil
import sys

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
CACHE_REL = "utils/image_cache.py"
HOME_REL = "screens/HomeScreen.py"

MARKER_CACHE = "# MEDIAPLUGINS2026_POSTER_PIPELINE_FINALIZE1_CACHE"
MARKER_HOME = "# MEDIAPLUGINS2026_POSTER_PIPELINE_FINALIZE1_HOME"
INTERNAL_CACHE = "/etc/enigma2/mediaplugins2026/poster_cache"
ASYNC_HELPER = '    # MEDIAPLUGINS2026_POSTER_PIPELINE_FINALIZE1_HOME\n    def _ensureHomeAsyncRuntimeState(self):\n        if not hasattr(self, "_preview_detail_cache"):\n            self._preview_detail_cache = {}\n        if not hasattr(self, "_preview_detail_failed"):\n            self._preview_detail_failed = set()\n        if not hasattr(self, "_preview_detail_inflight"):\n            self._preview_detail_inflight = {}\n        if not hasattr(self, "_preview_detail_pending"):\n            self._preview_detail_pending = None\n        if not hasattr(self, "_preview_detail_serial"):\n            self._preview_detail_serial = 0\n        if not hasattr(self, "_preview_detail_closed"):\n            self._preview_detail_closed = False\n        if not hasattr(self, "_preview_detail_timer"):\n            self._preview_detail_timer = eTimer()\n            try:\n                self._preview_detail_timer.callback.append(self._requestPreviewDetail)\n            except Exception:\n                pass\n\n        if not hasattr(self, "_home_ambient_closed"):\n            self._home_ambient_closed = False\n        if not hasattr(self, "_home_ambient_serial"):\n            self._home_ambient_serial = 0\n        if not hasattr(self, "_home_ambient_key"):\n            self._home_ambient_key = None\n        if not hasattr(self, "_home_ambient_pending"):\n            self._home_ambient_pending = None\n        if not hasattr(self, "_home_ambient_timer"):\n            self._home_ambient_timer = eTimer()\n            try:\n                self._home_ambient_timer.callback.append(self._requestHomeAmbient)\n            except Exception:\n                pass\n'


def read(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def backup(path, suffix):
    target = path + suffix
    if os.path.isfile(path) and not os.path.exists(target):
        shutil.copy2(path, target)
    return target


def module_has_image_cache_singleton(text):
    tree = ast.parse(text)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "image_cache"
            for target in node.targets
        ):
            continue
        value = node.value
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "ImageCache"
        ):
            return True
    return False


def patch_cache(text):
    if MARKER_CACHE in text:
        return text

    if "class ImageCache(object):" not in text:
        raise RuntimeError("ImageCache Klasse nicht gefunden")

    text, count = re.subn(
        r'(?m)^CACHE_DIR\s*=\s*.*$',
        'CACHE_DIR = "%s"' % INTERNAL_CACHE,
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError("CACHE_DIR nicht eindeutig gefunden")

    replacements = {
        r'(?m)^PERSISTENT_CACHE_MAX_BYTES\s*=.*$':
            "PERSISTENT_CACHE_MAX_BYTES = 12 * 1024 * 1024",
        r'(?m)^PERSISTENT_CACHE_MAX_FILES\s*=.*$':
            "PERSISTENT_CACHE_MAX_FILES = 120",
        r'(?m)^CACHE_MAX_AGE_DAYS\s*=.*$':
            "CACHE_MAX_AGE_DAYS = 14",
    }
    for pattern, replacement in replacements.items():
        text, n = re.subn(pattern, replacement, text, count=1)
        if n != 1:
            raise RuntimeError("Cache-Limit nicht gefunden: %s" % replacement)

    if re.search(r'(?m)^    def _stable_cache_key\(url\):$', text):
        text, n = re.subn(
            r'(?m)^    def _stable_cache_key\(url\):$',
            '    @staticmethod\n    def _stable_cache_key(url):',
            text,
            count=1,
        )
        if n != 1:
            raise RuntimeError("_stable_cache_key Reparatur fehlgeschlagen")

    init_anchor = "        self.cache_dir = CACHE_DIR\n"
    if init_anchor not in text:
        raise RuntimeError("ImageCache init cache_dir Anker fehlt")
    text = text.replace(
        init_anchor,
        init_anchor + '        self.cache_dir = "%s"\n' % INTERNAL_CACHE,
        1,
    )

    log_anchor = "        self._agent = None\n"
    if log_anchor not in text:
        raise RuntimeError("ImageCache _agent Anker fehlt")
    text = text.replace(
        log_anchor,
        '        log.info("PosterCache aktiv: %s", self.cache_dir)\n\n'
        + log_anchor,
        1,
    )

    if not module_has_image_cache_singleton(text):
        text = text.rstrip() + "\n\nimage_cache = ImageCache()\n"

    text = text.replace(
        "class ImageCache(object):\n",
        MARKER_CACHE + "\nclass ImageCache(object):\n",
        1,
    )

    compile(text, "image_cache.py", "exec")
    if not module_has_image_cache_singleton(text):
        raise RuntimeError("image_cache Singleton fehlt nach Patch")
    return text


def inject_method_guard(text, method_name):
    pattern = re.compile(
        r'(?m)^(    def %s\([^\n]*\):\n)' % re.escape(method_name)
    )
    matches = list(pattern.finditer(text))
    if not matches:
        return text, False
    if len(matches) != 1:
        raise RuntimeError("%s nicht eindeutig gefunden" % method_name)

    m = matches[0]
    insert_at = m.end()
    tail = text[insert_at:insert_at + 180]
    if "_ensureHomeAsyncRuntimeState()" in tail:
        return text, True

    guard = "        self._ensureHomeAsyncRuntimeState()\n"
    return text[:insert_at] + guard + text[insert_at:], True


def patch_home(text):
    if MARKER_HOME in text:
        return text

    if "class HomeScreen(Screen):" not in text:
        raise RuntimeError("HomeScreen Klasse nicht gefunden")

    anchor_candidates = [
        "    def _requestPreviewDetail(self):\n",
        "    def _previewDetailLoaded(self, serial, key, target, detail):\n",
        "    def _updateHomeAmbient(self, item):\n",
    ]
    anchor = next((candidate for candidate in anchor_candidates if candidate in text), None)
    if anchor is None:
        raise RuntimeError("Kein Home-Async-Anker gefunden")

    text = text.replace(
        anchor,
        ASYNC_HELPER.rstrip() + "\n\n" + anchor,
        1,
    )

    guarded = 0
    for name in (
        "_requestPreviewDetail",
        "_previewDetailLoaded",
        "_previewDetailFailed",
        "_closePreviewDetail",
        "_updateHomeAmbient",
        "_requestHomeAmbient",
        "_homeAmbientLoaded",
        "_closeHomeAmbient",
        "_updatePreview",
    ):
        text, found = inject_method_guard(text, name)
        guarded += int(found)

    if guarded < 5:
        raise RuntimeError(
            "Zu wenige Home-Async-Methoden abgesichert: %d" % guarded
        )

    text = re.sub(
        r'(?m)^    @staticmethod\n    @staticmethod\n'
        r'    def _homeSwapRowItemsWithoutRender\(',
        '    @staticmethod\n'
        '    def _homeSwapRowItemsWithoutRender(',
        text,
        count=1,
    )

    compile(text, "HomeScreen.py", "exec")
    return text


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DEFAULT
    cache_path = os.path.join(root, CACHE_REL)
    home_path = os.path.join(root, HOME_REL)

    for path in (cache_path, home_path):
        if not os.path.isfile(path):
            raise SystemExit("Datei nicht gefunden: %s" % path)

    cache_original = read(cache_path)
    home_original = read(home_path)

    cache_new = patch_cache(cache_original)
    home_new = patch_home(home_original)

    compile(cache_new, cache_path, "exec")
    compile(home_new, home_path, "exec")

    cache_backup = backup(cache_path, ".before_poster_pipeline_finalize1")
    home_backup = backup(home_path, ".before_poster_pipeline_finalize1")

    write(cache_path, cache_new)
    write(home_path, home_new)

    cache_verify = read(cache_path)
    home_verify = read(home_path)
    compile(cache_verify, cache_path, "exec")
    compile(home_verify, home_path, "exec")

    checks = [
        ('CACHE_DIR = "%s"' % INTERNAL_CACHE) in cache_verify,
        "PERSISTENT_CACHE_MAX_BYTES = 12 * 1024 * 1024" in cache_verify,
        "PERSISTENT_CACHE_MAX_FILES = 120" in cache_verify,
        "CACHE_MAX_AGE_DAYS = 14" in cache_verify,
        module_has_image_cache_singleton(cache_verify),
        "@staticmethod\n    def _stable_cache_key(url):" in cache_verify,
        MARKER_HOME in home_verify,
        "def _ensureHomeAsyncRuntimeState(self):" in home_verify,
    ]
    if not all(checks):
        raise RuntimeError("FINALIZE1 Verifikation fehlgeschlagen")

    print("OK MEDIAPLUGINS2026_POSTER_PIPELINE_FINALIZE1")
    print("- Poster-Downloads/rendering aus H1 bleiben erhalten")
    print("- Cache fest intern: %s" % INTERNAL_CACHE)
    print("- keine HDD-/USB-Abhaengigkeit")
    print("- 12 MiB / 120 Dateien / 14 Tage")
    print("- ImageCache-Singleton + _stable_cache_key validiert")
    print("- Preview-/Ambient-Callback-State defensiv initialisiert")
    print("- tatsaechlicher Cache-Pfad wird ins Pluginlog geschrieben")
    print("ImageCache Backup: %s" % cache_backup)
    print("Home Backup:       %s" % home_backup)


if __name__ == "__main__":
    main()
