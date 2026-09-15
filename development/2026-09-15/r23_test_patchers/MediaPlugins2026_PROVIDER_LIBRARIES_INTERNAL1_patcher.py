# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import re
import shutil
import sys

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
HOME_REL = "screens/HomeScreen.py"
FOLDER_REL = "screens/ServerFolderBrowser.py"
LIBRARY_REL = "screens/LibraryBrowser.py"

MARKER = "# MEDIAPLUGINS2026_PROVIDER_LIBRARIES_INTERNAL1"


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


def _replace_server_switch_ok(text):
    # Zustand A: vorheriger Testfix ist bereits installiert.
    disabled = '''        if self.zone == "server_switch":
            # MEDIAPLUGINS2026_SERVER_SWITCH_ACTION_DISABLE1
            # Der Bereich "Zu Server wechseln" bleibt sichtbar und navigierbar,
            # startet aber bewusst kein separates Emby/Jellyfin/Plex-Plugin mehr.
            try:
                log.info(
                    "Home Serverwechsel deaktiviert: provider=%s",
                    self._serverSwitchProvider(),
                )
            except Exception:
                pass
            return
'''

    # Zustand B: normaler r22-/Basisstand.
    original = '''        if self.zone == "server_switch":
            self._openProviderPlugin(self._serverSwitchProvider())
            return
'''

    replacement = '''        if self.zone == "server_switch":
            # MEDIAPLUGINS2026_PROVIDER_LIBRARIES_INTERNAL1
            self._openProviderLibraries(self._serverSwitchProvider())
            return
'''

    if disabled in text:
        return text.replace(disabled, replacement, 1)

    if original in text:
        return text.replace(original, replacement, 1)

    # Toleranter Fallback, falls nur Kommentare rund um den alten Block
    # abweichen, die eigentliche Aktion aber noch identisch ist.
    pattern = re.compile(
        r'(?ms)^        if self\.zone == "server_switch":\n'
        r'(?:            .*\n){0,14}?'
        r'            self\._openProviderPlugin\(self\._serverSwitchProvider\(\)\)\n'
        r'            return\n'
    )
    text2, n = pattern.subn(replacement, text, count=1)
    if n == 1:
        return text2

    raise RuntimeError(
        "Serverwechsel-OK-Block nicht erkannt; nichts wurde geaendert"
    )


def _insert_internal_method(text):
    if "def _openProviderLibraries(self, provider):" in text:
        return text

    anchor = '''    @staticmethod
    def _providerPluginAliases(provider):
'''
    if anchor not in text:
        raise RuntimeError("_providerPluginAliases Anker nicht gefunden")

    method = '''    def _openProviderLibraries(self, provider):
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

'''
    return text.replace(anchor, method + anchor, 1)


def patch_home(text):
    if MARKER in text and "def _openProviderLibraries(self, provider):" in text:
        return text

    text = _replace_server_switch_ok(text)
    text = _insert_internal_method(text)

    class_anchor = "class HomeScreen(Screen):\n"
    if MARKER not in text:
        if class_anchor not in text:
            raise RuntimeError("HomeScreen Klassenanker fehlt")
        text = text.replace(class_anchor, MARKER + "\n" + class_anchor, 1)

    compile(text, "HomeScreen.py", "exec")
    return text


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DEFAULT
    home_path = os.path.join(root, HOME_REL)
    folder_path = os.path.join(root, FOLDER_REL)
    library_path = os.path.join(root, LIBRARY_REL)

    for path in (home_path, folder_path, library_path):
        if not os.path.isfile(path):
            raise SystemExit("Benötigte Plugin-Datei fehlt: %s" % path)

    original = read(home_path)
    patched = patch_home(original)
    compile(patched, home_path, "exec")
    compile(read(folder_path), folder_path, "exec")
    compile(read(library_path), library_path, "exec")

    backup_path = backup(home_path, ".before_provider_libraries_internal1")
    write(home_path, patched)

    verify = read(home_path)
    compile(verify, home_path, "exec")

    required = (
        MARKER,
        "def _openProviderLibraries(self, provider):",
        "self._openProviderLibraries(self._serverSwitchProvider())",
    )
    missing = [item for item in required if item not in verify]
    if missing:
        raise RuntimeError("PROVIDER_LIBRARIES_INTERNAL1 Verifikation fehlgeschlagen: %r" % (missing,))

    if "self._openProviderPlugin(self._serverSwitchProvider())" in verify:
        raise RuntimeError("Alter externer Provider-Plugin-Aufruf ist noch im Serverwechsel-OK-Block vorhanden")

    print("OK MEDIAPLUGINS2026_PROVIDER_LIBRARIES_INTERNAL1")
    print("- Zu Server wechseln -> interne Bibliotheken des Providers")
    print("- kein Start eines separaten Provider-Plugins")
    print("- mehrere Server pro Provider werden gemeinsam uebergeben")
    print("- bestehende player/provider playback bridges bleiben unveraendert")
    print("Backup: %s" % backup_path)


if __name__ == "__main__":
    main()
