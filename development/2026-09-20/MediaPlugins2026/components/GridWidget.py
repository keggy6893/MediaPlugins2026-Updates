# -*- coding: utf-8 -*-
from Components.GUIComponent import GUIComponent
from enigma import eListbox, eListboxPythonMultiContent, gFont
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest, MultiContentEntryRectangle
from Tools.LoadPixmap import LoadPixmap

from ..utils.image_cache import image_cache
from ..utils import log


class GridWidget(GUIComponent):
    """Poster-Grid fuer LibraryBrowser/SearchScreen.

    r27: OpenATV-7.6-Kompatibilitaetsfix.
    - Kein ePicLoad/getData mehr im MultiContent-Grid. Auf der SF8008 mit
      OpenATV 7.6.1 kann getData() in diesem Callback-Pfad eine gesetzte
      C++/Python-Exception zurueckgeben.
    - Kein nicht unterstuetztes ``halign`` Keyword bei MultiContentEntryText.
    - Poster werden weiterhin bereits serverseitig klein angefordert (r25),
      daher ist LoadPixmap fuer die gecachten 320x480-Dateien vertretbar.
    """

    GUI_WIDGET = eListbox

    def __init__(self, columns=6, item_width=280, item_height=420):
        GUIComponent.__init__(self)
        self.columns = columns
        self.item_width = item_width
        self.item_height = item_height
        self.poster_w = min(230, self.item_width - 30)
        self.poster_h = 345

        self.l = eListboxPythonMultiContent()
        self.l.setItemHeight(item_height)
        # font=0 wird in buildEntry benutzt und muss auf OpenATV explizit
        # gesetzt sein.
        self.l.setFont(0, gFont("Regular", 22))
        self.l.setFont(1, gFont("Regular", 17))
        self.l.setBuildFunc(self.buildEntry)

        self.rows = []
        self.current_row = 0
        self.current_col = 0
        self._pixmap_cache = {}

    def postWidgetCreate(self, instance):
        instance.setContent(self.l)

    def preWidgetRemove(self, instance):
        try:
            instance.setContent(None)
        except Exception:
            pass
        self._pixmap_cache.clear()

    def setItems(self, items):
        items = list(items or [])
        self.rows = [items[i:i + self.columns] for i in range(0, len(items), self.columns)]
        self.current_row = 0
        self.current_col = 0
        # r60: Zeilennummer wird jetzt direkt als Teil der Listendaten
        # mitgegeben (i, row) statt sie in buildEntry ueber list.index()
        # oder eine id()-Nachschlagetabelle zu ermitteln. Beide frueheren
        # Ansaetze konnten in bestimmten Situationen (z.B. nach Rueckkehr
        # aus der Detailansicht) die falsche oder gar keine Zeile treffen -
        # mit der Zeilennummer direkt in den Daten ist das nicht mehr
        # moeglich.
        self.l.setList([(i, row) for i, row in enumerate(self.rows)])
        if self.instance:
            # Cursor explizit auf die erste Zeile zuruecksetzen, passend zu
            # current_row/current_col=0 oben. r61: "moveHome" existiert in
            # der enigma2-eListbox-API gar nicht (richtig heisst es
            # "moveTop") - der falsche Attributname loeste eine
            # AttributeError aus, die vom try/except stillschweigend
            # verschluckt wurde. Der Cursor wurde dadurch NIE zurueckgesetzt,
            # weshalb der eigentlich korrekt auf Zeile 0 stehende
            # Auswahlrahmen nach einem Neuladen ausserhalb des sichtbaren
            # Bereichs lag (kein Rahmen sichtbar, da der Viewport nicht
            # zurueckgescrollt wurde).
            try:
                self.instance.moveSelection(self.instance.moveTop)
            except Exception as e:
                log.warning("GridWidget r61: Cursor-Reset fehlgeschlagen: %s", e)
        self.l.invalidate()
        self._prefetchPosters(items)

    def _prefetchPosters(self, items):
        for item in items:
            cached = image_cache.get_local_path(getattr(item, "poster_url", None))
            item.local_poster_path = cached
            if cached:
                continue
            poster_url = getattr(item, "poster_url", None)
            if poster_url:
                image_cache.fetch(
                    poster_url,
                    lambda path, i=item: self._onPosterLoaded(i, path),
                    lambda err, i=item: log.warning(
                        "GridWidget: Poster fuer %s konnte nicht geladen werden: %s",
                        getattr(i, "title", "?"), err
                    )
                )

    def _onPosterLoaded(self, item, path):
        item.local_poster_path = path
        if self.instance:
            try:
                self.l.invalidate()
            except Exception:
                pass

    def _getPixmap(self, path):
        if not path:
            return None
        if path in self._pixmap_cache:
            return self._pixmap_cache[path]
        try:
            pixmap = LoadPixmap(path)
        except Exception as e:
            log.warning("GridWidget: LoadPixmap fehlgeschlagen fuer %s: %s", path, e)
            pixmap = None
        # Auch None cachen, damit eine defekte Datei nicht bei jedem Repaint
        # erneut dekodiert wird.
        self._pixmap_cache[path] = pixmap
        return pixmap

    def buildEntry(self, row_idx, row):
        res = [None]
        title_y = self.poster_h + 8
        # r60: row_idx kommt jetzt direkt aus den Listendaten mit (siehe
        # setItems()) statt ueber eine fehleranfaellige Nachschlage-Logik
        # ermittelt zu werden. current_row/current_col werden ausschliesslich
        # von uns selbst (moveUp/moveDown/moveLeft/moveRight/setItems)
        # veraendert - nie vom nativen Cursor abgeleitet, der zwischen
        # Repaint-Durchgaengen inkonsistent sein konnte.
        current_row = self.current_row

        for col, item in enumerate(row):
            x = col * self.item_width
            px = x + max(0, (self.item_width - self.poster_w) // 2)
            poster = self._getPixmap(getattr(item, "local_poster_path", None))
            selected = (row_idx == current_row and col == self.current_col)

            # r38: klar sichtbarer Fokus direkt um das markierte Cover.
            # MultiContentEntryRectangle ist eine OpenATV-Standardkomponente
            # und vermeidet zusaetzliche Bilddateien/Decoder.
            if selected:
                res.append(MultiContentEntryRectangle(
                    pos=(px - 6, 0), size=(self.poster_w + 12, self.poster_h + 12),
                    borderWidth=6, borderColor="#ff8a00"
                ))

            if poster is not None:
                res.append(MultiContentEntryPixmapAlphaTest(
                    pos=(px, 6 if selected else 0), size=(self.poster_w, self.poster_h), png=poster
                ))

            if getattr(item, "is_favorite", False):
                # r57: Herz-Kennzeichen jetzt oben LINKS statt oben rechts -
                # rechts oben sitzen bei vielen Covern bereits eingebrannte
                # Qualitaets-Badges ("4K"/"HDR"), mit denen sich das Herz
                # dort ueberlagert hat ("gruener Balken" hinter dem Herz).
                # Zusaetzlich ein dunkler Hintergrund hinter dem Herz, damit
                # es unabhaengig vom jeweiligen Cover-Motiv lesbar bleibt.
                heart_y = (6 if selected else 0) + 4
                res.append(MultiContentEntryRectangle(
                    pos=(px + 4, heart_y), size=(28, 28),
                    backgroundColor="#000000"
                ))
                res.append(MultiContentEntryText(
                    pos=(px + 4, heart_y), size=(28, 28), font=0, text="♥",
                    color="#ff3b30"
                ))

            title = (getattr(item, "title", "") or "")[:24]
            if selected:
                title = "▶ " + title
            source_label = (getattr(item, "source_label", "") or "").strip()
            title_height = 30 if source_label else 48
            res.append(MultiContentEntryText(
                pos=(x + 8, title_y + (6 if selected else 0)), size=(self.item_width - 16, title_height),
                font=0, text=title, color="#ff8a00" if selected else "#ffffff"
            ))
            if source_label:
                # Keep the source readable below the title without changing
                # HomeScreen rows, whose items have no source_label.
                if len(source_label) > 34:
                    source_label = source_label[:31] + "..."
                res.append(MultiContentEntryText(
                    pos=(x + 8, title_y + 31 + (6 if selected else 0)),
                    size=(self.item_width - 16, 27), font=1, text=source_label,
                    color="#ffb45e" if selected else "#a9adb4"
                ))

        return res

    def getCurrent(self):
        if 0 <= self.current_row < len(self.rows):
            row = self.rows[self.current_row]
            if 0 <= self.current_col < len(row):
                return row[self.current_col]
        return None

    def moveUp(self):
        if self.current_row <= 0:
            return
        self.current_row -= 1
        row = self.rows[self.current_row]
        if self.current_col >= len(row):
            self.current_col = len(row) - 1
        if self.instance:
            self.instance.moveSelection(self.instance.moveUp)
        self.l.invalidate()

    def moveDown(self):
        if self.current_row >= len(self.rows) - 1:
            return
        self.current_row += 1
        row = self.rows[self.current_row]
        if self.current_col >= len(row):
            self.current_col = len(row) - 1
        if self.instance:
            self.instance.moveSelection(self.instance.moveDown)
        self.l.invalidate()

    def moveLeft(self):
        self.current_col = max(0, self.current_col - 1)
        self.l.invalidate()

    def moveRight(self):
        row = self.rows[self.current_row] if 0 <= self.current_row < len(self.rows) else []
        max_col = len(row) - 1 if row else 0
        self.current_col = min(max_col, self.current_col + 1)
        self.l.invalidate()

    def selectPosition(self, row_idx, col_idx):
        """r62: Auswahl gezielt auf eine bestimmte Zeile/Spalte setzen (z.B.
        um nach einem Neuladen die vorherige Position wiederherzustellen).
        Werte werden auf den gueltigen Bereich begrenzt."""
        if not self.rows:
            return
        row_idx = max(0, min(row_idx, len(self.rows) - 1))
        row = self.rows[row_idx]
        col_idx = max(0, min(col_idx, len(row) - 1)) if row else 0
        self.current_row = row_idx
        self.current_col = col_idx
        if self.instance:
            try:
                self.instance.moveSelection(self.instance.moveTop)
                for _ in range(row_idx):
                    self.instance.moveSelection(self.instance.moveDown)
            except Exception as e:
                log.warning("GridWidget r62: Cursor-Sprung fehlgeschlagen: %s", e)
        self.l.invalidate()

    def selectItem(self, item_id, server_name):
        """r62: Auswahl auf ein bestimmtes Item springen lassen (per
        Identitaet statt Position, da sich die Reihenfolge nach einem
        Server-Neuladen aendern kann). Gibt True zurueck, wenn gefunden."""
        for row_idx, row in enumerate(self.rows):
            for col_idx, item in enumerate(row):
                if (getattr(item, "id", None) == item_id
                        and getattr(item, "server_name", None) == server_name):
                    self.selectPosition(row_idx, col_idx)
                    return True
        return False
