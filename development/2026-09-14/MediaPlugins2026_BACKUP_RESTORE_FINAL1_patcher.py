# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import re
import shutil
import sys

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
SETTINGS_REL = "screens/Settings.py"
SCREEN_REL = "screens/BackupScreen.py"
HELPER_REL = "utils/config_backup.py"

MARKER_SETTINGS = "# MEDIAPLUGINS2026_BACKUP_RESTORE_FINAL1_SETTINGS"
BACKUP_SCREEN_CODE = '# -*- coding: utf-8 -*-\n# MEDIAPLUGINS2026_AUTOBACKUP1_SCREEN\n# MEDIAPLUGINS2026_BACKUP_RESTORE_FINAL1_SCREEN\n\nimport os\n\nfrom Screens.Screen import Screen\nfrom Components.ActionMap import ActionMap\nfrom Components.Label import Label\n\ntry:\n    from skin import parseColor\nexcept Exception:\n    parseColor = None\n\nfrom ..config import config_store, BACKUP_PATH\nfrom ..utils.config_backup import (\n    AUTO_BACKUP_DIR,\n    AUTO_BACKUP_KEEP,\n    list_daily_backups,\n    force_backup_now,\n)\n\n\nclass MediaPluginsBackupScreen(Screen):\n    skinName = "MediaPlugins2026BackupScreen"\n    skin = r"""\n    <screen name="MediaPlugins2026BackupScreen" position="center,center" size="1240,520"\n            backgroundColor="#06121D" flags="wfNoBorder" title="Media Plugins 2026 Sicherung">\n        <eLabel zPosition="5" position="0,0" size="1240,4" backgroundColor="#23D7F2" />\n        <eLabel zPosition="5" position="0,0" size="2,520" backgroundColor="#1B4C6B" />\n        <eLabel zPosition="5" position="1238,0" size="2,520" backgroundColor="#1B4C6B" />\n        <eLabel zPosition="5" position="0,518" size="1240,2" backgroundColor="#1B4C6B" />\n\n        <widget zPosition="50" name="brand" position="42,28" size="310,44" font="Bold;30"\n                foregroundColor="#F4F7FB" backgroundColor="#06121D" transparent="1" />\n        <widget zPosition="50" name="year" position="350,28" size="130,44" font="Bold;30"\n                foregroundColor="#23D7F2" backgroundColor="#06121D" transparent="1" />\n        <widget zPosition="50" name="kicker" position="42,89" size="1110,28" font="Bold;18"\n                foregroundColor="#8CCEF6" backgroundColor="#06121D" transparent="1" />\n        <eLabel zPosition="5" position="42,130" size="1156,1" backgroundColor="#244863" />\n\n        <widget zPosition="50" name="title" position="55,154" size="1100,45" font="Bold;29"\n                foregroundColor="#F4F7FB" backgroundColor="#06121D" transparent="1" />\n        <widget zPosition="50" name="body" position="55,214" size="1100,150" font="Regular;21"\n                foregroundColor="#C8D7E6" backgroundColor="#06121D" transparent="1" />\n        <widget zPosition="50" name="status" position="55,374" size="1100,34" font="Regular;18"\n                foregroundColor="#7893A9" backgroundColor="#06121D" transparent="1" />\n\n        <widget zPosition="50" name="key_green" position="55,442" size="270,52" font="Bold;19"\n                foregroundColor="#FFFFFF" backgroundColor="#087A37" transparent="0"\n                halign="center" valign="center" />\n        <widget zPosition="50" name="key_yellow" position="341,442" size="270,52" font="Bold;19"\n                foregroundColor="#FFFFFF" backgroundColor="#B58B00" transparent="0"\n                halign="center" valign="center" />\n        <widget zPosition="50" name="key_blue" position="627,442" size="270,52" font="Bold;19"\n                foregroundColor="#FFFFFF" backgroundColor="#1762A7" transparent="0"\n                halign="center" valign="center" />\n        <widget zPosition="50" name="key_red" position="913,442" size="270,52" font="Bold;19"\n                foregroundColor="#FFFFFF" backgroundColor="#9E2428" transparent="0"\n                halign="center" valign="center" />\n        <widget zPosition="50" name="key_ok" position="392,442" size="455,52" font="Bold;20"\n                foregroundColor="#D6E1EB" backgroundColor="#263442" transparent="0"\n                halign="center" valign="center" />\n    </screen>\n    """\n\n    def __init__(self, session):\n        Screen.__init__(self, session)\n        self.session = session\n        self._done = False\n        self._import_confirm = False\n\n        self["brand"] = Label("Media Plugins")\n        self["year"] = Label("2026")\n        self["kicker"] = Label("KONFIGURATION · SICHERUNG · EXPORT · RESTORE")\n        self["title"] = Label("Sicherung & Wiederherstellung")\n        self["body"] = Label(\n            "GRÜN aktualisiert die heutige interne Sicherung sofort.\\n"\n            "GELB erstellt eine manuelle Exportdatei unter /tmp.\\n"\n            "BLAU stellt diese Exportdatei wieder her.\\n\\n"\n            "Automatische Sicherung: täglich · %d Tage Verlauf" % AUTO_BACKUP_KEEP\n        )\n        self["status"] = Label(self._backup_status())\n\n        self["key_green"] = Label("GRÜN   Jetzt sichern")\n        self["key_yellow"] = Label("GELB   Exportieren")\n        self["key_blue"] = Label("BLAU   Importieren")\n        self["key_red"] = Label("ROT   Abbrechen")\n        self["key_ok"] = Label("OK   Schließen")\n\n        self["actions"] = ActionMap(\n            ["OkCancelActions", "ColorActions"],\n            {\n                "ok": self.keyOk,\n                "cancel": self.close,\n                "green": self.doBackupNow,\n                "yellow": self.doExport,\n                "blue": self.doImport,\n                "red": self.close,\n            },\n            -1,\n        )\n        self.onLayoutFinish.append(self._showInitialButtons)\n\n    def _set_status_color(self, color):\n        if parseColor is None:\n            return\n        try:\n            self["status"].instance.setForegroundColor(parseColor(color))\n        except Exception:\n            pass\n\n    def _backup_status(self):\n        backups = list_daily_backups()\n        if backups:\n            return "Letzte automatische Sicherung: %s   ·   Speicherort: %s" % (\n                os.path.basename(backups[0]).replace("config-", "").replace(".json", ""),\n                AUTO_BACKUP_DIR,\n            )\n        return "Automatische Sicherung wird beim nächsten Pluginstart angelegt."\n\n    def _showInitialButtons(self):\n        self._done = False\n        self._import_confirm = False\n        self["key_green"].setText("GRÜN   Jetzt sichern")\n        self["key_yellow"].setText("GELB   Exportieren")\n        self["key_blue"].setText("BLAU   Importieren")\n        self["key_red"].setText("ROT   Abbrechen")\n        self["key_green"].show()\n        self["key_yellow"].show()\n        self["key_blue"].show()\n        self["key_red"].show()\n        self["key_ok"].hide()\n\n    def _showDone(self, title, body, status):\n        self._done = True\n        self._import_confirm = False\n        self["title"].setText(title)\n        self["body"].setText(body)\n        self["status"].setText(status)\n        self._set_status_color("#37D67A")\n        self["key_green"].hide()\n        self["key_yellow"].hide()\n        self["key_blue"].hide()\n        self["key_red"].hide()\n        self["key_ok"].setText("OK   Schließen")\n        self["key_ok"].show()\n\n    def _showFailure(self, title, body):\n        self["title"].setText(title)\n        self["body"].setText(body)\n        self["status"].setText(\n            "Es wurden keine bestehenden automatischen Sicherungen gelöscht."\n        )\n        self._set_status_color("#FF6B6B")\n\n    def keyOk(self):\n        if self._done:\n            self.close()\n\n    def doBackupNow(self):\n        if self._done:\n            self.close()\n            return\n        try:\n            path = force_backup_now()\n            count = len(list_daily_backups())\n            self._showDone(\n                "Sicherung aktualisiert",\n                "Die heutige Konfigurationssicherung wurde sofort aktualisiert.\\n\\n%s" % path,\n                "%d / %d Tages-Sicherungen vorhanden." % (count, AUTO_BACKUP_KEEP),\n            )\n        except Exception as exc:\n            self._showFailure(\n                "Sicherung fehlgeschlagen",\n                "Die heutige Sicherung konnte nicht aktualisiert werden.\\n\\n%s" % exc,\n            )\n\n    def doExport(self):\n        if self._done:\n            self.close()\n            return\n        try:\n            path = config_store.export_backup(BACKUP_PATH)\n            try:\n                os.chmod(path, 0o600)\n            except Exception:\n                pass\n            self._showDone(\n                "Export abgeschlossen",\n                "Konfiguration gespeichert unter:\\n%s\\n\\n"\n                "Die Datei enthält Anmeldedaten und sollte vertraulich behandelt werden." % path,\n                "Automatische Sicherungen bleiben separat im 7-Tage-Verlauf erhalten.",\n            )\n        except Exception as exc:\n            self._showFailure(\n                "Export fehlgeschlagen",\n                "Die Konfiguration konnte nicht exportiert werden.\\n\\n%s" % exc,\n            )\n\n    def doImport(self):\n        if self._done:\n            self.close()\n            return\n        if not os.path.isfile(BACKUP_PATH):\n            self._showFailure(\n                "Keine Exportdatei gefunden",\n                "Unter\\n%s\\nliegt keine manuell exportierte Konfiguration.\\n\\n"\n                "Erstelle zuerst mit GELB einen Export." % BACKUP_PATH,\n            )\n            return\n\n        if not self._import_confirm:\n            self._import_confirm = True\n            self["title"].setText("Exportdatei wiederherstellen?")\n            self["body"].setText(\n                "Konfiguration aus:\\n%s\\n\\n"\n                "Vorhandene Server und Favoriten werden durch den Inhalt dieser Exportdatei ersetzt."\n                % BACKUP_PATH\n            )\n            self["status"].setText("BLAU   Wiederherstellen   ·   ROT   Abbrechen")\n            self._set_status_color("#8CCEF6")\n            self["key_green"].hide()\n            self["key_yellow"].hide()\n            self["key_blue"].setText("BLAU   Wiederherstellen")\n            self["key_blue"].show()\n            self["key_red"].show()\n            self["key_ok"].hide()\n            return\n\n        try:\n            servers, favorites = config_store.import_backup(BACKUP_PATH)\n            self._showDone(\n                "Import abgeschlossen",\n                "%d Server und %d Favoriten wurden aus der Exportdatei übernommen."\n                % (servers, favorites),\n                "Die Serverliste wird nach dem Schließen aktualisiert.",\n            )\n        except Exception as exc:\n            self._import_confirm = False\n            self._showFailure(\n                "Import fehlgeschlagen",\n                "Die Konfiguration konnte nicht wiederhergestellt werden.\\n\\n%s" % exc,\n            )\n            self["key_blue"].setText("BLAU   Importieren")\n            self["key_green"].show()\n            self["key_yellow"].show()\n'
FORCE_BACKUP_FUNC = '\n\n# MEDIAPLUGINS2026_BACKUP_RESTORE_FINAL1_HELPER\ndef force_backup_now():\n    _ensure_private_dir(AUTO_BACKUP_DIR)\n    target = today_backup_path()\n    tmp_target = target + ".manual.tmp"\n    try:\n        if os.path.exists(tmp_target):\n            os.unlink(tmp_target)\n    except Exception:\n        pass\n\n    exported = config_store.export_backup(tmp_target) or tmp_target\n    if os.path.abspath(exported) != os.path.abspath(tmp_target):\n        import shutil\n        shutil.copy2(exported, tmp_target)\n\n    _private_file(tmp_target)\n    try:\n        os.replace(tmp_target, target)\n    except AttributeError:\n        if os.path.exists(target):\n            os.unlink(target)\n        os.rename(tmp_target, target)\n    _private_file(target)\n    _prune()\n    log.info("AutoBackup: Tages-Sicherung manuell aktualisiert: %s", target)\n    return target\n'


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


