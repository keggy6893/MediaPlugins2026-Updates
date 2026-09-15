# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
TARGET_REL = "screens/HomeScreen.py"
MARKER = "# MEDIAPLUGINS2026_HOME_PROVIDER_COLORKEYS1"


def read(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def backup(path):
    target = path + ".before_home_provider_colorkeys1"
    if os.path.isfile(path) and not os.path.exists(target):
        shutil.copy2(path, target)
    return target


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError("%s: erwarteter Block nicht gefunden" % label)
    return text.replace(old, new, 1)


def patch(text):
    if MARKER in text:
        return text

    if "def _openProviderLibraries(self, provider):" not in text:
        raise RuntimeError(
            "Interne Provider-Bibliotheken fehlen. "
            "PROVIDER_LIBRARIES_INTERNAL1 muss vorher vorhanden sein."
        )

    text = replace_once(
        text,
        '''        self["key_green"] = Label("■ Suche")
        self["key_yellow"] = Label("■ Filter")
        self["key_blue"] = Label("■ Details")
''',
        '''        self["key_green"] = Label("■ Emby")
        self["key_yellow"] = Label("■ Plex")
        self["key_blue"] = Label("■ Jellyfin")
''',
        "Footer-Farbtasten",
    )

    text = replace_once(
        text,
        '''                "green": self.keyOpenSearch,
                "yellow": self.keyFilter,
                "blue": self.keyDetailsCurrent,
''',
        '''                "green": self.keyOpenEmbyLibraries,
                "yellow": self.keyOpenPlexLibraries,
                "blue": self.keyOpenJellyfinLibraries,
''',
        "ColorActions",
    )

    anchor = '''    def keyFilter(self):
'''
    methods = '''    %s
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

''' % MARKER

    if anchor not in text:
        raise RuntimeError("keyFilter-Anker fehlt")
    text = text.replace(anchor, methods + anchor, 1)

    compile(text, "HomeScreen.py", "exec")
    return text


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DEFAULT
    target = os.path.join(root, TARGET_REL)

    if not os.path.isfile(target):
        raise SystemExit("HomeScreen.py fehlt: %s" % target)

    original = read(target)
    patched = patch(original)
    compile(patched, target, "exec")

    backup_path = backup(target)
    write(target, patched)

    verify = read(target)
    compile(verify, target, "exec")

    required = (
        MARKER,
        'self["key_green"] = Label("■ Emby")',
        'self["key_yellow"] = Label("■ Plex")',
        'self["key_blue"] = Label("■ Jellyfin")',
        '"green": self.keyOpenEmbyLibraries',
        '"yellow": self.keyOpenPlexLibraries',
        '"blue": self.keyOpenJellyfinLibraries',
        'self._openProviderByColorKey("emby")',
        'self._openProviderByColorKey("plex")',
        'self._openProviderByColorKey("jellyfin")',
        "def _openProviderLibraries(self, provider):",
    )
    missing = [x for x in required if x not in verify]
    if missing:
        raise RuntimeError("PROVIDER_COLORKEYS1 Verifikation fehlgeschlagen: %r" % missing)

    print("OK MEDIAPLUGINS2026_HOME_PROVIDER_COLORKEYS1")
    print("- GRUEN  -> Emby-Bibliotheken")
    print("- GELB   -> Plex-Bibliotheken")
    print("- BLAU   -> Jellyfin-Bibliotheken")
    print("- direkter Sprung; kein Fokus auf 'Zu Server wechseln' noetig")
    print("- nicht eingerichtet/offline -> vorhandener Provider-Hinweis")
    print("- OK auf Home-Postern oeffnet weiterhin Details")
    print("- Serverwechsel-Bereich und interne Bibliothekslogik bleiben erhalten")
    print("Backup: %s" % backup_path)


if __name__ == "__main__":
    main()
