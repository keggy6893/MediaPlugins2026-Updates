# -*- coding: utf-8 -*-
from .jellyfin_client import JellyfinClient
from .emby_client import EmbyClient
from .plex_client import PlexClient


def create_client_for_server(server_cfg):
    if server_cfg.protocol == "jellyfin":
        cls = JellyfinClient
    elif server_cfg.protocol == "emby":
        cls = EmbyClient
    elif server_cfg.protocol == "plex":
        cls = PlexClient
    else:
        raise ValueError("Unbekanntes Protokoll: %s" % server_cfg.protocol)

    return cls(
        name=server_cfg.name,
        address=server_cfg.address,
        port=server_cfg.port,
        username=server_cfg.username,
        password=server_cfg.password,
        https=server_cfg.https,
        path=server_cfg.path,
        library_mode=server_cfg.library_mode,
        token=getattr(server_cfg, "token", ""),
        user_id=getattr(server_cfg, "user_id", ""),
    )