def _replace_widget_geometry(text, name, position, size):
    pattern = re.compile(r'(?ms)(<widget\b[^>]*\bname="%s"[^>]*?/>)' % re.escape(name))
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError("%s: Skin-Widget nicht eindeutig gefunden" % name)
    block = matches[0].group(1)
    block = re.sub(r'position="[^"]+"', 'position="%s"' % position, block, count=1)
    block = re.sub(r'size="[^"]+"', 'size="%s"' % size, block, count=1)
    return text[:matches[0].start(1)] + block + text[matches[0].end(1):]


def _remove_skin_widget(text, name):
    pattern = re.compile(r'(?ms)\n\s*<widget\b[^>]*\bname="%s"[^>]*?/>' % re.escape(name))
    text, count = pattern.subn("", text, count=1)
    if count != 1:
        raise RuntimeError("%s: zu entfernendes Skin-Widget nicht eindeutig gefunden" % name)
    return text


def patch_helper(text):
    if "def force_backup_now():" in text:
        return text
    anchor = "\ndef list_daily_backups():\n"
    if anchor not in text:
        raise RuntimeError("config_backup.py: list_daily_backups fehlt")
    text = text.replace(anchor, FORCE_BACKUP_FUNC + anchor, 1)
    compile(text, "config_backup.py", "exec")
    return text


