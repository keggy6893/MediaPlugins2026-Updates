# -*- coding: utf-8 -*-
from __future__ import print_function

import base64
import io
import os
import shutil
import sys

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
SETTINGS_REL = "screens/Settings.py"

MARKER = "# MEDIAPLUGINS2026_PROVIDERICON_POLISH1"
REQUIRED = "# MEDIAPLUGINS2026_ICONALIGN_PROVIDERICONS1"

EMBY_ICON_REL = "skin/icons/provider_emby.png"
PLEX_ICON_REL = "skin/icons/provider_plex.png"

EMBY_ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAuklEQVR42u1W2w2AIAwsF6dxAXZzAHZjAdfRX2JSOEqJmnCfpPSuL6jIwsLfEc/jGrkfPInznsJ0ASVxSaiduwh4Rlsj6LGlBFgjY++BddhbX9Yelg7v7fyaPazRxPO4WkKYLGB0vhkhNX9oqWdrqRG0/ASvR8jasJAJYMsiIrLNEOCWgd5xy3sK2sSYp4AVoUXd8oPRNGpRs/5g7XqGmMkeLKo9/wV4zb7V/vv7wCc2opk74etb8cLCDbEsj7eqBE7NAAAAAElFTkSuQmCC"
PLEX_ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAgklEQVR42u3WwQ2AIBQDUOjVXZzDkZ2DXTzDApLAb8m/tEcC6QtRoBTHcZJTVyd+793/xq+nVQaA1YmzohlMDjiFwO4CNQKRRUoEolunQoD5gBQIsP8xi4DiMGEQEgCDkAGiJyUyyyUA9o5AZjkFUN2OyCwPAdTvAmSWbwFOvYgcxxl/FkwmGJvLRgAAAABJRU5ErkJggg=="


def read(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def write_icon(path, data):
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "wb") as handle:
        handle.write(base64.b64decode(data))
    try:
        os.chmod(path, 0o644)
    except Exception:
        pass


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            "%s: erwartete genau 1 Fundstelle, gefunden %d" % (label, count)
        )
    return text.replace(old, new, 1)


def patch(text):
    if MARKER in text:
        return text
    if REQUIRED not in text:
        raise RuntimeError("ICONALIGN_PROVIDERICONS1 fehlt")

    text = text.replace(
        REQUIRED + "\n",
        REQUIRED + "\n" + MARKER + "\n",
        1,
    )

    text = replace_once(
        text,
        "icon_widget.move(ePoint(p.x(), p.y() + 1))\n"
        "                try:\n"
        "                    icon_widget.resize(eSize(28, 28))\n"
        "                except Exception:\n"
        "                    pass\n"
        "\n"
        "                # Providername direkt rechts daneben; Titel bleibt unberührt.\n"
        "                provider_widget.move(ePoint(p.x() + 34, p.y()))\n"
        "                try:\n"
        "                    provider_widget.resize(eSize(max(50, s.width() - 34), s.height()))",
        "icon_widget.move(ePoint(p.x() + 2, p.y() + 5))\n"
        "                try:\n"
        "                    icon_widget.resize(eSize(18, 18))\n"
        "                except Exception:\n"
        "                    pass\n"
        "\n"
        "                # Kleiner Provider-Marker, nicht wie ein zweites Logo.\n"
        "                provider_widget.move(ePoint(p.x() + 24, p.y()))\n"
        "                try:\n"
        "                    provider_widget.resize(eSize(max(60, s.width() - 24), s.height()))",
        "Serverkarten-Icon-Geometrie",
    )

    text = replace_once(
        text,
        "detail_icon.move(ePoint(dp.x(), dp.y() + 2))\n"
        "            try:\n"
        "                detail_icon.resize(eSize(30, 30))\n"
        "            except Exception:\n"
        "                pass\n"
        "            detail.move(ePoint(dp.x() + 38, dp.y()))\n"
        "            try:\n"
        "                detail.resize(eSize(max(70, ds.width() - 38), ds.height()))",
        "detail_icon.move(ePoint(dp.x() + 2, dp.y() + 5))\n"
        "            try:\n"
        "                detail_icon.resize(eSize(20, 20))\n"
        "            except Exception:\n"
        "                pass\n"
        "            detail.move(ePoint(dp.x() + 28, dp.y()))\n"
        "            try:\n"
        "                detail.resize(eSize(max(80, ds.width() - 28), ds.height()))",
        "Detail-Icon-Geometrie",
    )

    text = text.replace(
        'name="card0_icon" position="0,0" size="30,30"',
        'name="card0_icon" position="0,0" size="18,18"',
    )
    text = text.replace(
        'name="card1_icon" position="0,0" size="30,30"',
        'name="card1_icon" position="0,0" size="18,18"',
    )
    text = text.replace(
        'name="card2_icon" position="0,0" size="30,30"',
        'name="card2_icon" position="0,0" size="18,18"',
    )
    text = text.replace(
        'name="card3_icon" position="0,0" size="30,30"',
        'name="card3_icon" position="0,0" size="18,18"',
    )
    text = text.replace(
        'name="detail_provider_icon" position="0,0" size="30,30"',
        'name="detail_provider_icon" position="0,0" size="20,20"',
    )

    compile(text, "Settings.py", "exec")
    return text


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DEFAULT
    settings_path = os.path.join(root, SETTINGS_REL)

    if not os.path.isfile(settings_path):
        raise SystemExit("Settings.py nicht gefunden: %s" % settings_path)

    original = read(settings_path)
    patched = patch(original)
    compile(patched, settings_path, "exec")

    backup = settings_path + ".before_providericon_polish1"
    if not os.path.exists(backup):
        shutil.copy2(settings_path, backup)

    write(settings_path, patched)
    write_icon(os.path.join(root, EMBY_ICON_REL), EMBY_ICON_B64)
    write_icon(os.path.join(root, PLEX_ICON_REL), PLEX_ICON_B64)

    verify = read(settings_path)
    compile(verify, settings_path, "exec")

    required = [
        MARKER,
        "icon_widget.resize(eSize(18, 18))",
        "provider_widget.move(ePoint(p.x() + 24, p.y()))",
        "detail_icon.resize(eSize(20, 20))",
        "detail.move(ePoint(dp.x() + 28, dp.y()))",
    ]
    missing = [item for item in required if item not in verify]
    if missing:
        raise RuntimeError("PROVIDERICON_POLISH1 Verifikation fehlgeschlagen: %r" % missing)

    print("OK MEDIAPLUGINS2026_PROVIDERICON_POLISH1")
    print("- Emby/Plex Icons deutlich kleiner: 18 px in Serverkarten")
    print("- Providername sauber 24 px rechts vom Icon")
    print("- Detailbereich: 20 px Icon, 28 px Abstand")
    print("- kompaktere, ruhigere Emby/Plex-Icons geschrieben")
    print("- Backup-Icon und Sicherungslogik unveraendert")
    print("Settings Backup: %s" % backup)


if __name__ == "__main__":
    main()
