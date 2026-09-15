# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import re
import shutil
import sys

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
SCREEN_REL = "screens/BackupScreen.py"
HELPER_REL = "utils/config_backup.py"

MARKER_SCREEN = "# MEDIAPLUGINS2026_BACKUP_ACTIONS1_SCREEN"
MARKER_HELPER = "# MEDIAPLUGINS2026_BACKUP_ACTIONS1_HELPER"
REQUIRED_SCREEN = "# MEDIAPLUGINS2026_AUTOBACKUP1_SCREEN"
REQUIRED_HELPER = "# MEDIAPLUGINS2026_AUTOBACKUP1_HELPER"

HELPER_FUNC = '\n# MEDIAPLUGINS2026_BACKUP_ACTIONS1_HELPER\ndef force_backup_now():\n    _ensure_private_dir(AUTO_BACKUP_DIR)\n    target = today_backup_path()\n    tmp_target = target + ".manual.tmp"\n\n    try:\n        if os.path.exists(tmp_target):\n            os.unlink(tmp_target)\n    except Exception:\n        pass\n\n    exported = config_store.export_backup(tmp_target)\n    exported = exported or tmp_target\n\n    if os.path.abspath(exported) != os.path.abspath(tmp_target):\n        try:\n            import shutil\n            shutil.copy2(exported, tmp_target)\n        except Exception:\n            raise RuntimeError(\n                "Exportpfad konnte nicht in die Tagesdatei übernommen werden"\n            )\n\n    _private_file(tmp_target)\n\n    try:\n        os.replace(tmp_target, target)\n    except AttributeError:\n        if os.path.exists(target):\n            os.unlink(target)\n        os.rename(tmp_target, target)\n\n    _private_file(target)\n    _prune()\n    log.info("AutoBackup: Tages-Sicherung manuell aktualisiert: %s", target)\n    return target\n'
BUTTON_BLOCK = '        <widget zPosition="50" name="key_green" position="55,422" size="350,52" font="Bold;20"\n                foregroundColor="#FFFFFF" backgroundColor="#087A37" transparent="0"\n                halign="center" valign="center" />\n        <widget zPosition="50" name="key_yellow" position="425,422" size="350,52" font="Bold;20"\n                foregroundColor="#FFFFFF" backgroundColor="#B58B00" transparent="0"\n                halign="center" valign="center" />\n        <widget zPosition="50" name="key_red" position="795,422" size="390,52" font="Bold;20"\n                foregroundColor="#FFFFFF" backgroundColor="#9E2428" transparent="0"\n                halign="center" valign="center" />\n        <widget zPosition="50" name="key_ok" position="392,422" size="455,52" font="Bold;20"\n                foregroundColor="#D6E1EB" backgroundColor="#263442" transparent="0"\n                halign="center" valign="center" />'
NEW_METHODS = '    # MEDIAPLUGINS2026_BACKUP_ACTIONS1_SCREEN\n    def _setInitialButtons(self):\n        try:\n            self["key_green"].show()\n            self["key_yellow"].show()\n            self["key_red"].show()\n            self["key_ok"].hide()\n        except Exception:\n            pass\n\n    def _showDone(self, title, body, status, color="#37D67A"):\n        self._done = True\n        self["title"].setText(title)\n        self["body"].setText(body)\n        self["status"].setText(status)\n        self._set_status_color(color)\n        try:\n            self["key_green"].hide()\n            self["key_yellow"].hide()\n            self["key_red"].hide()\n            self["key_ok"].setText("OK   Schließen")\n            self["key_ok"].show()\n        except Exception:\n            pass\n\n    def _showFailure(self, title, body):\n        self["title"].setText(title)\n        self["body"].setText(body)\n        self["status"].setText(\n            "Bestehende automatische Sicherungen bleiben unverändert."\n        )\n        self._set_status_color("#FF6B6B")\n\n    def keyOk(self):\n        if self._done:\n            self.close()\n        else:\n            self.doBackupNow()\n\n    def doBackupNow(self):\n        if self._done:\n            self.close()\n            return\n        try:\n            path = force_backup_now()\n            count = len(list_daily_backups())\n            self._showDone(\n                "Sicherung aktualisiert",\n                "Die heutige Konfigurationssicherung wurde sofort aktualisiert.\\n\\n%s"\n                % path,\n                "%d / %d Tages-Sicherungen vorhanden."\n                % (count, AUTO_BACKUP_KEEP),\n            )\n        except Exception as exc:\n            self._showFailure(\n                "Sicherung fehlgeschlagen",\n                "Die heutige Sicherung konnte nicht aktualisiert werden.\\n\\n%s"\n                % exc,\n            )\n\n    def doExport(self):\n        if self._done:\n            self.close()\n            return\n        try:\n            path = config_store.export_backup(BACKUP_PATH)\n            try:\n                os.chmod(path, 0o600)\n            except Exception:\n                pass\n            self._showDone(\n                "Export abgeschlossen",\n                "Konfiguration gespeichert unter:\\n%s\\n\\n"\n                "Die Datei enthält Anmeldedaten und sollte vertraulich behandelt werden."\n                % path,\n                "Automatische Sicherungen bleiben separat im 7-Tage-Verlauf erhalten.",\n            )\n        except Exception as exc:\n            self._showFailure(\n                "Export fehlgeschlagen",\n                "Die Konfiguration konnte nicht exportiert werden.\\n\\n%s" % exc,\n            )\n'
BODY_NEW = '        self["body"] = Label(\n            "GRÜN aktualisiert die heutige interne Sicherung sofort.\\n"\n            "GELB erstellt eine manuelle Exportdatei unter /tmp.\\n\\n"\n            "Automatische Sicherung: täglich · %d Tage Verlauf"\n            % AUTO_BACKUP_KEEP\n        )\n'
OLD_LABELS = '        self["status"] = Label(self._backup_status())\n        self["key_yellow"] = Label("GELB   Exportieren")\n        self["key_red"] = Label("ROT   Abbrechen")\n        self["key_ok"] = Label("OK   Exportieren")\n'
NEW_LABELS = '        self["status"] = Label(self._backup_status())\n        self["key_green"] = Label("GRÜN   Jetzt sichern")\n        self["key_yellow"] = Label("GELB   Exportieren")\n        self["key_red"] = Label("ROT   Abbrechen")\n        self["key_ok"] = Label("OK   Schließen")\n'
OLD_ACTIONS = '                "ok": self.keyOk,\n                "cancel": self.close,\n                "yellow": self.doExport,\n                "red": self.close,\n'
NEW_ACTIONS = '                "ok": self.keyOk,\n                "cancel": self.close,\n                "green": self.doBackupNow,\n                "yellow": self.doExport,\n                "red": self.close,\n'


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


