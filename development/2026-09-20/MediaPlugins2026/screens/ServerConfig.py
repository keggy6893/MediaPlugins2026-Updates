# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.config import ConfigText, ConfigPassword, ConfigSelection, ConfigYesNo
from Components.ConfigList import ConfigListScreen

from ..config import config_store, ServerConfig
from ..backends.factory import create_client_for_server
from ..utils import log


class ServerConfigScreen(ConfigListScreen, Screen):
    """Server hinzufuegen und Verbindung vor dem Speichern pruefen."""

    skinName = "MediaPlugins2026ServerConfigScreen"
    skin = """
    <screen name="MediaPlugins2026ServerConfigScreen" position="center,center" size="1600,900" backgroundColor="#ffffff" title="Server hinzufuegen">
        <widget name="title" position="60,40" size="900,70" font="Regular;44" foregroundColor="#000000" transparent="1" halign="left" />
        <widget name="config" position="60,140" size="1480,590" scrollbarMode="showOnDemand" />
        <widget name="status" position="60,750" size="1480,50" font="Regular;26" foregroundColor="#555555" transparent="1" />
        <widget name="key_green" position="60,820" size="300,60" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#2e7d32" halign="center" valign="center" text="Verbinden" />
    </screen>"""

    def __init__(self, session, protocol="jellyfin"):
        Screen.__init__(self, session)
        self.session = session
        self.protocol = protocol
        self._login_running = False

        self["title"] = Label(_("%s hinzufuegen") % protocol.capitalize())
        self["key_green"] = Label(_("Verbinden"))
        self["status"] = Label(_("Adresse und Login eingeben, dann Gruen/OK druecken."))

        self.cfg_name = ConfigText(default="Meine %s" % protocol.capitalize(), fixed_size=False)
        self.cfg_address = ConfigText(default="", fixed_size=False)
        self.cfg_username = ConfigText(default="", fixed_size=False)
        self.cfg_password = ConfigPassword(default="")
        self.cfg_port = ConfigText(default=("32400" if protocol == "plex" else ""), fixed_size=False)
        self.cfg_https = ConfigSelection(choices=[("auto", "Auto"), ("on", "An"), ("off", "Aus")], default="auto")
        self.cfg_path = ConfigText(default="", fixed_size=False)
        self.cfg_library_mode = ConfigYesNo(default=False)

        credential_rows = []
        if protocol == "plex":
            credential_rows = [(_("Plex Token (X-Plex-Token)"), self.cfg_password)]
            self["status"].setText(_("Plex-Serveradresse und Token eingeben, dann Gruen/OK druecken."))
        else:
            credential_rows = [(_("Benutzername"), self.cfg_username), (_("Passwort"), self.cfg_password)]

        clist = [
            (_("Freigabename"), self.cfg_name),
            (_("Adresse"), self.cfg_address),
        ] + credential_rows + [
            (_("Port"), self.cfg_port),
            (_("HTTPS"), self.cfg_https),
            (_("Pfad (erweitert)"), self.cfg_path),
            (_("Bibliotheksmodus"), self.cfg_library_mode),
        ]
        ConfigListScreen.__init__(self, clist, session=session)

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok": self.keySave,
                "cancel": self.keyCancel,
                "green": self.keySave,
            },
            -1
        )

    def _make_config(self):
        return ServerConfig(
            name=self.cfg_name.value.strip(),
            protocol=self.protocol,
            address=self.cfg_address.value.strip(),
            port=self.cfg_port.value.strip(),
            username=self.cfg_username.value,
            password=self.cfg_password.value,
            https=self.cfg_https.value,
            path=self.cfg_path.value.strip(),
            library_mode=self.cfg_library_mode.value,
        )

    def keySave(self):
        if self._login_running:
            return
        if not self.cfg_address.value.strip() or not self.cfg_name.value.strip():
            self["status"].setText(_("Freigabename und Adresse fehlen."))
            return

        port_text = self.cfg_port.value.strip()
        if port_text:
            try:
                port_num = int(port_text)
                if port_num < 1 or port_num > 65535:
                    raise ValueError
            except ValueError:
                self["status"].setText(_("Port muss leer oder eine Zahl von 1 bis 65535 sein."))
                return

        server_cfg = self._make_config()
        self._login_running = True
        self["status"].setText(_("Verbinde mit %s ...") % server_cfg.address)
        self["key_green"].setText(_("Bitte warten"))
        log.info("Teste %s-Login zu %s", self.protocol, server_cfg.address)

        try:
            client = create_client_for_server(server_cfg)
            client.login(
                lambda token, uid: log.safe_call(self._login_ok, server_cfg, client),
                lambda err: log.safe_call(self._login_failed, err),
            )
        except Exception as e:
            self._login_failed(str(e))

    def _login_ok(self, server_cfg, client):
        self._login_running = False
        self["status"].setText(_("Verbindung erfolgreich. Server wird gespeichert."))
        log.info("Server-Test erfolgreich: %s via %s", server_cfg.name, client._build_base_url())
        server_cfg.token = getattr(client, "token", "") or server_cfg.token
        server_cfg.user_id = getattr(client, "user_id", "") or server_cfg.user_id
        # Gleichnamigen Eintrag ersetzen statt Duplikate anzulegen.
        config_store.remove_server(server_cfg.name)
        config_store.add_server(server_cfg)
        self.close(True)

    def _login_failed(self, err):
        self._login_running = False
        self["key_green"].setText(_("Verbinden"))
        msg = _("Login/Verbindung fehlgeschlagen:\n%s") % err
        self["status"].setText(_("Verbindung fehlgeschlagen - Einstellungen pruefen."))
        log.error("Server-Test fehlgeschlagen: %s", err)
        self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout=10)

    def keyCancel(self):
        if not self._login_running:
            self.close(False)
