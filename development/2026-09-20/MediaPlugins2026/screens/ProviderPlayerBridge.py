# -*- coding: utf-8 -*-
# MEDIAPLUGINS2026_PROVIDERPLAYER_RESTORE1
# MEDIAPLUGINS2026_PLEX_NATIVE_UNIFIED_TEST1

from Screens.MessageBox import MessageBox
from ..utils import log


def _provider(item, client):
    value = str(getattr(item, "source_label", "") or "").strip().lower()
    if value in ("emby", "plex", "jellyfin"):
        return value

    class_name = client.__class__.__name__.lower()
    if "plex" in class_name:
        return "plex"
    if "emby" in class_name:
        return "emby"
    if "jellyfin" in class_name:
        return "jellyfin"

    server_name = str(getattr(item, "server_name", "") or "").lower()
    if "emby" in server_name:
        return "emby"
    if "jellyfin" in server_name:
        return "jellyfin"
    if "plex" in server_name:
        return "plex"
    return ""


def _bridge_log(message):
    try:
        with open("/tmp/mediaplugins2026_provider_player.log", "a") as handle:
            handle.write(str(message).replace("\n", " ")[:1200] + "\n")
    except Exception:
        pass


def _show_error(session, provider, error):
    label = {
        "plex": "Plex",
        "emby": "Emby",
        "jellyfin": "Jellyfin",
        "audio": "Media Plugins Audio",
    }.get(provider, provider or "Provider")

    _bridge_log("%s ERROR %s" % (label, error))
    try:
        session.open(
            MessageBox,
            "%s-Wiedergabe konnte nicht gestartet werden.\n\n%s" % (label, error),
            MessageBox.TYPE_ERROR,
            timeout=8,
        )
    except Exception:
        pass


# MEDIAPLUGINS2026_AUDIOPLAYER1
_AUDIO_CONTAINERS = set((
    "mp3", "aac", "m4a", "m4b", "mp4", "flac", "wav", "wave", "ogg",
    "oga", "opus", "alac", "aiff", "aif", "wma", "ape",
))


def _is_audio_item(item):
    media_type = str(getattr(item, "media_type", "") or "").strip().lower()
    if media_type in ("audio", "audiobook", "music", "song", "track"):
        return True
    container = str(getattr(item, "container", "") or "").strip().lower().lstrip(".")
    audio_codec = str(getattr(item, "audio_codec", "") or "").strip().lower()
    video_codec = str(getattr(item, "video_codec", "") or "").strip().lower()
    video_type = str(getattr(item, "video_type", "") or "").strip().lower()
    if container in _AUDIO_CONTAINERS and not video_codec:
        return True
    if audio_codec and not video_codec and not video_type:
        return True
    return False


def _open_audio(session, item, client, start_ticks):
    try:
        from .AudioPlayer import MediaPluginsAudioPlayer
        session.open(MediaPluginsAudioPlayer, item, client, start_ticks)
        _bridge_log(
            "AUDIO opened provider=%s item_id=%s title=%r"
            % (_provider(item, client), str(getattr(item, "id", "") or ""), str(getattr(item, "title", "") or ""))
        )
        return True
    except Exception as error:
        _show_error(session, "audio", error)
        return True


def _open_unified(session, item, client, provider, stream_url, start_ticks,
                  service_type=4097, extra=None):
    from enigma import eServiceReference
    from ..playback import PlaybackContext
    from .UnifiedVideoPlayer import MediaPluginsVideoPlayer

    url = str(stream_url or "").strip()
    if not url:
        raise RuntimeError("Keine Stream-URL vorhanden")

    ref = eServiceReference(int(service_type or 4097), 0, url)
    try:
        ref.setName(str(getattr(item, "title", "") or provider.title()))
    except Exception:
        pass

    playback = PlaybackContext(
        provider=provider,
        item=item,
        client=client,
        stream_url=url,
        start_ticks=start_ticks,
        service_type=service_type,
        extra=extra,
    )
    session.open(MediaPluginsVideoPlayer, ref, playback)
    _bridge_log(
        "UNIFIED opened provider=%s item=%s engine=%s title=%r"
        % (
            provider,
            str(getattr(item, "id", "") or ""),
            playback.engine_label(),
            str(getattr(item, "title", "") or ""),
        )
    )
    return True


