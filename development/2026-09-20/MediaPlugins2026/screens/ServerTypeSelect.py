# -*- coding: utf-8 -*-
# MEDIAPLUGINS2026_SERVERTYPE_WINDOWSTYLE1_SCREEN

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap

try:
    from skin import parseColor
except Exception:
    parseColor = None


_CARD_NORMAL = "#0A1C2B"
_CARD_SELECTED = "#0D5267"
_DETAIL_BG = "#081725"

_PROVIDER_COLORS = {
    "emby": "#37D67A",
    "jellyfin": "#48AFFF",
    "plex": "#F5B82E",
}

_PROVIDER_DATA = {
    "emby": {
        "name": "Emby",
        "subtitle": "Eigenen Emby Server hinzufügen",
        "description": (
            "Verbindet Media Plugins 2026 mit deinem Emby-Server.\n"
            "Vorhandene EmbyFlowE2-Anmeldedaten können übernommen werden."
        ),
        "features": (
            "✓ Filme & Serien\n"
            "✓ Live TV\n"
            "✓ Musik\n"
            "✓ Fotos\n"
            "✓ EmbyFlowE2-Anmeldung nutzbar"
        ),
        "icon": "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/skin/icons/provider_emby_select.png",
    },
    "jellyfin": {
        "name": "Jellyfin",
        "subtitle": "Eigenen Jellyfin Server hinzufügen",
        "description": (
            "Verbindet Media Plugins 2026 mit einem Jellyfin-Server.\n"
            "Serveradresse und Anmeldung werden im nächsten Schritt eingerichtet."
        ),
        "features": (
            "✓ Filme & Serien\n"
            "✓ Live TV\n"
            "✓ Musik\n"
            "✓ Open Source\n"
            "✓ Neue Server-Verbindung"
        ),
        "icon": "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/skin/icons/provider_jellyfin_select.png",
    },
    "plex": {
        "name": "Plex",
        "subtitle": "Eigenen Plex Server hinzufügen",
        "description": (
            "Verbindet Media Plugins 2026 mit deinem Plex-Server.\n"
            "Vorhandene Plex2026-Anmeldedaten können übernommen werden."
        ),
        "features": (
            "✓ Filme & Serien\n"
            "✓ Live TV\n"
            "✓ Musik\n"
            "✓ Discover\n"
            "✓ Plex2026-Anmeldung nutzbar"
        ),
        "icon": "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/skin/icons/provider_plex_select.png",
    },
}


