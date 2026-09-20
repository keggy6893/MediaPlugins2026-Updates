# -*- coding: utf-8 -*-
"""
r66: Gemeinsame Farbtasten-Legende (ROT/GRUEN/GELB/BLAU) als echte farbige
Buttons statt reinem Fliesstext ("ROT Zurueck GRUEN Oeffnen ..."). Vorlage:
vom Nutzer gezeigte Referenz-Oberflaeche mit farbigen Pillen pro Fernbedienungs-
taste. Wird von LibraryBrowser, SearchScreen, FavoritesBrowser und MediaDetail
gemeinsam genutzt, damit die Legende ueberall gleich aussieht.
"""
from Components.Label import Label

RED = "#a33327"
GREEN = "#2e7d32"
YELLOW = "#a3820a"
BLUE = "#1c5fa8"

_COLORS = {"red": RED, "green": GREEN, "yellow": YELLOW, "blue": BLUE}
_ORDER = ("red", "green", "yellow", "blue")


def skin_widgets(y, x=55, width=250, height=44, gap=14, font_size=22, keys=_ORDER):
    """Liefert die <widget>-Zeilen fuer die angegebenen Farbtasten.

    Reihenfolge/Anzahl ueber `keys` steuerbar (z.B. nur ("red","green","blue")
    wenn ein Screen "gelb" nicht braucht). Gibt zusaetzlich die X-Position
    zurueck, an der ein optionaler weiterer Hinweistext direkt anschliessen
    kann.
    """
    lines = []
    cx = x
    for key in keys:
        color = _COLORS[key]
        lines.append(
            '<widget name="key_%s" position="%d,%d" size="%d,%d" font="Regular;%d" '
            'foregroundColor="#ffffff" backgroundColor="%s" halign="center" valign="center" '
            'transparent="0" zPosition="2" />' % (key, cx, y, width, height, font_size, color)
        )
        cx += width + gap
    return "\n        ".join(lines), cx


def bind(screen, labels, keys=_ORDER):
    """Erzeugt/befuellt die Label-Instanzen fuer die Farbtasten auf screen.

    labels: dict {"red": "Zurueck", "green": "Oeffnen", ...} - nur die in
    keys enthaltenen Eintraege werden gebunden.
    """
    for key in keys:
        screen["key_%s" % key] = Label(labels.get(key, ""))
