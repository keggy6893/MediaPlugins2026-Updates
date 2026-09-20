# -*- coding: utf-8 -*-
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



# MEDIAPLUGINS2026_BACKUP_RESTORE_FINAL1_HELPER
def force_backup_now():
    _ensure_private_dir(AUTO_BACKUP_DIR)
    target = today_backup_path()
    tmp_target = target + ".manual.tmp"
    try:
        if os.path.exists(tmp_target):
            os.unlink(tmp_target)
    except Exception:
        pass

    exported = config_store.export_backup(tmp_target) or tmp_target
    if os.path.abspath(exported) != os.path.abspath(tmp_target):
        import shutil
        shutil.copy2(exported, tmp_target)

    _private_file(tmp_target)
    try:
        os.replace(tmp_target, target)
    except AttributeError:
        if os.path.exists(target):
            os.unlink(target)
        os.rename(tmp_target, target)
    _private_file(target)
    _prune()
    log.info("AutoBackup: Tages-Sicherung manuell aktualisiert: %s", target)
    return target

def list_daily_backups():
    try:
        return list(reversed(_backup_files()))
    except Exception:
        return []
