# -*- coding: utf-8 -*-
import hashlib
import io
import json
import os
import re
import subprocess
import tarfile
import threading
import time

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from enigma import eTimer

from ..version import (
    PLUGIN_VERSION,
    PLUGIN_UPDATE_BUILD,
    PLUGIN_UPDATE_CHANNEL,
    PLUGIN_UPDATE_MANIFEST_URL,
)

# MEDIAPLUGINS2026_GITHUB_UPDATER_V1
PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
PACKAGE_NAME = "enigma2-plugin-extensions-mediaplugins2026"
UPDATE_MANIFEST_MAX_BYTES = 128 * 1024
UPDATE_ARTIFACT_MAX_BYTES = 32 * 1024 * 1024
UPDATE_TIMEOUT_SECONDS = 25
UPDATE_STATE_FILE = os.path.join(PLUGIN_PATH, ".mediaplugins2026_update_state.json")
UPDATE_ALLOWED_FINAL_HOSTS = (
    "github.com",
    "raw.githubusercontent.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "github-releases.githubusercontent.com",
)


def _load_state():
    try:
        with open(UPDATE_STATE_FILE, "r") as handle:
            value = json.loads(handle.read())
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _save_state(state):
    temporary = UPDATE_STATE_FILE + ".tmp"
    try:
        with open(temporary, "w") as handle:
            handle.write(json.dumps(dict(state or {}), sort_keys=True))
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except Exception:
                pass
        os.replace(temporary, UPDATE_STATE_FILE)
    finally:
        try:
            if os.path.exists(temporary):
                os.remove(temporary)
        except Exception:
            pass


def _timestamp_text(value):
    try:
        value = int(value or 0)
        if value <= 0:
            return "Noch nie"
        return time.strftime("%d.%m.%Y  %H:%M:%S", time.localtime(value))
    except Exception:
        return "Unbekannt"


def _install_time_fallback():
    try:
        path = os.path.join(PLUGIN_PATH, "plugin.py")
        return int(os.path.getmtime(path)) if os.path.isfile(path) else 0
    except Exception:
        return 0


def _mark_checked(manifest):
    state = _load_state()
    state["last_checked_ts"] = int(time.time())
    state["last_checked_version"] = str((manifest or {}).get("version") or "")
    state["last_checked_build"] = int((manifest or {}).get("build") or 0)
    _save_state(state)


def _mark_installed(version, build):
    state = _load_state()
    state["last_installed_ts"] = int(time.time())
    state["last_installed_version"] = str(version or "")
    state["last_installed_build"] = int(build or 0)
    _save_state(state)


def _https_url(url, allowed_hosts=None):
    try:
        from urllib.parse import urlparse
        parsed = urlparse(str(url or "").strip())
        if parsed.scheme.lower() != "https":
            return False
        host = str(parsed.hostname or "").lower()
        if not host:
            return False
        return not allowed_hosts or host in tuple(allowed_hosts)
    except Exception:
        return False


def _read_url(url, max_bytes, allowed_hosts=None, no_cache=False):
    if not _https_url(url, allowed_hosts):
        raise RuntimeError("Unsichere oder nicht erlaubte Update-URL")
    import urllib.request
    headers = {
        "User-Agent": "MediaPlugins2026-Updater/1",
        "Accept": "application/json, application/octet-stream, text/plain, */*",
    }
    if no_cache:
        headers["Cache-Control"] = "no-cache, no-store, max-age=0"
        headers["Pragma"] = "no-cache"
    response = urllib.request.urlopen(
        urllib.request.Request(str(url), headers=headers),
        timeout=int(UPDATE_TIMEOUT_SECONDS),
    )
    try:
        status = getattr(response, "status", None)
        if status is None:
            try:
                status = response.getcode()
            except Exception:
                status = 200
        if int(status or 0) != 200:
            raise RuntimeError("HTTP %s" % str(status))
        final_url = str(getattr(response, "geturl", lambda: url)() or url)
        if not _https_url(final_url, UPDATE_ALLOWED_FINAL_HOSTS):
            raise RuntimeError("Download wurde auf einen nicht erlaubten Host umgeleitet")
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > int(max_bytes):
                    raise RuntimeError("Update-Datei ist zu gross")
            except ValueError:
                pass
        data = response.read(int(max_bytes) + 1)
        if len(data) > int(max_bytes):
            raise RuntimeError("Update-Datei ueberschreitet das Groessenlimit")
        return data
    finally:
        try:
            response.close()
        except Exception:
            pass


