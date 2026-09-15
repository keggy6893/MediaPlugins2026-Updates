# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import re
import shutil
import sys

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
SETTINGS_REL = "screens/Settings.py"
PLUGIN_REL = "plugin.py"
BACKUP_SCREEN_REL = "screens/BackupScreen.py"
AUTO_BACKUP_REL = "utils/config_backup.py"

MARKER_SETTINGS = "# MEDIAPLUGINS2026_AUTOBACKUP1_SETTINGS"
MARKER_PLUGIN = "# MEDIAPLUGINS2026_AUTOBACKUP1_PLUGIN"
MARKER_SCREEN = "# MEDIAPLUGINS2026_AUTOBACKUP1_SCREEN"
MARKER_HELPER = "# MEDIAPLUGINS2026_AUTOBACKUP1_HELPER"

AUTO_BACKUP_CODE = r'''# -*- coding: utf-8 -*-
# MEDIAPLUGINS2026_AUTOBACKUP1_HELPER

import glob
import os
import time

from ..config import config_store
from . import log

AUTO_BACKUP_DIR = "/etc/enigma2/mediaplugins2026/backups"
AUTO_BACKUP_KEEP = 7
AUTO_BACKUP_PREFIX = "config-"
AUTO_BACKUP_SUFFIX = ".json"


def _ensure_private_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)
    try:
        os.chmod(path, 0o700)
    except Exception:
        pass


def _private_file(path):
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def _backup_files():
    pattern = os.path.join(
        AUTO_BACKUP_DIR,
        AUTO_BACKUP_PREFIX + "????-??-??" + AUTO_BACKUP_SUFFIX,
    )
    return sorted(glob.glob(pattern))


def _prune():
    files = _backup_files()
    while len(files) > AUTO_BACKUP_KEEP:
        victim = files.pop(0)
        try:
            os.unlink(victim)
            log.info("AutoBackup: alte Sicherung entfernt: %s", victim)
        except Exception as exc:
            log.warning("AutoBackup: alte Sicherung konnte nicht entfernt werden: %s", exc)


def today_backup_path():
    date_text = time.strftime("%Y-%m-%d")
    return os.path.join(
        AUTO_BACKUP_DIR,
        AUTO_BACKUP_PREFIX + date_text + AUTO_BACKUP_SUFFIX,
    )


def ensure_daily_backup():
    """Erstellt pro Kalendertag genau eine persistente Konfigurationssicherung.

    Die Sicherung enthält dieselben Daten wie der bestehende Export, inklusive
    gespeicherter Zugangsdaten. Verzeichnis und Datei werden daher möglichst
    restriktiv (0700/0600) angelegt. Fehler dürfen den Pluginstart nie blockieren.
    """
    try:
        _ensure_private_dir(AUTO_BACKUP_DIR)
        target = today_backup_path()

        if os.path.isfile(target) and os.path.getsize(target) > 0:
            _private_file(target)
            _prune()
            return target, False

        tmp_target = target + ".tmp"
        try:
            if os.path.exists(tmp_target):
                os.unlink(tmp_target)
        except Exception:
            pass

        exported = config_store.export_backup(tmp_target)
        exported = exported or tmp_target

        if os.path.abspath(exported) != os.path.abspath(tmp_target):
            shutil_source = exported
            try:
                import shutil
                shutil.copy2(shutil_source, tmp_target)
            except Exception:
                raise RuntimeError("Exportpfad konnte nicht in die Tagesdatei übernommen werden")

        _private_file(tmp_target)
        os.rename(tmp_target, target)
        _private_file(target)
        _prune()
        log.info("AutoBackup: Tages-Sicherung erstellt: %s", target)
        return target, True
    except Exception as exc:
        log.warning("AutoBackup fehlgeschlagen (Pluginstart läuft weiter): %s", exc)
        return "", False


def list_daily_backups():
    try:
        return list(reversed(_backup_files()))
    except Exception:
        return []
'''

