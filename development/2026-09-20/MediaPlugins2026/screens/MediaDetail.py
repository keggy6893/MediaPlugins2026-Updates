# -*- coding: utf-8 -*-
# INFUSEMEDIA2026_PLEX_EPISODEUI3
# INFUSEMEDIA2026_PLEX_SEASONBROWSER1
# INFUSEMEDIA2026_R16_OPAQUE_LAYER_FIX_LOCALTEST
import os
from datetime import datetime

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel
from Components.ProgressBar import ProgressBar
from Tools.LoadPixmap import LoadPixmap
from enigma import eTimer

from ..utils.image_cache import image_cache
from ..utils import log


class MediaDetail(Screen):

    skinName = "MediaPlugins2026DetailScreen"
    skin = """
    <screen name="MediaPlugins2026DetailScreen" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="#07131d">
        <!-- Full-screen artwork with app-owned cinematic shading. -->
        <widget name="backdrop" position="0,0" size="1920,1080" zPosition="-10" alphatest="blend" scale="1" />
        <widget name="shade" position="0,0" size="1920,1080" zPosition="-9" alphatest="blend" scale="1" />

        <!-- Header -->
        <widget name="header_bg" position="0,0" size="1920,66" zPosition="1" backgroundColor="#07131d" />
        <widget name="brand1" position="44,15" size="215,40" zPosition="2" font="Regular;27" foregroundColor="#ffffff" transparent="1" text="Media Plugins" />
        <widget name="brand2" position="264,15" size="80,40" zPosition="2" font="Regular;27" foregroundColor="#47badd" transparent="1" text="2026" />
        <widget name="header_sep" position="350,15" size="20,40" zPosition="2" font="Regular;27" foregroundColor="#78909c" transparent="1" text="|" />
        <widget name="header_title" position="380,15" size="300,40" zPosition="2" font="Regular;27" foregroundColor="#ffffff" transparent="1" text="Details" />
        <widget name="date" position="1540,9" size="320,27" zPosition="2" font="Regular;21" foregroundColor="#d2dde2" transparent="1" halign="right" />
        <widget name="clock" position="1720,31" size="140,31" zPosition="2" font="Regular;29" foregroundColor="#ffffff" transparent="1" halign="right" />

        <!-- Poster + metadata block. -->
        <widget name="poster_frame" position="94,222" size="388,582" zPosition="1" backgroundColor="#263f4d" />
        <widget name="poster" position="100,228" size="376,570" zPosition="2" alphatest="blend" scale="1" />
        <widget name="title" position="540,348" size="1230,76" zPosition="2" font="Regular;58" foregroundColor="#ffffff" transparent="1" halign="left" />
        <widget name="year" position="540,431" size="190,44" zPosition="2" font="Regular;30" foregroundColor="#c2c8cb" transparent="1" halign="left" />
        <widget name="genres" position="760,431" size="690,44" zPosition="2" font="Regular;30" foregroundColor="#c2c8cb" transparent="1" halign="left" />
        <widget name="quality" position="1475,431" size="105,40" zPosition="2" font="Regular;22" foregroundColor="#32c7ec" backgroundColor="#101c24" halign="center" valign="center" />
        <widget name="provider" position="1595,431" size="130,40" zPosition="2" font="Regular;21" foregroundColor="#e9eef1" backgroundColor="#101c24" halign="center" valign="center" />
        <widget name="meta_line" position="540,486" size="1185,2" zPosition="2" backgroundColor="#40535e" />
        <widget name="description" position="540,510" size="1230,158" zPosition="2" font="Regular;29" foregroundColor="#f0f2f3" transparent="1" />

        <!-- Resume -->
        <widget name="progress" position="540,690" size="930,9" zPosition="2" borderWidth="0" backgroundColor="#54636b" foregroundColor="#30c7ec" />
        <widget name="resume" position="540,714" size="160,36" zPosition="2" font="Regular;25" foregroundColor="#ffffff" transparent="1" />
        <widget name="duration" position="1320,714" size="150,36" zPosition="2" font="Regular;24" foregroundColor="#aebbc1" transparent="1" halign="right" />
        <widget name="last_seen" position="540,752" size="360,32" zPosition="2" font="Regular;21" foregroundColor="#8fa0a8" transparent="1" text="Zuletzt gesehen" />

        <!-- Primary playback + compact remote hints. -->
        <widget name="play_focus" position="540,798" size="420,72" zPosition="3" backgroundColor="#35c5e8" />
        <widget name="key_ok" position="544,802" size="412,64" zPosition="4" font="Regular;25" foregroundColor="#ffffff" backgroundColor="#142532" halign="center" valign="center" text="OK  Abspielen" />
        <widget name="key_red" position="110,1025" size="250,35" zPosition="4" font="Regular;21" foregroundColor="#e75b55" transparent="1" text="■  Zurück" />
        <widget name="key_green" position="950,1025" size="245,35" zPosition="4" font="Regular;21" foregroundColor="#67c874" transparent="1" halign="center" text="■  Von Anfang" />
        <widget name="key_yellow" position="1200,1025" size="290,35" zPosition="4" font="Regular;21" foregroundColor="#d8b84a" transparent="1" halign="center" text="■  Favorit" />
        <widget name="key_blue" position="1490,1025" size="300,35" zPosition="4" font="Regular;21" foregroundColor="#4ca4d9" transparent="1" halign="right" text="■  Optionen" />

        <!-- Media-Plugins-style bottom action rail. OPAQUE by design: Enigma2/OpenATV alpha backgrounds can reveal the live video plane instead of compositing against our backdrop. -->
        <widget name="action_panel_border" position="44,842" size="1832,190" zPosition="19" backgroundColor="#294653" />
        <widget name="action_panel" position="46,844" size="1828,186" zPosition="20" backgroundColor="#0a141c" />

        <widget name="focus0" position="64,858" size="280,130" zPosition="21" backgroundColor="#3bd1f3" />
        <widget name="card0" position="68,862" size="272,122" zPosition="22" backgroundColor="#142532" />
        <widget name="icon0" position="172,869" size="64,56" zPosition="23" alphatest="blend" scale="1" />
        <widget name="action0" position="80,929" size="248,30" zPosition="23" font="Regular;20" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />
        <widget name="action_sub0" position="80,958" size="248,22" zPosition="23" font="Regular;16" foregroundColor="#8fa6b2" transparent="1" halign="center" valign="center" />

        <widget name="focus1" position="362,858" size="280,130" zPosition="21" backgroundColor="#3bd1f3" />
        <widget name="card1" position="366,862" size="272,122" zPosition="22" backgroundColor="#142532" />
        <widget name="icon1" position="470,869" size="64,56" zPosition="23" alphatest="blend" scale="1" />
        <widget name="action1" position="378,929" size="248,30" zPosition="23" font="Regular;20" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />
        <widget name="action_sub1" position="378,958" size="248,22" zPosition="23" font="Regular;16" foregroundColor="#8fa6b2" transparent="1" halign="center" valign="center" />

        <widget name="focus2" position="660,858" size="280,130" zPosition="21" backgroundColor="#3bd1f3" />
        <widget name="card2" position="664,862" size="272,122" zPosition="22" backgroundColor="#142532" />
        <widget name="icon2" position="768,869" size="64,56" zPosition="23" alphatest="blend" scale="1" />
        <widget name="action2" position="676,929" size="248,30" zPosition="23" font="Regular;20" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />
        <widget name="action_sub2" position="676,958" size="248,22" zPosition="23" font="Regular;16" foregroundColor="#8fa6b2" transparent="1" halign="center" valign="center" />

        <widget name="focus3" position="958,858" size="280,130" zPosition="21" backgroundColor="#3bd1f3" />
        <widget name="card3" position="962,862" size="272,122" zPosition="22" backgroundColor="#142532" />
        <widget name="icon3" position="1066,869" size="64,56" zPosition="23" alphatest="blend" scale="1" />
        <widget name="action3" position="974,929" size="248,30" zPosition="23" font="Regular;20" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />
        <widget name="action_sub3" position="974,958" size="248,22" zPosition="23" font="Regular;16" foregroundColor="#8fa6b2" transparent="1" halign="center" valign="center" />

        <widget name="focus4" position="1256,858" size="280,130" zPosition="21" backgroundColor="#3bd1f3" />
        <widget name="card4" position="1260,862" size="272,122" zPosition="22" backgroundColor="#142532" />
        <widget name="icon4" position="1364,869" size="64,56" zPosition="23" alphatest="blend" scale="1" />
        <widget name="action4" position="1272,929" size="248,30" zPosition="23" font="Regular;20" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />
        <widget name="action_sub4" position="1272,958" size="248,22" zPosition="23" font="Regular;16" foregroundColor="#8fa6b2" transparent="1" halign="center" valign="center" />

        <widget name="focus5" position="1554,858" size="280,130" zPosition="21" backgroundColor="#3bd1f3" />
        <widget name="card5" position="1558,862" size="272,122" zPosition="22" backgroundColor="#142532" />
        <widget name="icon5" position="1662,869" size="64,56" zPosition="23" alphatest="blend" scale="1" />
        <widget name="action5" position="1570,929" size="248,30" zPosition="23" font="Regular;20" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />
        <widget name="action_sub5" position="1570,958" size="248,22" zPosition="23" font="Regular;16" foregroundColor="#8fa6b2" transparent="1" halign="center" valign="center" />

        <widget name="action_status" position="350,996" size="920,28" zPosition="23" font="Regular;18" foregroundColor="#8fa6b2" transparent="1" />
        <widget name="action_red" position="72,996" size="250,28" zPosition="23" font="Regular;19" foregroundColor="#e75b55" transparent="1" text="■  Zurück" />
        <widget name="action_hint" position="1425,996" size="415,28" zPosition="23" font="Regular;19" foregroundColor="#dce7ed" transparent="1" halign="right" text="◀/▶  Auswählen     OK" />
    </screen>"""

    def __init__(self, session, item, client):
        Screen.__init__(self, session)
        self.session = session
        self.item = item
        self.client = client

        self["backdrop"] = Pixmap()
        self["shade"] = Pixmap()
        self["poster_frame"] = Label("")
        self["poster"] = Pixmap()
        self["header_bg"] = Label("")
        self["brand1"] = Label("Media Plugins")
        self["brand2"] = Label("2026")
        self["header_sep"] = Label("|")
        self["header_title"] = Label(_("Details"))
        self["date"] = Label("")
        self["clock"] = Label("")
        self["title"] = Label(item.title)
        self["year"] = Label(str(item.year) if item.year else "")
        self["description"] = ScrollLabel(item.overview or _("Keine Beschreibung verfügbar."))
        self["genres"] = Label(", ".join(item.genres) if item.genres else "")
        self["quality"] = Label(self._qualityLabel())
        self["provider"] = Label(self._providerName())
        self["meta_line"] = Label("")
        self["progress"] = ProgressBar()
        self["progress"].setRange((0, 1000))
        self["progress"].setValue(0)
        self["resume"] = Label("0:00")
        self["duration"] = Label("--:--")
        self["last_seen"] = Label(_("Zuletzt gesehen"))

        self["play_focus"] = Label("")
        self["key_ok"] = Label(_("OK  Abspielen"))
        self["key_red"] = Label(_("■  Zurück"))
        self["key_green"] = Label(_("■  Von Anfang"))
        self["key_yellow"] = Label(_("■  Favorit"))
        self["key_blue"] = Label(_("■  Optionen"))

        self.actionbar_active = False
        self.actionbar_index = 0
        self["action_panel_border"] = Label("")
        self["action_panel"] = Label("")
        self["action0"] = Label(_("Als gesehen markieren"))
        self["action1"] = Label(_("Als ungesehen markieren"))
        self["action2"] = Label(_("Favorit"))
        self["action3"] = Label(_("Untertitel"))
        self["action4"] = Label(_("Audio"))
        self["action5"] = Label(_("Weitere Optionen"))
        self["action_sub0"] = Label("")
        self["action_sub1"] = Label("")
        self["action_sub2"] = Label("")
        self["action_sub3"] = Label(_("während Wiedergabe"))
        self["action_sub4"] = Label(_("während Wiedergabe"))
        self["action_sub5"] = Label(_("Details"))
        self["action_status"] = Label("")
        self["action_red"] = Label(_("■  Zurück"))
        self["action_hint"] = Label(_("◀/▶  Auswählen     OK"))
        for idx in range(6):
            self["focus%d" % idx] = Label("")
            self["card%d" % idx] = Label("")
            self["icon%d" % idx] = Pixmap()

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.keyOK,
                "cancel": self.keyCancel,
                "red": self.keyCancel,
                "left": self.keyLeft,
                "right": self.keyRight,
                "up": self.keyUp,
                "down": self.keyDown,
                "green": self.keyGreen,
                "yellow": self.keyYellow,
                "blue": self.keyOptions,
            },
            -1
        )

        self._clock_timer = eTimer()
        self._clock_timer.callback.append(self._updateClock)

        # RESUME-REFRESH1: Wenn der Player geschlossen wird, wird dieser
        # Detail-Screen erneut sichtbar. Emby/Jellyfin haben den Stop-/Progress-
        # Stand dann serverseitig gespeichert; nach kurzer Verzögerung laden wir
        # die UserData erneut, damit "Fortsetzen" sofort den neuen Stand zeigt.
        self._detail_shown_once = False
        self._resume_refresh_timer = eTimer()
        self._resume_refresh_timer.callback.append(self._refreshAfterPlayer)
        self.onShown.append(self._onDetailShown)

        self.onLayoutFinish.append(self._onLayout)
        self.onClose.append(self._onClose)

    def _onLayout(self):
        self._loadStaticSkinAssets()
        self._loadActionIcons()
        self._hideActionBar()
        self._loadArtwork()
        self._loadFullDetail()
        self._updateFavoriteLabel()
        self._updatePlaybackLabels()
        self._updateClock()
        self._clock_timer.start(30000, False)

    def _onDetailShown(self):
        # Das erste Anzeigen wird bereits durch _onLayout() geladen. Erst bei
        # einer Rueckkehr (z. B. aus dem MoviePlayer) erneut vom Server lesen.
        if not self._detail_shown_once:
            self._detail_shown_once = True
            return
        try:
            self._resume_refresh_timer.start(800, True)
        except Exception:
            self._refreshAfterPlayer()

    def _refreshAfterPlayer(self):
        log.info("Detail Resume-Refresh: %s", self.item.title)
        # RESUME-LOCAL2: Player hat die Stop-Position bereits in demselben
        # MediaItem hinterlegt. Sofort anzeigen; Server-Reload bleibt danach
        # als Abgleich bestehen.
        self._updatePlaybackLabels()
        self._loadFullDetail()

    def _onClose(self):
        try:
            self._clock_timer.stop()
        except Exception:
            pass
        try:
            self._resume_refresh_timer.stop()
        except Exception:
            pass

    def _assetPath(self, name):
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "skin", "detail", name)

    def _loadStaticSkinAssets(self):
        pix = LoadPixmap(self._assetPath("detail_shade.png"))
        if pix and self["shade"].instance:
            self["shade"].instance.setPixmap(pix)

    def _loadActionIcons(self):
        names = ("seen.png", "unseen.png", "heart.png", "subs.png", "audio.png", "more.png")
        for idx, name in enumerate(names):
            try:
                pix = LoadPixmap(self._assetPath(name))
                if pix and self["icon%d" % idx].instance:
                    self["icon%d" % idx].instance.setPixmap(pix)
            except Exception:
                pass

    def _updateClock(self):
        now = datetime.now()
        weekdays = (_("Mo"), _("Di"), _("Mi"), _("Do"), _("Fr"), _("Sa"), _("So"))
        months = (_("Jan"), _("Feb"), _("Mär"), _("Apr"), _("Mai"), _("Jun"),
                  _("Jul"), _("Aug"), _("Sep"), _("Okt"), _("Nov"), _("Dez"))
        self["date"].setText("%s, %d. %s %d" % (weekdays[now.weekday()], now.day, months[now.month - 1], now.year))
        self["clock"].setText(now.strftime("%H:%M"))

    def _providerName(self):
        source = getattr(self.item, "source_label", "") or ""
        if source:
            return source.upper()
        return self.client.__class__.__name__.replace("Client", "").upper()

    def _qualityLabel(self):
        try:
            height = int(getattr(self.item, "video_height", 0) or 0)
            width = int(getattr(self.item, "video_width", 0) or 0)
        except Exception:
            height, width = 0, 0
        if height >= 2000 or width >= 3800:
            return "4K"
        if height >= 1000:
            return "1080"
        if height >= 700:
            return "HD"
        return ""

    def _loadArtwork(self):
        poster_url = getattr(self.item, "poster_url", None) or self.client.get_image_url(self.item.id, "Primary")
        backdrop_url = getattr(self.item, "backdrop_url", None) or self.client.get_image_url(self.item.id, "Backdrop")
        if poster_url:
            image_cache.fetch(poster_url, self._onPosterLoaded)
        if backdrop_url:
            image_cache.fetch(backdrop_url, self._onBackdropLoaded)

    def _onPosterLoaded(self, path):
        pix = LoadPixmap(path)
        if pix and self["poster"].instance:
            self["poster"].instance.setPixmap(pix)

    def _onBackdropLoaded(self, path):
        pix = LoadPixmap(path)
        if pix and self["backdrop"].instance:
            self["backdrop"].instance.setPixmap(pix)

    def _loadFullDetail(self):
        self.client.get_item_detail(
            self.item.id,
            lambda detail: log.safe_call(self._onDetailLoaded, detail),
            lambda err: log.warning("Detail-Nachladen fehlgeschlagen fuer %s: %s", self.item.id, err),
        )

    def _onDetailLoaded(self, detail):
        self.item.update_from_detail(detail)
        self["description"].setText(self.item.overview or "")
        self._loadArtwork()
        self["genres"].setText(", ".join(self.item.genres or []))
        self["quality"].setText(self._qualityLabel())
        self["provider"].setText(self._providerName())
        self._updateFavoriteLabel()
        self._updatePlaybackLabels()
        if not self._isContainerItem():
            self["title"].setText(self.item.title)
            self["year"].setText(str(self.item.year) if self.item.year else "")

    # INFUSEMEDIA2026_PLEX_SEASONBROWSER1
    def _mediaType(self):
        kind = str(getattr(self.item, "media_type", "") or "").strip().lower()
        if kind:
            return kind
        if self.client.__class__.__name__ == "PlexClient":
            if getattr(self.item, "season_number", None) is not None and getattr(self.item, "episode_number", None) is None and not getattr(self.item, "stream_url", ""):
                return "season"
        return ""

    def _isContainerItem(self):
        return self.client.__class__.__name__ == "PlexClient" and self._mediaType() in ("show", "season")

    def _containerDisplay(self):
        kind = self._mediaType()
        if kind == "season":
            title = getattr(self.item, "series_name", "") or self.item.title
            number = getattr(self.item, "season_number", None)
            subtitle = ("Staffel %d" % int(number)) if number is not None else self.item.title
            return title, subtitle
        return self.item.title, (str(self.item.year) if self.item.year else "")

    def _applyContainerMode(self):
        if not self._isContainerItem():
            for name in ("progress", "resume", "duration", "last_seen"):
                try:
                    self[name].show()
                except Exception:
                    pass
            return False
        title, subtitle = self._containerDisplay()
        self["title"].setText(title)
        self["year"].setText(subtitle)
        self["quality"].setText("")
        self["key_green"].setText("")
        self["key_yellow"].setText("")
        self["key_blue"].setText("")
        self["key_ok"].setText("OK  Episoden anzeigen" if self._mediaType() == "season" else "OK  Staffeln anzeigen")
        for name in ("progress", "resume", "duration", "last_seen"):
            try:
                self[name].hide()
            except Exception:
                try:
                    self[name].setText("")
                except Exception:
                    pass
        try:
            self["progress"].setValue(0)
        except Exception:
            pass
        return True

    def _openChildren(self):
        if not self._isContainerItem():
            return False
        try:
            if self._mediaType() == "season":
                from .PlexEpisodeBrowser import PlexEpisodeBrowser
                self.session.open(PlexEpisodeBrowser, self.item, self.client)
            else:
                from .PlexChildrenBrowser import PlexChildrenBrowser
                self.session.open(PlexChildrenBrowser, self.item, self.client)
        except Exception as exc:
            log.exception("Plex Staffel-/Serienbrowser konnte nicht geöffnet werden: %s", exc)
            from Screens.MessageBox import MessageBox
            self.session.open(MessageBox, "Plex-Inhalte konnten nicht geöffnet werden.", MessageBox.TYPE_ERROR)
        return True

    @staticmethod
    def _formatResume(ticks):
        try:
            seconds = max(0, int(ticks or 0) // 10000000)
        except Exception:
            seconds = 0
        hours, rem = divmod(seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        if hours:
            return "%d:%02d:%02d" % (hours, minutes, seconds)
        return "%d:%02d" % (minutes, seconds)

    def _updatePlaybackLabels(self):
        if self._applyContainerMode():
            return

        resume_ticks = int(getattr(self.item, "resume_ticks", 0) or 0)
        runtime_ticks = int(getattr(self.item, "runtime_ticks", 0) or 0)
        has_resume = resume_ticks >= 10 * 10000000
        if runtime_ticks and resume_ticks >= max(0, runtime_ticks - 30 * 10000000):
            has_resume = False
        if has_resume:
            resume_text = self._formatResume(resume_ticks)
            self["key_ok"].setText(_("OK  Fortsetzen") + "  " + resume_text)
            self["last_seen"].setText(_("Zuletzt gesehen"))
        else:
            resume_text = "0:00"
            self["key_ok"].setText(_("OK  Abspielen"))
            self["last_seen"].setText(_("Noch nicht begonnen"))
        self["resume"].setText(resume_text)
        self["duration"].setText(self._formatResume(runtime_ticks) if runtime_ticks else "--:--")
        if runtime_ticks > 0:
            value = max(0, min(1000, int((float(resume_ticks) / float(runtime_ticks)) * 1000.0)))
        else:
            value = 0
        self["progress"].setValue(value)

    def keyPlay(self):
        if self._openChildren():
            return
        try:
            stream_url = self.client.get_stream_url(self.item.id, self.item)
            resume_ticks = int(getattr(self.item, "resume_ticks", 0) or 0)
            log.info("Starte Wiedergabe/Fortsetzen: %s bei %.1f s -> %s",
                     self.item.title, float(resume_ticks) / 10000000.0, stream_url)
            self._startPlayback(stream_url, start_ticks=resume_ticks)
        except Exception as e:
            log.exception("Wiedergabe konnte nicht gestartet werden: %s", e)
            from Screens.MessageBox import MessageBox
            self.session.open(MessageBox, _("Wiedergabe fehlgeschlagen."), MessageBox.TYPE_ERROR)

    def keyPlayFromStart(self):
        if self._openChildren():
            return
        try:
            stream_url = self.client.get_stream_url(self.item.id, self.item)
            log.info("Starte Wiedergabe von Anfang: %s -> %s", self.item.title, stream_url)
            self._startPlayback(stream_url, start_ticks=0)
        except Exception as e:
            log.exception("Wiedergabe von Anfang konnte nicht gestartet werden: %s", e)
            from Screens.MessageBox import MessageBox
            self.session.open(MessageBox, _("Wiedergabe fehlgeschlagen."), MessageBox.TYPE_ERROR)

    def _startPlayback(self, url, start_ticks=None):
        # MEDIAPLUGINS2026_PROVIDERPLAYER_RESTORE1
        from .ProviderPlayerBridge import open_provider_player

        if open_provider_player(
            self.session,
            self.item,
            self.client,
            start_ticks=start_ticks,
        ):
            return

        from enigma import eServiceReference
        from .InfuseMoviePlayer import InfuseMoviePlayer

        ref = eServiceReference(4097, 0, url)
        ref.setName(self.item.title)
        self.session.open(
            InfuseMoviePlayer,
            ref,
            self.item,
            self.client,
            url,
            start_ticks,
        )

    def _normalKeyWidgets(self):
        return ("play_focus", "key_ok", "key_red", "key_green", "key_yellow", "key_blue")

    def _actionBarWidgets(self):
        names = ["action_panel_border", "action_panel", "action_status", "action_red", "action_hint"]
        names += ["action%d" % i for i in range(6)]
        names += ["focus%d" % i for i in range(6)]
        names += ["card%d" % i for i in range(6)]
        names += ["icon%d" % i for i in range(6)]
        names += ["action_sub%d" % i for i in range(6)]
        return names

    def _hideActionBar(self):
        self.actionbar_active = False
        for name in self._actionBarWidgets():
            try:
                self[name].hide()
            except Exception:
                pass
        for name in self._normalKeyWidgets():
            try:
                self[name].show()
            except Exception:
                pass

    def _showActionBar(self):
        self.actionbar_active = True
        self.actionbar_index = 0
        self["action_status"].setText("")
        self["action_sub0"].setText(self._providerName())
        self["action_sub1"].setText(self._providerName())
        self._updateFavoriteLabel()
        for name in self._normalKeyWidgets():
            try:
                self[name].hide()
            except Exception:
                pass
        for name in self._actionBarWidgets():
            try:
                self[name].show()
            except Exception:
                pass
        self._renderActionBarFocus()

    def _renderActionBarFocus(self):
        for idx in range(6):
            try:
                if self.actionbar_active and idx == self.actionbar_index:
                    self["focus%d" % idx].show()
                else:
                    self["focus%d" % idx].hide()
            except Exception:
                pass

    def keyLeft(self):
        if not self.actionbar_active:
            return
        self.actionbar_index = (self.actionbar_index - 1) % 6
        self["action_status"].setText("")
        self._renderActionBarFocus()

    def keyRight(self):
        if not self.actionbar_active:
            return
        self.actionbar_index = (self.actionbar_index + 1) % 6
        self["action_status"].setText("")
        self._renderActionBarFocus()

    def keyUp(self):
        if self.actionbar_active:
            return
        self["description"].pageUp()

    def keyDown(self):
        if self.actionbar_active:
            return
        self["description"].pageDown()

    def keyGreen(self):
        if self.actionbar_active:
            return
        self.keyPlayFromStart()

    def keyYellow(self):
        if self.actionbar_active or self._isContainerItem():
            return
        self.keyToggleFavorite()

    def keyOK(self):
        if not self.actionbar_active:
            self.keyPlay()
            return
        action = self.actionbar_index
        if action == 0:
            self.client.mark_watched(self.item.id, watched=True)
            self.item.played = True
            self["action_status"].setText(_("Als gesehen markiert."))
        elif action == 1:
            self.client.mark_watched(self.item.id, watched=False)
            self.item.played = False
            self["action_status"].setText(_("Als ungesehen markiert."))
        elif action == 2:
            if self.client.__class__.__name__ == "PlexClient":
                self["action_status"].setText(_("Plex-Watchlist folgt in einer späteren Version."))
            else:
                self.keyToggleFavorite()
                self["action_status"].setText(_("Favoritenstatus aktualisiert."))
        elif action == 3:
            self["action_status"].setText(_("Untertitel während der Wiedergabe mit GELB auswählen."))
        elif action == 4:
            self["action_status"].setText(_("Audiospur während der Wiedergabe mit GRÜN auswählen."))
        elif action == 5:
            self["action_status"].setText(_("Weitere Detailoptionen folgen."))

    def keyOptions(self):
        if self._isContainerItem():
            return
        if self.actionbar_active:
            self._hideActionBar()
        else:
            self._showActionBar()

    def keyToggleFavorite(self):
        if self._isContainerItem():
            return
        if self.client.__class__.__name__ == "PlexClient":
            return
        new_state = not getattr(self.item, "is_favorite", False)
        self.item.is_favorite = new_state
        self.client.set_favorite(self.item.id, new_state)
        self._updateFavoriteLabel()

    def _updateFavoriteLabel(self):
        if self.client.__class__.__name__ == "PlexClient":
            self["key_yellow"].setText(_("■  Plex-Watchlist folgt"))
            self["action2"].setText(_("Plex-Watchlist"))
            self["action_sub2"].setText(_("noch nicht verfügbar"))
            return
        is_fav = getattr(self.item, "is_favorite", False)
        label = _("Favorit entfernen") if is_fav else _("Favorit")
        self["key_yellow"].setText(_("■  ") + label)
        self["action2"].setText(label)
        self["action_sub2"].setText(self._providerName())

    def keyCancel(self):
        if self.actionbar_active:
            self._hideActionBar()
        else:
            self.close()
