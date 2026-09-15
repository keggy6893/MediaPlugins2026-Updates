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

MARKER = "# MEDIAPLUGINS2026_ICONALIGN_PROVIDERICONS1"
REQUIRED = "# MEDIAPLUGINS2026_BACKUPCARD_UI1"

BACKUP_ICON_REL = "skin/icons/backup_database.png"
EMBY_ICON_REL = "skin/icons/provider_emby.png"
PLEX_ICON_REL = "skin/icons/provider_plex.png"

BACKUP_ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAACgAAAAoCAYAAACM/rhtAAAApElEQVR42u2Vyw2AMAxDmypnluDE/sNwYgkWgAWQ2rj5SMjvHtdtErc1QggJRdDC/bwfa811bBJmEDHkYbhXmZvVFVQAaReiJ7NiiCGr4a8z1FMsYlQ0c4sRelQ8eOkqKpaVgxp5+7QWV/IPg5U/CXOQOcgcZA4yB5mDQS3O2tLReYqKrObgbL2stNLyyqiOVM/b6JJStRizr7+0CBbD2UtHiBcvyiZ2H2vUHT0AAAAASUVORK5CYII="
EMBY_ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAACgAAAAoCAYAAACM/rhtAAAA2klEQVR42u2Y0Q3DIAxEY4tpskB2ywDZLQt0nfa3ipJS4zvLlrhfpOPpAINZlqkpm7bX/kb6CRPsXA+3vzJTQ6QpSLDvxH6N0QEtk3tBJWKfefanMFJDekgEmMdTIsFG5lD0IbDo6nvnpVaTJ8hR0J6/MpcMIWXsKyQoHBCdJg0QlSYVEAEaAuhZ9lDAkTRbNKD1RtLMcGEJeu7xlhWMvsSo10/LCkZJkPFm7AL+U7PO9ZBRuJ5/+hd13Z6kTFdXpi8u8bNQ5m/GUiq8hwpSqJ8gGKUpZes55dEHu8+15/xmDjsAAAAASUVORK5CYII="
PLEX_ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAACgAAAAoCAYAAACM/rhtAAAApElEQVR42u3Y0Q2AMAgE0PZ+3cU5HNk53MVvHUFK7ygm3DfE16Qm0NYqlUpFmm4tvM/9+arZjquzgbAWWj5uOYQMuAqJ0YZoJDxNkUh4G6OQmGmOQGL2hGokGPdEiQTrb1MhaUAVkgpUIOlANlICZCJlQNb0g8w4CZA9NyIzjgpUTdzIjKMA1bsKMuOmgFFbHjLjXMDo/RiZcUPAVS8LlUrl73kBQflsNoQa9c8AAAAASUVORK5CYII="

PROVIDER_SKIN = r"""
        <!-- MEDIAPLUGINS2026_ICONALIGN_PROVIDERICONS1 -->
        <widget zPosition="30" name="card0_icon" position="0,0" size="30,30"
                alphatest="on" transparent="1" />
        <widget zPosition="30" name="card1_icon" position="0,0" size="30,30"
                alphatest="on" transparent="1" />
        <widget zPosition="30" name="card2_icon" position="0,0" size="30,30"
                alphatest="on" transparent="1" />
        <widget zPosition="30" name="card3_icon" position="0,0" size="30,30"
                alphatest="on" transparent="1" />
        <widget zPosition="30" name="detail_provider_icon" position="0,0" size="30,30"
                alphatest="on" transparent="1" />
"""

PROVIDER_INIT = r"""        # MEDIAPLUGINS2026_ICONALIGN_PROVIDERICONS1
        for _provider_icon_slot in range(self.VISIBLE_CARDS):
            self["card%d_icon" % _provider_icon_slot] = Pixmap()
        self["detail_provider_icon"] = Pixmap()
        self._provider_icon_layout_done = False
        self._provider_icon_cache = {}

"""

