# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import re
import shutil
import sys
import time

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
SETTINGS_REL = "screens/Settings.py"
UPDATE_REL = "screens/UpdateScreen.py"
HELPER_REL = "utils/update_channel.py"

MARKER_SETTINGS = "# MEDIAPLUGINS2026_UPDATER_CHANNEL_SWITCH1_SETTINGS"
MARKER_UPDATE = "# MEDIAPLUGINS2026_UPDATER_CHANNEL_SWITCH1_UPDATE"
MARKER_HELPER = "# MEDIAPLUGINS2026_UPDATER_CHANNEL_SWITCH1_HELPER"

HELPER = r'''# -*- coding: utf-8 -*-
# MEDIAPLUGINS2026_UPDATER_CHANNEL_SWITCH1_HELPER

from __future__ import print_function

import os

CHANNEL_DIR = "/etc/enigma2/mediaplugins2026"
CHANNEL_FILE = os.path.join(CHANNEL_DIR, "update_channel")
VALID_CHANNELS = ("stable", "test")
STABLE_MANIFEST_URL = (
    "https://raw.githubusercontent.com/keggy6893/"
    "MediaPlugins2026-Updates/refs/heads/main/update.json"
)
TEST_MANIFEST_URL = (
    "https://raw.githubusercontent.com/keggy6893/"
    "MediaPlugins2026-Updates/refs/heads/main/update-test.json"
)


def _normalize(value, fallback="stable"):
    value = str(value or "").strip().lower()
    if value in VALID_CHANNELS:
        return value
    fallback = str(fallback or "stable").strip().lower()
    return fallback if fallback in VALID_CHANNELS else "stable"


def get_update_channel(default="stable"):
    default = _normalize(default)
    try:
        with open(CHANNEL_FILE, "r") as handle:
            return _normalize(handle.read(), default)
    except Exception:
        return default


def set_update_channel(channel):
    channel = _normalize(channel)
    try:
        if not os.path.isdir(CHANNEL_DIR):
            os.makedirs(CHANNEL_DIR)
        try:
            os.chmod(CHANNEL_DIR, 0o700)
        except Exception:
            pass

        temporary = CHANNEL_FILE + ".tmp"
        with open(temporary, "w") as handle:
            handle.write(channel + "\n")
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except Exception:
                pass
        try:
            os.chmod(temporary, 0o600)
        except Exception:
            pass
        os.replace(temporary, CHANNEL_FILE)
        try:
            os.chmod(CHANNEL_FILE, 0o600)
        except Exception:
            pass
    finally:
        try:
            if os.path.exists(CHANNEL_FILE + ".tmp"):
                os.unlink(CHANNEL_FILE + ".tmp")
        except Exception:
            pass
    return channel


def get_manifest_url(channel=None, default="stable"):
    channel = _normalize(channel, get_update_channel(default)) if channel else get_update_channel(default)
    return TEST_MANIFEST_URL if channel == "test" else STABLE_MANIFEST_URL
'''