def patch_settings(text):
    if MARKER_SETTINGS not in text:
        class_anchor = None
        for candidate in ("class Settings(Screen):\n", "class MediaPluginsSettings(Screen):\n"):
            if candidate in text:
                class_anchor = candidate
                break
        if class_anchor is None:
            raise RuntimeError("Settings-Klassenanker fehlt")
        text = text.replace(class_anchor, MARKER_SETTINGS + "\n" + class_anchor, 1)

    if 'name="key_blue"' in text:
        text = _remove_skin_widget(text, "key_blue")
    text = re.sub(r'^\s*self\["key_blue"\]\s*=\s*Label\([^\n]*\)\n', "", text, count=1, flags=re.M)
    text = re.sub(r'^\s*"blue"\s*:\s*self\.keyImport,\s*\n', "", text, count=1, flags=re.M)

    text = _replace_widget_geometry(text, "key_green", "52,658", "360,48")
    text = _replace_widget_geometry(text, "key_red", "430,658", "360,48")
    text = _replace_widget_geometry(text, "key_yellow", "808,658", "360,48")
    text = _replace_widget_geometry(text, "key_back", "1186,658", "360,48")

    text = text.replace(
        'self["footer_hint"] = Label("↑↓ Server / Update   OK auswählen")',
        'self["footer_hint"] = Label("↑↓ Server / Update / Sicherungen   OK auswählen")',
    )
    text = text.replace(
        "lambda *args: self._render_all(),\n                MediaPluginsBackupScreen,",
        "lambda *args: self.refreshList(),\n                MediaPluginsBackupScreen,",
        1,
    )

    old_export = (
        "    def keyExport(self):\n"
        "        # MEDIAPLUGINS2026_AUTOBACKUP1_SETTINGS\n"
        "        from .BackupScreen import MediaPluginsBackupScreen\n"
        "        self.session.open(MediaPluginsBackupScreen)\n"
    )
    new_export = (
        "    def keyExport(self):\n"
        "        # MEDIAPLUGINS2026_AUTOBACKUP1_SETTINGS\n"
        "        from .BackupScreen import MediaPluginsBackupScreen\n"
        "        self.session.openWithCallback(\n"
        "            lambda *args: self.refreshList(),\n"
        "            MediaPluginsBackupScreen,\n"
        "        )\n"
    )
    if old_export in text:
        text = text.replace(old_export, new_export, 1)

    compile(text, "Settings.py", "exec")
    return text


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DEFAULT
    settings_path = os.path.join(root, SETTINGS_REL)
    screen_path = os.path.join(root, SCREEN_REL)
    helper_path = os.path.join(root, HELPER_REL)

    for path in (settings_path, helper_path):
        if not os.path.isfile(path):
            raise SystemExit("Datei nicht gefunden: %s" % path)

    settings_new = patch_settings(read(settings_path))
    helper_new = patch_helper(read(helper_path))

    compile(settings_new, settings_path, "exec")
    compile(helper_new, helper_path, "exec")
    compile(BACKUP_SCREEN_CODE, screen_path, "exec")

    sb = backup(settings_path, ".before_backup_restore_final1")
    db = backup(screen_path, ".before_backup_restore_final1")
    hb = backup(helper_path, ".before_backup_restore_final1")

    write(settings_path, settings_new)
    write(helper_path, helper_new)
    write(screen_path, BACKUP_SCREEN_CODE)

    for path in (settings_path, helper_path, screen_path):
        compile(read(path), path, "exec")

    s = read(settings_path)
    b = read(screen_path)
    h = read(helper_path)
    checks = [
        ('name="key_blue"' not in s, "BLAU aus Hauptscreen entfernt"),
        ('"blue": self.keyImport' not in s, "BLAU Hauptscreen-Action entfernt"),
        ('name="key_blue"' in b, "BLAU im Sicherungsdialog"),
        ('"blue": self.doImport' in b, "Restore-Action"),
        ('Sicherung & Wiederherstellung' in b, "finale Überschrift"),
        ('def force_backup_now():' in h, "Jetzt-sichern Helper"),
    ]
    missing = [label for ok, label in checks if not ok]
    if missing:
        raise RuntimeError("BACKUP_RESTORE_FINAL1 Verifikation fehlgeschlagen: %r" % missing)

    print("OK MEDIAPLUGINS2026_BACKUP_RESTORE_FINAL1")
    print("- Hauptscreen: BLAU Importieren entfernt, vier gleichmaessige Tasten")
    print("- Sicherungsdialog: GRUEN sichern / GELB exportieren / BLAU importieren / ROT abbrechen")
    print("- Restore mit Bestaetigungsschritt")
    print("- Erfolgsansicht zeigt nur OK Schliessen")
    print("- Titel: Sicherung & Wiederherstellung")
    print("- Settings aktualisieren Serverliste nach Dialog/Restore")
    print("Settings Backup: %s" % sb)
    print("Dialog Backup:   %s" % db)
    print("Helper Backup:   %s" % hb)


if __name__ == "__main__":
    main()