PROVIDER_HELPERS = r"""
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
                icon_widget.move(ePoint(p.x(), p.y() + 1))
                try:
                    icon_widget.resize(eSize(28, 28))
                except Exception:
                    pass

                # Providername direkt rechts daneben; Titel bleibt unberührt.
                provider_widget.move(ePoint(p.x() + 34, p.y()))
                try:
                    provider_widget.resize(eSize(max(50, s.width() - 34), s.height()))
                except Exception:
                    pass

            detail = self["detail_provider"].instance
            detail_icon = self["detail_provider_icon"].instance
            dp = detail.position()
            ds = detail.size()
            detail_icon.move(ePoint(dp.x(), dp.y() + 2))
            try:
                detail_icon.resize(eSize(30, 30))
            except Exception:
                pass
            detail.move(ePoint(dp.x() + 38, dp.y()))
            try:
                detail.resize(eSize(max(70, ds.width() - 38), ds.height()))
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
"""

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

def write_icon(path, b64data):
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "wb") as handle:
        handle.write(base64.b64decode(b64data))
    try:
        os.chmod(path, 0o644)
    except Exception:
        pass

def insert_before(text, candidates, block, label):
    for anchor in candidates:
        if anchor in text:
            return text.replace(anchor, block + "\n" + anchor, 1)
    raise RuntimeError("%s: kein Anker gefunden" % label)

def patch_settings(text):
    if MARKER in text:
        return text
    if REQUIRED not in text:
        raise RuntimeError("BACKUPCARD_UI1 fehlt; Abbruch ohne Aenderung")

    # LoadPixmap wird fuer dynamische Providerlogos gebraucht.
    if "from Tools.LoadPixmap import LoadPixmap\n" not in text:
        anchors = (
            "from Components.Pixmap import Pixmap\n",
            "from Components.Label import Label\n",
        )
        done = False
        for anchor in anchors:
            if anchor in text:
                text = text.replace(
                    anchor,
                    anchor + "from Tools.LoadPixmap import LoadPixmap\n",
                    1,
                )
                done = True
                break
        if not done:
            raise RuntimeError("Import-Anker fuer LoadPixmap fehlt")

    # Zusätzliche Pixmap-Widgets in den bestehenden Skin.
    text = insert_before(
        text,
        (
            '        <!-- footer keys -->',
            '        <!-- bottom keys -->',
            '        <widget zPosition="20" name="key_green"',
            '        <widget name="key_green"',
        ),
        PROVIDER_SKIN,
        "Provider-Icon-Skin",
    )

    # Komponenten initialisieren.
    text = insert_before(
        text,
        (
            '        self["key_green"] = Label(',
            '        self["key_red"] = Label(',
        ),
        PROVIDER_INIT,
        "Provider-Icon-Init",
    )

    # Helper vor refreshList.
    anchor = "    def refreshList(self):\n"
    if anchor not in text:
        raise RuntimeError("refreshList Anker fehlt")
    text = text.replace(anchor, PROVIDER_HELPERS + anchor, 1)

    # Layout nach dem Skin-Aufbau einmal ausrichten.
    layout_anchor = "        self.onLayoutFinish.append(self.refreshList)\n"
    if layout_anchor not in text:
        raise RuntimeError("onLayoutFinish Anker fehlt")
    text = text.replace(
        layout_anchor,
        layout_anchor + "        self.onLayoutFinish.append(self._providerIconLayoutReady)\n",
        1,
    )

    # Hide/show helpers sollen die neuen Pixmaps mitnehmen.
    text = text.replace(
        '("bg", "focus", "provider", "title", "url", "state")',
        '("bg", "focus", "icon", "provider", "title", "url", "state")',
    )

    # Bei leeren Karten/Slots Icon ausblenden.
    empty_anchor = '            self["card0_provider"].setText("+")\n'
    if empty_anchor in text:
        text = text.replace(
            empty_anchor,
            empty_anchor + '            self._setProviderCardIcon(0, "")\n',
            1,
        )

    # Im normalen Server-Render das passende Emby/Plex-Icon setzen.
    provider_anchor = (
        '            provider = self._provider(server)\n'
        '            color = _PROVIDER_COLORS.get(provider, "#8FA4B8")\n'
    )
    if provider_anchor in text:
        text = text.replace(
            provider_anchor,
            provider_anchor + "            self._setProviderCardIcon(slot, provider)\n",
            1,
        )
    else:
        m = re.search(
            r'(?m)^            provider = self\._provider\(server\)\n',
            text,
        )
        if not m:
            raise RuntimeError("_render_cards Provider-Anker fehlt")
        text = text[:m.end()] + "            self._setProviderCardIcon(slot, provider)\n" + text[m.end():]

    details = "    def _render_details(self):\n"
    if details not in text:
        raise RuntimeError("_render_details fehlt")
    text = text.replace(
        details,
        details
        + '        try:\n'
        + '            self["detail_provider_icon"].hide()\n'
        + '        except Exception:\n'
        + '            pass\n',
        1,
    )

    details_pattern = re.compile(
        r"(?ms)(^    def _render_details\(self\):\n.*?)(?=^    def |\Z)"
    )
    details_match = details_pattern.search(text)
    if not details_match:
        raise RuntimeError("_render_details Block nicht gefunden")

    details_block = details_match.group(1)
    detail_provider_anchor = '        provider = self._provider(server)\n'
    if detail_provider_anchor not in details_block:
        raise RuntimeError("Detail-Provider-Anker in _render_details fehlt")

    details_new = details_block.replace(
        detail_provider_anchor,
        detail_provider_anchor + "        self._setDetailProviderIcon(provider)\n",
        1,
    )
    text = (
        text[:details_match.start(1)]
        + details_new
        + text[details_match.end(1):]
    )

    backup_details = "    def _render_backup_details(self):\n"
    if backup_details in text:
        text = text.replace(
            backup_details,
            backup_details
            + '        try:\n'
            + '            self["detail_provider_icon"].hide()\n'
            + '        except Exception:\n'
            + '            pass\n',
            1,
        )

    render_backup_anchor = "        self._move_backup_card()\n        self._render_backup_card()\n"
    if render_backup_anchor in text:
        text = text.replace(
            render_backup_anchor,
            "        self._move_backup_card()\n"
            "        self._provider_icon_layout_done = False\n"
            "        self._providerIconLayoutReady()\n"
            "        self._render_backup_card()\n",
            1,
        )

    return text