BACKUP_SCREEN_CODE = r'''# -*- coding: utf-8 -*-
# MEDIAPLUGINS2026_AUTOBACKUP1_SCREEN

import os

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label

try:
    from skin import parseColor
except Exception:
    parseColor = None

from ..config import config_store, BACKUP_PATH
from ..utils.config_backup import AUTO_BACKUP_DIR, AUTO_BACKUP_KEEP, list_daily_backups


class MediaPluginsBackupScreen(Screen):
    """Eigener Media-Plugins-2026-Dialog für manuellen Konfigurationsexport."""

    skinName = "MediaPlugins2026BackupScreen"
    skin = r"""
    <screen name="MediaPlugins2026BackupScreen" position="center,center" size="1240,500"
            backgroundColor="#06121D" flags="wfNoBorder" title="Media Plugins 2026 Sicherung">

        <eLabel position="0,0" size="1240,500" backgroundColor="#06121D"
                borderWidth="2" borderColor="#1B4C6B" />
        <eLabel position="0,0" size="1240,4" backgroundColor="#23D7F2" />

        <widget name="brand" position="42,28" size="310,44" font="Bold;30"
                foregroundColor="#F4F7FB" backgroundColor="#06121D" transparent="1" />
        <widget name="year" position="350,28" size="130,44" font="Bold;30"
                foregroundColor="#23D7F2" backgroundColor="#06121D" transparent="1" />
        <widget name="kicker" position="42,89" size="1110,28" font="Bold;18"
                foregroundColor="#8CCEF6" backgroundColor="#06121D" transparent="1" />

        <eLabel position="42,130" size="1156,1" backgroundColor="#244863" />

        <widget name="title" position="55,154" size="1100,45" font="Bold;29"
                foregroundColor="#F4F7FB" backgroundColor="#06121D" transparent="1" />
        <widget name="body" position="55,214" size="1100,145" font="Regular;21"
                foregroundColor="#C8D7E6" backgroundColor="#06121D" transparent="1" />

        <widget name="status" position="55,366" size="1100,34" font="Regular;18"
                foregroundColor="#7893A9" backgroundColor="#06121D" transparent="1" />

        <widget name="key_yellow" position="55,422" size="455,52" font="Bold;20"
                foregroundColor="#FFFFFF" backgroundColor="#B58B00" transparent="0"
                halign="center" valign="center" />
        <widget name="key_red" position="530,422" size="330,52" font="Bold;20"
                foregroundColor="#FFFFFF" backgroundColor="#9E2428" transparent="0"
                halign="center" valign="center" />
        <widget name="key_ok" position="880,422" size="305,52" font="Bold;20"
                foregroundColor="#D6E1EB" backgroundColor="#263442" transparent="0"
                halign="center" valign="center" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self._done = False

        self["brand"] = Label("Media Plugins")
        self["year"] = Label("2026")
        self["kicker"] = Label("KONFIGURATION · SICHERUNG & EXPORT")
        self["title"] = Label("Manuellen Export erstellen?")
        self["body"] = Label(
            "Der Export enthält Server-URLs und gespeicherte Anmeldedaten.\n"
            "Er wird nur auf ausdrücklichen Tastendruck nach /tmp geschrieben.\n\n"
            "Automatische Sicherung: täglich · %d Tage Verlauf" % AUTO_BACKUP_KEEP
        )
        self["status"] = Label(self._backup_status())
        self["key_yellow"] = Label("GELB   Exportieren")
        self["key_red"] = Label("ROT   Abbrechen")
        self["key_ok"] = Label("OK   Exportieren")

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok": self.keyOk,
                "cancel": self.close,
                "yellow": self.doExport,
                "red": self.close,
            },
            -1,
        )

    def _set_status_color(self, color):
        if parseColor is None:
            return
        try:
            self["status"].instance.setForegroundColor(parseColor(color))
        except Exception:
            pass

    def _backup_status(self):
        backups = list_daily_backups()
        if backups:
            return "Letzte automatische Sicherung: %s   ·   Speicherort: %s" % (
                os.path.basename(backups[0]).replace("config-", "").replace(".json", ""),
                AUTO_BACKUP_DIR,
            )
        return "Automatische Sicherung wird beim nächsten Pluginstart angelegt."

    def keyOk(self):
        if self._done:
            self.close()
        else:
            self.doExport()

    def doExport(self):
        if self._done:
            self.close()
            return
        try:
            path = config_store.export_backup(BACKUP_PATH)
            try:
                os.chmod(path, 0o600)
            except Exception:
                pass

            self._done = True
            self["title"].setText("Export abgeschlossen")
            self["body"].setText(
                "Konfiguration gespeichert unter:\n%s\n\n"
                "Die Datei enthält Anmeldedaten und sollte vertraulich behandelt werden."
                % path
            )
            self["status"].setText(
                "Automatische Sicherungen bleiben separat im 7-Tage-Verlauf erhalten."
            )
            self._set_status_color("#37D67A")
            self["key_yellow"].setText("")
            self["key_red"].setText("")
            self["key_ok"].setText("OK   Schließen")
        except Exception as exc:
            self["title"].setText("Export fehlgeschlagen")
            self["body"].setText(
                "Die Konfiguration konnte nicht exportiert werden.\n\n%s" % exc
            )
            self["status"].setText("Es wurden keine automatischen Sicherungen gelöscht.")
            self._set_status_color("#FF6B6B")
            self["key_ok"].setText("OK   Erneut versuchen")
'''