def _normalize_manifest(raw):
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except Exception as error:
        raise RuntimeError("update.json ist ungueltig: %s" % str(error))
    if not isinstance(manifest, dict):
        raise RuntimeError("update.json enthaelt kein JSON-Objekt")

    version = str(manifest.get("version") or "").strip()
    channel = str(manifest.get("channel") or "").strip().lower()
    download = str(manifest.get("download") or "").strip()
    sha256_value = str(manifest.get("sha256") or "").strip().upper()
    artifact_type = str(manifest.get("artifact_type") or "").strip().lower()
    package = str(manifest.get("package") or "").strip()
    try:
        build = int(manifest.get("build"))
    except Exception:
        raise RuntimeError("Update-Build fehlt oder ist ungueltig")

    if not version:
        raise RuntimeError("Update-Version fehlt")
    if channel != str(PLUGIN_UPDATE_CHANNEL).lower():
        raise RuntimeError("Falscher Update-Kanal: %s" % (channel or "unbekannt"))
    if artifact_type != "ipk":
        raise RuntimeError("Nur IPK-Updates sind erlaubt")
    # MEDIAPLUGINS2026_UPDATER_LEGACYMANIFEST1
    # Transitional compatibility for the final legacy r17 manifest.
    # It may be displayed as an older version, but it can never be installed.
    legacy_package = package == "enigma2-plugin-extensions-infusemedia2026"
    if package != PACKAGE_NAME:
        if (not legacy_package) or build > int(PLUGIN_UPDATE_BUILD):
            raise RuntimeError("Falscher Paketname im Manifest")
    if not download.split("?", 1)[0].lower().endswith(".ipk"):
        raise RuntimeError("Download ist keine IPK-Datei")
    if not _https_url(download, ("github.com",)):
        raise RuntimeError("Download-URL ist nicht erlaubt")
    if not re.match(r"^[0-9A-F]{64}$", sha256_value):
        raise RuntimeError("SHA256 fehlt oder ist ungueltig")

    changelog = manifest.get("changelog") or []
    if isinstance(changelog, str):
        changelog = [changelog]
    if not isinstance(changelog, list):
        changelog = []
    changelog = [str(item).strip() for item in changelog if str(item).strip()]

    return {
        "version": version,
        "build": build,
        "channel": channel,
        "download": download,
        "sha256": sha256_value,
        "artifact_type": artifact_type,
        "package": package,
        "changelog": changelog,
        "installable": package == PACKAGE_NAME,
    }


def _version_revision(value):
    """Return numeric r-revision for MediaPlugins versions, or None."""
    match = re.search(r"(?:^|[-_.])r(\d+)(?:$|[-_.])", str(value or "").strip(), re.I)
    return int(match.group(1)) if match else None


def _is_remote_newer(remote_version, remote_build):
    """Never offer an older r-revision merely because its build number is higher."""
    local_revision = _version_revision(PLUGIN_VERSION)
    remote_revision = _version_revision(remote_version)
    if local_revision is not None and remote_revision is not None:
        if remote_revision != local_revision:
            return remote_revision > local_revision
    return int(remote_build or 0) > int(PLUGIN_UPDATE_BUILD)


def _fetch_manifest():
    separator = "&" if "?" in PLUGIN_UPDATE_MANIFEST_URL else "?"
    url = PLUGIN_UPDATE_MANIFEST_URL + separator + "_mediaplugins_ts=%d" % int(time.time())
    raw = _read_url(
        url,
        UPDATE_MANIFEST_MAX_BYTES,
        ("raw.githubusercontent.com",),
        no_cache=True,
    )
    return _normalize_manifest(raw)


def _ar_members(data):
    if not isinstance(data, (bytes, bytearray)) or not data.startswith(b"!<arch>\n"):
        raise RuntimeError("IPK ist kein gueltiges ar-Archiv")
    result = {}
    pos = 8
    total = len(data)
    while pos + 60 <= total:
        header = data[pos:pos + 60]
        if header[58:60] != b"`\n":
            raise RuntimeError("IPK-ar-Header ist ungueltig")
        name = header[0:16].decode("utf-8", "replace").strip().rstrip("/")
        try:
            size = int(header[48:58].decode("ascii", "replace").strip())
        except Exception:
            raise RuntimeError("IPK-ar-Groesse ist ungueltig")
        start = pos + 60
        end = start + size
        if end > total:
            raise RuntimeError("IPK-ar-Datei ist abgeschnitten")
        result[name] = bytes(data[start:end])
        pos = end + (size & 1)
    return result


