# -*- coding: utf-8 -*-
# MEDIAPLUGINS2026_AUTOBACKUP1_SCREEN
# MEDIAPLUGINS2026_BACKUP_RESTORE_FINAL1_SCREEN

import os

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label

try:
    from skin import parseColor
except Exception:
    parseColor = None

from ..config import config_store, BACKUP_PATH
from ..utils.config_backup import (
    AUTO_BACKUP_DIR,
    AUTO_BACKUP_KEEP,
    list_daily_backups,
    force_backup_now,
)


class MediaPluginsBackupScreen(Screen):
    skinName = "MediaPlugins2026BackupScreen"
    skin = r"""
    <screen name="MediaPlugins2026BackupScreen" position="center,center" size="1240,520"
            backgroundColor="#06121D" flags="wfNoBorder" title="Media Plugins 2026 Sicherung">
        <eLabel zPosition="5" position="0,0" size="1240,4" backgroundColor="#23D7F2" />
        <eLabel zPosition="5" position="0,0" size="2,520" backgroundColor="#1B4C6B" />
        <eLabel zPosition="5" position="1238,0" size="2,520" backgroundColor="#1B4C6B" />
        <eLabel zPosition="5" position="0,518" size="1240,2" backgroundColor="#1B4C6B" />

        <widget zPosition="50" name="brand" position="42,28" size="310,44" font="Bold;30"
                foregroundColor="#F4F7FB" backgroundColor="#06121D" transparent="1" />
        <widget zPosition="50" name="year" position="350,28" size="130,44" font="Bold;30"
                foregroundColor="#23D7F2" backgroundColor="#06121D" transparent="1" />
        <widget zPosition="50" name="kicker" position="42,89" size="1110,28" font="Bold;18"
                foregroundColor="#8CCEF6" backgroundColor="#06121D" transparent="1" />
        <eLabel zPosition="5" position="42,130" size="1156,1" backgroundColor="#244863" />

        <widget zPosition="50" name="title" position="55,154" size="1100,45" font="Bold;29"
                foregroundColor="#F4F7FB" backgroundColor="#06121D" transparent="1" />
        <widget zPosition="50" name="body" position="55,214" size="1100,150" font="Regular;21"
                foregroundColor="#C8D7E6" backgroundColor="#06121D" transparent="1" />
        <widget zPosition="50" name="status" position="55,374" size="1100,34" font="Regular;18"
                foregroundColor="#7893A9" backgroundColor="#06121D" transparent="1" />

        <widget zPosition="50" name="key_green" position="55,442" size="270,52" font="Bold;19"
                foregroundColor="#FFFFFF" backgroundColor="#087A37" transparent="0"
                halign="center" valign="center" />
        <widget zPosition="50" name="key_yellow" position="341,442" size="270,52" font="Bold;19"
                foregroundColor="#FFFFFF" backgroundColor="#B58B00" transparent="0"
                halign="center" valign="center" />
        <widget zPosition="50" name="key_blue" position="627,442" size="270,52" font="Bold;19"
                foregroundColor="#FFFFFF" backgroundColor="#1762A7" transparent="0"
                halign="center" valign="center" />
        <widget zPosition="50" name="key_red" position="913,442" size="270,52" font="Bold;19"
                foregroundColor="#FFFFFF" backgroundColor="#9E2428" transparent="0"
                halign="center" valign="center" />
        <widget zPosition="50" name="key_ok" position="392,442" size="455,52" font="Bold;20"
                foregroundColor="#D6E1EB" backgroundColor="#263442" transparent="0"
                halign="center" valign="center" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self._done = False
        self._import_confirm = False

        self["brand"] = Label("Media Plugins")
        self["year"] = Label("2026")
        self["kicker"] = Label("KONFIGURATION · SICHERUNG · EXPORT · RESTORE")
        self["title"] = Label("Sicherung & Wiederherstellung")
        self["body"] = Label(
            "GRÜN aktualisiert die heutige interne Sicherung sofort.\n"
            "GELB erstellt eine manuelle Exportdatei unter %s.\n"
            "BLAU stellt diese Exportdatei wieder her.\n\n"
            "Automatische Sicherung: täglich · %d Tage Verlauf" % (BACKUP_PATH, AUTO_BACKUP_KEEP)
        )
        self["status"] = Label(self._backup_status())

        self["key_green"] = Label("GRÜN   Jetzt sichern")
        self["key_yellow"] = Label("GELB   Exportieren")
        self["key_blue"] = Label("BLAU   Importieren")
        self["key_red"] = Label("ROT   Abbrechen")
        self["key_ok"] = Label("OK   Schließen")

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok": self.keyOk,
                "cancel": self.close,
                "green": self.doBackupNow,
                "yellow": self.doExport,
                "blue": self.doImport,
                "red": self.close,
            },
            -1,
        )
        self.onLayoutFinish.append(self._showInitialButtons)

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

    def _showInitialButtons(self):
        self._done = False
        self._import_confirm = False
        self["key_green"].setText("GRÜN   Jetzt sichern")
        self["key_yellow"].setText("GELB   Exportieren")
        self["key_blue"].setText("BLAU   Importieren")
        self["key_red"].setText("ROT   Abbrechen")
        self["key_green"].show()
        self["key_yellow"].show()
        self["key_blue"].show()
        self["key_red"].show()
        self["key_ok"].hide()

    def _showDone(self, title, body, status):
        self._done = True
        self._import_confirm = False
        self["title"].setText(title)
        self["body"].setText(body)
        self["status"].setText(status)
        self._set_status_color("#37D67A")
        self["key_green"].hide()
        self["key_yellow"].hide()
        self["key_blue"].hide()
        self["key_red"].hide()
        self["key_ok"].setText("OK   Schließen")
        self["key_ok"].show()

    def _showFailure(self, title, body):
        self["title"].setText(title)
        self["body"].setText(body)
        self["status"].setText(
            "Es wurden keine bestehenden automatischen Sicherungen gelöscht."
        )
        self._set_status_color("#FF6B6B")

    def keyOk(self):
        if self._done:
            self.close()

    def doBackupNow(self):
        if self._done:
            self.close()
            return
        try:
            path = force_backup_now()
            count = len(list_daily_backups())
            self._showDone(
                "Sicherung aktualisiert",
                "Die heutige Konfigurationssicherung wurde sofort aktualisiert.\n\n%s" % path,
                "%d / %d Tages-Sicherungen vorhanden." % (count, AUTO_BACKUP_KEEP),
            )
        except Exception as exc:
            self._showFailure(
                "Sicherung fehlgeschlagen",
                "Die heutige Sicherung konnte nicht aktualisiert werden.\n\n%s" % exc,
            )

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
            self._showDone(
                "Export abgeschlossen",
                "Konfiguration gespeichert unter:\n%s\n\n"
                "Die Datei enthält Anmeldedaten und sollte vertraulich behandelt werden." % path,
                "Automatische Sicherungen bleiben separat im 7-Tage-Verlauf erhalten.",
            )
        except Exception as exc:
            self._showFailure(
                "Export fehlgeschlagen",
                "Die Konfiguration konnte nicht exportiert werden.\n\n%s" % exc,
            )

    def doImport(self):
        if self._done:
            self.close()
            return
        if not os.path.isfile(BACKUP_PATH):
            self._showFailure(
                "Keine Exportdatei gefunden",
                "Unter\n%s\nliegt keine manuell exportierte Konfiguration.\n\n"
                "Erstelle zuerst mit GELB einen Export." % BACKUP_PATH,
            )
            return

        if not self._import_confirm:
            self._import_confirm = True
            self["title"].setText("Exportdatei wiederherstellen?")
            self["body"].setText(
                "Konfiguration aus:\n%s\n\n"
                "Vorhandene Server und Favoriten werden durch den Inhalt dieser Exportdatei ersetzt."
                % BACKUP_PATH
            )
            self["status"].setText("BLAU   Wiederherstellen   ·   ROT   Abbrechen")
            self._set_status_color("#8CCEF6")
            self["key_green"].hide()
            self["key_yellow"].hide()
            self["key_blue"].setText("BLAU   Wiederherstellen")
            self["key_blue"].show()
            self["key_red"].show()
            self["key_ok"].hide()
            return

        try:
            servers, favorites = config_store.import_backup(BACKUP_PATH)
            self._showDone(
                "Import abgeschlossen",
                "%d Server und %d Favoriten wurden aus der Exportdatei übernommen."
                % (servers, favorites),
                "Die Serverliste wird nach dem Schließen aktualisiert.",
            )
        except Exception as exc:
            self._import_confirm = False
            self._showFailure(
                "Import fehlgeschlagen",
                "Die Konfiguration konnte nicht wiederhergestellt werden.\n\n%s" % exc,
            )
            self["key_blue"].setText("BLAU   Importieren")
            self["key_green"].show()
            self["key_yellow"].show()
