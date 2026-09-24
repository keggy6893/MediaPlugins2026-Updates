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

    def login(self, callback, error_callback):
        """
        Emby: importierte Token/User-ID nicht blind weiterverwenden.

        Fuer Emby wird mit den vorhandenen Zugangsdaten neu authentifiziert,
        damit ein importierter oder abgelaufener Token nicht erst bei den
        nachfolgenden Home-/Library-/Favorites-Requests als HTTP 401 auffaellt.

        JellyfinClient bleibt unveraendert.
        """
        old_token = self.token
        old_user_id = self.user_id

        self.token = None
        self.user_id = None

        def login_ok(token, user_id):
            callback(token, user_id)

        def login_failed(err):
            self.token = old_token
            self.user_id = old_user_id
            error_callback(err)

        return super(EmbyClient, self).login(login_ok, login_failed)