def _safe_tar_names(tf):
    names = []
    for member in tf.getmembers():
        name = str(member.name or "").replace("\\", "/")
        clean = name[2:] if name.startswith("./") else name
        if clean.startswith("/") or clean == ".." or clean.startswith("../") or "/../" in clean:
            raise RuntimeError("Unsicherer Pfad im IPK: %s" % name)
        names.append(clean)
    return names


def _validate_ipk(data, manifest):
    members = _ar_members(data)
    control_name = next((name for name in members if name.startswith("control.tar")), None)
    data_name = next((name for name in members if name.startswith("data.tar")), None)
    if not control_name or not data_name:
        raise RuntimeError("IPK enthaelt control/data Archiv nicht")

    try:
        with tarfile.open(fileobj=io.BytesIO(members[control_name]), mode="r:*") as tf:
            names = _safe_tar_names(tf)
            forbidden = {"preinst", "postinst", "prerm", "postrm"}
            if any(name.rsplit("/", 1)[-1] in forbidden for name in names):
                raise RuntimeError("IPK enthaelt Installationsskripte; Update abgebrochen")
            control_member = next(
                (member for member in tf.getmembers() if str(member.name).lstrip("./") == "control"),
                None,
            )
            if control_member is None:
                raise RuntimeError("IPK-control fehlt")
            content = tf.extractfile(control_member).read().decode("utf-8", "replace")
    except RuntimeError:
        raise
    except Exception as error:
        raise RuntimeError("IPK-control konnte nicht gelesen werden: %s" % error)

    fields = {}
    for line in content.splitlines():
        if ":" in line and not line[:1].isspace():
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip()
    if fields.get("package") != PACKAGE_NAME:
        raise RuntimeError("IPK enthaelt das falsche Paket")
    if fields.get("version") != str(manifest.get("version") or ""):
        raise RuntimeError("IPK-Version stimmt nicht mit update.json ueberein")

    try:
        with tarfile.open(fileobj=io.BytesIO(members[data_name]), mode="r:*") as tf:
            names = _safe_tar_names(tf)
    except RuntimeError:
        raise
    except Exception as error:
        raise RuntimeError("IPK-Datenarchiv konnte nicht gelesen werden: %s" % error)

    expected = "usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/plugin.py"
    if expected not in names:
        raise RuntimeError("IPK enthaelt MediaPlugins2026/plugin.py nicht")
    if any(name == "etc/enigma2" or name.startswith("etc/enigma2/") for name in names):
        raise RuntimeError("IPK darf /etc/enigma2 nicht veraendern")
    return fields


def _backup_plugin():
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = "/tmp/mediaplugins2026_update_backup_%s.tar.gz" % stamp
    if not os.path.isdir(PLUGIN_PATH):
        raise RuntimeError("Installiertes Plugin-Verzeichnis fehlt")
    with tarfile.open(path, "w:gz") as tf:
        tf.add(PLUGIN_PATH, arcname="MediaPlugins2026", recursive=True)
    if not os.path.isfile(path) or os.path.getsize(path) < 1000:
        raise RuntimeError("Backup konnte nicht erstellt werden")
    return path


