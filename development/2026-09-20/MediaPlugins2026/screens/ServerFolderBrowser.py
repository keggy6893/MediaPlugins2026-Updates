# MEDIAPLUGINS2026_MEDIASERVER_TARGETSTYLE4
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import time

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from enigma import ePoint, eTimer
from skin import parseColor

from ..utils.image_cache import image_cache
from ..utils import log


PAGE_SIZE = 10
COLS = 5

CARD_W = 220
CARD_H = 314
CARD_IMAGE_H = 242

CARD_POS = [
    (48, 245), (288, 245), (528, 245), (768, 245), (1008, 245),
    (48, 585), (288, 585), (528, 585), (768, 585), (1008, 585),
]

SAMPLE_POS = [
    (1372, 715), (1484, 715), (1596, 715), (1708, 715),
]

PROVIDER_COLORS = {
    "EMBY": "#52d273",
    "JELLYFIN": "#38a9ff",
    "PLEX": "#e5ad28",
}

THEME_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "skin", "library_theme",
)


# MEDIAPLUGINS2026_MEDIASERVER_TARGETSTYLE4
# MEDIAPLUGINS2026_MEDIASERVER_DETAILTHEMEFIX1
# MEDIAPLUGINS2026_MEDIASERVER_FOCUS_SUBTLE1
# MEDIAPLUGINS2026_PLEX_LIBRARY_THEMES1
# MEDIAPLUGINS2026_LIBRARY_DUPLICATE_THEMES_FIX1
class ServerFolderBrowser(Screen):
    """TargetStyle4: finale Vorschauoptik mit Library-Art und Cinema-Hintergrund."""

    skinName = "MediaPlugins2026ServerFolderBrowser"
    skin = """
    <screen name="MediaPlugins2026ServerFolderBrowser"
            position="0,0" size="1920,1080" flags="wfNoBorder"
            backgroundColor="#03101a" title="Medienserver">

        <widget name="cinema_bg" position="0,0" size="1920,1080"
                alphatest="blend" scale="1" zPosition="0" />

        <!-- Header -->
        <widget name="header" position="28,18" size="450,55" font="Regular;38"
                foregroundColor="#f4f7fa" transparent="1" zPosition="4" />
        <widget name="brand" position="1385,22" size="430,40" font="Regular;26"
                foregroundColor="#dbe7ee" transparent="1" halign="right" zPosition="4" />
        <widget name="clock" position="1830,18" size="75,45" font="Regular;30"
                foregroundColor="#f3f6f8" transparent="1" halign="right" zPosition="4" />

        <widget name="provider_icon" position="48,92" size="58,58" alphatest="blend" scale="1" zPosition="4" />
        <widget name="provider_mark" position="48,94" size="54,54" font="Regular;46"
                foregroundColor="#52d273" transparent="1" halign="center" valign="center" />
        <widget name="title" position="116,92" size="1040,62" font="Regular;42"
                foregroundColor="#ffffff" transparent="1" />
        <widget name="hint" position="48,160" size="1160,42" font="Regular;23"
                foregroundColor="#d4dde4" transparent="1" />
        <widget name="server_alias" position="48,198" size="1160,32" font="Regular;19"
                foregroundColor="#20c8f4" transparent="1" />
        <widget name="brand_sub" position="1360,58" size="450,28" font="Regular;16"
                foregroundColor="#8599a7" transparent="1" halign="right" />

        <!-- 10 Library cards -->
        <widget name="card_bg0" position="48,245" size="220,314" backgroundColor="#0a1925" transparent="0" zPosition="1" />
        <widget name="card_bg1" position="288,245" size="220,314" backgroundColor="#0a1925" transparent="0" zPosition="1" />
        <widget name="card_bg2" position="528,245" size="220,314" backgroundColor="#0a1925" transparent="0" zPosition="1" />
        <widget name="card_bg3" position="768,245" size="220,314" backgroundColor="#0a1925" transparent="0" zPosition="1" />
        <widget name="card_bg4" position="1008,245" size="220,314" backgroundColor="#0a1925" transparent="0" zPosition="1" />
        <widget name="card_bg5" position="48,585" size="220,314" backgroundColor="#0a1925" transparent="0" zPosition="1" />
        <widget name="card_bg6" position="288,585" size="220,314" backgroundColor="#0a1925" transparent="0" zPosition="1" />
        <widget name="card_bg7" position="528,585" size="220,314" backgroundColor="#0a1925" transparent="0" zPosition="1" />
        <widget name="card_bg8" position="768,585" size="220,314" backgroundColor="#0a1925" transparent="0" zPosition="1" />
        <widget name="card_bg9" position="1008,585" size="220,314" backgroundColor="#0a1925" transparent="0" zPosition="1" />

        <widget name="card_img0" position="54,251" size="208,302" alphatest="blend" scale="1" zPosition="2" />
        <widget name="card_img1" position="294,251" size="208,302" alphatest="blend" scale="1" zPosition="2" />
        <widget name="card_img2" position="534,251" size="208,302" alphatest="blend" scale="1" zPosition="2" />
        <widget name="card_img3" position="774,251" size="208,302" alphatest="blend" scale="1" zPosition="2" />
        <widget name="card_img4" position="1014,251" size="208,302" alphatest="blend" scale="1" zPosition="2" />
        <widget name="card_img5" position="54,591" size="208,302" alphatest="blend" scale="1" zPosition="2" />
        <widget name="card_img6" position="294,591" size="208,302" alphatest="blend" scale="1" zPosition="2" />
        <widget name="card_img7" position="534,591" size="208,302" alphatest="blend" scale="1" zPosition="2" />
        <widget name="card_img8" position="774,591" size="208,302" alphatest="blend" scale="1" zPosition="2" />
        <widget name="card_img9" position="1014,591" size="208,302" alphatest="blend" scale="1" zPosition="2" />

        <widget name="card_alias0" position="63,258" size="178,27" font="Regular;17"
                foregroundColor="#ffffff" backgroundColor="#0b2231" transparent="0"
                halign="center" valign="center" zPosition="6" />
        <widget name="card_alias1" position="303,258" size="178,27" font="Regular;17"
                foregroundColor="#ffffff" backgroundColor="#0b2231" transparent="0"
                halign="center" valign="center" zPosition="6" />
        <widget name="card_alias2" position="543,258" size="178,27" font="Regular;17"
                foregroundColor="#ffffff" backgroundColor="#0b2231" transparent="0"
                halign="center" valign="center" zPosition="6" />
        <widget name="card_alias3" position="783,258" size="178,27" font="Regular;17"
                foregroundColor="#ffffff" backgroundColor="#0b2231" transparent="0"
                halign="center" valign="center" zPosition="6" />
        <widget name="card_alias4" position="1023,258" size="178,27" font="Regular;17"
                foregroundColor="#ffffff" backgroundColor="#0b2231" transparent="0"
                halign="center" valign="center" zPosition="6" />
        <widget name="card_alias5" position="63,598" size="178,27" font="Regular;17"
                foregroundColor="#ffffff" backgroundColor="#0b2231" transparent="0"
                halign="center" valign="center" zPosition="6" />
        <widget name="card_alias6" position="303,598" size="178,27" font="Regular;17"
                foregroundColor="#ffffff" backgroundColor="#0b2231" transparent="0"
                halign="center" valign="center" zPosition="6" />
        <widget name="card_alias7" position="543,598" size="178,27" font="Regular;17"
                foregroundColor="#ffffff" backgroundColor="#0b2231" transparent="0"
                halign="center" valign="center" zPosition="6" />
        <widget name="card_alias8" position="783,598" size="178,27" font="Regular;17"
                foregroundColor="#ffffff" backgroundColor="#0b2231" transparent="0"
                halign="center" valign="center" zPosition="6" />
        <widget name="card_alias9" position="1023,598" size="178,27" font="Regular;17"
                foregroundColor="#ffffff" backgroundColor="#0b2231" transparent="0"
                halign="center" valign="center" zPosition="6" />

        <!-- Dynamic library initials over the themed artwork -->
        <widget name="card_letter0" position="54,285" size="208,120" font="Regular;72" foregroundColor="#eaf8ff" transparent="1" halign="center" valign="center" zPosition="6" />
        <widget name="card_letter1" position="294,285" size="208,120" font="Regular;72" foregroundColor="#eaf8ff" transparent="1" halign="center" valign="center" zPosition="6" />
        <widget name="card_letter2" position="534,285" size="208,120" font="Regular;72" foregroundColor="#eaf8ff" transparent="1" halign="center" valign="center" zPosition="6" />
        <widget name="card_letter3" position="774,285" size="208,120" font="Regular;72" foregroundColor="#eaf8ff" transparent="1" halign="center" valign="center" zPosition="6" />
        <widget name="card_letter4" position="1014,285" size="208,120" font="Regular;72" foregroundColor="#eaf8ff" transparent="1" halign="center" valign="center" zPosition="6" />
        <widget name="card_letter5" position="54,625" size="208,120" font="Regular;72" foregroundColor="#eaf8ff" transparent="1" halign="center" valign="center" zPosition="6" />
        <widget name="card_letter6" position="294,625" size="208,120" font="Regular;72" foregroundColor="#eaf8ff" transparent="1" halign="center" valign="center" zPosition="6" />
        <widget name="card_letter7" position="534,625" size="208,120" font="Regular;72" foregroundColor="#eaf8ff" transparent="1" halign="center" valign="center" zPosition="6" />
        <widget name="card_letter8" position="774,625" size="208,120" font="Regular;72" foregroundColor="#eaf8ff" transparent="1" halign="center" valign="center" zPosition="6" />
        <widget name="card_letter9" position="1014,625" size="208,120" font="Regular;72" foregroundColor="#eaf8ff" transparent="1" halign="center" valign="center" zPosition="6" />
        <widget name="detail_letter" position="1310,150" size="190,130" font="Regular;86" foregroundColor="#eaf8ff" transparent="1" halign="center" valign="center" zPosition="6" />

        <widget name="card_text_bg0" position="54,463" size="208,90" backgroundColor="#08131d" transparent="0" zPosition="3" />
        <widget name="card_title0" position="64,471" size="188,35" font="Regular;19" foregroundColor="#ffffff" transparent="1" zPosition="4" />
        <widget name="card_count0" position="64,512" size="150,27" font="Regular;19" foregroundColor="#b3c1cb" transparent="1" zPosition="4" />
        <widget name="card_badge0" position="214,508" size="38,29" font="Regular;18" foregroundColor="#ffffff" backgroundColor="#1687b6" transparent="0" halign="center" valign="center" zPosition="5" />
        <widget name="card_text_bg1" position="294,463" size="208,90" backgroundColor="#08131d" transparent="0" zPosition="3" />
        <widget name="card_title1" position="304,471" size="188,35" font="Regular;19" foregroundColor="#ffffff" transparent="1" zPosition="4" />
        <widget name="card_count1" position="304,512" size="150,27" font="Regular;19" foregroundColor="#b3c1cb" transparent="1" zPosition="4" />
        <widget name="card_badge1" position="454,508" size="38,29" font="Regular;18" foregroundColor="#ffffff" backgroundColor="#1687b6" transparent="0" halign="center" valign="center" zPosition="5" />
        <widget name="card_text_bg2" position="534,463" size="208,90" backgroundColor="#08131d" transparent="0" zPosition="3" />
        <widget name="card_title2" position="544,471" size="188,35" font="Regular;19" foregroundColor="#ffffff" transparent="1" zPosition="4" />
        <widget name="card_count2" position="544,512" size="150,27" font="Regular;19" foregroundColor="#b3c1cb" transparent="1" zPosition="4" />
        <widget name="card_badge2" position="694,508" size="38,29" font="Regular;18" foregroundColor="#ffffff" backgroundColor="#1687b6" transparent="0" halign="center" valign="center" zPosition="5" />
        <widget name="card_text_bg3" position="774,463" size="208,90" backgroundColor="#08131d" transparent="0" zPosition="3" />
        <widget name="card_title3" position="784,471" size="188,35" font="Regular;19" foregroundColor="#ffffff" transparent="1" zPosition="4" />
        <widget name="card_count3" position="784,512" size="150,27" font="Regular;19" foregroundColor="#b3c1cb" transparent="1" zPosition="4" />
        <widget name="card_badge3" position="934,508" size="38,29" font="Regular;18" foregroundColor="#ffffff" backgroundColor="#1687b6" transparent="0" halign="center" valign="center" zPosition="5" />
        <widget name="card_text_bg4" position="1014,463" size="208,90" backgroundColor="#08131d" transparent="0" zPosition="3" />
        <widget name="card_title4" position="1024,471" size="188,35" font="Regular;19" foregroundColor="#ffffff" transparent="1" zPosition="4" />
        <widget name="card_count4" position="1024,512" size="150,27" font="Regular;19" foregroundColor="#b3c1cb" transparent="1" zPosition="4" />
        <widget name="card_badge4" position="1174,508" size="38,29" font="Regular;18" foregroundColor="#ffffff" backgroundColor="#1687b6" transparent="0" halign="center" valign="center" zPosition="5" />
        <widget name="card_text_bg5" position="54,803" size="208,90" backgroundColor="#08131d" transparent="0" zPosition="3" />
        <widget name="card_title5" position="64,811" size="188,35" font="Regular;19" foregroundColor="#ffffff" transparent="1" zPosition="4" />
        <widget name="card_count5" position="64,852" size="150,27" font="Regular;19" foregroundColor="#b3c1cb" transparent="1" zPosition="4" />
        <widget name="card_badge5" position="214,848" size="38,29" font="Regular;18" foregroundColor="#ffffff" backgroundColor="#1687b6" transparent="0" halign="center" valign="center" zPosition="5" />
        <widget name="card_text_bg6" position="294,803" size="208,90" backgroundColor="#08131d" transparent="0" zPosition="3" />
        <widget name="card_title6" position="304,811" size="188,35" font="Regular;19" foregroundColor="#ffffff" transparent="1" zPosition="4" />
        <widget name="card_count6" position="304,852" size="150,27" font="Regular;19" foregroundColor="#b3c1cb" transparent="1" zPosition="4" />
        <widget name="card_badge6" position="454,848" size="38,29" font="Regular;18" foregroundColor="#ffffff" backgroundColor="#1687b6" transparent="0" halign="center" valign="center" zPosition="5" />
        <widget name="card_text_bg7" position="534,803" size="208,90" backgroundColor="#08131d" transparent="0" zPosition="3" />
        <widget name="card_title7" position="544,811" size="188,35" font="Regular;19" foregroundColor="#ffffff" transparent="1" zPosition="4" />
        <widget name="card_count7" position="544,852" size="150,27" font="Regular;19" foregroundColor="#b3c1cb" transparent="1" zPosition="4" />
        <widget name="card_badge7" position="694,848" size="38,29" font="Regular;18" foregroundColor="#ffffff" backgroundColor="#1687b6" transparent="0" halign="center" valign="center" zPosition="5" />
        <widget name="card_text_bg8" position="774,803" size="208,90" backgroundColor="#08131d" transparent="0" zPosition="3" />
        <widget name="card_title8" position="784,811" size="188,35" font="Regular;19" foregroundColor="#ffffff" transparent="1" zPosition="4" />
        <widget name="card_count8" position="784,852" size="150,27" font="Regular;19" foregroundColor="#b3c1cb" transparent="1" zPosition="4" />
        <widget name="card_badge8" position="934,848" size="38,29" font="Regular;18" foregroundColor="#ffffff" backgroundColor="#1687b6" transparent="0" halign="center" valign="center" zPosition="5" />
        <widget name="card_text_bg9" position="1014,803" size="208,90" backgroundColor="#08131d" transparent="0" zPosition="3" />
        <widget name="card_title9" position="1024,811" size="188,35" font="Regular;19" foregroundColor="#ffffff" transparent="1" zPosition="4" />
        <widget name="card_count9" position="1024,852" size="150,27" font="Regular;19" foregroundColor="#b3c1cb" transparent="1" zPosition="4" />
        <widget name="card_badge9" position="1174,848" size="38,29" font="Regular;18" foregroundColor="#ffffff" backgroundColor="#1687b6" transparent="0" halign="center" valign="center" zPosition="5" />

        <!-- Pixel-exact focus overlay: card 220x314 + 6px margin -->
        <widget name="focus_frame" position="42,239" size="232,326" alphatest="blend" scale="1" zPosition="8" />

        <!-- Right detail panel -->
        <widget name="detail_bg" position="1280,112" size="600,787" backgroundColor="#071723" transparent="0" zPosition="1" />
        <widget name="detail_border_top" position="1280,112" size="600,2" backgroundColor="#173f55" transparent="0" zPosition="5" />
        <widget name="detail_border_bottom" position="1280,897" size="600,2" backgroundColor="#173f55" transparent="0" zPosition="5" />
        <widget name="detail_border_left" position="1280,112" size="2,787" backgroundColor="#173f55" transparent="0" zPosition="5" />
        <widget name="detail_border_right" position="1878,112" size="2,787" backgroundColor="#173f55" transparent="0" zPosition="5" />
        <widget name="detail_image" position="1296,128" size="568,390" alphatest="blend" scale="1" zPosition="2" />
        <widget name="detail_title" position="1302,535" size="550,48" font="Regular;34" foregroundColor="#ffffff" transparent="1" zPosition="3" />
        <widget name="detail_count" position="1302,585" size="550,34" font="Regular;22" foregroundColor="#9fb3c1" transparent="1" zPosition="3" />
        <widget name="detail_text" position="1302,628" size="550,74" font="Regular;21" foregroundColor="#b8c6d0" transparent="1" zPosition="3" />

        <widget name="sample0" position="1302,718" size="100,150" alphatest="on" scale="1" zPosition="3" />
        <widget name="sample1" position="1414,718" size="100,150" alphatest="on" scale="1" zPosition="3" />
        <widget name="sample2" position="1526,718" size="100,150" alphatest="on" scale="1" zPosition="3" />
        <widget name="sample3" position="1638,718" size="100,150" alphatest="on" scale="1" zPosition="3" />
        <widget name="sample4" position="1750,718" size="100,150" alphatest="on" scale="1" zPosition="3" />

        <!-- Footer -->
        <widget name="key_red_box" position="48,981" size="34,34" backgroundColor="#ef3340" transparent="0" />
        <widget name="key_red" position="96,978" size="135,40" font="Regular;22"
                foregroundColor="#ffffff" transparent="1" valign="center" />
        <widget name="key_green_box" position="280,981" size="34,34" backgroundColor="#19c979" transparent="0" />
        <widget name="key_green" position="328,978" size="160,40" font="Regular;22"
                foregroundColor="#ffffff" transparent="1" valign="center" />
        <widget name="key_yellow_box" position="520,981" size="34,34" backgroundColor="#f0c51d" transparent="0" />
        <widget name="key_yellow" position="568,978" size="180,40" font="Regular;22"
                foregroundColor="#ffffff" transparent="1" valign="center" />
        <widget name="key_blue_box" position="790,981" size="34,34" backgroundColor="#26a7ef" transparent="0" />
        <widget name="key_blue" position="838,978" size="180,40" font="Regular;22"
                foregroundColor="#ffffff" transparent="1" valign="center" />
        <widget name="page" position="1245,982" size="310,35" font="Regular;21"
                foregroundColor="#94a7b5" transparent="1" halign="right" />
        <widget name="total" position="1570,982" size="300,35" font="Regular;21"
                foregroundColor="#94a7b5" transparent="1" halign="right" />
    </screen>
    """

    def __init__(self, session, title, server_names, server_libraries, clients):
        Screen.__init__(self, session)
        self.session = session
        self.server_names = list(server_names or [])
        self.server_libraries = server_libraries or {}
        self.clients = clients or {}

        self.entries = []
        self.start_index = 0
        self.selected = 0
        self._child_open = False
        self._closing = False

        self._image_request = 0
        self._preview_request = 0
        self._tile_preview_generation = 0
        self._detail_image_generation = 0
        self._tile_preview_pending = set()
        self._preview_cache = {}
        self._library_image_paths = {}
        self._server_display_names = {}
        self._server_display_failed = set()
        self._server_display_request = 0
        self._themed_library_ids = set()

        self["cinema_bg"] = Pixmap()
        self["header"] = Label(_("Medienserver"))
        self["brand"] = Label("Media Plugins 2026")
        self["brand_sub"] = Label(_("Filme. Serien. Musik. Alles in einer Oberfläche."))
        self["clock"] = Label("")
        self["provider_icon"] = Pixmap()
        self["provider_mark"] = Label("◆")
        self["title"] = Label(title)
        self["hint"] = Label(_("Wähle eine Bibliothek, um den Inhalt zu durchsuchen."))
        self["server_alias"] = Label("")

        for i in range(PAGE_SIZE):
            self["card_bg%d" % i] = Label("")
            self["card_img%d" % i] = Pixmap()
            self["card_text_bg%d" % i] = Label("")
            self["card_title%d" % i] = Label("")
            self["card_count%d" % i] = Label("")
            self["card_badge%d" % i] = Label("")
            self["card_alias%d" % i] = Label("")
            self["card_letter%d" % i] = Label("")

        self["focus_frame"] = Pixmap()

        self["detail_bg"] = Label("")
        self["detail_border_top"] = Label("")
        self["detail_border_bottom"] = Label("")
        self["detail_border_left"] = Label("")
        self["detail_border_right"] = Label("")
        self["detail_image"] = Pixmap()
        self["detail_letter"] = Label("")
        self["detail_title"] = Label("")
        self["detail_count"] = Label("")
        self["detail_text"] = Label("")

        for i in range(5):
            self["sample%d" % i] = Pixmap()

        self["key_red_box"] = Label("")
        self["key_green_box"] = Label("")
        self["key_yellow_box"] = Label("")
        self["key_blue_box"] = Label("")
        self["key_red"] = Label(_("Zurück"))
        self["key_green"] = Label(_("Öffnen"))
        self["key_yellow"] = Label(_("Neu laden"))
        self["key_blue"] = Label(_("Startseite"))
        self["page"] = Label("")
        self["total"] = Label("")

        self._clock_timer = eTimer()
        self._clock_timer.callback.append(self._updateClock)

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.keyOpen,
                "cancel": self.keyCancel,
                "left": self.keyLeft,
                "right": self.keyRight,
                "up": self.keyUp,
                "down": self.keyDown,
                "red": self.keyCancel,
                "green": self.keyOpen,
                "yellow": self.keyRefreshPreview,
                "blue": self.keyCancel,
            },
            -2,
        )

        self.onClose.append(self._onClose)
        self.onLayoutFinish.append(self._applyCinemaBackground)
        self.onLayoutFinish.append(self._buildList)
        self.onLayoutFinish.append(self._startClock)

    def _applyCinemaBackground(self):
        path = os.path.join(THEME_DIR, "mediaserver_bg.jpg")
        try:
            if os.path.isfile(path) and self["cinema_bg"].instance:
                self["cinema_bg"].instance.setScale(1)
                self["cinema_bg"].instance.setPixmapFromFile(path)
                self["cinema_bg"].show()
        except Exception as exc:
            log.debug("CinemaUI Hintergrund: %s", exc)

    @staticmethod
    def _themeKey(title):
        value = (title or "").strip().lower()
        value = (
            value.replace("ö", "oe")
                 .replace("ä", "ae")
                 .replace("ü", "ue")
                 .replace("ß", "ss")
        )
        if "hoer" in value:
            return "hoerbuecher"
        if "konzert" in value or ("musik" in value and "serie" not in value):
            return "konzerte"
        if "serie" in value:
            if "anime" in value:
                return "serien_anime"
            if (
                "bald weg" in value or "baldweg" in value
                or "leaving" in value or "expire" in value
            ):
                return "serien_baldweg"
            if "doku" in value or "reality" in value:
                return "serien_doku"
            if (
                "kids" in value or "kinder" in value
                or "family" in value or "familie" in value
            ):
                return "serien_kids"
            if "sport" in value:
                return "serien_sport"
            if "vintage" in value or "klassiker" in value or "classic" in value:
                return "serien_vintage"
            if "4k" in value or "uhd" in value:
                return "serien_4k"
            if "o-ton" in value or "oton" in value or "original" in value:
                return "serien_oton"
            return "serien"
        if "film" in value:
            # Providerneutral: Plex nennt Bibliotheken oft z.B.
            # "Filme - Kids", "Filme - Doku", "Filme - KinoStart" usw.
            if "adult" in value or "18+" in value or "erwachsen" in value:
                return "filme_adult"
            if "anime" in value:
                return "filme_anime"
            if "sport" in value:
                return "filme_sport"
            if "vintage" in value or "klassiker" in value or "classic" in value:
                return "filme_vintage"
            if (
                "bald weg" in value or "baldweg" in value
                or "leaving" in value or "expire" in value
            ):
                return "filme_baldweg"
            if "doku" in value or "document" in value:
                return "filme_doku"
            if (
                "kids" in value or "kinder" in value
                or "family" in value or "familie" in value
            ):
                return "filme_kids"
            if (
                "kinostart" in value or "kino start" in value
                or "premiere" in value or "neu im kino" in value
            ):
                return "filme_kinostart"
            if "3d" in value:
                return "filme_3d"
            if "4k" in value or "uhd" in value:
                return "filme_4k"
            if "o-ton" in value or "oton" in value or "original" in value:
                return "filme_oton"
            return "filme"
        return None

    @staticmethod
    def _libraryInitial(title):
        value = (title or "").strip()
        upper = value.upper()
        if "4K" in upper or "UHD" in upper:
            return "4K"
        # "Filme Laufwerk D" -> D, otherwise first useful word/character.
        parts = [p for p in value.replace("-", " ").split() if p]
        if "LAUFWERK" in upper and parts:
            return parts[-1][:2].upper()
        skip = set(("FILME", "FILM", "MOVIES", "MOVIE", "SERIEN", "SERIES", "LIBRARY", "BIBLIOTHEK"))
        for part in parts:
            if part.upper() not in skip:
                return part[:1].upper()
        return (parts[0][:1].upper() if parts else "•")

    def _dynamicThemePath(self, absolute_index):
        names = ("cyan", "gold", "green", "violet", "red")
        name = names[int(absolute_index or 0) % len(names)]
        path = os.path.join(THEME_DIR, "library_dynamic_%s.jpg" % name)
        return path if os.path.isfile(path) else None

    def _themePathForItem(self, item):
        key = self._themeKey(getattr(item, "title", "") or "")
        if not key:
            return None
        path = os.path.join(THEME_DIR, key + ".jpg")
        return path if os.path.isfile(path) else None

    def _themeDetailPathForItem(self, item):
        key = self._themeKey(getattr(item, "title", "") or "")
        if key:
            detail = os.path.join(THEME_DIR, "detail_" + key + ".jpg")
            if os.path.isfile(detail):
                return detail
        if key == "filme":
            special = os.path.join(THEME_DIR, "detail_filme.jpg")
            if os.path.isfile(special):
                return special
        if key:
            path = os.path.join(THEME_DIR, key + ".jpg")
            if os.path.isfile(path):
                return path
        return None

    def _showThemeCard(self, pos, item):
        path = self._themePathForItem(item)
        if not path:
            return False
        lib_id = self._libraryKey(item)
        if lib_id:
            self._themed_library_ids.add(lib_id)
            self._library_image_paths[lib_id] = path
        try:
            widget = self["card_img%d" % pos]
            if widget.instance:
                widget.instance.setScale(1)
                widget.instance.setPixmapFromFile(path)
                widget.show()
                return True
        except Exception as exc:
            log.debug("CinemaUI Theme-Kachel %d: %s", pos, exc)
        return False

    # ------------------------------------------------------------------
    # Provider / Header
    # ------------------------------------------------------------------
    def _provider(self):
        for item in self.entries:
            value = (getattr(item, "source_label", "") or "").strip().upper()
            if value:
                return value
        text = (self["title"].getText() or "").upper()
        for provider in ("EMBY", "JELLYFIN", "PLEX"):
            if provider in text:
                return provider
        return ""

    def _applyProviderAccent(self):
        provider = self._provider()
        color = PROVIDER_COLORS.get(provider, "#20c8f4")
        try:
            self["provider_mark"].instance.setForegroundColor(parseColor(color))
        except Exception:
            pass

        # Echtes Provider-Icon aus unserem Plugin verwenden, falls vorhanden.
        try:
            root = os.path.dirname(os.path.dirname(__file__))
            icon = os.path.join(
                root, "skin", "icons", "provider_%s.png" % provider.lower()
            )
            if provider and os.path.isfile(icon) and self["provider_icon"].instance:
                self["provider_icon"].instance.setScale(1)
                self["provider_icon"].instance.setPixmapFromFile(icon)
                self["provider_icon"].show()
                self["provider_mark"].hide()
            else:
                self["provider_icon"].hide()
                self["provider_mark"].show()
        except Exception:
            try:
                self["provider_icon"].hide()
                self["provider_mark"].show()
            except Exception:
                pass

    def _startClock(self):
        self._updateClock()
        try:
            self._clock_timer.start(30000, False)
        except Exception:
            pass

    def _updateClock(self):
        if self._closing:
            return
        try:
            self["clock"].setText(time.strftime("%H:%M"))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Libraries / Grid
    # ------------------------------------------------------------------
    # MEDIAPLUGINS2026_SERVER_ALIAS_LABELS1_HUB
    # MEDIAPLUGINS2026_REMOTE_SERVERNAME1_HUB
    def _aliasSummary(self):
        aliases = []
        unresolved = False

        for technical_name in self.server_names:
            display = str(
                self._server_display_names.get(technical_name, "") or ""
            ).strip()
            if display:
                if display not in aliases:
                    aliases.append(display)
                continue

            if technical_name in self._server_display_failed:
                fallback = str(technical_name or "").strip()
                if fallback and fallback not in aliases:
                    aliases.append(fallback)
            else:
                unresolved = True

        if not aliases and unresolved:
            return _("Server: wird ermittelt …")
        if not aliases:
            return _("Server: Unbekannt")
        if len(aliases) == 1 and not unresolved:
            return _("Server: %s") % aliases[0]

        shown = list(aliases)
        if unresolved:
            shown.append("…")

        if len(shown) <= 3:
            return _("Server: %s") % "  ·  ".join(shown)
        return _("Server: %s  ·  +%d") % (
            "  ·  ".join(shown[:2]),
            len(shown) - 2,
        )

    def _resolveServerDisplayNames(self):
        self._server_display_request += 1
        request = self._server_display_request

        for technical_name in self.server_names:
            client = self.clients.get(technical_name)
            getter = getattr(client, "get_server_display_name", None)
            if not callable(getter):
                self._server_display_failed.add(technical_name)
                continue

            try:
                getter(
                    lambda name, key=technical_name, req=request:
                        self._onServerDisplayName(key, name, req),
                    lambda err, key=technical_name, req=request:
                        self._onServerDisplayNameError(key, err, req),
                )
            except Exception as exc:
                self._onServerDisplayNameError(
                    technical_name,
                    str(exc),
                    request,
                )

        self._refreshServerAliasLabels()

    def _onServerDisplayName(self, technical_name, display_name, request):
        if self._closing or request != self._server_display_request:
            return

        display_name = str(display_name or "").strip()
        if not display_name:
            self._onServerDisplayNameError(
                technical_name,
                "leerer Servername",
                request,
            )
            return

        self._server_display_names[technical_name] = display_name
        self._server_display_failed.discard(technical_name)
        log.info(
            "Medienserver Anzeigename: %s -> %s",
            technical_name,
            display_name,
        )
        self._refreshServerAliasLabels()

    def _onServerDisplayNameError(self, technical_name, err, request):
        if self._closing or request != self._server_display_request:
            return
        self._server_display_failed.add(technical_name)
        log.debug(
            "Medienserver Anzeigename nicht lesbar (%s): %s",
            technical_name,
            err,
        )
        self._refreshServerAliasLabels()

    def _displayNameForTechnical(self, technical_name):
        value = str(
            self._server_display_names.get(technical_name, "") or ""
        ).strip()
        if value:
            return value
        if technical_name in self._server_display_failed:
            return str(technical_name or "").strip()
        return ""

    def _refreshServerAliasLabels(self):
        try:
            self["server_alias"].setText(self._aliasSummary())
        except Exception:
            pass

        visible = self._visible()
        for pos in range(PAGE_SIZE):
            try:
                self["card_alias%d" % pos].setText("")
                self["card_alias%d" % pos].hide()
            except Exception:
                pass

        if len(self.server_names) <= 1:
            return

        for pos, item in enumerate(visible):
            technical_name = str(
                getattr(item, "server_name", "") or ""
            ).strip()
            display = self._displayNameForTechnical(technical_name)
            if not display:
                continue
            try:
                self["card_alias%d" % pos].setText(display)
                self["card_alias%d" % pos].show()
            except Exception:
                pass

    def _buildList(self):
        self.entries = []
        self["server_alias"].setText(self._aliasSummary())

        for server_name in self.server_names:
            for item in self.server_libraries.get(server_name, []):
                self.entries.append(item)

        self.start_index = 0
        self.selected = 0
        self._applyProviderAccent()
        self._renderPage()
        self._resolveServerDisplayNames()

        log.info(
            "ServerFolderBrowser CinemaUI: %s Bibliotheken=%d",
            self["title"].getText(),
            len(self.entries),
        )

        if not self.entries:
            self["hint"].setText(_("Keine Bibliotheken gefunden"))
            self._clearDetail()

    def _visible(self):
        return self.entries[self.start_index:self.start_index + PAGE_SIZE]

    def _renderPage(self):
        self._image_request += 1
        request = self._image_request
        visible = self._visible()

        for i in range(PAGE_SIZE):
            self["card_title%d" % i].setText("")
            self["card_count%d" % i].setText("")
            self["card_badge%d" % i].setText("")
            self["card_alias%d" % i].setText("")
            self["card_letter%d" % i].setText("")
            # Empty slots must be completely invisible; otherwise the fixed
            # skin backgrounds create a fake second row.
            for name in ("card_bg", "card_img", "card_text_bg", "card_title", "card_count", "card_badge", "card_alias", "card_letter"):
                try:
                    self["%s%d" % (name, i)].hide()
                except Exception:
                    pass

        for i, item in enumerate(visible):
            # Show only slots that really contain a library.
            for name in ("card_bg", "card_text_bg", "card_title", "card_count", "card_letter"):
                try:
                    self["%s%d" % (name, i)].show()
                except Exception:
                    pass
            title = getattr(item, "title", "") or _("Bibliothek")
            self["card_title%d" % i].setText(title)

            if len(self.server_names) > 1:
                technical_name = str(
                    getattr(item, "server_name", "") or ""
                ).strip()
                item_alias = self._displayNameForTechnical(technical_name)
                if item_alias:
                    self["card_alias%d" % i].setText(item_alias)
                    try:
                        self["card_alias%d" % i].show()
                    except Exception:
                        pass

            lib_id = str(getattr(item, "library_id", None) or getattr(item, "id", "") or "")
            cached_preview = self._preview_cache.get(lib_id)
            if cached_preview:
                total = int(cached_preview.get("total", 0) or 0)
                self["card_count%d" % i].setText(
                    _("%d Einträge") % total if total else _("Bibliothek")
                )
            else:
                self["card_count%d" % i].setText(_("Bibliothek"))

            upper_title = title.upper()
            badge = ""
            if "3D" in upper_title:
                badge = "3D"
            elif "4K" in upper_title or "UHD" in upper_title:
                badge = "4K"
            if badge:
                self["card_badge%d" % i].setText(badge)
                try:
                    self["card_badge%d" % i].show()
                except Exception:
                    pass

            # Provider-/serverneutral: color theme follows card position, initial follows library name.
            dynamic_path = self._dynamicThemePath(self.start_index + i)
            if dynamic_path:
                try:
                    widget = self["card_img%d" % i]
                    if widget.instance:
                        widget.instance.setScale(1)
                        widget.instance.setPixmapFromFile(dynamic_path)
                        widget.show()
                except Exception as exc:
                    log.debug("Dynamic Library-Art %d: %s", i, exc)
            self["card_letter%d" % i].setText(self._libraryInitial(title))

        pages = max(1, (len(self.entries) + PAGE_SIZE - 1) // PAGE_SIZE)
        page_no = min(pages, (self.start_index // PAGE_SIZE) + 1)
        self["page"].setText(_("Seite %d/%d") % (page_no, pages) if pages > 1 else "")
        self["total"].setText(_("Insgesamt %d Bibliotheken") % len(self.entries))

        if visible:
            self.selected = min(self.selected, len(visible) - 1)
            self._updateFocus()
            self._prefetchVisibleLibraries()
            self._loadSelectedPreview()
        else:
            self._showFocus(False)

    def _libraryKey(self, item):
        return str(
            getattr(item, "library_id", None)
            or getattr(item, "id", "")
            or ""
        )

    def _prefetchVisibleLibraries(self):
        self._tile_preview_generation += 1
        generation = self._tile_preview_generation
        self._tile_preview_pending = set()

        for pos, item in enumerate(self._visible()):
            lib_id = self._libraryKey(item)
            client = self.clients.get(getattr(item, "server_name", ""))

            cached = self._preview_cache.get(lib_id)
            if cached:
                total = int(cached.get("total", 0) or 0)
                self["card_count%d" % pos].setText(
                    _("%d Einträge") % total if total else _("Bibliothek")
                )
                self._applyTileRepresentative(
                    pos, item, cached.get("items", []), generation
                )
                continue

            if not lib_id or client is None or lib_id in self._tile_preview_pending:
                continue

            self._tile_preview_pending.add(lib_id)
            try:
                client.get_items(
                    lib_id,
                    lambda media, total, p=pos, target=item, gen=generation:
                        self._onTilePreviewLoaded(p, target, media, total, gen),
                    lambda err, lid=lib_id, gen=generation:
                        self._onTilePreviewError(lid, err, gen),
                    start_index=0,
                    limit=1,
                    sort_by="SortName",
                )
            except Exception as exc:
                self._onTilePreviewError(lib_id, str(exc), generation)

    def _onTilePreviewLoaded(self, pos, target, media, total, generation):
        if self._closing or generation != self._tile_preview_generation:
            return

        lib_id = self._libraryKey(target)
        self._tile_preview_pending.discard(lib_id)

        items = list(media or [])[:1]
        old = self._preview_cache.get(lib_id) or {}
        old_items = list(old.get("items", []) or [])
        data = {
            "total": int(total or old.get("total", 0) or len(items)),
            "items": old_items if len(old_items) > len(items) else items,
        }
        self._preview_cache[lib_id] = data

        visible = self._visible()
        if not (0 <= pos < len(visible)):
            return
        if self._libraryKey(visible[pos]) != lib_id:
            return

        self["card_count%d" % pos].setText(
            _("%d Einträge") % data["total"] if data["total"] else _("Bibliothek")
        )
        self._applyTileRepresentative(pos, target, data["items"], generation)

        if target is self._current():
            self["detail_count"].setText(
                _("%d Einträge") % data["total"] if data["total"] else _("Bibliothek")
            )
            self._applyDetailRepresentative(target, data["items"])

    def _onTilePreviewError(self, lib_id, err, generation):
        if generation != self._tile_preview_generation:
            return
        self._tile_preview_pending.discard(lib_id)
        log.debug("CinemaUI Tile-Vorschau fehlgeschlagen %s: %s", lib_id, err)

    def _representativeUrl(self, items, prefer_backdrop=False):
        for sample in list(items or []):
            if prefer_backdrop:
                url = (
                    getattr(sample, "backdrop_url", None)
                    or getattr(sample, "poster_url", None)
                )
            else:
                url = (
                    getattr(sample, "poster_url", None)
                    or getattr(sample, "backdrop_url", None)
                )
            if url:
                return url
        return None

    def _applyTileRepresentative(self, pos, item, items, generation):
        # Library cards deliberately use the dynamic theme artwork.  Real
        # media posters belong only in the detail preview on the right.
        return

    def _showTileRepresentative(self, pos, path, generation, lib_id):
        # Kept as a compatibility no-op for callbacks from older async jobs.
        return

    def _applyDetailRepresentative(self, item, items):
        if item is not self._current():
            return
        absolute_index = self.start_index + self.selected
        path = self._dynamicThemePath(absolute_index)
        self["detail_letter"].setText(self._libraryInitial(getattr(item, "title", "") or ""))
        if path:
            self._detail_image_generation += 1
            self._showDetailImageDirect(path)

    def _showDetailRepresentative(self, path, generation, lib_id):
        if self._closing or generation != self._detail_image_generation:
            return
        current = self._current()
        if current is None or self._libraryKey(current) != lib_id:
            return
        self._showDetailImageDirect(path)

    def _showDetailImageDirect(self, path):
        try:
            if path and os.path.isfile(path) and self["detail_image"].instance:
                self["detail_image"].instance.setScale(1)
                self["detail_image"].instance.setPixmapFromFile(path)
                self["detail_image"].show()
        except Exception as exc:
            log.debug("CinemaUI direktes Detailbild: %s", exc)

    def _showCardImage(self, pos, path, request, lib_id):
        if self._closing or request != self._image_request:
            return
        visible = self._visible()
        if not (0 <= pos < len(visible)):
            return

        current_id = str(
            getattr(visible[pos], "library_id", None)
            or getattr(visible[pos], "id", "")
            or ""
        )
        if lib_id and current_id != lib_id:
            return

        try:
            if not path or not os.path.isfile(path):
                return
            widget = self["card_img%d" % pos]
            if widget.instance:
                widget.instance.setScale(1)
                widget.instance.setPixmapFromFile(path)
                widget.show()
                self._library_image_paths[lib_id] = path
        except Exception as exc:
            log.debug("CinemaUI Library-Bild %d: %s", pos, exc)

    def _showFocus(self, visible):
        try:
            self["focus_frame"].show() if visible else self["focus_frame"].hide()
        except Exception:
            pass

    def _updateFocus(self):
        visible = self._visible()
        if not visible or not (0 <= self.selected < len(visible)):
            self._showFocus(False)
            return

        self._showFocus(True)
        x, y = CARD_POS[self.selected]
        try:
            frame = self["focus_frame"]
            frame.instance.move(ePoint(x - 6, y - 6))
            focus_png = os.path.join(THEME_DIR, "library_focus_glow.png")
            if os.path.isfile(focus_png):
                frame.instance.setScale(1)
                frame.instance.setPixmapFromFile(focus_png)
        except Exception:
            pass

    def _current(self):
        visible = self._visible()
        if 0 <= self.selected < len(visible):
            return visible[self.selected]
        return None

    # ------------------------------------------------------------------
    # Right preview
    # ------------------------------------------------------------------
    def _clearSamples(self):
        for i in range(5):
            try:
                self["sample%d" % i].hide()
            except Exception:
                pass

    def _clearDetail(self):
        self["detail_title"].setText("")
        self["detail_count"].setText("")
        self["detail_text"].setText("")
        self["detail_letter"].setText("")
        self._clearSamples()
        try:
            self["detail_image"].hide()
        except Exception:
            pass

    def _loadSelectedPreview(self, force=False):
        item = self._current()
        if item is None:
            self._clearDetail()
            return

        title = getattr(item, "title", "") or _("Bibliothek")
        lib_id = str(getattr(item, "library_id", None) or getattr(item, "id", "") or "")
        client = self.clients.get(getattr(item, "server_name", ""))

        self["detail_title"].setText(title)
        self["detail_text"].setText(
            _("Diese Bibliothek direkt innerhalb von Media Plugins 2026 durchsuchen.")
        )
        self._clearSamples()

        # Dynamic Library-Art immediately; real media stays in sample posters below.
        self._applyDetailRepresentative(item, [])

        cached = None if force else self._preview_cache.get(lib_id)
        if cached is not None:
            self._renderPreviewData(item, cached)
            if len(list(cached.get("items", []) or [])) >= 5:
                return

        if client is None or not lib_id:
            self["detail_count"].setText(_("Bibliothek"))
            return

        self._preview_request += 1
        request = self._preview_request
        self["detail_count"].setText(_("Lade Vorschau …"))

        try:
            client.get_items(
                lib_id,
                lambda media, total, rid=request, target=item:
                    self._onPreviewLoaded(target, media, total, rid),
                lambda err, rid=request:
                    self._onPreviewError(err, rid),
                start_index=0,
                limit=5,
                sort_by="SortName",
            )
        except TypeError:
            # Kompatibilität mit älteren Backends.
            client.get_items(
                lib_id,
                lambda media, total, rid=request, target=item:
                    self._onPreviewLoaded(target, media, total, rid),
                lambda err, rid=request:
                    self._onPreviewError(err, rid),
            )
        except Exception as exc:
            self._onPreviewError(str(exc), request)

    def _onPreviewLoaded(self, target, media, total, request):
        if self._closing or request != self._preview_request:
            return

        lib_id = str(
            getattr(target, "library_id", None)
            or getattr(target, "id", "")
            or ""
        )
        data = {
            "total": int(total or len(media or [])),
            "items": list(media or [])[:5],
        }
        self._preview_cache[lib_id] = data

        for i, visible_item in enumerate(self._visible()):
            if self._libraryKey(visible_item) == lib_id:
                self._applyTileRepresentative(
                    i,
                    visible_item,
                    data["items"],
                    self._tile_preview_generation,
                )
                break

        # Count auch auf sichtbarer Karte aktualisieren.
        for i, item in enumerate(self._visible()):
            current_id = str(
                getattr(item, "library_id", None)
                or getattr(item, "id", "")
                or ""
            )
            if current_id == lib_id:
                self["card_count%d" % i].setText(
                    _("%d Einträge") % data["total"]
                )
                break

        if target is self._current():
            self._renderPreviewData(target, data)

    def _onPreviewError(self, err, request):
        if self._closing or request != self._preview_request:
            return
        self["detail_count"].setText(_("Vorschau nicht verfügbar"))
        log.debug("CinemaUI Library-Vorschau fehlgeschlagen: %s", err)

    def _renderPreviewData(self, item, data):
        if item is not self._current():
            return

        total = int(data.get("total", 0) or 0)
        self["detail_count"].setText(
            _("%d Einträge") % total if total else _("Bibliothek")
        )

        sample_items = list(data.get("items", []) or [])
        self._clearSamples()

        # Rechte Grossvorschau: feste Library-Theme-Art; nur unbekannte
        # Libraries fallen auf Provider-Backdrop/Poster zurueck.
        self._applyDetailRepresentative(item, sample_items)

        for i, sample in enumerate(sample_items[:5]):
            url = getattr(sample, "poster_url", None)
            if not url:
                continue
            path = image_cache.get_local_path(url)
            if path:
                self._showSample(i, path, self._preview_request)
            else:
                rid = self._preview_request
                image_cache.fetch(
                    url,
                    lambda p, pos=i, req=rid: self._showSample(pos, p, req),
                    lambda err: None,
                )

    def _showDetailImage(self, path, request):
        if self._closing or request != self._preview_request:
            return
        try:
            if path and os.path.isfile(path) and self["detail_image"].instance:
                self["detail_image"].instance.setScale(1)
                self["detail_image"].instance.setPixmapFromFile(path)
                self["detail_image"].show()
        except Exception as exc:
            log.debug("CinemaUI Detailbild: %s", exc)

    def _showSample(self, pos, path, request):
        if self._closing or request != self._preview_request:
            return
        try:
            if path and os.path.isfile(path) and self["sample%d" % pos].instance:
                widget = self["sample%d" % pos]
                widget.instance.setScale(1)
                widget.instance.setPixmapFromFile(path)
                widget.show()
        except Exception as exc:
            log.debug("CinemaUI Sampleposter %d: %s", pos, exc)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def _selectionChanged(self):
        self._updateFocus()
        self._loadSelectedPreview()

    def keyLeft(self):
        visible = self._visible()
        if not visible:
            return

        if self.selected % COLS > 0:
            self.selected -= 1
            self._selectionChanged()
            return

        if self.start_index > 0:
            self.start_index = max(0, self.start_index - PAGE_SIZE)
            self._renderPage()
            self.selected = min(COLS - 1, len(self._visible()) - 1)
            self._selectionChanged()

    def keyRight(self):
        visible = self._visible()
        if not visible:
            return

        if self.selected % COLS < COLS - 1 and self.selected + 1 < len(visible):
            self.selected += 1
            self._selectionChanged()
            return

        if self.start_index + PAGE_SIZE < len(self.entries):
            self.start_index += PAGE_SIZE
            self.selected = 0
            self._renderPage()

    def keyUp(self):
        if self.selected >= COLS:
            self.selected -= COLS
            self._selectionChanged()

    def keyDown(self):
        visible = self._visible()
        if self.selected + COLS < len(visible):
            self.selected += COLS
            self._selectionChanged()

    def keyRefreshPreview(self):
        if self._current() is not None:
            self._loadSelectedPreview(force=True)

    def keyOpen(self):
        if self._child_open:
            return

        item = self._current()
        if item is None:
            return

        client = self.clients.get(getattr(item, "server_name", ""))
        if client is None:
            log.warning(
                "ServerFolderBrowser CinemaUI: kein Client fuer %s",
                getattr(item, "server_name", ""),
            )
            return

        from .LibraryBrowser import LibraryBrowser

        self._child_open = True
        log.info(
            "ServerFolderBrowser CinemaUI: oeffne Bibliothek %s / %s",
            getattr(item, "server_name", ""),
            getattr(item, "title", ""),
        )
        try:
            child = self.session.open(
                LibraryBrowser,
                item.server_name,
                item.library_id,
                item.title,
                client,
            )
            child.onClose.append(self._childClosed)
        except Exception as exc:
            self._child_open = False
            log.exception(
                "ServerFolderBrowser CinemaUI: Bibliothek konnte nicht geoeffnet werden: %s",
                exc,
            )

    def _childClosed(self, *args):
        self._child_open = False

    def keyCancel(self):
        if self._closing or self._child_open:
            return
        self._closing = True
        try:
            self["actions"].setEnabled(False)
        except Exception:
            pass
        self.close()

    def _onClose(self):
        self._closing = True
        self._image_request += 1
        self._preview_request += 1
        self._tile_preview_generation += 1
        self._server_display_request += 1
        self._detail_image_generation += 1
        try:
            self._clock_timer.stop()
        except Exception:
            pass
