# -*- coding: utf-8 -*-
"""
r53: Gemeinsame Duplikat-Erkennung fuer LibraryBrowser/SearchScreen.

Jellyfin/Emby liefern fuer denselben physischen Titel manchmal zwei
Items (z.B. wenn eine Bibliothek mehrere Pfade auf denselben Ordner hat,
oder wenn ein Titel einmal automatisch erkannt und einmal nur anhand des
Ordnernamens mit angehaengter Provider-ID importiert wurde). Beispiele
aus der Praxis:
    "Anaconda"                     vs. "Anaconda (2025) [imdb-tt33244668]"
    "Avatar: Fire and Ash"         vs. "Avatar Fire and Ash (2025) [imdb-tt1757678]"
    "Code Name Banshee (2022)"     vs. "CODE NAME BANSHEE"           (kein Jahr erkannt)
    "The Contractor (2022)"        vs. "THE CONTRACTOR"              (kein Jahr erkannt)
    "Clash of Gods - Krieg der Titanen (2021)" vs. "CLASH_OF_GODS"   (Rohordnername)

Strategie:
  1. Wenn beide Items eine gemeinsame Provider-ID (IMDb/TMDb/TVDb) haben,
     ist das der zuverlaessigste Duplikat-Schluessel.
  2. Sonst: normalisierter Titel (Klammerzusaetze wie "[imdb-tt...]",
     ein am Ende angehaengtes "(JAHR)", Satzzeichen UND Unterstriche
     ignorieren, Gross-/Kleinschreibung ignorieren).
  3. Das Jahr wird dabei nur als zusaetzliche Absicherung genutzt, nicht
     als hartes Kriterium: viele unidentifizierte Rohordner-Items haben
     gar kein ProductionYear (0). Fehlt es auf einer Seite, wird das
     Jahr fuer den Vergleich ignoriert - sind beide Jahre bekannt und
     widersprechen sich, gelten die Items als unterschiedlich.

Grenzen dieses Ansatzes: Titel, die sich nicht nur in Schreibweise/
Satzzeichen, sondern in tatsaechlichen Woertern unterscheiden (z.B.
"Clash of Gods" vs. der vollstaendige Titel "Clash of Gods - Krieg der
Titanen" auf der Rohkopie, oder "Cosmic Sin" vs. "Cosmic Sin - Invasion
im All"), koennen NICHT automatisch zusammengefuehrt werden. Ein reiner
Praefix-/Teilstring-Abgleich waere hier zwar verlockend, wuerde aber bei
Filmreihen mit gemeinsamem Praefix (z.B. verschiedene "Avatar"- oder
"Mission: Impossible"-Teile) faelschlich unterschiedliche Filme
zusammenwerfen - deshalb bewusst nicht implementiert. Wiederholt sich
dieses Muster (identifizierte Kopie + ALLCAPS/Unterstrich-Rohkopie) bei
praktisch jedem Titel einer Bibliothek, deutet das auf einen doppelt
eingebundenen Ordnerpfad in der Jellyfin/Emby-Bibliothek selbst hin -
das laesst sich nur dort (Bibliothek bearbeiten -> Ordner) beheben.
"""
import re

_BRACKET_SUFFIX_RE = re.compile(r"\s*[\[\(](?:imdb|tmdb|tvdb)[-:][^\]\)]*[\]\)]\s*$", re.IGNORECASE)
_YEAR_SUFFIX_RE = re.compile(r"\s*\(\d{4}\)\s*$")
# r53: Unterstriche zaehlen fuer \w als Wortzeichen und wurden bisher NICHT
# als Trenner erkannt ("CLASH_OF_GODS" blieb "clash_of_gods" statt
# "clash of gods" und verfehlte dadurch sogar 1:1-identische Titel).
_SEPARATOR_RE = re.compile(r"[^\w]+|_+", re.UNICODE)
_WS_RE = re.compile(r"\s+")


def normalize_title(title):
    """Normalisiert einen Titel fuer den Duplikatvergleich."""
    t = (title or "").strip()
    if not t:
        return ""
    # Wiederholt anhaengen entfernen, z.B. "X (2025) [imdb-tt123]" -> "X"
    for _ in range(2):
        new_t = _BRACKET_SUFFIX_RE.sub("", t)
        new_t = _YEAR_SUFFIX_RE.sub("", new_t)
        if new_t == t:
            break
        t = new_t.strip()
    t = _SEPARATOR_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip().casefold()
    return t


def provider_key(item):
    """Liefert (Anbieter, ID) fuer die erste bekannte Provider-ID, sonst None."""
    provider_ids = getattr(item, "provider_ids", None) or {}
    for provider in ("imdb", "tmdb", "tvdb"):
        value = (provider_ids.get(provider) or "").strip()
        if value:
            return (provider, value.casefold())
    return None


def dedupe_items(items):
    """Gibt (eindeutige_items, anzahl_dubletten) zurueck; Reihenfolge bleibt erhalten.

    Provider-IDs werden exakt verglichen (Set). Titel-basierte Duplikate
    werden pro normalisiertem Titel gruppiert; innerhalb einer Gruppe gilt
    ein Item nur dann als neues, eigenstaendiges Item, wenn sein Jahr einem
    bereits gesehenen Jahr in dieser Gruppe eindeutig widerspricht (beide
    Jahre bekannt und unterschiedlich). Fehlt das Jahr auf einer Seite,
    zaehlt der Titel-Treffer allein.
    """
    unique = []
    seen_provider_keys = set()
    # normalisierter Titel -> Liste bereits gesehener Jahre (0 = unbekannt)
    title_groups = {}
    duplicates = 0

    for item in (items or []):
        pkey = provider_key(item)
        if pkey:
            if pkey in seen_provider_keys:
                duplicates += 1
                continue
            seen_provider_keys.add(pkey)
            unique.append(item)
            continue

        title = normalize_title(getattr(item, "title", ""))
        year = int(getattr(item, "year", 0) or 0)
        group = title_groups.setdefault(title, [])

        is_duplicate = any(
            seen_year == 0 or year == 0 or seen_year == year
            for seen_year in group
        )
        if is_duplicate:
            duplicates += 1
            continue

        group.append(year)
        unique.append(item)

    return unique, duplicates

