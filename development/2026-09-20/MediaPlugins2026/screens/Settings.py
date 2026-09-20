# -*- coding: utf-8 -*-
import os
import time

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Tools.LoadPixmap import LoadPixmap
from enigma import ePoint, eSize

try:
    from skin import parseColor
except Exception:
    parseColor = None

from ..config import config_store, BACKUP_PATH
from ..utils.config_backup import AUTO_BACKUP_DIR, AUTO_BACKUP_KEEP, list_daily_backups
from ..version import PLUGIN_VERSION, PLUGIN_UPDATE_BUILD, PLUGIN_UPDATE_CHANNEL

# MEDIAPLUGINS2026_SETTINGS_UPDATER1
# MEDIAPLUGINS2026_SETTINGS_UI1
# MEDIAPLUGINS2026_SETTINGS_LAYERFIX1
# MEDIAPLUGINS2026_SETTINGS_UPDATELEFT1
# MEDIAPLUGINS2026_SETTINGS_COMPACT1
# MEDIAPLUGINS2026_SETTINGS_UPDATEDETAIL1
# MEDIAPLUGINS2026_SETTINGS_GITHUBUPDATE1
# MEDIAPLUGINS2026_SETTINGS_FINALPOLISH1

_PROVIDER_COLORS = {
    "emby": "#37D67A",
    "jellyfin": "#48AFFF",
    "plex": "#F5B82E",
}
_PROVIDER_NAMES = {
    "emby": "Emby",
    "jellyfin": "Jellyfin",
    "plex": "Plex",
}
_CARD_NORMAL = "#0A1C2B"
_CARD_SELECTED = "#0B3D52"
_PANEL = "#081725"
_TEXT = "#F4F7FB"
_MUTED = "#8FA4B8"
_CYAN = "#23D7F2"