SETTINGS_METHOD = r'''    def keyExport(self):
        # MEDIAPLUGINS2026_AUTOBACKUP1_SETTINGS
        from .BackupScreen import MediaPluginsBackupScreen
        self.session.open(MediaPluginsBackupScreen)
'''

PLUGIN_INJECT = r'''    # MEDIAPLUGINS2026_AUTOBACKUP1_PLUGIN
    # Einmal pro Kalendertag eine persistente 7-Tage-Konfigurationssicherung.
    # Fehler blockieren den Home-Screen niemals.
    try:
        from .utils.config_backup import ensure_daily_backup
        ensure_daily_backup()
    except Exception as backup_error:
        log.warning("AutoBackup Start-Hook fehlgeschlagen: %s", backup_error)
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
        r"(?ms)^    def %s\(.*?(?=^    def |\Z)" % re.escape(name)
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(
            "%s: erwartete genau 1 Methode, gefunden %d" % (name, len(matches))
        )
    match = matches[0]
    return text[:match.start()] + replacement.rstrip() + "\n\n" + text[match.end():]


def patch_settings(text):
    if MARKER_SETTINGS in text:
        return text
    return replace_method(text, "keyExport", SETTINGS_METHOD)


def patch_plugin(text):
    if MARKER_PLUGIN in text:
        return text

    anchor = '    log.info("Plugin-Start (Media Plugins 2026)")\n'
    if anchor not in text:
        raise RuntimeError("plugin.py Start-Anker nicht gefunden")
    return text.replace(anchor, anchor + PLUGIN_INJECT + "\n", 1)


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DEFAULT
    settings_path = os.path.join(root, SETTINGS_REL)
    plugin_path = os.path.join(root, PLUGIN_REL)
    backup_screen_path = os.path.join(root, BACKUP_SCREEN_REL)
    auto_backup_path = os.path.join(root, AUTO_BACKUP_REL)

    for path in (settings_path, plugin_path):
        if not os.path.isfile(path):
            raise SystemExit("Datei nicht gefunden: %s" % path)

    settings_original = read(settings_path)
    plugin_original = read(plugin_path)
    settings_new = patch_settings(settings_original)
    plugin_new = patch_plugin(plugin_original)

    # Vor Live-Aenderungen alles syntaktisch prüfen.
    compile(AUTO_BACKUP_CODE, auto_backup_path, "exec")
    compile(BACKUP_SCREEN_CODE, backup_screen_path, "exec")
    compile(settings_new, settings_path, "exec")
    compile(plugin_new, plugin_path, "exec")

    settings_backup = backup(settings_path, ".before_autobackup1")
    plugin_backup = backup(plugin_path, ".before_autobackup1")
    backup(backup_screen_path, ".before_autobackup1")
    backup(auto_backup_path, ".before_autobackup1")

    write(auto_backup_path, AUTO_BACKUP_CODE)
    write(backup_screen_path, BACKUP_SCREEN_CODE)
    write(settings_path, settings_new)
    write(plugin_path, plugin_new)

    # Readback / Syntax.
    for path in (auto_backup_path, backup_screen_path, settings_path, plugin_path):
        compile(read(path), path, "exec")

    checks = [
        (MARKER_HELPER in read(auto_backup_path), "AutoBackup helper"),
        (MARKER_SCREEN in read(backup_screen_path), "Backup dialog"),
        (MARKER_SETTINGS in read(settings_path), "Settings keyExport"),
        (MARKER_PLUGIN in read(plugin_path), "Plugin start hook"),
        ("AUTO_BACKUP_KEEP = 7" in read(auto_backup_path), "7-Tage-Rotation"),
        ('AUTO_BACKUP_DIR = "/etc/enigma2/mediaplugins2026/backups"' in read(auto_backup_path), "persistenter Pfad"),
        ("os.chmod(path, 0o600)" in read(backup_screen_path), "manueller Export 0600"),
    ]
    missing = [name for ok, name in checks if not ok]
    if missing:
        raise RuntimeError("AUTOBACKUP1 Verifikation fehlgeschlagen: %r" % missing)

    print("OK MEDIAPLUGINS2026_AUTOBACKUP1")
    print("- automatische Sicherung beim ersten Pluginstart pro Kalendertag")
    print("- 7 taegliche Sicherungen, danach wird die aelteste geloescht")
    print("- persistent: /etc/enigma2/mediaplugins2026/backups")
    print("- Verzeichnis 0700 / Sicherungsdateien 0600")
    print("- GELB Exportieren oeffnet eigenen Media-Plugins-2026-Dialog")
    print("- Warnung erfolgt VOR dem manuellen Export")
    print("- bestehender BLAU-Import bleibt unveraendert")
    print("Settings Backup: %s" % settings_backup)
    print("Plugin Backup:   %s" % plugin_backup)


if __name__ == "__main__":
    main()