def read(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def backup(path, suffix):
    target = path + suffix
    if os.path.isfile(path) and not os.path.exists(target):
        shutil.copy2(path, target)
    return target


def replace_method(text, name, replacement):
    pattern = re.compile(
        r"(?ms)^    def %s\(.*?(?=^    def |^    @staticmethod|^    @classmethod|^class |\Z)"
        % re.escape(name)
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError("%s: erwartete genau 1 Methode, gefunden %d" % (name, len(matches)))
    match = matches[0]
    return text[:match.start()] + replacement.rstrip() + "\n\n" + text[match.end():]


SETTINGS_HELPERS = r'''    def _activeUpdateChannel(self):
        try:
            from ..utils.update_channel import get_update_channel
            return get_update_channel(PLUGIN_UPDATE_CHANNEL)
        except Exception:
            return str(PLUGIN_UPDATE_CHANNEL or "stable").strip().lower()

    def _setUpdateChannel(self, channel):
        if self._focus_zone != "update":
            return
        try:
            from ..utils.update_channel import set_update_channel
            set_update_channel(channel)
        except Exception:
            return
        self._render_all()
'''

KEY_LEFT = r'''    def keyLeft(self):
        if self._focus_zone == "update":
            self._setUpdateChannel("stable")
            return
        return
'''

KEY_RIGHT = r'''    def keyRight(self):
        if self._focus_zone == "update":
            self._setUpdateChannel("test")
            return
        return
'''


def patch_settings(text):
    if MARKER_SETTINGS in text:
        return text

    # Media Plugins 2026 Settings updater row is required.
    for token in ("def _render_update_details(self):", "def keyLeft(self):", "def keyRight(self):", "PLUGIN_UPDATE_CHANNEL"):
        if token not in text:
            raise RuntimeError("Settings-Anker fehlt: %s" % token)

    anchor = "    def _render_update_details(self):\n"
    if anchor not in text:
        raise RuntimeError("_render_update_details Anker nicht gefunden")
    text = text.replace(anchor, SETTINGS_HELPERS.rstrip() + "\n\n" + anchor, 1)

    # Use the effective persisted channel in the detail panel.
    old_channel_expr = 'str(PLUGIN_UPDATE_CHANNEL or "stable").lower(),'
    if old_channel_expr not in text:
        raise RuntimeError("Settings Kanal-Anzeige nicht gefunden")
    text = text.replace(old_channel_expr, 'self._activeUpdateChannel(),', 1)

    # If the user switches channel, an old check from the other channel must not be shown as current.
    state_anchor = '''        except Exception:\n            state = {}\n            last_checked = "Noch nie"\n            checked_build = 0\n\n        if checked_build <= 0:\n'''
    state_new = '''        except Exception:\n            state = {}\n            last_checked = "Noch nie"\n            checked_build = 0\n\n        active_channel = self._activeUpdateChannel()\n        checked_channel = str(state.get("last_checked_channel") or PLUGIN_UPDATE_CHANNEL or "stable").lower()\n        if checked_channel != active_channel:\n            last_checked = "Noch nie"\n            checked_build = 0\n\n        if checked_build <= 0:\n'''
    if state_anchor not in text:
        raise RuntimeError("Settings Update-State-Anker nicht gefunden")
    text = text.replace(state_anchor, state_new, 1)

    # Make the switch discoverable without a native ChoiceBox.
    hint_candidates = (
        'self["detail_hint"].setText("OK   Nach Updates suchen")',
        'self["detail_hint"].setText("OK Nach Updates suchen")',
    )
    replaced = False
    for old in hint_candidates:
        if old in text:
            text = text.replace(
                old,
                'self["detail_hint"].setText("← STABLE    TEST →    ·    OK Updates prüfen")',
                1,
            )
            replaced = True
            break
    if not replaced:
        raise RuntimeError("Settings Update-Hinweis nicht gefunden")

    # Also annotate the left update card/subtitle while it has focus.
    detail_start = text.find("    def _render_update_details(self):")
    detail_end = text.find("\n    def ", detail_start + 10)
    if detail_end < 0:
        detail_end = len(text)
    detail_block = text[detail_start:detail_end]
    provider_anchor = '        self["detail_heading"].setText("SOFTWARE-UPDATE")\n'
    if provider_anchor in detail_block and 'update_subtitle' not in detail_block:
        detail_block = detail_block.replace(
            provider_anchor,
            provider_anchor
            + '        self["update_subtitle"].setText("Kanal: %s   ·   ←/→ wechseln" % active_channel.upper())\n',
            1,
        )
        text = text[:detail_start] + detail_block + text[detail_end:]

    text = replace_method(text, "keyLeft", KEY_LEFT)
    text = replace_method(text, "keyRight", KEY_RIGHT)

    cls = "class Settings(Screen):\n"
    if cls not in text:
        raise RuntimeError("Settings Klasse nicht gefunden")
    text = text.replace(cls, MARKER_SETTINGS + "\n" + cls, 1)
    compile(text, "Settings.py", "exec")
    return text


def patch_update(text):
    if MARKER_UPDATE in text:
        return text

    for token in ("def _mark_checked(manifest):", "def _normalize_manifest(raw):", "def _fetch_manifest():", "PLUGIN_UPDATE_CHANNEL"):
        if token not in text:
            raise RuntimeError("UpdateScreen-Anker fehlt: %s" % token)

    # State records which channel was actually checked.
    mark_anchor = '    state["last_checked_build"] = int((manifest or {}).get("build") or 0)\n'
    if mark_anchor not in text:
        raise RuntimeError("_mark_checked Build-Anker fehlt")
    text = text.replace(
        mark_anchor,
        mark_anchor + '    state["last_checked_channel"] = str((manifest or {}).get("channel") or "").lower()\n',
        1,
    )

    # Validate manifests against the persisted effective channel, not a compile-time constant.
    old_validate = '''    if channel != str(PLUGIN_UPDATE_CHANNEL).lower():\n        raise RuntimeError("Falscher Update-Kanal: %s" % (channel or "unbekannt"))\n'''
    new_validate = '''    try:\n        from ..utils.update_channel import get_update_channel\n        expected_channel = get_update_channel(PLUGIN_UPDATE_CHANNEL)\n    except Exception:\n        expected_channel = str(PLUGIN_UPDATE_CHANNEL or "stable").lower()\n    if channel != expected_channel:\n        raise RuntimeError("Falscher Update-Kanal: %s" % (channel or "unbekannt"))\n'''
    if old_validate not in text:
        raise RuntimeError("UpdateScreen Kanal-Pruefung nicht gefunden")
    text = text.replace(old_validate, new_validate, 1)

    old_fetch = '''def _fetch_manifest():\n    separator = "&" if "?" in PLUGIN_UPDATE_MANIFEST_URL else "?"\n    url = PLUGIN_UPDATE_MANIFEST_URL + separator + "_mediaplugins_ts=%d" % int(time.time())\n'''
    new_fetch = '''def _fetch_manifest():\n    try:\n        from ..utils.update_channel import get_manifest_url\n        manifest_url = get_manifest_url(default=PLUGIN_UPDATE_CHANNEL)\n    except Exception:\n        manifest_url = PLUGIN_UPDATE_MANIFEST_URL\n    separator = "&" if "?" in manifest_url else "?"\n    url = manifest_url + separator + "_mediaplugins_ts=%d" % int(time.time())\n'''
    if old_fetch not in text:
        raise RuntimeError("_fetch_manifest Block nicht gefunden")
    text = text.replace(old_fetch, new_fetch, 1)

    # Initial label on the updater screen.
    old_label = 'self["update_channel"] = Label(str(PLUGIN_UPDATE_CHANNEL).lower())'
    new_label = '''try:\n            from ..utils.update_channel import get_update_channel\n            active_update_channel = get_update_channel(PLUGIN_UPDATE_CHANNEL)\n        except Exception:\n            active_update_channel = str(PLUGIN_UPDATE_CHANNEL or "stable").lower()\n        self["update_channel"] = Label(active_update_channel)'''
    if old_label not in text:
        raise RuntimeError("UpdateScreen initiale Kanal-Anzeige nicht gefunden")
    text = text.replace(old_label, new_label, 1)

    # Fallback display after a manifest is loaded.
    old_fallback = 'str(self._manifest.get("channel") or PLUGIN_UPDATE_CHANNEL).lower()'
    if old_fallback not in text:
        raise RuntimeError("UpdateScreen Manifest-Kanal-Anzeige nicht gefunden")
    text = text.replace(old_fallback, 'str(self._manifest.get("channel") or self["update_channel"].getText()).lower()', 1)

    marker_anchor = "# MEDIAPLUGINS2026_GITHUB_UPDATER_V1\n"
    if marker_anchor not in text:
        raise RuntimeError("Updater Marker-Anker fehlt")
    text = text.replace(marker_anchor, marker_anchor + MARKER_UPDATE + "\n", 1)
    compile(text, "UpdateScreen.py", "exec")
    return text


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DEFAULT
    settings_path = os.path.join(root, SETTINGS_REL)
    update_path = os.path.join(root, UPDATE_REL)
    helper_path = os.path.join(root, HELPER_REL)

    for path in (settings_path, update_path):
        if not os.path.isfile(path):
            raise SystemExit("Datei nicht gefunden: %s" % path)

    settings = patch_settings(read(settings_path))
    update = patch_update(read(update_path))

    compile(HELPER, helper_path, "exec")
    compile(settings, settings_path, "exec")
    compile(update, update_path, "exec")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup(settings_path, ".before_update_channel_switch1_" + stamp)
    backup(update_path, ".before_update_channel_switch1_" + stamp)
    backup(helper_path, ".before_update_channel_switch1_" + stamp)

    write(helper_path, HELPER)
    write(settings_path, settings)
    write(update_path, update)

    for path in (helper_path, settings_path, update_path):
        compile(read(path), path, "exec")

    checks = {
        "Settings Marker": MARKER_SETTINGS in read(settings_path),
        "Updater Marker": MARKER_UPDATE in read(update_path),
        "Helper Marker": MARKER_HELPER in read(helper_path),
        "Stable URL": "update.json" in read(helper_path),
        "Test URL": "update-test.json" in read(helper_path),
        "Persistenz": 'CHANNEL_FILE = os.path.join(CHANNEL_DIR, "update_channel")' in read(helper_path),
        "LEFT Stable": 'self._setUpdateChannel("stable")' in read(settings_path),
        "RIGHT Test": 'self._setUpdateChannel("test")' in read(settings_path),
        "Dynamischer Fetch": 'manifest_url = get_manifest_url(default=PLUGIN_UPDATE_CHANNEL)' in read(update_path),
        "State pro Kanal": 'last_checked_channel' in read(update_path),
    }
    missing = [name for name, ok in checks.items() if not ok]
    if missing:
        raise RuntimeError("CHANNEL_SWITCH1 Verifikation fehlgeschlagen: %r" % missing)

    print("OK MEDIAPLUGINS2026_UPDATER_CHANNEL_SWITCH1")
    print("- Update-Fokus: LINKS = STABLE, RECHTS = TEST")
    print("- Auswahl persistent unter /etc/enigma2/mediaplugins2026/update_channel")
    print("- Stable nutzt update.json, Test nutzt update-test.json")
    print("- Updater validiert das Manifest gegen den aktiv gewaehlten Kanal")
    print("- alter Pruefstatus eines anderen Kanals wird nicht als aktuell angezeigt")
    print("- keine Server-/Login-Daten werden veraendert")


if __name__ == "__main__":
    main()
