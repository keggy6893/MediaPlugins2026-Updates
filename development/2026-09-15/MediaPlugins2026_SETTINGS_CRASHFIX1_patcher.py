# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import re
import shutil
import sys

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
SETTINGS_REL = "screens/Settings.py"
SERVER_TYPE_REL = "screens/ServerTypeSelect.py"

MARKER_SETTINGS = "# MEDIAPLUGINS2026_SETTINGS_CRASHFIX1"
MARKER_SERVER = "# MEDIAPLUGINS2026_SERVERTYPE_CRASHFIX1"


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


def patch_settings(text):
    if MARKER_SETTINGS in text:
        return text

    # 1) Hauptcrash:
    # Enigma2 kann openWithCallback beim Schliessen eines Screens ohne
    # Rueckgabewert mit NULL Argumenten aufrufen. result muss deshalb
    # optional sein.
    text, n = re.subn(
        r'(?m)^    def _onProtocolChosen\(self, result\):$',
        '    def _onProtocolChosen(self, result=None):',
        text,
        count=1,
    )
    if n != 1:
        # Bereits anderweitig optional? Akzeptieren, aber nur wenn Methode existiert.
        if not re.search(
            r'(?m)^    def _onProtocolChosen\(self,\s*result\s*=\s*None\):$',
            text,
        ):
            raise RuntimeError("_onProtocolChosen Signatur nicht gefunden")

    # 2) Auch der nachfolgende ServerConfig-Callback darf bei close() ohne
    # Rueckgabewert nicht crashen.
    text = text.replace(
        "lambda ok: self.refreshList(),",
        "lambda *args: self.refreshList(),",
    )

    # 3) Settings nutzt VISIBLE_CARDS=4, im alten eingebetteten Skin stehen
    # aber noch card4_*-Widgets. Enigma2 protokolliert dafuer SkinErrors.
    # Diese ungenutzten XML-Widgets werden entfernt.
    card4_names = (
        "card4_bg",
        "card4_focus",
        "card4_provider",
        "card4_title",
        "card4_url",
        "card4_state",
    )
    removed = 0
    for name in card4_names:
        pattern = re.compile(
            r'(?ms)\n\s*<widget\b(?=[^>]*\bname="%s")[^>]*?/>'
            % re.escape(name)
        )
        text, count = pattern.subn("", text, count=1)
        removed += count

    # Wenn der Skin diese alten Widgets bereits nicht mehr enthaelt, ist das
    # ebenfalls okay. Bei einem Altstand erwarten wir aber alle sechs.
    leftovers = [name for name in card4_names if 'name="%s"' % name in text]
    if leftovers:
        raise RuntimeError("card4 Skinreste nicht entfernt: %r" % leftovers)

    # Marker direkt vor der Settings-Klasse.
    class_anchor = None
    for candidate in (
        "class Settings(Screen):\n",
        "class MediaPluginsSettings(Screen):\n",
    ):
        if candidate in text:
            class_anchor = candidate
            break
    if class_anchor is None:
        raise RuntimeError("Settings Klassenanker fehlt")

    text = text.replace(
        class_anchor,
        MARKER_SETTINGS + "\n" + class_anchor,
        1,
    )

    compile(text, "Settings.py", "exec")
    return text


def patch_server_type(text):
    if MARKER_SERVER in text:
        return text

    # Eigener Media-Plugins-Servertyp-Screen:
    # cancel/red muessen explizit None zurueckgeben, damit der Callback
    # unabhaengig von Enigma2-Version/Screen.close-Verhalten stabil ist.
    replacements = (
        ('"cancel": self.close,', '"cancel": lambda: self.close(None),'),
        ('"red": self.close,', '"red": lambda: self.close(None),'),
    )
    for old, new in replacements:
        if old in text:
            text = text.replace(old, new, 1)

    # Marker an sicherer Modulstelle.
    class_anchor = "class MediaPluginsServerTypeScreen(Screen):\n"
    if class_anchor not in text:
        raise RuntimeError("MediaPluginsServerTypeScreen Klassenanker fehlt")
    text = text.replace(
        class_anchor,
        MARKER_SERVER + "\n" + class_anchor,
        1,
    )

    compile(text, "ServerTypeSelect.py", "exec")
    return text


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DEFAULT
    settings_path = os.path.join(root, SETTINGS_REL)
    server_type_path = os.path.join(root, SERVER_TYPE_REL)

    if not os.path.isfile(settings_path):
        raise SystemExit("Settings.py nicht gefunden: %s" % settings_path)

    settings_original = read(settings_path)
    settings_new = patch_settings(settings_original)
    compile(settings_new, settings_path, "exec")

    server_original = None
    server_new = None
    if os.path.isfile(server_type_path):
        server_original = read(server_type_path)
        server_new = patch_server_type(server_original)
        compile(server_new, server_type_path, "exec")

    settings_backup = backup(
        settings_path,
        ".before_settings_crashfix1",
    )
    server_backup = None
    if server_original is not None:
        server_backup = backup(
            server_type_path,
            ".before_settings_crashfix1",
        )

    write(settings_path, settings_new)
    if server_new is not None:
        write(server_type_path, server_new)

    # Live-Verifikation.
    verify_settings = read(settings_path)
    compile(verify_settings, settings_path, "exec")

    required_settings = [
        MARKER_SETTINGS,
        "def _onProtocolChosen(self, result=None):",
        "lambda *args: self.refreshList(),",
    ]
    missing = [x for x in required_settings if x not in verify_settings]
    if missing:
        raise RuntimeError(
            "SETTINGS_CRASHFIX1 Verifikation fehlgeschlagen: %r" % missing
        )

    for name in (
        "card4_bg",
        "card4_focus",
        "card4_provider",
        "card4_title",
        "card4_url",
        "card4_state",
    ):
        if 'name="%s"' % name in verify_settings:
            raise RuntimeError("Ungenutztes Skin-Widget noch vorhanden: %s" % name)

    if server_new is not None:
        verify_server = read(server_type_path)
        compile(verify_server, server_type_path, "exec")
        for required in (
            MARKER_SERVER,
            '"cancel": lambda: self.close(None),',
            '"red": lambda: self.close(None),',
        ):
            if required not in verify_server:
                raise RuntimeError(
                    "ServerTypeSelect Verifikation fehlt: %s" % required
                )

    print("OK MEDIAPLUGINS2026_SETTINGS_CRASHFIX1")
    print("- _onProtocolChosen akzeptiert Abbruch ohne Rueckgabewert")
    print("- ServerConfig Callback akzeptiert 0..n Rueckgabewerte")
    print("- ungenutzte card4_* Skin-Widgets entfernt")
    if server_new is not None:
        print("- ServerTypeSelect ROT/EXIT gibt explizit None zurueck")
    else:
        print("- kein eigener ServerTypeSelect.py vorhanden; native Auswahl bleibt kompatibel")
    print("Settings Backup: %s" % settings_backup)
    if server_backup:
        print("ServerType Backup: %s" % server_backup)


if __name__ == "__main__":
    main()
