# -*- coding: utf-8 -*-
from __future__ import print_function

import base64
import io
import os
import re
import shutil
import sys

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
SETTINGS_REL = "screens/Settings.py"
BACKUP_SCREEN_REL = "screens/BackupScreen.py"
BACKUP_HELPER_REL = "utils/config_backup.py"
ICON_REL = "skin/icons/backup_database.png"

MARKER = "# MEDIAPLUGINS2026_BACKUPCARD_UI1"
REQUIRED_AUTOBACKUP = "# MEDIAPLUGINS2026_AUTOBACKUP1_SETTINGS"

ICON_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABVklEQVR4nO2aQRKDIBAESSrnfMJT"
    "/v8YTvmEHzAnqywFww67sMr0WZhlCsGxNgRCCCGEjMqjhcgU5wUd+/28TWtUn7xmsaVomqIy"
    "UYtF56g1Ax7cc9E5EDMgAySL19iulnri4s6KsT6wLOoQFZwSbbnoHDV1FRe/F/Gw8D1IjU9k4"
    "qswxXn5V3uRAXfmhQ5cnfXwKtTsUNiAlLiXW0BCtQFbrG4J6XeA5HnIAIlIywMUMRveAVuxK2"
    "cBlVegtRmaZ43qGRBCujjP/wPUDUjh4arMMfyHEA3oXUBvaAAyyGs6LEl/e4bfAUyDmuJMg0y"
    "DR5gGjWEarIRp0HLyFQ9XZY7hP4RoADKIWeBGMAtoijMLMAscuWUWmOK8eMwCSB3qHSI9swDS"
    "IdKkR8g6CzTpEToTk4pq0KVLrES8ppgeeuwU1RD2cgsgsFtca6IzPP8RIoQQQgbmB8zYEKU04"
    "6pSAAAAAElFTkSuQmCC"
)

SKIN_WIDGETS = r'''
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
'''

INIT_WIDGETS = r'''        # MEDIAPLUGINS2026_BACKUPCARD_UI1
        self["backup_bg"] = Label("")
        self["backup_focus"] = Label("")
        self["backup_icon"] = Pixmap()
        self["backup_title"] = Label("Sicherungen")
        self["backup_subtitle"] = Label("Automatisch · täglich · 7 Tage")
        self["backup_status"] = Label("")
        self["backup_count"] = Label("")
        self["backup_chevron"] = Label("›")

'''