def _open_jellyfin(session, item, client, start_ticks):
    try:
        url = client.get_stream_url(item.id, item)
        return _open_unified(
            session, item, client, "jellyfin", url, start_ticks, 4097,
            {"url_source": "MediaPlugins JellyfinClient"},
        )
    except Exception as error:
        _show_error(session, "jellyfin", error)
        return True


def _open_emby(session, item, client, start_ticks):
    """Route Emby through the same MediaPlugins2026 unified 4097 player."""
    try:
        url = client.get_stream_url(item.id, item)
        return _open_unified(
            session, item, client, "emby", url, start_ticks, 4097,
            {"url_source": "MediaPlugins EmbyClient",
             "playback_path": "native-unified"},
        )
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


def _plex_embyflow_item(item, raw=None):
    """Build the Emby-shaped metadata consumed by the EmbyFlow player UI."""
    item_id = str(getattr(item, "id", "") or "")
    media_type = str(getattr(item, "media_type", "") or "").strip().lower()
    emby_type = "Episode" if media_type == "episode" else "Movie"
    video_codec = str(getattr(item, "video_codec", "") or "")
    audio_codec = str(getattr(item, "audio_codec", "") or "")
    width = int(getattr(item, "video_width", 0) or 0)
    height = int(getattr(item, "video_height", 0) or 0)
    channels = int(getattr(item, "audio_channels", 0) or 0)
    language = str(getattr(item, "audio_language", "") or "")
    runtime_ticks = int(getattr(item, "runtime_ticks", 0) or 0)

    streams = []
    if video_codec or width or height:
        streams.append({
            "Type": "Video", "Index": 0, "Codec": video_codec,
            "Width": width, "Height": height,
        })
    if audio_codec or channels or language:
        streams.append({
            "Type": "Audio", "Index": 1, "Codec": audio_codec,
            "Channels": channels, "Language": language,
            "DisplayLanguage": language,
        })

    data = {
        "Id": item_id,
        "Name": str(getattr(item, "title", "") or "Plex"),
        "Type": emby_type,
        "ProductionYear": getattr(item, "year", None),
        "Genres": list(getattr(item, "genres", None) or []),
        "CommunityRating": getattr(item, "rating", None),
        "RunTimeTicks": runtime_ticks,
        "SeriesName": str(getattr(item, "series_name", "") or ""),
        "ParentIndexNumber": getattr(item, "season_number", None),
        "IndexNumber": getattr(item, "episode_number", None),
        "UserData": {"PlaybackPositionTicks": int(getattr(item, "resume_ticks", 0) or 0)},
        "MediaSources": [{
            "Id": "plex-%s" % item_id,
            "MediaStreams": streams,
            "RunTimeTicks": runtime_ticks,
        }],
        "EmbyFlowPlaybackMode": "direct",
    }
    # Only accept already-normalized chapter dictionaries.  Do not guess Plex
    # chapter schema in this first adapter build.
    if isinstance(raw, dict) and isinstance(raw.get("Chapters"), list):
        data["Chapters"] = raw.get("Chapters")
    return data