# MEDIAPLUGINS2026_BACKUP_RESTORE_FINAL1_SETTINGS
# MEDIAPLUGINS2026_SETTINGS_CRASHFIX1
class Settings(Screen):
    """MediaPlugins2026 Medienserver-/Update-Verwaltung im eigenen UI."""

    skinName = "MediaPlugins2026SettingsScreen"
    skin = r"""
    <screen name="MediaPlugins2026SettingsScreen" position="center,center" size="1600,900"
            backgroundColor="#06121D" flags="wfNoBorder" title="Media Plugins 2026 Einstellungen">

        <!-- header -->
        <widget zPosition="20" name="brand" position="46,23" size="421,45" font="Bold;32"
                foregroundColor="#F4F7FB" backgroundColor="#06121D" transparent="1" />
        <widget zPosition="20" name="brand_year" position="304,23" size="158,45" font="Bold;32"
                foregroundColor="#23D7F2" backgroundColor="#06121D" transparent="1" />
        <eLabel position="479,22" size="2,52" backgroundColor="#23D7F2" />
        <widget zPosition="20" name="screen_title" position="512,25" size="417,36" font="Regular;27"
                foregroundColor="#C8D7E6" backgroundColor="#06121D" transparent="1" />
        <widget zPosition="20" name="screen_subtitle" position="512,60" size="542,25" font="Regular;17"
                foregroundColor="#86A1B8" backgroundColor="#06121D" transparent="1" />

        <widget source="global.CurrentTime" render="Label" position="1317,23" size="229,33"
                font="Regular;26" foregroundColor="#D8E7F4" backgroundColor="#06121D"
                transparent="1" halign="right">
            <convert type="ClockToText">Format:%H:%M</convert>
        </widget>
        <widget source="global.CurrentTime" render="Label" position="1208,58" size="338,22"
                font="Regular;14" foregroundColor="#86A1B8" backgroundColor="#06121D"
                transparent="1" halign="right">
            <convert type="ClockToText">Format:%a, %d.%m.%Y</convert>
        </widget>

        <!-- left media server panel -->
        <eLabel position="42,104" size="688,525" backgroundColor="#081725"
                borderWidth="2" borderColor="#1B4C6B" />
        <widget zPosition="20" name="left_heading" position="62,119" size="417,30" font="Bold;21"
                foregroundColor="#8CCEF6" backgroundColor="#081725" transparent="1" />
        <widget zPosition="20" name="left_counter" position="517,122" size="183,23" font="Regular;14"
                foregroundColor="#7893A9" backgroundColor="#081725" transparent="1"
                halign="right" />

        <!-- 5 visible server cards -->
        <widget zPosition="5" name="card0_bg" position="60,162" size="650,72" backgroundColor="#0A1C2B"
                transparent="0" borderWidth="2" borderColor="#244863" />
        <widget zPosition="20" name="card0_focus" position="73,176" size="28,38" font="Bold;22"
                foregroundColor="#23D7F2" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card0_provider" position="107,172" size="125,25" font="Bold;18"
                foregroundColor="#37D67A" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card0_title" position="238,168" size="312,28" font="Bold;21"
                foregroundColor="#F4F7FB" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card0_url" position="238,199" size="350,22" font="Regular;15"
                foregroundColor="#91B4CE" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card0_state" position="587,178" size="104,27" font="Bold;14"
                foregroundColor="#37D67A" backgroundColor="#0A1C2B" transparent="1"
                halign="right" />

        <widget zPosition="5" name="card1_bg" position="60,242" size="650,72" backgroundColor="#0A1C2B"
                transparent="0" borderWidth="2" borderColor="#244863" />
        <widget zPosition="20" name="card1_focus" position="73,256" size="28,38" font="Bold;22"
                foregroundColor="#23D7F2" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card1_provider" position="107,252" size="125,25" font="Bold;18"
                foregroundColor="#48AFFF" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card1_title" position="238,248" size="312,28" font="Bold;21"
                foregroundColor="#F4F7FB" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card1_url" position="238,279" size="350,22" font="Regular;15"
                foregroundColor="#91B4CE" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card1_state" position="587,258" size="104,27" font="Bold;14"
                foregroundColor="#48AFFF" backgroundColor="#0A1C2B" transparent="1"
                halign="right" />

        <widget zPosition="5" name="card2_bg" position="60,322" size="650,72" backgroundColor="#0A1C2B"
                transparent="0" borderWidth="2" borderColor="#244863" />
        <widget zPosition="20" name="card2_focus" position="73,336" size="28,38" font="Bold;22"
                foregroundColor="#23D7F2" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card2_provider" position="107,332" size="125,25" font="Bold;18"
                foregroundColor="#F5B82E" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card2_title" position="238,328" size="312,28" font="Bold;21"
                foregroundColor="#F4F7FB" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card2_url" position="238,359" size="350,22" font="Regular;15"
                foregroundColor="#91B4CE" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card2_state" position="587,338" size="104,27" font="Bold;14"
                foregroundColor="#F5B82E" backgroundColor="#0A1C2B" transparent="1"
                halign="right" />

        <widget zPosition="5" name="card3_bg" position="60,402" size="650,72" backgroundColor="#0A1C2B"
                transparent="0" borderWidth="2" borderColor="#244863" />
        <widget zPosition="20" name="card3_focus" position="73,416" size="28,38" font="Bold;22"
                foregroundColor="#23D7F2" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card3_provider" position="107,412" size="125,25" font="Bold;18"
                foregroundColor="#8FA4B8" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card3_title" position="238,408" size="312,28" font="Bold;21"
                foregroundColor="#F4F7FB" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card3_url" position="238,439" size="350,22" font="Regular;15"
                foregroundColor="#91B4CE" backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="card3_state" position="587,418" size="104,27" font="Bold;14"
                foregroundColor="#8FA4B8" backgroundColor="#0A1C2B" transparent="1"
                halign="right" />

        <widget zPosition="20" name="scroll_hint" position="75,575" size="608,22" font="Regular;14"
                foregroundColor="#7893A9" backgroundColor="#081725" transparent="1"
                halign="center" />

        <!-- right selected server -->
        <eLabel position="750,104" size="808,525" backgroundColor="#081725"
                borderWidth="2" borderColor="#1B4C6B" />
        <widget zPosition="20" name="detail_heading" position="775,119" size="417,30" font="Bold;21"
                foregroundColor="#8CCEF6" backgroundColor="#081725" transparent="1" />
        <widget zPosition="20" name="detail_provider" position="775,165" size="158,32" font="Bold;22"
                foregroundColor="#37D67A" backgroundColor="#081725" transparent="1" />
        <widget zPosition="20" name="detail_name" position="925,162" size="446,33" font="Bold;23"
                foregroundColor="#F4F7FB" backgroundColor="#081725" transparent="1" />
        <widget zPosition="20" name="detail_state" position="1392,166" size="138,28" font="Bold;14"
                foregroundColor="#37D67A" backgroundColor="#081725" transparent="1"
                halign="right" />

        <eLabel position="775,207" size="733,1" backgroundColor="#244863" />
        <widget zPosition="20" name="detail_labels" position="779,229" size="183,171" font="Regular;18"
                foregroundColor="#78BCE5" backgroundColor="#081725" transparent="1" />
        <widget zPosition="20" name="detail_values" position="962,229" size="529,171" font="Regular;18"
                foregroundColor="#D6E1EB" backgroundColor="#081725" transparent="1" />
        <widget zPosition="20" name="detail_hint" position="779,410" size="712,25" font="Regular;14"
                foregroundColor="#7893A9" backgroundColor="#081725" transparent="1"
                halign="center" />

        <!-- Update is the last navigation row in the LEFT server column.
             Runtime positions it directly below the visible servers. -->
        <widget zPosition="5" name="update_bg" position="60,322" size="650,72"
                backgroundColor="#0A1C2B" transparent="0"
                borderWidth="2" borderColor="#244863" />
        <widget zPosition="20" name="update_focus" position="73,336" size="28,38"
                font="Bold;22" foregroundColor="#23D7F2"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="update_icon" position="107,332" size="43,43"
                font="Bold;27" foregroundColor="#23D7F2"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="update_title" position="162,328" size="300,28"
                font="Bold;20" foregroundColor="#F4F7FB"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="update_subtitle" position="162,359" size="325,22"
                font="Regular;14" foregroundColor="#91B4CE"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="update_version" position="488,341" size="196,27"
                font="Regular;15" foregroundColor="#9EC8E4"
                backgroundColor="#0A1C2B" transparent="1" halign="right" />



        <!-- MEDIAPLUGINS2026_BACKUPCARD_UI1 -->
        <!-- Runtime legt diese Karte direkt unter die GitHub-Update-Karte. -->
        <widget zPosition="5" name="backup_bg" position="0,0" size="620,82"
                backgroundColor="#0A1C2B" transparent="0"
                borderWidth="2" borderColor="#244863" />
        <widget zPosition="20" name="backup_focus" position="0,0" size="34,42"
                font="Bold;25" foregroundColor="#23D7F2"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="30" name="backup_icon" position="0,0" size="48,48"
                pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/skin/icons/backup_database.png"
                alphatest="on" transparent="1" />
        <widget zPosition="20" name="backup_title" position="0,0" size="280,30"
                font="Bold;22" foregroundColor="#F4F7FB"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="backup_subtitle" position="0,0" size="340,26"
                font="Regular;17" foregroundColor="#91B4CE"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="backup_status" position="0,0" size="210,28"
                font="Bold;17" foregroundColor="#37D67A"
                backgroundColor="#0A1C2B" transparent="1" halign="right" />
        <widget zPosition="20" name="backup_count" position="0,0" size="210,24"
                font="Regular;16" foregroundColor="#9EC8E4"
                backgroundColor="#0A1C2B" transparent="1" halign="right" />
        <widget zPosition="20" name="backup_chevron" position="0,0" size="26,34"
                font="Bold;27" foregroundColor="#8CCEF6"
                backgroundColor="#0A1C2B" transparent="1" halign="center" />


        <!-- MEDIAPLUGINS2026_ICONALIGN_PROVIDERICONS1 -->
        <widget zPosition="30" name="card0_icon" position="0,0" size="26,26"
                alphatest="on" transparent="1" />
        <widget zPosition="30" name="card1_icon" position="0,0" size="26,26"
                alphatest="on" transparent="1" />
        <widget zPosition="30" name="card2_icon" position="0,0" size="26,26"
                alphatest="on" transparent="1" />
        <widget zPosition="30" name="card3_icon" position="0,0" size="26,26"
                alphatest="on" transparent="1" />
        <widget zPosition="30" name="detail_provider_icon" position="0,0" size="24,24"
                alphatest="on" transparent="1" />

        <!-- footer keys -->
        <widget zPosition="20" name="key_green" position="52,658" size="360,48" font="Bold;18"
                foregroundColor="#FFFFFF" backgroundColor="#087A37" transparent="0"
                halign="center" valign="center" />
        <widget zPosition="20" name="key_red" position="430,658" size="360,48" font="Bold;18"
                foregroundColor="#FFFFFF" backgroundColor="#9E2428" transparent="0"
                halign="center" valign="center" />
        <widget zPosition="20" name="key_yellow" position="808,658" size="360,48" font="Bold;18"
                foregroundColor="#FFFFFF" backgroundColor="#B58B00" transparent="0"
                halign="center" valign="center" />
        <widget zPosition="20" name="key_back" position="1186,658" size="360,48" font="Bold;18"
                foregroundColor="#D6E1EB" backgroundColor="#263442" transparent="0"
                halign="center" valign="center" />

        <widget zPosition="20" name="footer_version" position="52,738" size="500,23" font="Regular;14"
                foregroundColor="#7893A9" backgroundColor="#06121D" transparent="1" />
        <widget zPosition="20" name="footer_hint" position="633,738" size="912,23" font="Regular;14"
                foregroundColor="#7893A9" backgroundColor="#06121D" transparent="1"
                halign="right" />
    </screen>
    """

    VISIBLE_CARDS = 4

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        self["brand"] = Label("Media Plugins")
        self["brand_year"] = Label("2026")
        self["screen_title"] = Label("Einstellungen")
        self["screen_subtitle"] = Label("Emby · Jellyfin · Plex in einer Oberfläche.")
        self["left_heading"] = Label("MEDIENSERVER")
        self["left_counter"] = Label("")
        self["detail_heading"] = Label("AUSGEWÄHLTER SERVER")

        for i in range(self.VISIBLE_CARDS):
            self["card%d_bg" % i] = Label("")
            self["card%d_focus" % i] = Label("")
            self["card%d_provider" % i] = Label("")
            self["card%d_title" % i] = Label("")
            self["card%d_url" % i] = Label("")
            self["card%d_state" % i] = Label("")

        self["scroll_hint"] = Label("")
        self["detail_provider"] = Label("")
        self["detail_name"] = Label("")
        self["detail_state"] = Label("")
        self["detail_labels"] = Label("")
        self["detail_values"] = Label("")
        self["detail_hint"] = Label("ROT entfernt den ausgewählten Server")

        self["update_bg"] = Label("")
        self["update_focus"] = Label("")
        self["update_icon"] = Label("↓")
        self["update_title"] = Label("GitHub Update")
        self["update_subtitle"] = Label("Neue Version auf GitHub suchen und installieren")
        self["update_version"] = Label("Installiert: %s" % PLUGIN_VERSION)

        # MEDIAPLUGINS2026_BACKUPCARD_UI1
        self["backup_bg"] = Label("")
        self["backup_focus"] = Label("")
        self["backup_icon"] = Pixmap()
        self["backup_title"] = Label("Sicherungen")
        self["backup_subtitle"] = Label("Automatisch · täglich · 7 Tage")
        self["backup_status"] = Label("")
        self["backup_count"] = Label("")
        self["backup_chevron"] = Label("›")


        # MEDIAPLUGINS2026_ICONALIGN_PROVIDERICONS1
