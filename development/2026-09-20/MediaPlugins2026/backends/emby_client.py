# -*- coding: utf-8 -*-
from .jellyfin_client import JellyfinClient


class EmbyClient(JellyfinClient):
    """
    Jellyfin entstand aus der frueher offenen Emby-Codebasis; die REST-APIs
    sind bis heute in vielen Bereichen strukturell kompatibel.
    (gleiche Endpunkte /Users/AuthenticateByName, /Items, /Views usw.).
    Daher wird nur der Client-Name für die Auth-Kennung angepasst; bei
    tatsächlich abweichendem Verhalten einzelner Endpunkte werden die
    jeweiligen Methoden hier gezielt überschrieben.
    """

    CLIENT_NAME = "MediaPlugins2026-Emby"