def patch_helper(text):
    if MARKER_HELPER in text:
        return text
    if REQUIRED_HELPER not in text:
        raise RuntimeError("AUTOBACKUP1 Helper-Basis fehlt")

    anchor = "\ndef list_daily_backups():\n"
    if anchor not in text:
        raise RuntimeError("list_daily_backups Anker fehlt")

    text = text.replace(anchor, HELPER_FUNC + anchor, 1)
    compile(text, "config_backup.py", "exec")
    return text


def patch_screen(text):
    if MARKER_SCREEN in text:
        return text
    if REQUIRED_SCREEN not in text:
        raise RuntimeError("AUTOBACKUP1 BackupScreen-Basis fehlt")

    old_import = (
        "from ..utils.config_backup import "
        "AUTO_BACKUP_DIR, AUTO_BACKUP_KEEP, list_daily_backups"
    )
    new_import = (
        "from ..utils.config_backup import "
        "AUTO_BACKUP_DIR, AUTO_BACKUP_KEEP, list_daily_backups, force_backup_now"
    )
    if old_import in text:
        text = text.replace(old_import, new_import, 1)
    elif "force_backup_now" not in text:
        raise RuntimeError("config_backup Import-Anker fehlt")

    button_pattern = re.compile(
        r'(?ms)\s*<widget\s+zPosition="(?:20|50)"\s+name="key_yellow".*?'
        r'<widget\s+zPosition="(?:20|50)"\s+name="key_ok".*?/>'
    )
    matches = list(button_pattern.finditer(text))
    if len(matches) != 1:
        button_pattern = re.compile(
            r'(?ms)\s*<widget\s+name="key_yellow".*?'
            r'<widget\s+name="key_ok".*?/>'
        )
        matches = list(button_pattern.finditer(text))

    if len(matches) != 1:
        raise RuntimeError(
            "Buttonbereich: erwartete genau 1 Fundstelle, gefunden %d"
            % len(matches)
        )

    m = matches[0]
    text = text[:m.start()] + "\n" + BUTTON_BLOCK + text[m.end():]

    text = text.replace(
        'self["title"] = Label("Manuellen Export erstellen?")',
        'self["title"] = Label("Sicherung oder Export?")',
        1,
    )

    body_pattern = re.compile(
        r'(?ms)        self\["body"\] = Label\(\n.*?\n        \)\n'
    )
    body_matches = list(body_pattern.finditer(text))
    if len(body_matches) != 1:
        raise RuntimeError(
            "Body-Initialisierung: erwartete 1 Fundstelle, gefunden %d"
            % len(body_matches)
        )
    bm = body_matches[0]
    text = text[:bm.start()] + BODY_NEW + text[bm.end():]

    if OLD_LABELS not in text:
        raise RuntimeError("Button-Label-Initialisierung nicht gefunden")
    text = text.replace(OLD_LABELS, NEW_LABELS, 1)

    if OLD_ACTIONS not in text:
        raise RuntimeError("ActionMap-Anker nicht gefunden")
    text = text.replace(OLD_ACTIONS, NEW_ACTIONS, 1)

    action_end_pattern = re.compile(
        r'(?ms)(        self\["actions"\] = ActionMap\(.*?\n        \)\n)'
    )
    am = action_end_pattern.search(text)
    if not am:
        raise RuntimeError("ActionMap Block nicht gefunden")
    block = am.group(1)
    text = (
        text[:am.start(1)]
        + block
        + "\n        self.onLayoutFinish.append(self._setInitialButtons)\n"
        + text[am.end(1):]
    )

    methods_pattern = re.compile(r'(?ms)^    def keyOk\(self\):\n.*\Z')
    mm = methods_pattern.search(text)
    if not mm:
        raise RuntimeError("keyOk/doExport Methodenblock nicht gefunden")
    text = text[:mm.start()] + NEW_METHODS.rstrip() + "\n"

    compile(text, "BackupScreen.py", "exec")
    return text


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DEFAULT
    screen_path = os.path.join(root, SCREEN_REL)
    helper_path = os.path.join(root, HELPER_REL)

    for path in (screen_path, helper_path):
        if not os.path.isfile(path):
            raise SystemExit("Datei nicht gefunden: %s" % path)

    screen_original = read(screen_path)
    helper_original = read(helper_path)

    helper_new = patch_helper(helper_original)
    screen_new = patch_screen(screen_original)

    compile(helper_new, helper_path, "exec")
    compile(screen_new, screen_path, "exec")

    helper_backup = backup(helper_path, ".before_backup_actions1")
    screen_backup = backup(screen_path, ".before_backup_actions1")

    write(helper_path, helper_new)
    write(screen_path, screen_new)

    helper_verify = read(helper_path)
    screen_verify = read(screen_path)
    compile(helper_verify, helper_path, "exec")
    compile(screen_verify, screen_path, "exec")

    required_screen = [
        MARKER_SCREEN,
        'self["key_green"] = Label("GRÜN   Jetzt sichern")',
        '"green": self.doBackupNow',
        'self["key_green"].hide()',
        'self["key_ok"].show()',
        '"Sicherung aktualisiert"',
        '"Export abgeschlossen"',
    ]
    required_helper = [
        MARKER_HELPER,
        "def force_backup_now():",
        "os.replace(tmp_target, target)",
        "_prune()",
    ]

    missing = [x for x in required_screen if x not in screen_verify]
    missing += [x for x in required_helper if x not in helper_verify]
    if missing:
        raise RuntimeError(
            "BACKUP_ACTIONS1 Verifikation fehlgeschlagen: %r" % missing
        )

    print("OK MEDIAPLUGINS2026_BACKUP_ACTIONS1")
    print("- GRUEN Jetzt sichern: heutige persistente Sicherung sofort aktualisieren")
    print("- GELB Exportieren: manuelle Datei nach /tmp")
    print("- ROT Abbrechen")
    print("- nach Erfolg verschwinden die farbigen Tasten komplett")
    print("- danach bleibt nur ein mittiger OK Schliessen-Button")
    print("- 7-Tage-Rotation und 0600/0700 Schutz bleiben erhalten")
    print("BackupScreen Backup: %s" % screen_backup)
    print("BackupHelper Backup: %s" % helper_backup)


if __name__ == "__main__":
    main()
