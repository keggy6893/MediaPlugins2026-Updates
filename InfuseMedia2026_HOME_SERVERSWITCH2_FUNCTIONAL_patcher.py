# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import shutil
import sys

TARGET_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/InfuseMedia2026/screens/HomeScreen.py"
REQUIRED_MARKER = "# INFUSEMEDIA2026_HOME_SERVERSWITCH1"
MARKER = "# INFUSEMEDIA2026_HOME_SERVERSWITCH2_FUNCTIONAL"
BACKUP_SUFFIX = ".before_serverswitch2"


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError("%s: erwartete genau 1 Fundstelle, gefunden %d" % (label, count))
    return text.replace(old, new, 1)


def replace_method(text, name, replacement):
    start_token = "    def %s(" % name
    start = text.find(start_token)
    if start < 0:
        raise RuntimeError("Methode nicht gefunden: %s" % name)
    next_def = text.find("\n    def ", start + len(start_token))
    if next_def < 0:
        raise RuntimeError("Folgemethode nach %s nicht gefunden" % name)
    return text[:start] + replacement.rstrip() + "\n\n" + text[next_def + 1:]


def patch(text):
    if MARKER in text:
        return text
    if REQUIRED_MARKER not in text:
        raise RuntimeError("HOME_SERVERSWITCH1 fehlt. Bitte zuerst den kompakten Serverwechsel installieren.")

    text = text.replace(REQUIRED_MARKER, REQUIRED_MARKER + "\n" + MARKER, 1)

    text = replace_method(text, "_moveZone", '''    def _moveZone(self, delta):
        zones = self._zones()
        if not zones:
            return
        try:
            idx = zones.index(self.zone)
        except ValueError:
            idx = 0

        old_zone = self.zone
        old_item = self._previewItem()
        idx = max(0, min(len(zones) - 1, idx + delta))
        new_zone = zones[idx]

        if new_zone == "server_switch" and old_zone != "server_switch":
            self._enterServerSwitch(old_item, old_zone)
            return

        if old_zone == "server_switch" and new_zone != "server_switch":
            self._server_switch_item = None

        self.zone = new_zone
        self._refreshFocus()''')

    anchor = "    def keyUp(self):\n"
    helpers = '''    def _enterServerSwitch(self, item=None, return_zone=None):
        # Serverliste fokussieren, ohne das aktuell angezeigte Medium zu verlieren.
        if item is None:
            item = self._previewItem()
        self._server_switch_item = item
        self._server_switch_return_zone = return_zone or self.zone
        self._syncServerSwitchToItem(item)
        self.zone = "server_switch"
        self._refreshFocus()
        self._renderServerSwitch()

    def _leaveServerSwitch(self):
        # Zur Medienzeile zurueckkehren, aus der der Serverbereich betreten wurde.
        target = getattr(self, "_server_switch_return_zone", "")
        valid = [z for z in self._zones() if z != "server_switch"]
        if target not in valid:
            target = valid[-1] if valid else "continue"
        self._server_switch_item = None
        self.zone = target
        self._refreshFocus()

'''
    text = replace_once(text, anchor, helpers + anchor, "Serverwechsel Navigation-Helfer")

    text = replace_method(text, "keyUp", '''    def keyUp(self):
        self._touchHomeSlideshow()
        if self.zone == "server_switch":
            if self.server_switch_index > 0:
                self.server_switch_index -= 1
                self._renderServerSwitch()
            else:
                self._leaveServerSwitch()
            return
        self._moveZone(-1)''')

    text = replace_method(text, "keyDown", '''    def keyDown(self):
        self._touchHomeSlideshow()

        if self.zone == "server_switch":
            providers = self._serverSwitchProviders()
            if self.server_switch_index < len(providers) - 1:
                self.server_switch_index += 1
                self._renderServerSwitch()
            return

        # Der Serverbereich liegt direkt unter den beiden unteren Medienreihen.
        if self.zone in ("favorites", "latest"):
            self._enterServerSwitch(self._previewItem(), self.zone)
            return

        self._moveZone(1)''')

    text = replace_method(text, "_findProviderPlugin", '''    def _findProviderPlugin(self, provider):
        # Originalplugin in der bereits geladenen Enigma2-Pluginliste suchen.
        try:
            from Components.PluginComponent import plugins
            from Plugins.Plugin import PluginDescriptor
        except Exception as e:
            log.warning("Serverwechsel: PluginComponent nicht verfuegbar: %s", e)
            return None

        descriptors = []
        seen = set()
        where_values = [
            PluginDescriptor.WHERE_PLUGINMENU,
            getattr(PluginDescriptor, "WHERE_EXTENSIONSMENU", None),
            getattr(PluginDescriptor, "WHERE_MENU", None),
        ]
        for where in where_values:
            if where is None:
                continue
            try:
                rows = plugins.getPlugins(where) or []
            except Exception:
                rows = []
            for descriptor in rows:
                ident = id(descriptor)
                if ident in seen:
                    continue
                seen.add(ident)
                descriptors.append(descriptor)

        aliases = self._providerPluginAliases(provider)
        for alias in aliases:
            for descriptor in descriptors:
                name = str(getattr(descriptor, "name", "") or "").strip().lower()
                if name == alias:
                    return descriptor

        provider = (provider or "").strip().lower()
        candidates = []
        seen_names = set()
        for descriptor in descriptors:
            name = str(getattr(descriptor, "name", "") or "").strip()
            folded = name.lower()
            if not folded or "infusemedia" in folded:
                continue
            matched = bool(provider and provider in folded)
            if provider == "emby" and "embyflow" in folded:
                matched = True
            if provider == "plex" and "plex2026" in folded:
                matched = True
            if matched and folded not in seen_names:
                seen_names.add(folded)
                candidates.append(descriptor)

        return candidates[0] if candidates else None''')

    anchor2 = "    def _openProviderPlugin(self, provider):\n"
    direct_helper = '''    def _openProviderPluginDirect(self, provider):
        # Fallback fuer Images, deren PluginComponent den Ziel-Descriptor nicht liefert.
        import importlib

        known = {
            "emby": ("Plugins.Extensions.EmbyFlowE2.plugin",),
            "plex": ("Plugins.Extensions.Plex2026.plugin",),
            "jellyfin": (
                "Plugins.Extensions.Jellyfin.plugin",
                "Plugins.Extensions.Jellyfin2026.plugin",
            ),
        }

        module_names = list(known.get(provider, ()))
        ext_dir = "/usr/lib/enigma2/python/Plugins/Extensions"
        try:
            for entry in os.listdir(ext_dir):
                folded = entry.lower()
                if folded == "infusemedia2026":
                    continue
                if provider == "emby":
                    match = "emby" in folded
                elif provider == "plex":
                    match = "plex" in folded
                elif provider == "jellyfin":
                    match = "jelly" in folded
                else:
                    match = False
                if match:
                    modname = "Plugins.Extensions.%s.plugin" % entry
                    if modname not in module_names:
                        module_names.append(modname)
        except Exception:
            pass

        errors = []
        for module_name in module_names:
            try:
                module = importlib.import_module(module_name)
            except Exception as e:
                errors.append("%s import: %s" % (module_name, e))
                continue

            fn = getattr(module, "main", None)
            if callable(fn):
                try:
                    fn(self.session)
                    log.info("Home Serverwechsel direkt: provider=%s module=%s", provider, module_name)
                    return True
                except TypeError:
                    try:
                        fn(session=self.session)
                        log.info("Home Serverwechsel direkt: provider=%s module=%s", provider, module_name)
                        return True
                    except Exception as e:
                        errors.append("%s main(session=): %s" % (module_name, e))
                except Exception as e:
                    errors.append("%s main: %s" % (module_name, e))

            plugins_fn = getattr(module, "Plugins", None)
            if callable(plugins_fn):
                try:
                    rows = plugins_fn() or []
                    if not isinstance(rows, (list, tuple)):
                        rows = [rows]
                    for descriptor in rows:
                        name = str(getattr(descriptor, "name", "") or "")
                        if "infusemedia" in name.lower():
                            continue
                        try:
                            descriptor(session=self.session)
                            log.info(
                                "Home Serverwechsel direkt: provider=%s module=%s descriptor=%s",
                                provider, module_name, name,
                            )
                            return True
                        except Exception as e:
                            errors.append("%s descriptor %s: %s" % (module_name, name, e))
                except Exception as e:
                    errors.append("%s Plugins(): %s" % (module_name, e))

        if errors:
            log.warning(
                "Serverwechsel direkte Fallbacks fehlgeschlagen (%s): %s",
                provider, " | ".join(errors[-4:]),
            )
        return False

'''
    text = replace_once(text, anchor2, direct_helper + anchor2, "Direktstart-Fallback")

    text = replace_method(text, "_openProviderPlugin", '''    def _openProviderPlugin(self, provider):
        provider = (provider or "").strip().lower()
        provider_name = _PROVIDER_NAMES.get(
            provider,
            provider.capitalize() if provider else "Quelle",
        )

        if provider not in ("emby", "jellyfin", "plex"):
            return

        try:
            self._home_slideshow_timer.stop()
        except Exception:
            pass

        descriptor = self._findProviderPlugin(provider)
        if descriptor is not None:
            try:
                log.info(
                    "Home Serverwechsel: provider=%s plugin=%s",
                    provider,
                    getattr(descriptor, "name", "?"),
                )
                descriptor(session=self.session)
                return
            except TypeError:
                try:
                    descriptor(self.session)
                    return
                except Exception as e:
                    log.warning("Serverwechsel Descriptor %s fehlgeschlagen: %s", provider_name, e)
            except Exception as e:
                log.warning("Serverwechsel Descriptor %s fehlgeschlagen: %s", provider_name, e)

        if self._openProviderPluginDirect(provider):
            return

        self.session.open(
            MessageBox,
            "%s konnte nicht geoeffnet werden.\\n\\nBitte pruefen, ob das %s-Plugin installiert ist."
            % (provider_name, provider_name),
            MessageBox.TYPE_ERROR,
            timeout=7,
        )''')

    return text


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_DEFAULT
    if not os.path.isfile(target):
        raise SystemExit("Datei nicht gefunden: %s" % target)

    with io.open(target, "r", encoding="utf-8") as handle:
        original = handle.read()

    if MARKER in original:
        print("HOME_SERVERSWITCH2_FUNCTIONAL bereits installiert: %s" % target)
        return

    patched = patch(original)
    compile(patched, target, "exec")

    backup = target + BACKUP_SUFFIX
    if not os.path.exists(backup):
        shutil.copy2(target, backup)

    with io.open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(patched)

    with io.open(target, "r", encoding="utf-8") as handle:
        verify = handle.read()
    compile(verify, target, "exec")

    if MARKER not in verify:
        raise RuntimeError("Verifikation fehlgeschlagen: Marker fehlt")

    print("OK HOME_SERVERSWITCH2_FUNCTIONAL: %s" % target)
    print("- RUNTER aus Favoriten/Neu hinzugefuegt -> Zu Server wechseln")
    print("- HOCH/RUNTER -> Emby / Jellyfin / Plex")
    print("- OK -> Originalplugin oeffnen")
    print("- PluginDescriptor + direkter Extensions-Fallback")
    print("- EmbyFlowE2 und Plex2026 explizit unterstuetzt")
    print("- Backup: %s" % backup)


if __name__ == "__main__":
    main()
