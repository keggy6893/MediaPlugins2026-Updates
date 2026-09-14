# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import re
import shutil
import sys

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/SearchScreen.py"
MARKER = "# INFUSEMEDIA2026_SEARCH_ZORDER1"
BACKUP_SUFFIX = ".before_search_zorder1"

TARGET_WIDGETS = ['search_title', 'legend_title', 'legend_emby', 'legend_jelly', 'legend_plex', 'availability_title', 'avail_emby_name', 'avail_jelly_name', 'avail_plex_name', 'actions_title', 'action_open', 'action_keyboard', 'action_favorite', 'action_filter']


def promote_widget(text, name):
    # Nur das Skin-Widget mit exakt diesem Namen anfassen.
    pattern = r'(<widget\s+name="' + re.escape(name) + r'"[^>]*)(/>)'
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise RuntimeError(
            "%s: erwartete genau 1 Widget, gefunden %d" % (name, len(matches))
        )

    match = matches[0]
    widget = match.group(0)

    # Bereits vorhandene zPosition sauber ersetzen, sonst ergänzen.
    if 'zPosition=' in widget:
        promoted = re.sub(r'zPosition="[^"]*"', 'zPosition="20"', widget, count=1)
    else:
        promoted = widget[:-2].rstrip() + ' zPosition="20" />'

    return text[:match.start()] + promoted + text[match.end():]


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_DEFAULT

    if not os.path.isfile(target):
        raise SystemExit("Datei nicht gefunden: %s" % target)

    with io.open(target, "r", encoding="utf-8") as handle:
        original = handle.read()

    if MARKER in original:
        print("SEARCH_ZORDER1 bereits installiert: %s" % target)
        return

    if "# INFUSEMEDIA2026_SEARCH_DISNEY1" not in original:
        raise RuntimeError("SEARCH_ZORDER1 erwartet SEARCH_DISNEY1")

    patched = original
    for name in TARGET_WIDGETS:
        patched = promote_widget(patched, name)

    if patched.startswith("# -*- coding: utf-8 -*-"):
        first, rest = patched.split("\n", 1)
        patched = first + "\n" + MARKER + "\n" + rest
    else:
        patched = MARKER + "\n" + patched

    compile(patched, target, "exec")

    backup = target + BACKUP_SUFFIX
    if not os.path.exists(backup):
        shutil.copy2(target, backup)

    with io.open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(patched)

    with io.open(target, "r", encoding="utf-8") as handle:
        verify = handle.read()

    compile(verify, target, "exec")

    for name in TARGET_WIDGETS:
        m = re.search(
            r'<widget\s+name="' + re.escape(name) + r'"[^>]*zPosition="20"[^>]*/>',
            verify
        )
        if not m:
            raise RuntimeError("ZORDER1 Verifikation fehlgeschlagen: %s" % name)

    print("OK INFUSEMEDIA2026_SEARCH_ZORDER1: %s" % target)
    print("- Suche-Ueberschrift nach vorne geholt")
    print("- Provider-Legende Emby/Jellyfin/Plex nach vorne geholt")
    print("- Verfuegbar-bei-Namen nach vorne geholt")
    print("- Aktionsbeschriftungen nach vorne geholt")
    print("- Suchlogik / Gruppierung / Navigation / Poster unveraendert")
    print("- Backup: %s" % backup)


if __name__ == "__main__":
    main()
