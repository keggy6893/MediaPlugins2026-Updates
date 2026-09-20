# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label

from ..components.GridWidget import GridWidget
from ..utils.dedupe import dedupe_items
from ..utils import log


class FavoritesBrowser(Screen):
    """r56: Serveruebergreifende Favoritenliste - direkt vom Server geladen.

    Fragt bei jedem eingeloggten Client dessen echte, serverseitig als
    Favorit markierte Items ab (Jellyfin/Emby FavoriteItems-API, ueber
    Filters=IsFavorite) und fuehrt die Ergebnisse aus Emby und Jellyfin (Plex-Watchlist folgt separat)
    zusammen. Ersetzt die fruehere rein lokale, nur auf dieser Box
    gespeicherte Favoritenliste - Favoriten, die z.B. ueber die Jellyfin-
    Web-Oberflaeche oder eine andere App markiert wurden, tauchen jetzt
    ebenfalls hier auf.
    """

    skinName = "MediaPlugins2026FavoritesBrowser"
    skin = """
    <screen name="MediaPlugins2026FavoritesBrowser" position="center,center" size="1920,1080" backgroundColor="#101114" title="Favoriten">
        <widget name="title" position="60,45" size="1000,70" font="Regular;46" foregroundColor="#ffffff" transparent="1" />
        <widget name="status" position="60,118" size="1780,40" font="Regular;22" foregroundColor="#90939a" transparent="1" />
        <widget name="grid" position="60,180" size="1800,790" transparent="1" />
        <widget name="key_red" position="60,985" size="250,44" font="Regular;22"
                foregroundColor="#ffffff" backgroundColor="#a33327" halign="center" valign="center"
                transparent="0" zPosition="2" />
        <widget name="key_blue" position="324,985" size="250,44" font="Regular;22"
                foregroundColor="#ffffff" backgroundColor="#1c5fa8" halign="center" valign="center"
                transparent="0" zPosition="2" />
        <widget name="hint" position="588,985" size="900,44" font="Regular;22" foregroundColor="#8a8d92"
                transparent="1" valign="center" />
    </screen>"""

    def __init__(self, session, clients, server_configs):
        Screen.__init__(self, session)
        self.session = session
        self.clients = clients or {}
        self.server_configs = server_configs or {}
        self.results = []
        self._raw_results = []
        self._pending = 0
        self._request = 0
        self._child_open = False
        self._closing = False
        # r62: Item-Identitaet merken, das vor dem Oeffnen der Detailansicht
        # ausgewaehlt war, um die Cursorposition nach dem Neuladen wieder
        # dorthin zu setzen (Neuladen springt sonst immer auf Position 0).
        self._restore_selection = None

        self["title"] = Label(_("Favoriten"))
        self["status"] = Label(_("Lade Favoriten vom Server..."))
        # r66: farbige Tasten-Legende statt reinem Fliesstext.
        self["key_red"] = Label(_("Startseite"))
        self["key_blue"] = Label(_("Favorit entfernen"))
        self["hint"] = Label(_("OK: Öffnen"))
        self.grid = GridWidget(columns=6, item_width=280, item_height=420)
        self["grid"] = self.grid

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.keyOpen,
                "cancel": self.keyCancel,
                "up": self.grid.moveUp,
                "down": self.grid.moveDown,
                "left": self.grid.moveLeft,
                "right": self.grid.moveRight,
                "blue": self.keyRemoveFavorite,
            },
            -1
        )
        self.onLayoutFinish.append(self._load)

    def _load(self):
        self._request += 1
        rid = self._request

        if not self.clients:
            self["status"].setText(_("Kein Server verbunden"))
            self.grid.setItems([])
            return

        self._pending = len(self.clients)
        self._raw_results = []
        self["status"].setText(_("Lade Favoriten vom Server..."))

        for name, client in self.clients.items():
            self._fetchServerFavorites(rid, name, client)

    def _fetchServerFavorites(self, rid, name, client):
        def on_favorites(items):
            self._onServerDone(rid, name, items)

        def on_error(err):
            log.warning("FavoritesBrowser r56: Favoriten von %s konnten nicht geladen werden: %s",
                        name, err)
            self._onServerDone(rid, name, [])

        if getattr(client, "token", None) and getattr(client, "user_id", None):
            client.get_favorites(on_favorites, on_error)
        else:
            client.login(
                lambda token, uid, c=client: c.get_favorites(on_favorites, on_error),
                on_error
            )

    def _onServerDone(self, rid, name, items):
        if self._closing or rid != self._request:
            return
        self._raw_results.extend(items or [])
        self._pending -= 1
        if self._pending <= 0:
            self._finish()

    def _finish(self):
        # r56: dasselbe Medium kann auf mehreren Servern als Favorit
        # markiert sein - hier wie in LibraryBrowser/SearchScreen ueber
        # Provider-ID/normalisierten Titel entduplizieren.
        self.results, duplicates = dedupe_items(self._raw_results)
        if duplicates:
            log.info("FavoritesBrowser r56: %d serveruebergreifende Dublette(n) entfernt", duplicates)

        self.results.sort(key=lambda i: (getattr(i, "title", "") or "").casefold())
        if not self.results:
            self["status"].setText(_("Keine Favoriten auf dem Server markiert"))
        else:
            self["status"].setText(_("%d Favoriten") % len(self.results))
        self.grid.setItems(self.results)
        # r62: vorherige Auswahl wiederherstellen, falls vorhanden (z.B.
        # nach Rueckkehr aus den Details).
        if self._restore_selection:
            item_id, server_name = self._restore_selection
            self._restore_selection = None
            self.grid.selectItem(item_id, server_name)

    def keyOpen(self):
        if self._child_open:
            return
        item = self.grid.getCurrent()
        if not item:
            return
        client = self.clients.get(item.server_name)
        if not client:
            return
        from .MediaDetail import MediaDetail
        self._child_open = True
        # r62: Auswahl merken, damit sie nach dem Neuladen beim Zurueckkehren
        # wiederhergestellt werden kann.
        self._restore_selection = (item.id, item.server_name)
        try:
            child = self.session.open(MediaDetail, item, client)
            child.onClose.append(self._childClosed)
        except Exception as e:
            self._child_open = False
            log.exception("FavoritesBrowser r56: Details konnten nicht geoeffnet werden: %s", e)

    def _childClosed(self, *args):
        self._child_open = False
        # Nach Rueckkehr aus den Details (dort kann der Favoritenstatus
        # ueber GELB geaendert worden sein) die Liste neu vom Server laden.
        self._load()

    def keyRemoveFavorite(self):
        item = self.grid.getCurrent()
        if not item:
            return
        client = self.clients.get(item.server_name)
        if not client:
            return
        # r62: Position merken, um nach dem Entfernen an (ungefaehr)
        # derselben Stelle stehen zu bleiben statt auf Position 0
        # zurueckzuspringen.
        row_idx, col_idx = self.grid.current_row, self.grid.current_col
        item.is_favorite = False
        client.set_favorite(item.id, False)
        # Optimistisch sofort aus der Ansicht entfernen, statt auf die
        # Server-Antwort zu warten.
        self.results = [i for i in self.results if i is not item]
        self["status"].setText(_("%d Favoriten") % len(self.results) if self.results
                                else _("Keine Favoriten auf dem Server markiert"))
        self.grid.setItems(self.results)
        self.grid.selectPosition(row_idx, col_idx)

    def keyCancel(self):
        if self._closing or self._child_open:
            return
        self._closing = True
        self._request += 1
        try:
            self["actions"].setEnabled(False)
        except Exception:
            pass
        self.close()