# MEDIAPLUGINS2026_PROVIDERICON_POLISH1
# MEDIAPLUGINS2026_PROVIDERICON_VISIBLE1
        for _provider_icon_slot in range(self.VISIBLE_CARDS):
            self["card%d_icon" % _provider_icon_slot] = Pixmap()
        self["detail_provider_icon"] = Pixmap()
        self._provider_icon_layout_done = False
        self._provider_icon_cache = {}


        self["key_green"] = Label("GRÜN   Server hinzufügen")
        self["key_red"] = Label("ROT   Entfernen")
        self["key_yellow"] = Label("GELB   Exportieren")
        self["key_back"] = Label("ZURÜCK")
        self["footer_version"] = Label("Media Plugins 2026  v%s" % PLUGIN_VERSION)
        self["footer_hint"] = Label("↑↓ Server / Update / Sicherungen   OK auswählen")

        self._servers = []
        self._selected_server_index = 0
        self._server_window_start = 0
        self._focus_zone = "servers"

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "ok": self.keyOk,
                "cancel": self.keyCancel,
                "green": self.keyAddServer,
                "red": self.keyRemoveServer,
                "yellow": self.keyExport,
                "up": self.keyUp,
                "down": self.keyDown,
                "left": self.keyLeft,
                "right": self.keyRight,
            },
            -1,
        )

        self.onLayoutFinish.append(self.refreshList)
        self.onLayoutFinish.append(self._providerIconLayoutReady)
        self.onLayoutFinish.append(self._backupUiLayoutReady)

    @staticmethod
    def _provider(server):
        return str(getattr(server, "protocol", "") or "").strip().lower()

    @staticmethod
    def _server_url(server):
        address = str(getattr(server, "address", "") or "").strip()
        port = str(getattr(server, "port", "") or "").strip()
        path = str(getattr(server, "path", "") or "").strip()
        https_mode = str(getattr(server, "https", "auto") or "auto").strip().lower()

        if "://" in address:
            base = address.rstrip("/")
        else:
            scheme = "https" if https_mode == "on" else "http"
            base = "%s://%s" % (scheme, address.rstrip("/"))
        if port:
            # Kein doppeltes :PORT anhaengen, falls die Adresse es bereits enthaelt.
            tail = base.rsplit("/", 1)[-1]
            if not tail.endswith(":" + port):
                base += ":" + port
        if path:
            base += "/" + path.strip("/")
        return base

    @staticmethod
    def _short_url(value, max_chars=52):
        text = str(value or "").strip()
        try:
            max_chars = max(12, int(max_chars))
        except Exception:
            max_chars = 52
        if len(text) <= max_chars:
            return text
        return text[:max_chars - 3] + "..."

    def _set_bg(self, widget_name, color):
        if parseColor is None:
            return
        try:
            instance = self[widget_name].instance
            instance.setBackgroundColor(parseColor(color))
            try:
                instance.invalidate()
            except Exception:
                pass
        except Exception:
            pass

    def _set_fg(self, widget_name, color):
        if parseColor is None:
            return
        try:
            self[widget_name].instance.setForegroundColor(parseColor(color))
        except Exception:
            pass

    def _move_update_card(self):
        """Update is visually the list item after the last visible server."""
        visible_servers = min(len(self._servers), self.VISIBLE_CARDS) if self._servers else 1
        y = 163 + (80 * visible_servers)

        positions = {
            "update_bg": (60, y),
            "update_focus": (73, y + 13),
            "update_icon": (107, y + 10),
            "update_title": (163, y + 6),
            "update_subtitle": (163, y + 37),
            "update_version": (488, y + 18),
        }
        for name, (x, py) in positions.items():
            try:
                self[name].instance.move(ePoint(x, py))
            except Exception:
                pass

        try:
            self["scroll_hint"].instance.move(ePoint(75, min(575, y + 80)))
        except Exception:
            pass

    def _hide_card(self, slot):
        for suffix in ("bg", "focus", "icon", "provider", "title", "url", "state"):
            try:
                self["card%d_%s" % (slot, suffix)].hide()
            except Exception:
                pass

    def _show_card(self, slot):
        for suffix in ("bg", "focus", "icon", "provider", "title", "url", "state"):
            try:
                self["card%d_%s" % (slot, suffix)].show()
            except Exception:
                pass


    # MEDIAPLUGINS2026_BACKUPCARD_UI1
    def _backupUiLayoutReady(self):
        self._move_backup_card()
        self._provider_icon_layout_done = False
        self._providerIconLayoutReady()
        self._render_backup_card()

    def _move_backup_card(self):
        """Spiegelt die Geometrie der Update-Karte direkt eine Zeile tiefer."""
        try:
            widgets = (
                ("backup_bg", "update_bg"),
                ("backup_focus", "update_focus"),
                ("backup_title", "update_title"),
                ("backup_subtitle", "update_subtitle"),
            )

            update_bg = self["update_bg"].instance
            bg_pos = update_bg.position()
            bg_size = update_bg.size()
            offset_y = bg_size.height() + 8

            for target, source in widgets:
                src = self[source].instance
                dst = self[target].instance
                p = src.position()
                s = src.size()
                dst.move(ePoint(p.x(), p.y() + offset_y))
                try:
                    dst.resize(eSize(s.width(), s.height()))
                except Exception:
                    pass

            src_icon = self["update_icon"].instance
            ip = src_icon.position()
            self["backup_icon"].instance.move(ePoint(ip.x(), ip.y() + offset_y))
            try:
                self["backup_icon"].instance.resize(eSize(48, 48))
            except Exception:
                pass

            version = self["update_version"].instance
            vp = version.position()
            vs = version.size()
            status_x = vp.x() - 20
            status_w = max(150, vs.width() + 5)

            self["backup_status"].instance.move(
                ePoint(status_x, vp.y() + offset_y - 10)
            )
            self["backup_count"].instance.move(
                ePoint(status_x, vp.y() + offset_y + 18)
            )
            try:
                self["backup_status"].instance.resize(eSize(status_w, 28))
                self["backup_count"].instance.resize(eSize(status_w, 24))
            except Exception:
                pass

            self["backup_chevron"].instance.move(
                ePoint(
                    bg_pos.x() + bg_size.width() - 34,
                    bg_pos.y() + offset_y + max(6, (bg_size.height() - 34) // 2),
                )
            )

            try:
                hint = self["scroll_hint"].instance
                hp = hint.position()
                backup_bottom = bg_pos.y() + offset_y + bg_size.height()
                if hp.y() < backup_bottom + 6:
                    hint.move(ePoint(hp.x(), backup_bottom + 8))
            except Exception:
                pass

        except Exception as exc:
            try:
                log.warning("Backup-Karte konnte nicht positioniert werden: %s", exc)
            except Exception:
                pass

    def _backup_summary(self):
        backups = list_daily_backups()
        count = len(backups)
        if not backups:
            return "Noch keine Sicherung", "%d / %d vorhanden" % (
                count, AUTO_BACKUP_KEEP
            )

        latest = backups[0]
        try:
            stamp = os.path.getmtime(latest)
            tm = time.localtime(stamp)
            today = time.strftime("%Y-%m-%d")
            if time.strftime("%Y-%m-%d", tm) == today:
                status = "Heute %s ✓" % time.strftime("%H:%M", tm)
            else:
                status = time.strftime("%d.%m.%Y", tm)
        except Exception:
            status = os.path.basename(latest)

        return status, "%d / %d vorhanden" % (count, AUTO_BACKUP_KEEP)

    def _render_backup_card(self):
        selected = self._focus_zone == "backup"
        bg = _CARD_SELECTED if selected else _CARD_NORMAL

        self["backup_focus"].setText("▶" if selected else "")
        self["backup_title"].setText("Sicherungen")
        self["backup_subtitle"].setText("Automatisch · täglich · 7 Tage")
        status, count = self._backup_summary()
        self["backup_status"].setText(status)
        self["backup_count"].setText(count)
        self["backup_chevron"].setText("›")

        for name in (
            "backup_bg",
            "backup_focus",
            "backup_title",
            "backup_subtitle",
            "backup_status",
            "backup_count",
            "backup_chevron",
        ):
            self._set_bg(name, bg)

    def _render_backup_details(self):
        try:
            self["detail_provider_icon"].hide()
        except Exception:
            pass
        status, count = self._backup_summary()

        self["detail_heading"].setText("SICHERUNGEN")
        self["detail_provider"].setText("Auto")
        self["detail_name"].setText("7-Tage-Verlauf")
        self["detail_state"].setText("AKTIV")
        self["detail_labels"].setText(
            "Automatik:\n\nVerlauf:\n\nLetzte Sicherung:\n\nSpeicherort:"
        )
        self["detail_values"].setText(
            "Täglich beim ersten Pluginstart\n\n"
            "%s\n\n%s\n\n%s"
            % (
                count,
                status,
                AUTO_BACKUP_DIR,
            )
        )
        self._set_fg("detail_provider", "#23D7F2")
        self._set_fg("detail_state", "#37D67A")
        self["detail_hint"].setText(
            "OK öffnet Sicherung & Export · GELB exportiert manuell"
        )


    # MEDIAPLUGINS2026_ICONALIGN_PROVIDERICONS1
    def _providerIconPath(self, provider):
        provider = str(provider or "").strip().lower()
        if provider == "emby":
            return "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/skin/icons/provider_emby.png"
        if provider == "plex":
            return "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/skin/icons/provider_plex.png"
        return ""

    def _providerIconPixmap(self, provider):
        provider = str(provider or "").strip().lower()
        if provider in self._provider_icon_cache:
            return self._provider_icon_cache.get(provider)
        path = self._providerIconPath(provider)
        pix = None
        if path and os.path.isfile(path):
            try:
                pix = LoadPixmap(path=path)
            except Exception:
                pix = None
        self._provider_icon_cache[provider] = pix
        return pix

    def _setProviderCardIcon(self, slot, provider):
        try:
            widget = self["card%d_icon" % slot]
        except Exception:
            return
        pix = self._providerIconPixmap(provider)
        if pix is None:
            try:
                widget.hide()
            except Exception:
                pass
            return
        try:
            widget.instance.setPixmap(pix)
            widget.show()
        except Exception:
            try:
                widget.hide()
            except Exception:
                pass

    def _setDetailProviderIcon(self, provider):
        try:
            widget = self["detail_provider_icon"]
        except Exception:
            return
        pix = self._providerIconPixmap(provider)
        if pix is None:
            try:
                widget.hide()
            except Exception:
                pass
            return
        try:
            widget.instance.setPixmap(pix)
            widget.show()
        except Exception:
            try:
                widget.hide()
            except Exception:
                pass

    def _providerIconLayoutReady(self):
        if self._provider_icon_layout_done:
            return
        try:
            for slot in range(self.VISIBLE_CARDS):
                provider_widget = self["card%d_provider" % slot].instance
                icon_widget = self["card%d_icon" % slot].instance
                p = provider_widget.position()
                s = provider_widget.size()

                # Icon nimmt den bisherigen linken Provider-Anfang ein.
                icon_widget.move(ePoint(p.x() + 1, p.y() + 2))
                try:
                    icon_widget.resize(eSize(26, 26))
                except Exception:
                    pass

                # Gut sichtbarer Provider-Marker mit 7 px Abstand zum Namen.
                provider_widget.move(ePoint(p.x() + 34, p.y()))
                try:
                    provider_widget.resize(eSize(max(60, s.width() - 34), s.height()))
                except Exception:
                    pass

            detail = self["detail_provider"].instance
            detail_icon = self["detail_provider_icon"].instance
            dp = detail.position()
            ds = detail.size()
            detail_icon.move(ePoint(dp.x() + 1, dp.y() + 3))
            try:
                detail_icon.resize(eSize(24, 24))
            except Exception:
                pass
            detail.move(ePoint(dp.x() + 32, dp.y()))
            try:
                detail.resize(eSize(max(80, ds.width() - 32), ds.height()))
            except Exception:
                pass

            # Backup-Icon: kleiner, exakt vertikal in der Karte zentriert
            # und mit sauberem Abstand vor dem Titel.
            bg = self["backup_bg"].instance
            title = self["backup_title"].instance
            icon = self["backup_icon"].instance
            bp = bg.position()
            bs = bg.size()
            tp = title.position()

            icon_size = 32
            icon_x = max(bp.x() + 42, tp.x() - 42)
            icon_y = bp.y() + max(0, (bs.height() - icon_size) // 2)
            icon.move(ePoint(icon_x, icon_y))
            try:
                icon.resize(eSize(icon_size, icon_size))
            except Exception:
                pass

            self._provider_icon_layout_done = True
        except Exception as exc:
            try:
                log.warning("Provider-/Backup-Icon-Layout fehlgeschlagen: %s", exc)
            except Exception:
                pass
    def refreshList(self):
        self._servers = list(config_store.get_servers() or [])
        if self._servers:
            self._selected_server_index = max(
                0, min(self._selected_server_index, len(self._servers) - 1)
            )
        else:
            self._selected_server_index = 0
            self._server_window_start = 0
        self._keep_selected_visible()
        self._render_all()

    def _keep_selected_visible(self):
        if not self._servers:
            self._server_window_start = 0
            return
        if self._selected_server_index < self._server_window_start:
            self._server_window_start = self._selected_server_index
        if self._selected_server_index >= self._server_window_start + self.VISIBLE_CARDS:
            self._server_window_start = (
                self._selected_server_index - self.VISIBLE_CARDS + 1
            )
        max_start = max(0, len(self._servers) - self.VISIBLE_CARDS)
        self._server_window_start = max(
            0, min(self._server_window_start, max_start)
        )

    def _render_all(self):
        self._render_cards()
        self._move_update_card()
        self._render_details()
        self._render_update_focus()
        self._move_backup_card()
        self._render_backup_card()

    def _render_cards(self):
        total = len(self._servers)
        self["left_counter"].setText(
            "%d Server" % total if total != 1 else "1 Server"
        )

        if not total:
            for slot in range(self.VISIBLE_CARDS):
                self._hide_card(slot)
            # Erstes Kartenset als Empty-State wiederverwenden.
            self._show_card(0)
            self["card0_focus"].setText("▶" if self._focus_zone == "servers" else "")
            self["card0_provider"].setText("+")
            self._setProviderCardIcon(0, "")
            self["card0_title"].setText("Noch kein Medienserver")
            self["card0_url"].setText("GRÜN drücken, um einen Server hinzuzufügen")
            self["card0_state"].setText("")
            self._set_fg("card0_provider", _CYAN)
            self._set_bg(
                "card0_bg",
                _CARD_SELECTED if self._focus_zone == "servers" else _CARD_NORMAL,
            )
            self["scroll_hint"].setText("")
            return

        for slot in range(self.VISIBLE_CARDS):
            idx = self._server_window_start + slot
            if idx >= total:
                self._hide_card(slot)
                continue

            self._show_card(slot)
            server = self._servers[idx]
            provider = self._provider(server)
            color = _PROVIDER_COLORS.get(provider, "#8FA4B8")
            self._setProviderCardIcon(slot, provider)
            selected = (
                self._focus_zone == "servers"
                and idx == self._selected_server_index
            )

            self["card%d_focus" % slot].setText("▶" if selected else "")
            self["card%d_provider" % slot].setText(
                _PROVIDER_NAMES.get(provider, provider.capitalize() or "Server")
            )
            self["card%d_title" % slot].setText(
                str(getattr(server, "name", "") or "Medienserver")
            )
            self["card%d_url" % slot].setText(self._short_url(self._server_url(server), 46))
            self["card%d_state" % slot].setText("KONFIGURIERT")
            self._set_fg("card%d_provider" % slot, color)
            self._set_fg("card%d_state" % slot, color)
            bg = _CARD_SELECTED if selected else _CARD_NORMAL
            self._set_bg("card%d_bg" % slot, bg)
            self._set_bg("card%d_focus" % slot, bg)
            self._set_bg("card%d_provider" % slot, bg)
            self._set_bg("card%d_title" % slot, bg)
            self._set_bg("card%d_url" % slot, bg)
            self._set_bg("card%d_state" % slot, bg)

        if total > self.VISIBLE_CARDS:
            first = self._server_window_start + 1
            last = min(total, self._server_window_start + self.VISIBLE_CARDS)
            self["scroll_hint"].setText(
                "Server %d–%d von %d   ·   ↓ bis Update" % (first, last, total)
            )
        else:
            self["scroll_hint"].setText("↓ Nach Updates suchen")

    def _selected_server(self):
        if not self._servers:
            return None
        idx = max(0, min(self._selected_server_index, len(self._servers) - 1))
        return self._servers[idx]

    def _render_update_details(self):
        """Right panel content while 'Nach Updates suchen' is selected."""
        try:
            from .UpdateScreen import _load_state, _timestamp_text
            state = _load_state()
            last_checked = _timestamp_text(state.get("last_checked_ts"))
            try:
                checked_build = int(state.get("last_checked_build") or 0)
            except Exception:
                checked_build = 0
        except Exception:
            state = {}
            last_checked = "Noch nie"
            checked_build = 0

        if checked_build <= 0:
            status = "Noch nicht geprüft"
            state_title = "BEREIT"
            state_color = _CYAN
        elif checked_build > int(PLUGIN_UPDATE_BUILD):
            status = "Update verfügbar"
            state_title = "UPDATE"
            state_color = "#F5B82E"
        else:
            status = "Deine Version ist aktuell"
            state_title = "AKTUELL"
            state_color = "#37D67A"

        self["detail_heading"].setText("SOFTWARE-UPDATE")
        self["detail_provider"].setText("Media Plugins")
        self["detail_name"].setText("2026")
        self["detail_state"].setText(state_title)
        self["detail_labels"].setText(
            "Installiert:\n\nKanal:\n\nQuelle:\n\nLetzte Prüfung:\n\nStatus:"
        )
        self["detail_values"].setText(
            "%s\n\n%s\n\nMediaPlugins2026-Updates\n\n%s\n\n%s"
            % (
                PLUGIN_VERSION,
                str(PLUGIN_UPDATE_CHANNEL or "stable").lower(),
                last_checked,
                status,
            )
        )
        # Kein doppelter Update-Hinweis: rechts reicht "OK Nach Updates suchen".
        self["scroll_hint"].setText("")
        self._set_fg("detail_provider", _CYAN)
        self._set_fg("detail_name", _CYAN)
        self._set_fg("detail_state", state_color)
        self["detail_hint"].setText("OK   Nach Updates suchen")

    def _render_details(self):
        try:
            self["detail_provider_icon"].hide()
        except Exception:
            pass
        if self._focus_zone == "backup":
            self._render_backup_details()
            return
        if self._focus_zone == "update":
            self._render_update_details()
            return

        self["detail_heading"].setText("AUSGEWÄHLTER SERVER")
        self._set_fg("detail_name", _TEXT)

        server = self._selected_server()
        if server is None:
            self["detail_provider"].setText("—")
            self["detail_name"].setText("Kein Server ausgewählt")
            self["detail_state"].setText("")
            self["detail_labels"].setText(
                "Status:\n\nHinweis:"
            )
            self["detail_values"].setText(
                "Noch kein Server konfiguriert\n\n"
                "Mit GRÜN einen Medienserver hinzufügen."
            )
            self._set_fg("detail_provider", _MUTED)
            self["detail_hint"].setText("GRÜN fügt einen Medienserver hinzu")
            return

        provider = self._provider(server)
        self._setDetailProviderIcon(provider)
        color = _PROVIDER_COLORS.get(provider, "#8FA4B8")
        provider_name = _PROVIDER_NAMES.get(
            provider, provider.capitalize() or "Server"
        )
        username = str(getattr(server, "username", "") or "").strip()
        token = str(getattr(server, "token", "") or "").strip()
        password = str(getattr(server, "password", "") or "").strip()
        imported = str(getattr(server, "imported_from", "") or "").strip()

        auth = "Gespeichert" if (username or token or password) else "Nicht hinterlegt"
        if provider == "emby":
            source = "EmbyFlowE2 Plugin"
        elif provider == "plex":
            source = "Plex2026 Plugin"
        elif provider == "jellyfin":
            source = "Jellyfin Plugin"
        else:
            source = "Media Plugins 2026"

        self["detail_provider"].setText(provider_name)
        self["detail_name"].setText(
            str(getattr(server, "name", "") or "Medienserver")
        )
        self["detail_state"].setText("KONFIGURIERT")
        self["detail_labels"].setText(
            "Typ:\n\nURL:\n\nAnmeldung:\n\nQuelle:"
        )
        self["detail_values"].setText(
            "%s\n\n%s\n\n%s\n\n%s"
            % (
                provider_name,
                self._short_url(self._server_url(server), 62),
                auth,
                source,
            )
        )
        self._set_fg("detail_provider", color)
        self._set_fg("detail_name", _TEXT)
        self._set_fg("detail_state", color)
        self["detail_hint"].setText(
            "ROT entfernt den ausgewählten Server"
        )

    def _render_update_focus(self):
        selected = self._focus_zone == "update"
        bg = _CARD_SELECTED if selected else _CARD_NORMAL
        self["update_focus"].setText("▶" if selected else "")
        for name in (
            "update_bg",
            "update_focus",
            "update_icon",
            "update_title",
            "update_subtitle",
            "update_version",
        ):
            self._set_bg(name, bg)

    def keyUp(self):
        if self._focus_zone == "backup":
            self._focus_zone = "update"
            self._render_all()
            return
        if self._focus_zone == "update":
            self._focus_zone = "servers"
            if self._servers:
                self._selected_server_index = len(self._servers) - 1
                self._keep_selected_visible()
            self._render_all()
            return
        if self._servers and self._selected_server_index > 0:
            self._selected_server_index -= 1
            self._keep_selected_visible()
            self._render_all()

    def keyDown(self):
        if self._focus_zone == "update":
            self._focus_zone = "backup"
            self._render_all()
            return
        if self._servers and self._selected_server_index < len(self._servers) - 1:
            self._selected_server_index += 1
            self._keep_selected_visible()
            self._render_all()
            return
        self._focus_zone = "update"
        self._render_all()

    def keyLeft(self):
        return

    def keyRight(self):
        return

    def keyOk(self):
        if self._focus_zone == "backup":
            from .BackupScreen import MediaPluginsBackupScreen
            self.session.openWithCallback(
                lambda *args: self.refreshList(),
                MediaPluginsBackupScreen,
            )
            return
        if self._focus_zone == "update":
            from .UpdateScreen import MediaPluginsUpdateScreen
            self.session.openWithCallback(
                lambda *args: self._render_all(),
                MediaPluginsUpdateScreen,
            )
            return
        if not self._servers:
            self.keyAddServer()

    def keyAddServer(self):
        self.session.openWithCallback(
            self._onProtocolChosen,
            ChoiceBox,
            title="Medienserver-Typ wählen",
            list=[
                ("Emby hinzufügen", "emby"),
                ("Jellyfin hinzufügen", "jellyfin"),
                ("Plex hinzufügen", "plex"),
            ],
        )

    def _onProtocolChosen(self, result=None):
        if not result:
            return
        protocol = result[1]
        from .ServerConfig import ServerConfigScreen
        self.session.openWithCallback(
            lambda *args: self.refreshList(),
            ServerConfigScreen,
            protocol=protocol,
        )

    def keyRemoveServer(self):
        server = self._selected_server()
        if server is None:
            self.session.open(
                MessageBox,
                "Kein Server zum Entfernen ausgewählt.",
                MessageBox.TYPE_INFO,
                timeout=4,
            )
            return
        self.session.openWithCallback(
            lambda confirmed: self._doRemove(
                confirmed, str(getattr(server, "name", "") or "")
            ),
            MessageBox,
            "Server '%s' wirklich entfernen?"
            % str(getattr(server, "name", "") or "Medienserver"),
            MessageBox.TYPE_YESNO,
        )

    def _doRemove(self, confirmed, name):
        if confirmed:
            config_store.remove_server(name)
            self.refreshList()

    def keyExport(self):
        # MEDIAPLUGINS2026_AUTOBACKUP1_SETTINGS
        from .BackupScreen import MediaPluginsBackupScreen
        self.session.openWithCallback(
            lambda *args: self.refreshList(),
            MediaPluginsBackupScreen,
        )

    def keyImport(self):
        if not os.path.isfile(BACKUP_PATH):
            self.session.open(
                MessageBox,
                "Keine Backup-Datei gefunden:\n%s" % BACKUP_PATH,
                MessageBox.TYPE_ERROR,
                timeout=8,
            )
            return
        self.session.openWithCallback(
            self._doImport,
            MessageBox,
            "Konfiguration aus\n%s\nimportieren?\n\n"
            "Vorhandene Server werden ersetzt." % BACKUP_PATH,
            MessageBox.TYPE_YESNO,
        )

    def _doImport(self, confirmed):
        if not confirmed:
            return
        try:
            servers, favorites = config_store.import_backup(BACKUP_PATH)
            self._selected_server_index = 0
            self.refreshList()
            self.session.open(
                MessageBox,
                "Import erfolgreich.\n%d Server und %d Favoriten übernommen."
                % (servers, favorites),
                MessageBox.TYPE_INFO,
                timeout=8,
            )
        except Exception as e:
            self.session.open(
                MessageBox,
                "Import fehlgeschlagen:\n%s" % e,
                MessageBox.TYPE_ERROR,
                timeout=10,
            )

    def keyCancel(self):
        self.close()
