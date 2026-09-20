# -*- coding: utf-8 -*-
# R13: legacy screen retained for compatibility; MediaDetail uses inline bottom actionbar.
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label


class DetailOptions(Screen):
    """Media-Plugins-2026-eigene Detailoptionen ohne OpenATV ChoiceBox-Skin."""

    skinName = "MediaPlugins2026DetailOptions"
    skin = """
    <screen name="MediaPlugins2026DetailOptions" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="#07131d">
        <widget name="heading" position="120,110" size="1680,70" font="Regular;48" foregroundColor="#ffffff" transparent="1" />
        <widget name="context" position="120,185" size="1680,45" font="Regular;27" foregroundColor="#7fa7b8" transparent="1" />
        <widget name="rule" position="120,250" size="1680,2" backgroundColor="#244150" />

        <widget name="focus0" position="365,350" size="1190,86" backgroundColor="#35c5e8" />
        <widget name="row0" position="369,354" size="1182,78" font="Regular;32" foregroundColor="#ffffff" backgroundColor="#142532" valign="center" />
        <widget name="focus1" position="365,454" size="1190,86" backgroundColor="#35c5e8" />
        <widget name="row1" position="369,458" size="1182,78" font="Regular;32" foregroundColor="#ffffff" backgroundColor="#142532" valign="center" />

        <widget name="hint" position="365,585" size="1190,50" font="Regular;24" foregroundColor="#8fa6b2" transparent="1" halign="left" />

        <widget name="key_red" position="120,960" size="250,55" font="Regular;24" foregroundColor="#e75b55" transparent="1" text="■  Zurück" />
        <widget name="key_ok" position="1510,960" size="290,55" font="Regular;24" foregroundColor="#ffffff" transparent="1" halign="right" text="OK  Auswählen" />
    </screen>"""

    def __init__(self, session, item=None, provider_name=""):
        Screen.__init__(self, session)
        self.item = item
        self.provider_name = provider_name or ""
        self.index = 0

        self["heading"] = Label(_("Optionen"))
        title = getattr(item, "title", "") if item is not None else ""
        context = title
        if self.provider_name:
            context = (context + "  ·  " if context else "") + self.provider_name
        self["context"] = Label(context)
        self["rule"] = Label("")
        self["focus0"] = Label("")
        self["focus1"] = Label("")
        self["row0"] = Label(_("Als gesehen markieren"))
        self["row1"] = Label(_("Als ungesehen markieren"))
        self["hint"] = Label(_("Mit ↑/↓ auswählen und mit OK bestätigen."))
        self["key_red"] = Label(_("■  Zurück"))
        self["key_ok"] = Label(_("OK  Auswählen"))

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.keyOK,
                "cancel": self.keyCancel,
                "red": self.keyCancel,
                "up": self.keyUp,
                "down": self.keyDown,
            },
            -1,
        )
        self.onLayoutFinish.append(self._renderFocus)

    def _renderFocus(self):
        if self.index == 0:
            self["focus0"].show()
            self["focus1"].hide()
        else:
            self["focus0"].hide()
            self["focus1"].show()

    def keyUp(self):
        self.index = 0 if self.index <= 0 else self.index - 1
        self._renderFocus()

    def keyDown(self):
        self.index = 1 if self.index >= 1 else self.index + 1
        self._renderFocus()

    def keyOK(self):
        self.close("watched" if self.index == 0 else "unwatched")

    def keyCancel(self):
        self.close(None)