def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DEFAULT
    settings_path = os.path.join(root, SETTINGS_REL)
    if not os.path.isfile(settings_path):
        raise SystemExit("Settings.py nicht gefunden: %s" % settings_path)

    original = read(settings_path)
    patched = patch_settings(original)

    compile(patched, settings_path, "exec")
    bak = backup(settings_path, ".before_iconalign_providericons1")
    write(settings_path, patched)

    write_icon(os.path.join(root, BACKUP_ICON_REL), BACKUP_ICON_B64)
    write_icon(os.path.join(root, EMBY_ICON_REL), EMBY_ICON_B64)
    write_icon(os.path.join(root, PLEX_ICON_REL), PLEX_ICON_B64)

    verify = read(settings_path)
    compile(verify, settings_path, "exec")

    required = [
        MARKER,
        'self["card%d_icon" % _provider_icon_slot] = Pixmap()',
        'self["detail_provider_icon"] = Pixmap()',
        "_setProviderCardIcon(slot, provider)",
        "_setDetailProviderIcon(provider)",
        "icon_size = 32",
        "provider_emby.png",
        "provider_plex.png",
    ]
    missing = [x for x in required if x not in verify]
    if missing:
        raise RuntimeError("ICONALIGN_PROVIDERICONS1 Verifikation fehlgeschlagen: %r" % missing)

    for rel in (BACKUP_ICON_REL, EMBY_ICON_REL, PLEX_ICON_REL):
        p = os.path.join(root, rel)
        if not os.path.isfile(p) or os.path.getsize(p) < 100:
            raise RuntimeError("Icon fehlt/ungueltig: %s" % p)

    print("OK MEDIAPLUGINS2026_ICONALIGN_PROVIDERICONS1")
    print("- Backup-Icon: 32px, exakt in Sicherungen-Karte zentriert")
    print("- Emby-Icon: gruenes Providerlogo in allen Serverkarten")
    print("- Plex-Icon: gelbes Providerlogo in allen Serverkarten")
    print("- Emby/Plex-Icon auch im rechten Server-Detailbereich")
    print("- Update-/Backup-Detailansichten blenden Providerlogos aus")
    print("- Navigation/AutoBackup/Export/Import unveraendert")
    print("Settings Backup: %s" % bak)

if __name__ == "__main__":
    main()