# MEDIAPLUGINS2026_SERVERTYPE_CRASHFIX1
class MediaPluginsServerTypeScreen(Screen):
    skinName = "MediaPlugins2026ServerTypeScreen"

    # Exakt dasselbe 1600x900-Fensterformat wie Einstellungen.
    skin = r"""
    <screen name="MediaPlugins2026ServerTypeScreen"
            position="center,center" size="1600,900"
            backgroundColor="#06121D" flags="wfNoBorder"
            title="Media Plugins 2026">

        <!-- Header identisch zum Settings-Screen -->
        <widget zPosition="20" name="brand" position="46,23" size="421,45"
                font="Bold;32" foregroundColor="#F4F7FB"
                backgroundColor="#06121D" transparent="1" />
        <widget zPosition="20" name="brand_year" position="304,23" size="158,45"
                font="Bold;32" foregroundColor="#23D7F2"
                backgroundColor="#06121D" transparent="1" />
        <eLabel position="479,22" size="2,52" backgroundColor="#23D7F2" />
        <widget zPosition="20" name="screen_title" position="512,25" size="520,36"
                font="Regular;27" foregroundColor="#C8D7E6"
                backgroundColor="#06121D" transparent="1" />
        <widget zPosition="20" name="screen_subtitle" position="512,60" size="680,25"
                font="Regular;17" foregroundColor="#86A1B8"
                backgroundColor="#06121D" transparent="1" />

        <widget source="global.CurrentTime" render="Label"
                position="1317,23" size="229,33"
                font="Regular;26" foregroundColor="#D8E7F4"
                backgroundColor="#06121D" transparent="1" halign="right">
            <convert type="ClockToText">Format:%H:%M</convert>
        </widget>
        <widget source="global.CurrentTime" render="Label"
                position="1208,58" size="338,22"
                font="Regular;14" foregroundColor="#86A1B8"
                backgroundColor="#06121D" transparent="1" halign="right">
            <convert type="ClockToText">Format:%a, %d.%m.%Y</convert>
        </widget>

        <!-- Linkes Panel -->
        <eLabel position="42,104" size="688,525"
                backgroundColor="#081725"
                borderWidth="2" borderColor="#1B4C6B" />
        <widget zPosition="20" name="left_heading"
                position="62,119" size="440,30"
                font="Bold;21" foregroundColor="#8CCEF6"
                backgroundColor="#081725" transparent="1" />
        <widget zPosition="20" name="left_counter"
                position="517,122" size="183,23"
                font="Regular;14" foregroundColor="#7893A9"
                backgroundColor="#081725" transparent="1" halign="right" />

        <!-- Emby -->
        <widget zPosition="5" name="row0_bg"
                position="60,166" size="650,112"
                backgroundColor="#0A1C2B" transparent="0"
                borderWidth="2" borderColor="#244863" />
        <widget zPosition="20" name="row0_focus"
                position="73,200" size="28,38"
                font="Bold;22" foregroundColor="#23D7F2"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="30" name="row0_icon"
                position="112,188" size="64,64"
                pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/skin/icons/provider_emby_select.png"
                alphatest="on" transparent="1" />
        <widget zPosition="20" name="row0_title"
                position="196,186" size="330,32"
                font="Bold;24" foregroundColor="#F4F7FB"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="row0_subtitle"
                position="196,221" size="390,24"
                font="Regular;17" foregroundColor="#91B4CE"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="row0_number"
                position="642,188" size="42,32"
                font="Bold;21" foregroundColor="#D8E7F4"
                backgroundColor="#0A1C2B" transparent="1" halign="right" />

        <!-- Jellyfin -->
        <widget zPosition="5" name="row1_bg"
                position="60,294" size="650,112"
                backgroundColor="#0A1C2B" transparent="0"
                borderWidth="2" borderColor="#244863" />
        <widget zPosition="20" name="row1_focus"
                position="73,328" size="28,38"
                font="Bold;22" foregroundColor="#23D7F2"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="30" name="row1_icon"
                position="112,316" size="64,64"
                pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/skin/icons/provider_jellyfin_select.png"
                alphatest="on" transparent="1" />
        <widget zPosition="20" name="row1_title"
                position="196,314" size="330,32"
                font="Bold;24" foregroundColor="#F4F7FB"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="row1_subtitle"
                position="196,349" size="390,24"
                font="Regular;17" foregroundColor="#91B4CE"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="row1_number"
                position="642,316" size="42,32"
                font="Bold;21" foregroundColor="#D8E7F4"
                backgroundColor="#0A1C2B" transparent="1" halign="right" />

        <!-- Plex -->
        <widget zPosition="5" name="row2_bg"
                position="60,422" size="650,112"
                backgroundColor="#0A1C2B" transparent="0"
                borderWidth="2" borderColor="#244863" />
        <widget zPosition="20" name="row2_focus"
                position="73,456" size="28,38"
                font="Bold;22" foregroundColor="#23D7F2"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="30" name="row2_icon"
                position="112,444" size="64,64"
                pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/skin/icons/provider_plex_select.png"
                alphatest="on" transparent="1" />
        <widget zPosition="20" name="row2_title"
                position="196,442" size="330,32"
                font="Bold;24" foregroundColor="#F4F7FB"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="row2_subtitle"
                position="196,477" size="390,24"
                font="Regular;17" foregroundColor="#91B4CE"
                backgroundColor="#0A1C2B" transparent="1" />
        <widget zPosition="20" name="row2_number"
                position="642,444" size="42,32"
                font="Bold;21" foregroundColor="#D8E7F4"
                backgroundColor="#0A1C2B" transparent="1" halign="right" />

        <widget zPosition="20" name="left_hint"
                position="75,575" size="608,22"
                font="Regular;14" foregroundColor="#7893A9"
                backgroundColor="#081725" transparent="1" halign="center" />

        <!-- Rechtes Detailpanel -->
        <eLabel position="750,104" size="808,525"
                backgroundColor="#081725"
                borderWidth="2" borderColor="#1B4C6B" />
        <widget zPosition="20" name="detail_heading"
                position="775,119" size="417,30"
                font="Bold;21" foregroundColor="#8CCEF6"
                backgroundColor="#081725" transparent="1" />
        <widget zPosition="30" name="detail_icon"
                position="790,171" size="82,82"
                alphatest="on" transparent="1" />
        <widget zPosition="20" name="detail_provider"
                position="900,174" size="370,40"
                font="Bold;30" foregroundColor="#37D67A"
                backgroundColor="#081725" transparent="1" />
        <widget zPosition="20" name="detail_state"
                position="1360,177" size="155,28"
                font="Bold;14" foregroundColor="#23D7F2"
                backgroundColor="#081725" transparent="1" halign="right" />

        <widget zPosition="20" name="detail_description"
                position="900,224" size="575,78"
                font="Regular;19" foregroundColor="#C8D7E6"
                backgroundColor="#081725" transparent="1" />

        <eLabel position="790,323" size="725,1"
                backgroundColor="#244863" />

        <widget zPosition="20" name="feature_heading"
                position="804,346" size="260,28"
                font="Bold;18" foregroundColor="#8CCEF6"
                backgroundColor="#081725" transparent="1" />
        <widget zPosition="20" name="feature_list"
                position="804,386" size="660,150"
                font="Regular;19" foregroundColor="#D6E1EB"
                backgroundColor="#081725" transparent="1" />
        <widget zPosition="20" name="detail_hint"
                position="790,562" size="725,24"
                font="Regular;14" foregroundColor="#7893A9"
                backgroundColor="#081725" transparent="1" halign="center" />

        <!-- Footer exakt im Settings-Stil -->
        <widget zPosition="20" name="key_green"
                position="52,658" size="360,48"
                font="Bold;18" foregroundColor="#FFFFFF"
                backgroundColor="#087A37" transparent="0"
                halign="center" valign="center" />
        <widget zPosition="20" name="key_red"
                position="430,658" size="360,48"
                font="Bold;18" foregroundColor="#FFFFFF"
                backgroundColor="#9E2428" transparent="0"
                halign="center" valign="center" />
        <widget zPosition="20" name="key_yellow"
                position="808,658" size="360,48"
                font="Bold;18" foregroundColor="#FFFFFF"
                backgroundColor="#B58B00" transparent="0"
                halign="center" valign="center" />
        <widget zPosition="20" name="key_back"
                position="1186,658" size="360,48"
                font="Bold;18" foregroundColor="#D6E1EB"
                backgroundColor="#263442" transparent="0"
                halign="center" valign="center" />

        <widget zPosition="20" name="footer_version"
                position="52,738" size="500,23"
                font="Regular;14" foregroundColor="#7893A9"
                backgroundColor="#06121D" transparent="1" />
        <widget zPosition="20" name="footer_hint"
                position="633,738" size="912,23"
                font="Regular;14" foregroundColor="#7893A9"
                backgroundColor="#06121D" transparent="1" halign="right" />
    </screen>
    """

    PROVIDERS = ("emby", "jellyfin", "plex")

    def __init__(self, session):
        Screen.__init__(self, session)
        self._index = 0

        self["brand"] = Label("Media Plugins")
        self["brand_year"] = Label("2026")
        self["screen_title"] = Label("Medienserver-Typ wählen")
        self["screen_subtitle"] = Label(
            "Wähle den zu deinem Server passenden Anbieter."
        )

        self["left_heading"] = Label("MEDIENSERVER")
        self["left_counter"] = Label("3 Anbieter")

        self["row0_bg"] = Label("")
        self["row0_focus"] = Label("")
        self["row0_icon"] = Pixmap()
        self["row0_title"] = Label("Emby")
        self["row0_subtitle"] = Label(_PROVIDER_DATA["emby"]["subtitle"])
        self["row0_number"] = Label("1")

        self["row1_bg"] = Label("")
        self["row1_focus"] = Label("")
        self["row1_icon"] = Pixmap()
        self["row1_title"] = Label("Jellyfin")
        self["row1_subtitle"] = Label(_PROVIDER_DATA["jellyfin"]["subtitle"])
        self["row1_number"] = Label("2")

        self["row2_bg"] = Label("")
        self["row2_focus"] = Label("")
        self["row2_icon"] = Pixmap()
        self["row2_title"] = Label("Plex")
        self["row2_subtitle"] = Label(_PROVIDER_DATA["plex"]["subtitle"])
        self["row2_number"] = Label("3")

        self["left_hint"] = Label("↑↓ Anbieter auswählen")

        self["detail_heading"] = Label("AUSGEWÄHLTER MEDIENSERVER")
        self["detail_icon"] = Pixmap()
        self["detail_provider"] = Label("")
        self["detail_state"] = Label("BEREIT")
        self["detail_description"] = Label("")
        self["feature_heading"] = Label("FUNKTIONEN")
        self["feature_list"] = Label("")
        self["detail_hint"] = Label(
            "Nach Auswahl werden die Server-Einstellungen geöffnet."
        )

        self["key_green"] = Label("OK   Auswählen")
        self["key_red"] = Label("ROT   Abbrechen")
        self["key_yellow"] = Label("1 / 2 / 3   Direktwahl")
        self["key_back"] = Label("ZURÜCK")
        self["footer_version"] = Label("Media Plugins 2026   v2026.1-r20")
        self["footer_hint"] = Label(
            "↑↓ Auswahl   OK/GRÜN bestätigen   EXIT zurück"
        )

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions", "NumberActions"],
            {
                "up": self.keyUp,
                "down": self.keyDown,
                "ok": self.keyOk,
                "green": self.keyOk,
                "cancel": lambda: self.close(None),
                "red": lambda: self.close(None),
                "1": lambda: self.selectIndex(0, True),
                "2": lambda: self.selectIndex(1, True),
                "3": lambda: self.selectIndex(2, True),
            },
            -1,
        )

        self.onLayoutFinish.append(self._layoutReady)

    def _set_bg(self, name, color):
        if parseColor is None:
            return
        try:
            self[name].instance.setBackgroundColor(parseColor(color))
        except Exception:
            pass

    def _set_fg(self, name, color):
        if parseColor is None:
            return
        try:
            self[name].instance.setForegroundColor(parseColor(color))
        except Exception:
            pass

    def _setPixmap(self, name, path):
        try:
            from Tools.LoadPixmap import LoadPixmap
            pix = LoadPixmap(path=path, cached=True)
            if pix is not None:
                self[name].instance.setPixmap(pix)
                self[name].show()
        except Exception:
            pass

    def _layoutReady(self):
        self._setPixmap("row0_icon", _PROVIDER_DATA["emby"]["icon"])
        self._setPixmap("row1_icon", _PROVIDER_DATA["jellyfin"]["icon"])
        self._setPixmap("row2_icon", _PROVIDER_DATA["plex"]["icon"])
        self._render()

    def _render(self):
        for idx, provider in enumerate(self.PROVIDERS):
            selected = idx == self._index
            bg = _CARD_SELECTED if selected else _CARD_NORMAL

            self["row%d_focus" % idx].setText("▶" if selected else "")

            for suffix in (
                "bg", "focus", "title", "subtitle", "number"
            ):
                self._set_bg("row%d_%s" % (idx, suffix), bg)

        provider = self.PROVIDERS[self._index]
        data = _PROVIDER_DATA[provider]

        self["detail_provider"].setText(data["name"])
        self["detail_description"].setText(data["description"])
        self["feature_list"].setText(data["features"])
        self._set_fg("detail_provider", _PROVIDER_COLORS[provider])
        self._setPixmap("detail_icon", data["icon"])

    def keyUp(self):
        self._index = (self._index - 1) % len(self.PROVIDERS)
        self._render()

    def keyDown(self):
        self._index = (self._index + 1) % len(self.PROVIDERS)
        self._render()

    def selectIndex(self, index, confirm=False):
        if index < 0 or index >= len(self.PROVIDERS):
            return
        self._index = index
        self._render()
        if confirm:
            self.keyOk()

    def keyOk(self):
        self.close(self.PROVIDERS[self._index])
