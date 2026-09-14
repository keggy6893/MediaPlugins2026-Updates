# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import re
import shutil
import sys

PLUGIN_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
DETAIL_REL = "screens/MediaDetail.py"
HOME_REL = "screens/HomeScreen.py"
BRIDGE_REL = "screens/ProviderPlayerBridge.py"

MARKER = "# MEDIAPLUGINS2026_PROVIDERPLAYER_RESTORE1"

BRIDGE = '''# -*- coding: utf-8 -*-
# MEDIAPLUGINS2026_PROVIDERPLAYER_RESTORE1

import copy

from Screens.MessageBox import MessageBox
from ..utils import log


def _provider(item, client):
    value = str(getattr(item, "source_label", "") or "").strip().lower()
    if value in ("emby", "plex", "jellyfin"):
        return value

    class_name = client.__class__.__name__.lower()
    if "plex" in class_name:
        return "plex"

    server_name = str(getattr(item, "server_name", "") or "").lower()
    if "emby" in server_name:
        return "emby"
    if "jellyfin" in server_name:
        return "jellyfin"
    return ""


def _bridge_log(message):
    try:
        with open("/tmp/mediaplugins2026_provider_player.log", "a") as handle:
            handle.write(str(message).replace("\\n", " ")[:1200] + "\\n")
    except Exception:
        pass


def _show_error(session, provider, error):
    label = {
        "plex": "Plex2026",
        "emby": "EmbyFlowE2",
        "jellyfin": "Jellyfin",
    }.get(provider, provider or "Provider")

    _bridge_log("%s ERROR %s" % (label, error))
    try:
        session.open(
            MessageBox,
            "%s-Player konnte nicht gestartet werden.\\n\\n%s" % (label, error),
            MessageBox.TYPE_ERROR,
            timeout=8,
        )
    except Exception:
        pass


def _set_emby_resume(info, start_ticks):
    result = copy.deepcopy(info or {})
    item = result.get("item")
    if not isinstance(item, dict):
        return result

    try:
        ticks = max(0, int(start_ticks or 0))
    except Exception:
        ticks = 0

    user_data = dict(item.get("UserData") or item.get("user_data") or {})
    user_data["PlaybackPositionTicks"] = ticks
    item["UserData"] = user_data
    item["PlaybackPositionTicks"] = ticks
    result["item"] = item
    return result


def _open_emby(session, item, start_ticks):
    try:
        from enigma import eServiceReference
        from Plugins.Extensions.EmbyFlowE2 import plugin as emby

        fetch = getattr(emby, "fetch_stream_info", None)
        if not callable(fetch):
            raise RuntimeError("EmbyFlowE2: fetch_stream_info fehlt")

        item_id = str(getattr(item, "id", "") or "").strip()
        title = str(getattr(item, "title", "") or "Emby")

        if not item_id:
            raise RuntimeError("Emby-ID fehlt")

        info = fetch(
            search_term=title,
            audio_mode="direct",
            item_id=item_id,
        )

        if not isinstance(info, dict) or not info.get("url"):
            raise RuntimeError("EmbyFlowE2 lieferte keine Wiedergabe-Informationen")

        info = _set_emby_resume(info, start_ticks)
        url = str(info.get("url") or "")
        service_type = int(getattr(emby, "STREAM_SERVICE_TYPE", 4097) or 4097)

        ref = eServiceReference(service_type, 0, url)
        try:
            ref.setName(title)
        except Exception:
            pass

        open_now = getattr(emby, "_open_embyflow_player_now", None)
        if callable(open_now):
            open_now(session, ref, title, url, info)
        else:
            opener = getattr(emby, "open_embyflow_player", None)
            if not callable(opener):
                raise RuntimeError("EmbyFlowE2 Player-Startfunktion fehlt")
            opener(session, ref, title, url, info)

        _bridge_log("EMBY opened item_id=%s title=%r" % (item_id, title))
        return True

    except Exception as error:
        _show_error(session, "emby", error)
        return True


def _plex_seed(item):
    item_id = str(getattr(item, "id", "") or "").strip()
    seed = {
        "ratingKey": item_id,
        "key": "/library/metadata/%s" % item_id if item_id else "",
        "title": str(getattr(item, "title", "") or "Plex"),
    }

    media_type = str(getattr(item, "media_type", "") or "").strip().lower()
    if media_type:
        seed["type"] = media_type

    series_name = str(getattr(item, "series_name", "") or "").strip()
    if series_name:
        seed["grandparentTitle"] = series_name

    season = getattr(item, "season_number", None)
    episode = getattr(item, "episode_number", None)

    if season is not None:
        seed["parentIndex"] = season
    if episode is not None:
        seed["index"] = episode

    return seed


def _open_plex(session, item, start_ticks):
    try:
        from Plugins.Extensions.Plex2026Phase1 import plugin as plex

        token_loader = getattr(plex, "load_plex_token", None)
        server_loader = getattr(plex, "plex_first_server", None)
        direct_url = getattr(plex, "plex2026_direct_play_url", None)
        opener = getattr(plex, "plex2026_open_emby_player_ab", None)

        if not callable(token_loader):
            raise RuntimeError("Plex2026: load_plex_token fehlt")
        if not callable(server_loader):
            raise RuntimeError("Plex2026: plex_first_server fehlt")
        if not callable(direct_url):
            raise RuntimeError("Plex2026: plex2026_direct_play_url fehlt")
        if not callable(opener):
            raise RuntimeError("Plex2026 Player-Startfunktion fehlt")

        item_id = str(getattr(item, "id", "") or "").strip()
        if not item_id:
            raise RuntimeError("Plex ratingKey fehlt")

        token = token_loader()
        if not token:
            raise RuntimeError("Plex2026 ist nicht angemeldet")

        server = server_loader(token)
        if not server:
            raise RuntimeError("Plex2026 findet keinen Server")

        seed = _plex_seed(item)
        stream_url, full_item = direct_url(server, seed)
        stream_url = str(stream_url or "")

        if not stream_url:
            raise RuntimeError("Plex2026 lieferte keine Stream-URL")

        opener(
            session,
            full_item if isinstance(full_item, dict) else seed,
            stream_url,
        )

        _bridge_log(
            "PLEX opened ratingKey=%s title=%r"
            % (item_id, str(getattr(item, "title", "") or ""))
        )
        return True

    except Exception as error:
        _show_error(session, "plex", error)
        return True


def open_provider_player(session, item, client, start_ticks=None):
    provider = _provider(item, client)

    _bridge_log(
        "route provider=%s item=%s title=%r"
        % (
            provider,
            str(getattr(item, "id", "") or ""),
            str(getattr(item, "title", "") or ""),
        )
    )

    if provider == "plex":
        return _open_plex(session, item, start_ticks)

    if provider == "emby":
        return _open_emby(session, item, start_ticks)

    return False
'''

