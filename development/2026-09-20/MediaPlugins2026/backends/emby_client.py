# -*- coding: utf-8 -*-
from .jellyfin_client import JellyfinClient


class EmbyClient(JellyfinClient):
    """
    Jellyfin entstand aus der frueher offenen Emby-Codebasis; die REST-APIs
    sind bis heute in vielen Bereichen strukturell kompatibel.
    (gleiche Endpunkte /Users/AuthenticateByName, /Items, /Views usw.).
    Daher wird nur der Client-Name fuer die Auth-Kennung angepasst; bei
    tatsaechlich abweichendem Verhalten einzelner Endpunkte werden die
    jeweiligen Methoden hier gezielt ueberschrieben.
    """

    CLIENT_NAME = "MediaPlugins2026-Emby"