def _install_ipk(manifest):
    data = _read_url(
        str(manifest.get("download") or ""),
        UPDATE_ARTIFACT_MAX_BYTES,
        ("github.com",),
    )
    expected_sha = str(manifest.get("sha256") or "").upper()
    actual_sha = hashlib.sha256(data).hexdigest().upper()
    if actual_sha != expected_sha:
        raise RuntimeError("SHA256 stimmt nicht ueberein")

    _validate_ipk(data, manifest)
    backup = _backup_plugin()
    safe_version = re.sub(r"[^A-Za-z0-9._-]+", "_", str(manifest.get("version") or "update"))
    ipk_path = "/tmp/mediaplugins2026_update_%s.ipk" % safe_version
    with open(ipk_path, "wb") as handle:
        handle.write(data)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except Exception:
            pass

    proc = subprocess.Popen(
        ["opkg", "install", "--force-reinstall", ipk_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        try:
            output, _ = proc.communicate(timeout=180)
        except TypeError:
            output, _ = proc.communicate()
    except subprocess.TimeoutExpired:
        proc.kill()
        output, _ = proc.communicate()
        raise RuntimeError("opkg-Installation hat das Zeitlimit ueberschritten")

    text = (output or b"").decode("utf-8", "replace")[-4000:]
    if proc.returncode != 0:
        raise RuntimeError(
            "opkg meldet Fehler (%d):\n%s\n\nBackup: %s"
            % (proc.returncode, text, backup)
        )

    _mark_installed(
        str(manifest.get("version") or ""),
        int(manifest.get("build") or 0),
    )
    try:
        os.remove(ipk_path)
    except Exception:
        pass
    return {
        "version": str(manifest.get("version") or ""),
        "build": int(manifest.get("build") or 0),
        "backup": backup,
    }


class MediaPluginsUpdateScreen(Screen):
    skin = """
    <screen name="MediaPluginsUpdateScreen" position="center,center" size="1600,900" flags="wfNoBorder" backgroundColor="#02070D">
        <eLabel position="0,0" size="1600,900" backgroundColor="#02070D" zPosition="0" />
        <eLabel position="285,93" size="1030,728" backgroundColor="#243A50" zPosition="1" />
        <eLabel position="288,97" size="1023,722" backgroundColor="#07111B" zPosition="2" />
        <eLabel position="288,97" size="1023,77" backgroundColor="#0C1723" zPosition="3" />
        <eLabel position="288,172" size="1023,2" backgroundColor="#263E55" zPosition="4" />
        <eLabel text="IM" position="318,112" size="53,45" font="Bold;26" foregroundColor="#27C8FF" backgroundColor="#0C1723" halign="center" valign="center" transparent="1" zPosition="10" />
        <eLabel text="MediaPlugins2026" position="388,111" size="325,47" font="Bold;29" foregroundColor="#F4F7FB" backgroundColor="#0C1723" valign="center" transparent="1" zPosition="10" />
        <widget name="state_title" position="942,115" size="333,38" font="Regular;21" foregroundColor="#E2E8EF" backgroundColor="#0C1723" halign="right" valign="center" transparent="1" zPosition="20" />

        <eLabel text="Installiert:" position="327,212" size="154,33" font="Regular;22" foregroundColor="#B7C2CF" backgroundColor="#07111B" transparent="1" zPosition="10" />
        <widget name="update_installed" position="479,212" size="392,37" font="Bold;19" foregroundColor="#F4F7FB" backgroundColor="#07111B" transparent="1" noWrap="1" zPosition="20" />
        <eLabel text="Verfuegbar:" position="327,258" size="154,33" font="Regular;22" foregroundColor="#B7C2CF" backgroundColor="#07111B" transparent="1" zPosition="10" />
        <widget name="update_available" position="479,258" size="392,37" font="Bold;19" foregroundColor="#27E477" backgroundColor="#07111B" transparent="1" noWrap="1" zPosition="20" />
        <eLabel text="Kanal:" position="327,302" size="154,33" font="Regular;22" foregroundColor="#B7C2CF" backgroundColor="#07111B" transparent="1" zPosition="10" />
        <widget name="update_channel" position="508,302" size="358,37" font="Regular;21" foregroundColor="#F4F7FB" backgroundColor="#07111B" transparent="1" zPosition="20" />
        <eLabel text="Zuletzt geprueft:" position="327,339" size="158,28" font="Regular;18" foregroundColor="#8294A6" backgroundColor="#07111B" transparent="1" zPosition="10" />
        <widget name="update_last_checked" position="508,339" size="358,30" font="Regular;18" foregroundColor="#C7D2DE" backgroundColor="#07111B" transparent="1" zPosition="20" />
        <eLabel text="Installiert am:" position="327,372" size="154,28" font="Regular;18" foregroundColor="#8294A6" backgroundColor="#07111B" transparent="1" zPosition="10" />
        <widget name="update_last_installed" position="508,372" size="358,30" font="Regular;18" foregroundColor="#C7D2DE" backgroundColor="#07111B" transparent="1" zPosition="20" />

        <eLabel position="327,413" size="542,1" backgroundColor="#354657" zPosition="5" />
        <widget name="content_title" position="327,432" size="542,32" font="Regular;22" foregroundColor="#E1E7ED" backgroundColor="#07111B" transparent="1" zPosition="20" />
        <widget name="update_changelog" position="335,468" size="508,121" font="Regular;18" foregroundColor="#F0F3F6" backgroundColor="#07111B" transparent="1" noWrap="0" zPosition="20" />
        <widget name="update_scroll_hint" position="771,593" size="90,22" font="Regular;14" foregroundColor="#8294A6" backgroundColor="#07111B" transparent="1" halign="right" zPosition="24" />

        <eLabel position="892,203" size="1,395" backgroundColor="#354657" zPosition="5" />
        <eLabel text="SICHERHEIT" position="925,208" size="300,32" font="Bold;18" foregroundColor="#9AA9B9" backgroundColor="#07111B" transparent="1" zPosition="10" />
        <widget name="update_steps" position="925,255" size="325,313" font="Regular;19" foregroundColor="#D5DEE8" backgroundColor="#07111B" transparent="1" zPosition="21" />

        <widget name="update_status" position="327,605" size="923,28" font="Regular;17" foregroundColor="#8FA2B5" backgroundColor="#07111B" halign="center" valign="center" transparent="1" zPosition="20" />
        <widget name="key_green" position="483,642" size="633,55" font="Regular;23" foregroundColor="#FFFFFF" backgroundColor="#006DCE" halign="center" valign="center" transparent="0" zPosition="30" />
        <eLabel text="Abbrechen" position="483,707" size="633,45" font="Regular;21" foregroundColor="#F4F7FB" backgroundColor="#26313C" halign="center" valign="center" transparent="0" zPosition="25" />

        <eLabel position="315,778" size="15,15" backgroundColor="red" zPosition="31" />
        <eLabel text="Zurueck" position="340,770" size="100,30" font="Regular;15" foregroundColor="#9BA9B7" backgroundColor="#07111B" transparent="1" zPosition="31" />
        <eLabel text="UP/DOWN  Aenderungen scrollen" position="617,770" size="367,30" font="Regular;15" foregroundColor="#9BA9B7" backgroundColor="#07111B" transparent="1" halign="center" zPosition="31" />
        <eLabel position="1143,778" size="15,15" backgroundColor="blue" zPosition="31" />
        <eLabel text="Neu pruefen" position="1168,770" size="108,30" font="Regular;15" foregroundColor="#9BA9B7" backgroundColor="#07111B" transparent="1" zPosition="31" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.setTitle("Media Plugins 2026 Update")
        self["state_title"] = Label("Update pruefen")
        self["update_status"] = Label("Bereit zur Update-Pruefung")
        self["update_installed"] = Label(str(PLUGIN_VERSION))
        self["update_available"] = Label("-")
        self["update_channel"] = Label(str(PLUGIN_UPDATE_CHANNEL).lower())
        self["update_last_checked"] = Label("Noch nie")
        self["update_last_installed"] = Label("Unbekannt")
        self["content_title"] = Label("Aenderungen:")
        self["update_changelog"] = Label("Noch nicht geprueft.")
        self["update_scroll_hint"] = Label("")
        self["update_steps"] = Label(
            "○ Manifest laden\n\n○ SHA256 pruefen\n\n○ IPK pruefen\n\n○ Backup vorbereiten\n\n○ Paket installieren"
        )
        self["key_green"] = Label("PRUEFEN")
        self._busy = False
        self._worker_done = False
        self._worker_result = None
        self._worker_kind = ""
        self._manifest = None
        self._update_available_flag = False
        self._installable = False
        self._installed_success = False
        self._changelog_pages = ["Noch nicht geprueft."]
        self._changelog_page = 0

        self._poll_timer = eTimer()
        try:
            self._poll_timer.callback.append(self._poll_worker)
        except Exception:
            try:
                self._poll_timer.timeout.connect(self._poll_worker)
            except Exception:
                pass

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "ok": self.green_pressed,
                "green": self.green_pressed,
                "blue": self.check_updates,
                "up": self.changelog_page_up,
                "down": self.changelog_page_down,
            },
            -1,
        )
        self._refresh_timestamps()
        self.onLayoutFinish.append(self.check_updates)

    def _refresh_timestamps(self):
        state = _load_state()
        checked = int(state.get("last_checked_ts") or 0)
        installed = int(state.get("last_installed_ts") or 0)
        if installed <= 0:
            installed = _install_time_fallback()
        self["update_last_checked"].setText(_timestamp_text(checked))
        self["update_last_installed"].setText(_timestamp_text(installed))

    def _render_changelog_page(self):
        pages = list(self._changelog_pages or [""])
        page = max(0, min(int(self._changelog_page or 0), len(pages) - 1))
        self._changelog_page = page
        self["update_changelog"].setText(pages[page])
        self["update_scroll_hint"].setText(
            "%d/%d" % (page + 1, len(pages)) if len(pages) > 1 else ""
        )

    def changelog_page_up(self):
        if self._changelog_page > 0:
            self._changelog_page -= 1
            self._render_changelog_page()

    def changelog_page_down(self):
        if self._changelog_page + 1 < len(self._changelog_pages):
            self._changelog_page += 1
            self._render_changelog_page()

    def _set_changelog_static(self, value):
        self._changelog_pages = [str(value or "")]
        self._changelog_page = 0
        self._render_changelog_page()

    def _set_changelog(self, items):
        import textwrap
        values = [
            str(value or "").strip()
            for value in list(items or [])[:20]
            if str(value or "").strip()
        ]
        if not values:
            self._set_changelog_static("Keine Aenderungsnotizen angegeben.")
            return
        lines = []
        for value in values:
            wrapped = textwrap.wrap(
                value,
                width=49,
                break_long_words=False,
                break_on_hyphens=False,
            ) or [value]
            lines.append("• " + wrapped[0])
            lines.extend("  " + part for part in wrapped[1:])
        page_size = 5
        self._changelog_pages = [
            "\n".join(lines[index:index + page_size])
            for index in range(0, len(lines), page_size)
        ] or [""]
        self._changelog_page = 0
        self._render_changelog_page()

    def _start_worker(self, kind, worker):
        if self._busy:
            return
        self._busy = True
        self._worker_done = False
        self._worker_result = None
        self._worker_kind = str(kind or "")

        def run():
            try:
                self._worker_result = {"ok": True, "value": worker()}
            except Exception as error:
                self._worker_result = {"ok": False, "error": str(error)}
                try:
                    with open("/tmp/mediaplugins2026_updater_error.log", "a") as handle:
                        handle.write(
                            "%s kind=%s error=%s\n"
                            % (
                                time.strftime("%Y-%m-%d %H:%M:%S"),
                                self._worker_kind,
                                str(error),
                            )
                        )
                except Exception:
                    pass
            finally:
                self._worker_done = True

        thread = threading.Thread(target=run, name="MediaPlugins2026Updater")
        thread.daemon = True
        thread.start()
        self._poll_timer.start(150, False)

    def check_updates(self):
        if self._busy:
            return
        self._installed_success = False
        self._manifest = None
        self._update_available_flag = False
        self._installable = False
        self["state_title"].setText("Update pruefen")
        self["update_status"].setText("Suche auf GitHub nach Updates ...")
        self["update_available"].setText("Wird geprueft ...")
        self["content_title"].setText("Aenderungen:")
        self._set_changelog_static("Manifest wird geladen ...")
        self["update_steps"].setText(
            "○ Manifest laden\n\n○ SHA256 pruefen\n\n○ IPK pruefen\n\n○ Backup vorbereiten\n\n○ Paket installieren"
        )
        self["key_green"].setText("PRUEFUNG LAEUFT")
        self._start_worker("check", _fetch_manifest)

    def _poll_worker(self):
        if not self._worker_done:
            return
        try:
            self._poll_timer.stop()
        except Exception:
            pass
        self._busy = False
        result = self._worker_result or {"ok": False, "error": "Keine Antwort"}
        kind = self._worker_kind
        if not result.get("ok"):
            self["state_title"].setText(
                "Pruefung fehlgeschlagen" if kind == "check" else "Update fehlgeschlagen"
            )
            self["update_status"].setText(
                "Update-Pruefung fehlgeschlagen" if kind == "check" else "Update fehlgeschlagen"
            )
            self["update_available"].setText("-")
            self["key_green"].setText("ERNEUT PRUEFEN")
            self["content_title"].setText("Fehlerbehandlung:")
            self._set_changelog_static(
                str(result.get("error") or "Unbekannter Fehler")[:500]
            )
            self["update_steps"].setText(
                "✗ Vorgang abgebrochen\n\n✓ Vorhandene Installation geschuetzt\n\n✓ Keine Serverdaten veraendert"
            )
            return
        value = result.get("value") or {}
        if kind == "check":
            self._apply_manifest(value)
        else:
            self._apply_install_success(value)

    def _apply_manifest(self, manifest):
        self._manifest = dict(manifest or {})
        try:
            _mark_checked(self._manifest)
        except Exception:
            pass
        self._refresh_timestamps()
        remote_build = int(self._manifest.get("build") or 0)
        remote_version = str(self._manifest.get("version") or "-")
        self._update_available_flag = _is_remote_newer(remote_version, remote_build)
        self._installable = bool(self._manifest.get("installable"))
        self["update_available"].setText(remote_version)
        self["update_channel"].setText(
            str(self._manifest.get("channel") or PLUGIN_UPDATE_CHANNEL).lower()
        )
        self["content_title"].setText("Aenderungen:")
        self._set_changelog(self._manifest.get("changelog"))
        self["update_steps"].setText(
            "✓ HTTPS-Manifest\n\n✓ Build geprueft\n\n✓ SHA256 vorhanden\n\n✓ IPK/Paket festgelegt\n\n✓ Backup vor Installation"
        )
        if not self._update_available_flag:
            self["state_title"].setText("Aktuell")
            local_revision = _version_revision(PLUGIN_VERSION)
            remote_revision = _version_revision(remote_version)
            local_is_newer = (
                local_revision is not None and remote_revision is not None and
                local_revision > remote_revision
            ) or (
                (local_revision is None or remote_revision is None or local_revision == remote_revision) and
                remote_build < int(PLUGIN_UPDATE_BUILD)
            )
            if local_is_newer:
                self["update_status"].setText(
                    "✓ Du hast bereits eine neuere Version installiert."
                )
            else:
                self["update_status"].setText("✓ Media Plugins 2026 ist aktuell.")
            self["key_green"].setText("ERNEUT PRUEFEN")
            return
        self["state_title"].setText("Update gefunden")
        self["update_status"].setText("Update verfuegbar und installierbar")
        self["key_green"].setText("UPDATE INSTALLIEREN")

    def green_pressed(self):
        if self._busy:
            return
        if self._installed_success:
            self.restart_gui()
            return
        if self._update_available_flag and self._installable and self._manifest:
            self.session.openWithCallback(
                self._install_confirmed,
                MessageBox,
                "Media Plugins 2026 Update wirklich installieren?\n\n%s\n\n"
                "SHA256, Paketname und IPK-Inhalt werden vor der Installation geprueft."
                % str(self._manifest.get("version") or "Update"),
                MessageBox.TYPE_YESNO,
            )
            return
        self.check_updates()

    def _install_confirmed(self, answer):
        if not answer or self._busy or not self._manifest:
            return
        manifest = dict(self._manifest)
        self["state_title"].setText("Update wird installiert")
        self["update_status"].setText("Bitte warten ...")
        self["key_green"].setText("INSTALLATION LAEUFT")
        self["update_steps"].setText(
            "○ Download ...\n\n○ SHA256 pruefen ...\n\n○ IPK pruefen ...\n\n○ Backup erstellen ...\n\n○ opkg installieren ..."
        )
        self._start_worker("install", lambda: _install_ipk(manifest))

    def _apply_install_success(self, result):
        self._installed_success = True
        self._refresh_timestamps()
        version = str(result.get("version") or "Update")
        self["state_title"].setText("Update erfolgreich")
        self["update_status"].setText(
            "✓ Update erfolgreich installiert · GUI-Neustart erforderlich"
        )
        self["update_available"].setText(version)
        self["content_title"].setText("Abgeschlossen:")
        self._set_changelog_static(
            "Media Plugins 2026 wurde erfolgreich aktualisiert.\n\n"
            "Die neue Version wird nach dem GUI-Neustart aktiv.\n\n"
            "Backup: %s" % str(result.get("backup") or "-")
        )
        self["key_green"].setText("GUI NEU STARTEN")
        self["update_steps"].setText(
            "✓ Download\n\n✓ SHA256 geprueft\n\n✓ IPK geprueft\n\n✓ Backup erstellt\n\n✓ Paket installiert"
        )

    def restart_gui(self):
        try:
            from Screens.Standby import TryQuitMainloop
            self.session.open(TryQuitMainloop, 3)
        except Exception as error:
            self.session.open(
                MessageBox,
                "Update ist installiert.\n\nAutomatischer GUI-Neustart nicht moeglich:\n%s\n\n"
                "Bitte Enigma2 manuell neu starten." % str(error),
                MessageBox.TYPE_INFO,
                timeout=12,
            )