HOME_METHOD = '''    def keyPlayCurrent(self):
        item = self._selectedItem()
        if item is None:
            return
        if getattr(item, "is_demo", False):
            self.keyOpenSettings()
            return

        client = self.clients.get(item.server_name)
        if not client:
            return

        try:
            # MEDIAPLUGINS2026_PROVIDERPLAYER_RESTORE1
            from .ProviderPlayerBridge import open_provider_player

            if open_provider_player(
                self.session,
                item,
                client,
                start_ticks=int(getattr(item, "resume_ticks", 0) or 0),
            ):
                return

            from enigma import eServiceReference
            from .InfuseMoviePlayer import InfuseMoviePlayer

            url = client.get_stream_url(item.id, item)
            ref = eServiceReference(4097, 0, url)
            ref.setName(item.title)
            self.session.open(
                InfuseMoviePlayer,
                ref,
                item,
                client,
                url,
            )

        except Exception as e:
            log.exception("MediaWall-Wiedergabe fehlgeschlagen: %s", e)
            self.session.open(
                MessageBox,
                "Wiedergabe fehlgeschlagen.",
                MessageBox.TYPE_ERROR,
            )
'''

DETAIL_METHOD = '''    def _startPlayback(self, url, start_ticks=None):
        # MEDIAPLUGINS2026_PROVIDERPLAYER_RESTORE1
        from .ProviderPlayerBridge import open_provider_player

        if open_provider_player(
            self.session,
            self.item,
            self.client,
            start_ticks=start_ticks,
        ):
            return

        from enigma import eServiceReference
        from .InfuseMoviePlayer import InfuseMoviePlayer

        ref = eServiceReference(4097, 0, url)
        ref.setName(self.item.title)
        self.session.open(
            InfuseMoviePlayer,
            ref,
            self.item,
            self.client,
            url,
            start_ticks,
        )
'''


