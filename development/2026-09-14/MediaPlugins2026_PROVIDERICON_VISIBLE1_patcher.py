# -*- coding: utf-8 -*-
from __future__ import print_function

import base64
import io
import os
import shutil
import sys

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
SETTINGS_REL = "screens/Settings.py"

MARKER = "# MEDIAPLUGINS2026_PROVIDERICON_VISIBLE1"
REQUIRED = "# MEDIAPLUGINS2026_PROVIDERICON_POLISH1"

EMBY_ICON_REL = "skin/icons/provider_emby.png"
PLEX_ICON_REL = "skin/icons/provider_plex.png"

EMBY_ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAA4klEQVR42u1Xyw1CMQxrLKZhAXZjgLcbC7AOnJAQ6sdOXLiQ6+tzbKdN09b+UYzL/fqo/B/OxLfzEVsJsGoVIuFS+7mGJRGq2hWwSiQcIBUMOOu5KlHPVcyYr+rMkFhhIGNthsjoGyp9oNqEpgTY2rNEqE1YUaQ48r4OzRxqaewEVCJgjt9OIqfd1/VKDHaoHjWhXg7sGDIYMa8ccPT9mer0KVBcYBNTl5GiQFE8EoTsCKYQnU1UUMHVOq/GOWokc0xEIyw4LGZV9zAjuwdGJNX3QmStdDUlq83OMn5tHvh5PAGkAL08FbPEZgAAAABJRU5ErkJggg=="
PLEX_ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAoElEQVR42u3XwRGAIAwEQHJfe7EOS7YOevGtDegYkgv3gaeD3k4MCq2tIR72dvE69/vvxu3oxgAg+nAPMgyYiUC2zFmE+z1W9QW8E6uqgZHJFQiMitkIRBqHiUC0e1kIytcss0LAAGSqQQFkEDRAFEEFRHoBynAaILMKTBWcrgDr7whleAjA3hdAGT4EqNoRmSrYVYEZ5wMowz8BM09GazyKYWwy33Yz7QAAAABJRU5ErkJggg=="


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
        raise RuntimeError("PROVIDERICON_POLISH1 fehlt")

    text = text.replace(
        REQUIRED + "\n",
        REQUIRED + "\n" + MARKER + "\n",
        1,
    )

    text = replace_once(
        text,
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
        "icon_widget.move(ePoint(p.x() + 1, p.y() + 2))\n"
        "                try:\n"
        "                    icon_widget.resize(eSize(26, 26))\n"
        "                except Exception:\n"
        "                    pass\n"
        "\n"
        "                # Gut sichtbarer Provider-Marker mit 7 px Abstand zum Namen.\n"
        "                provider_widget.move(ePoint(p.x() + 34, p.y()))\n"
        "                try:\n"
        "                    provider_widget.resize(eSize(max(60, s.width() - 34), s.height()))",
        "Serverkarten-Geometrie",
    )

    text = replace_once(
        text,
        "detail_icon.move(ePoint(dp.x() + 2, dp.y() + 5))\n"
        "            try:\n"
        "                detail_icon.resize(eSize(20, 20))\n"
        "            except Exception:\n"
        "                pass\n"
        "            detail.move(ePoint(dp.x() + 28, dp.y()))\n"
        "            try:\n"
        "                detail.resize(eSize(max(80, ds.width() - 28), ds.height()))",
        "detail_icon.move(ePoint(dp.x() + 1, dp.y() + 3))\n"
        "            try:\n"
        "                detail_icon.resize(eSize(24, 24))\n"
        "            except Exception:\n"
        "                pass\n"
        "            detail.move(ePoint(dp.x() + 32, dp.y()))\n"
        "            try:\n"
        "                detail.resize(eSize(max(80, ds.width() - 32), ds.height()))",
        "Detail-Geometrie",
    )

    for slot in range(4):
        text = text.replace(
            'name="card%d_icon" position="0,0" size="18,18"' % slot,
            'name="card%d_icon" position="0,0" size="26,26"' % slot,
        )
    text = text.replace(
        'name="detail_provider_icon" position="0,0" size="20,20"',
        'name="detail_provider_icon" position="0,0" size="24,24"',
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

    backup = settings_path + ".before_providericon_visible1"
    if not os.path.exists(backup):
        shutil.copy2(settings_path, backup)

    write(settings_path, patched)
    write_icon(os.path.join(root, EMBY_ICON_REL), EMBY_ICON_B64)
    write_icon(os.path.join(root, PLEX_ICON_REL), PLEX_ICON_B64)

    verify = read(settings_path)
    compile(verify, settings_path, "exec")

    required = [
        MARKER,
        "icon_widget.resize(eSize(26, 26))",
        "provider_widget.move(ePoint(p.x() + 34, p.y()))",
        "detail_icon.resize(eSize(24, 24))",
        "detail.move(ePoint(dp.x() + 32, dp.y()))",
    ]
    missing = [x for x in required if x not in verify]
    if missing:
        raise RuntimeError(
            "PROVIDERICON_VISIBLE1 Verifikation fehlgeschlagen: %r" % missing
        )

    print("OK MEDIAPLUGINS2026_PROVIDERICON_VISIBLE1")
    print("- Emby/Plex Serverkarten-Icons jetzt 26 px")
    print("- Icon-Grafiken selbst fuellen die Flaeche deutlich besser aus")
    print("- 7 px Abstand zwischen Icon und Providername")
    print("- rechter Detailbereich: 24 px")
    print("- Backup/Sicherungen/Export bleiben unveraendert")
    print("Settings Backup: %s" % backup)


if __name__ == "__main__":
    main()