HELPER_METHODS = r'''
    # MEDIAPLUGINS2026_BACKUPCARD_UI1
    def _backupUiLayoutReady(self):
        self._move_backup_card()
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


def _add_import(text, anchor, addition):
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError("Import-Anker fehlt: %s" % anchor.strip())
    return text.replace(anchor, anchor + addition, 1)


def _insert_before_first(text, candidates, block, label):
    for anchor in candidates:
        if anchor in text:
            return text.replace(anchor, block + "\n" + anchor, 1)
    raise RuntimeError("%s: kein passender Anker gefunden" % label)


def _inject_method_start(text, method_name, body, label):
    pattern = re.compile(r"(?m)^    def %s\(self\):\n" % re.escape(method_name))
    match = pattern.search(text)
    if not match:
        raise RuntimeError("%s: Methode %s nicht gefunden" % (label, method_name))
    insert_at = match.end()
    return text[:insert_at] + body + text[insert_at:]


def patch_settings(text):
    if MARKER in text:
        return text

    if REQUIRED_AUTOBACKUP not in text:
        raise RuntimeError(
            "AUTOBACKUP1 fehlt. Bitte zuerst MediaPlugins2026_AUTOBACKUP1 installieren."
        )

    text = _add_import(text, "import os\n", "import time\n")
    text = _add_import(
        text,
        "from Components.Label import Label\n",
        "from Components.Pixmap import Pixmap\n",
    )

    if "from enigma import ePoint, eSize\n" not in text:
        if "from enigma import ePoint\n" in text:
            text = text.replace(
                "from enigma import ePoint\n",
                "from enigma import ePoint, eSize\n",
                1,
            )
        else:
            raise RuntimeError("ePoint-Import nicht gefunden")

    helper_import = (
        "from ..utils.config_backup import "
        "AUTO_BACKUP_DIR, AUTO_BACKUP_KEEP, list_daily_backups\n"
    )
    if helper_import not in text:
        # Settings.py hat je nach r19-Build unterschiedliche version.py-Imports.
        # Der config_store-Import ist in allen aktuellen Builds vorhanden und
        # ist deshalb der stabilere Anker.
        config_import = re.search(
            r"(?m)^from \.\.config import .*?$",
            text,
        )
        if config_import:
            insert_at = config_import.end()
            text = text[:insert_at] + "\n" + helper_import.rstrip("\n") + text[insert_at:]
        else:
            # Letzter robuster Fallback: vor der ersten Marker-/Klassenzeile
            # in den Importbereich einsetzen.
            fallback = re.search(
                r"(?m)^(# MEDIAPLUGINS2026_|# INFUSEMEDIA2026_|class Settings\b)",
                text,
            )
            if not fallback:
                raise RuntimeError("Kein stabiler Import-Anker in Settings.py gefunden")
            text = text[:fallback.start()] + helper_import + "\n" + text[fallback.start():]

    text = _insert_before_first(
        text,
        (
            '        <!-- footer keys -->',
            '        <!-- bottom keys -->',
            '        <widget zPosition="20" name="key_green"',
            '        <widget name="key_green"',
        ),
        SKIN_WIDGETS,
        "Backup-Skin",
    )

    text = _insert_before_first(
        text,
        (
            '        self["key_green"] = Label(',
            '        self["key_red"] = Label(',
        ),
        INIT_WIDGETS,
        "Backup-Widget-Initialisierung",
    )

    layout_anchor = "        self.onLayoutFinish.append(self.refreshList)\n"
    if layout_anchor not in text:
        raise RuntimeError("onLayoutFinish/refreshList Anker fehlt")
    text = text.replace(
        layout_anchor,
        layout_anchor + "        self.onLayoutFinish.append(self._backupUiLayoutReady)\n",
        1,
    )

    method_anchor = "    def refreshList(self):\n"
    if method_anchor not in text:
        raise RuntimeError("refreshList Anker fehlt")
    text = text.replace(method_anchor, HELPER_METHODS + method_anchor, 1)

    render_pattern = re.compile(
        r"(?ms)(^    def _render_all\(self\):\n.*?)(?=^    def )"
    )
    render_match = render_pattern.search(text)
    if not render_match:
        raise RuntimeError("_render_all nicht gefunden")
    render_block = render_match.group(1)
    if "self._render_backup_card()" not in render_block:
        insert_after = "        self._render_update_focus()\n"
        if insert_after not in render_block:
            raise RuntimeError("_render_all: _render_update_focus Anker fehlt")
        render_new = render_block.replace(
            insert_after,
            insert_after
            + "        self._move_backup_card()\n"
            + "        self._render_backup_card()\n",
            1,
        )
        text = text[:render_match.start(1)] + render_new + text[render_match.end(1):]

    details_pattern = re.compile(
        r"(?ms)(^    def _render_details\(self\):\n)(.*?)(?=^    def )"
    )
    details_match = details_pattern.search(text)
    if not details_match:
        raise RuntimeError("_render_details nicht gefunden")
    details_block = details_match.group(0)
    if 'self._focus_zone == "backup"' not in details_block:
        details_block = details_block.replace(
            "    def _render_details(self):\n",
            "    def _render_details(self):\n"
            '        if self._focus_zone == "backup":\n'
            "            self._render_backup_details()\n"
            "            return\n",
            1,
        )
        text = text[:details_match.start()] + details_block + text[details_match.end():]

    text = _inject_method_start(
        text,
        "keyUp",
        '        if self._focus_zone == "backup":\n'
        '            self._focus_zone = "update"\n'
        "            self._render_all()\n"
        "            return\n",
        "Backup Navigation HOCH",
    )

    down_pattern = re.compile(
        r'(?m)^        if self\._focus_zone == "update":\n'
        r'            return\n'
    )
    if down_pattern.search(text):
        text = down_pattern.sub(
            '        if self._focus_zone == "update":\n'
            '            self._focus_zone = "backup"\n'
            '            self._render_all()\n'
            '            return\n',
            text,
            count=1,
        )
    else:
        text = _inject_method_start(
            text,
            "keyDown",
            '        if self._focus_zone == "backup":\n'
            "            return\n"
            '        if self._focus_zone == "update":\n'
            '            self._focus_zone = "backup"\n'
            "            self._render_all()\n"
            "            return\n",
            "Backup Navigation RUNTER",
        )

    text = _inject_method_start(
        text,
        "keyOk",
        '        if self._focus_zone == "backup":\n'
        "            from .BackupScreen import MediaPluginsBackupScreen\n"
        "            self.session.openWithCallback(\n"
        "                lambda *args: self._render_all(),\n"
        "                MediaPluginsBackupScreen,\n"
        "            )\n"
        "            return\n",
        "Backup OK",
    )

    return text


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DEFAULT
    settings_path = os.path.join(root, SETTINGS_REL)
    backup_screen_path = os.path.join(root, BACKUP_SCREEN_REL)
    backup_helper_path = os.path.join(root, BACKUP_HELPER_REL)
    icon_path = os.path.join(root, ICON_REL)

    for path in (settings_path, backup_screen_path, backup_helper_path):
        if not os.path.isfile(path):
            raise SystemExit("Datei nicht gefunden: %s" % path)

    original = read(settings_path)
    patched = patch_settings(original)

    compile(patched, settings_path, "exec")

    settings_backup = backup(settings_path, ".before_backupcard_ui1")
    write(settings_path, patched)

    icon_dir = os.path.dirname(icon_path)
    if not os.path.isdir(icon_dir):
        os.makedirs(icon_dir)
    with open(icon_path, "wb") as handle:
        handle.write(base64.b64decode(ICON_B64))
    try:
        os.chmod(icon_path, 0o644)
    except Exception:
        pass

    verify = read(settings_path)
    compile(verify, settings_path, "exec")

    required = [
        MARKER,
        'self["backup_icon"] = Pixmap()',
        'Label("Sicherungen")',
        'self._focus_zone = "backup"',
        'self._render_backup_details()',
        "AUTO_BACKUP_KEEP",
        "list_daily_backups",
    ]
    missing = [item for item in required if item not in verify]
    if missing:
        raise RuntimeError("BACKUPCARD_UI1 Verifikation fehlgeschlagen: %r" % missing)

    if not os.path.isfile(icon_path) or os.path.getsize(icon_path) < 100:
        raise RuntimeError("Backup-Icon wurde nicht korrekt geschrieben")

    print("OK MEDIAPLUGINS2026_BACKUPCARD_UI1")
    print("- sichtbare Sicherungen-Karte direkt unter GitHub Update")
    print("- echtes Cyan Backup/Database-PNG-Icon")
    print("- Status rechts: letzte Sicherung + X / 7 vorhanden")
    print("- HOCH/RUNTER Navigation: Server -> Update -> Sicherungen")
    print("- OK auf Sicherungen oeffnet den bestehenden Backup-/Exportdialog")
    print("- rechte Detailspalte zeigt Automatik, Verlauf, letzte Sicherung und Pfad")
    print("- bestehende AutoBackup-Routine/7-Tage-Rotation bleibt unveraendert")
    print("Settings Backup: %s" % settings_backup)
    print("Icon:            %s" % icon_path)


if __name__ == "__main__":
    main()
