# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from .utils import log

# INFUSEMEDIA2026_R16_OPAQUE_LAYER_FIX_LOCALTEST


def main(session, **kwargs):
    log.info("=" * 40)
    log.info("Plugin-Start (Media Plugins 2026)")
    # MEDIAPLUGINS2026_AUTOBACKUP1_PLUGIN
    # Einmal pro Kalendertag eine persistente 7-Tage-Konfigurationssicherung.
    # Fehler blockieren den Home-Screen niemals.
    try:
        from .utils.config_backup import ensure_daily_backup
        ensure_daily_backup()
    except Exception as backup_error:
        log.warning("AutoBackup Start-Hook fehlgeschlagen: %s", backup_error)

    try:
        from .screens.HomeScreen import HomeScreen
        dialog = session.open(HomeScreen)
        log.debug("HomeScreen erfolgreich geoeffnet")
    except Exception as e:
        log.exception("Plugin konnte nicht gestartet werden: %s", e)
        from Screens.MessageBox import MessageBox
        session.open(
            MessageBox,
            _("Media Plugins 2026 konnte nicht gestartet werden.\n"
              "Details in %s") % log.log_path(),
            MessageBox.TYPE_ERROR,
        )


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="Media Plugins 2026",
            description="Emby, Jellyfin & Plex in einer gemeinsamen Oberflaeche",
            where=[PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU],
            icon="skin/icons/plugin_icon.png",
            fnc=main,
        )
    ]