def read(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def replace_method(text, name, new_method):
    pattern = re.compile(
        r'(?ms)^    def %s\(.*?(?=^    def |\Z)' % re.escape(name)
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(
            "%s: erwartete genau 1 Methode, gefunden %d"
            % (name, len(matches))
        )
    match = matches[0]
    return text[:match.start()] + new_method.rstrip() + "\n\n" + text[match.end():]


def backup(path, suffix):
    target = path + suffix
    if not os.path.exists(target):
        shutil.copy2(path, target)
    return target


def main():
    plugin = sys.argv[1] if len(sys.argv) > 1 else PLUGIN_DEFAULT

    home_path = os.path.join(plugin, HOME_REL)
    detail_path = os.path.join(plugin, DETAIL_REL)
    bridge_path = os.path.join(plugin, BRIDGE_REL)

    if not os.path.isfile(home_path):
        raise SystemExit("HomeScreen fehlt: %s" % home_path)
    if not os.path.isfile(detail_path):
        raise SystemExit("MediaDetail fehlt: %s" % detail_path)

    home_original = read(home_path)
    detail_original = read(detail_path)

    home_new = replace_method(home_original, "keyPlayCurrent", HOME_METHOD)
    detail_new = replace_method(detail_original, "_startPlayback", DETAIL_METHOD)

    compile(BRIDGE, bridge_path, "exec")
    compile(home_new, home_path, "exec")
    compile(detail_new, detail_path, "exec")

    home_backup = backup(home_path, ".before_providerplayer_restore1")
    detail_backup = backup(detail_path, ".before_providerplayer_restore1")
    bridge_backup = None
    if os.path.isfile(bridge_path):
        bridge_backup = backup(bridge_path, ".before_providerplayer_restore1")

    write(bridge_path, BRIDGE)
    write(home_path, home_new)
    write(detail_path, detail_new)

    for path in (bridge_path, home_path, detail_path):
        compile(read(path), path, "exec")

    home_verify = read(home_path)
    detail_verify = read(detail_path)
    bridge_verify = read(bridge_path)

    checks = [
        (MARKER in home_verify, "HomeScreen Routing"),
        (MARKER in detail_verify, "MediaDetail Routing"),
        ("Plugins.Extensions.EmbyFlowE2" in bridge_verify, "EmbyFlowE2 Bridge"),
        ("fetch_stream_info" in bridge_verify, "EmbyFlowE2 Streamentscheidung"),
        ("_open_embyflow_player_now" in bridge_verify, "EmbyFlowE2 Player"),
        ("Plugins.Extensions.Plex2026Phase1" in bridge_verify, "Plex2026 Bridge"),
    ]
    missing = [name for ok, name in checks if not ok]
    if missing:
        raise RuntimeError("Verifikation fehlgeschlagen: %r" % missing)

    print("OK MEDIAPLUGINS2026_PROVIDERPLAYER_RESTORE1")
    print("- Emby -> EmbyFlowE2 eigener Player")
    print("- Plex -> Plex2026 eigener Player")
    print("- Jellyfin -> interner MediaPlugins-Player")
    print("- HomeScreen + MediaDetail verwenden wieder die Provider-Bridge")
    print("- Server-Health / Latest-Fix bleiben unveraendert")
    print("Home Backup:   %s" % home_backup)
    print("Detail Backup: %s" % detail_backup)
    if bridge_backup:
        print("Bridge Backup: %s" % bridge_backup)


if __name__ == "__main__":
    main()