def _open_plex_embyflow(session, item, client, start_ticks, stream_url, service_type, raw=None):
    from enigma import eServiceReference
    from .PlexEmbyFlowPlayer import PlexEmbyFlowMoviePlayer

    title = str(getattr(item, "title", "") or "Plex")
    ref = eServiceReference(int(service_type or 4097), 0, str(stream_url))
    try:
        ref.setName(title)
    except Exception:
        pass
    try:
        old_ref = session.nav.getCurrentlyPlayingServiceReference()
    except Exception:
        old_ref = None

    info = {
        "url": str(stream_url),
        "item": _plex_embyflow_item(item, raw),
        "playback_mode": "direct",
        "engine_mode": "auto",
        "service_type": int(service_type or 4097),
        # Deliberately no Emby server/token/user_id for Plex.
    }
    if start_ticks:
        info["start_ticks"] = int(start_ticks)
        info["position_ticks"] = int(start_ticks)

    # Plex differs from Emby here: EmbyFlow normally owns the service start via
    # its Emby-specific bootstrap.  A Plex item deliberately has no Emby
    # server/token, so start the already-resolved Direct-Play reference first
    # and then open the proven EmbyFlow OSD around that active service.
    try:
        session.nav.stopService()
    except Exception:
        pass
    try:
        session.nav.playService(ref)
    except Exception as error:
        raise RuntimeError("Plex Direct Play konnte nicht gestartet werden: %s" % error)

    session.open(PlexEmbyFlowMoviePlayer, ref, title, info, old_ref, client, item)
    _bridge_log(
        "PLEX_EMBYFLOW_DIRECT1 playing+opened item=%s service=%s title=%r"
        % (getattr(item, "id", ""), int(service_type or 4097), title)
    )
    return True


def _open_plex(session, item, client, start_ticks):
    # Prefer the Direct-Play Media/Part URL already resolved by our logged-in
    # PlexClient.  It carries the active PMS endpoint/token and avoids routing
    # normal playback through a second Plex helper/session.
    local_error = None
    try:
        url = client.get_stream_url(item.id, item)
        if url:
            return _open_unified(
                session, item, client, "plex", url, start_ticks, 4097,
                {"url_source": "MediaPlugins PlexClient",
                 "playback_path": "native-unified"},
            )
    except Exception as error:
        local_error = str(error)
        _bridge_log("PLEX direct Media/Part unavailable: %s" % error)

    # Fallback only when the MediaPlugins item does not contain a playable Part.
    external_error = None
    try:
        from Plugins.Extensions.Plex2026Phase1 import plugin as plex
        token_loader = getattr(plex, "load_plex_token", None)
        server_loader = getattr(plex, "plex_first_server", None)
        direct_url = getattr(plex, "plex2026_direct_play_url", None)
        if callable(token_loader) and callable(server_loader) and callable(direct_url):
            token = token_loader()
            server = token and server_loader(token)
            if server:
                seed = _plex_seed(item)
                stream_url, full_item = direct_url(server, seed)
                if stream_url:
                    service_type = int(getattr(plex, "STREAM_SERVICE_TYPE", 4097) or 4097)
                    return _open_unified(
                        session, item, client, "plex", stream_url, start_ticks, service_type,
                        {"url_source": "Plex2026 fallback",
                         "playback_path": "native-unified"},
                    )
            external_error = "Plex2026 lieferte keine Stream-URL"
        else:
            external_error = "Plex2026 Helper-API unvollstaendig"
    except Exception as error:
        external_error = str(error)

    _show_error(
        session, "plex",
        "%s; Fallback: %s" % (local_error or "Plex Direct-Play-Pfad fehlt", external_error or "nicht verfuegbar")
    )
    return True

def open_provider_player(session, item, client, start_ticks=None):
    provider = _provider(item, client)
    _bridge_log(
        "route provider=%s item=%s title=%r"
        % (provider, str(getattr(item, "id", "") or ""), str(getattr(item, "title", "") or ""))
    )

    if provider in ("emby", "jellyfin", "plex") and _is_audio_item(item):
        return _open_audio(session, item, client, start_ticks)
    if provider == "jellyfin":
        return _open_jellyfin(session, item, client, start_ticks)
    if provider == "emby":
        return _open_emby(session, item, client, start_ticks)
    if provider == "plex":
        return _open_plex(session, item, client, start_ticks)
    return False
