# -*- coding: utf-8 -*-
import os
import hashlib
import time

from . import log

PERSISTENT_CACHE_MAX_BYTES = 12 * 1024 * 1024
PERSISTENT_CACHE_MAX_FILES = 120
CACHE_MAX_AGE_DAYS = 14
CACHE_DIR = "/etc/enigma2/mediaplugins2026/poster_cache"


# MEDIAPLUGINS2026_POSTER_PIPELINE_R21_CACHE
class ImageCache(object):
    """
    WICHTIG: twisted.internet.reactor/Agent werden bewusst NICHT auf
    Modulebene importiert, sondern erst lazy in _get_agent() beim ersten
    tatsaechlichen Download. Ein zu frueher twisted-reactor-Import (schon
    beim Laden des Plugin-Moduls, vor dem ersten applySkin()) stand im
    Verdacht, mit Enigma2s eigener Reactor-Installation zu kollidieren
    und einen exec()-Absturz in Screen.py createGUIScreen auszuloesen.
    """

    def __init__(self):
        self.cache_dir = CACHE_DIR
        try:
            if not os.path.isdir(self.cache_dir):
                os.makedirs(self.cache_dir)
        except Exception as exc:
            log.warning("PosterCache intern nicht anlegbar (%s), verwende /tmp", exc)
            self.cache_dir = "/tmp/mediaplugins2026_unified_cache"
            if not os.path.isdir(self.cache_dir):
                os.makedirs(self.cache_dir)
        log.info("PosterCache aktiv: %s", self.cache_dir)
        self._agent = None
        self._pending = {}
        self._queue = []
        self._active_downloads = 0
        self._max_parallel = 4
        self._retry_counts = {}
        self.timeout = 12
        try:
            self.cleanup_old_entries()
            self._prune_limits()
        except Exception:
            pass

    def _get_agent(self):
        if self._agent is None:
            from twisted.internet import reactor
            from twisted.web.client import Agent
            self._agent = Agent(reactor)
        return self._agent

    def get_local_path(self, url):
        if not url:
            return None
        local_path = self._path_for_url(url)
        if not os.path.isfile(local_path):
            return None
        if not self.is_valid_path(local_path):
            self.invalidate_path(local_path)
            return None
        try:
            os.utime(local_path, None)
        except Exception:
            pass
        return local_path

    def fetch(self, url, callback, error_callback=None):
        if not url:
            if error_callback:
                error_callback("keine URL")
            return

        cached = self.get_local_path(url)
        if cached:
            callback(cached)
            return

        if url in self._pending:
            self._pending[url].append((callback, error_callback))
            return

        self._pending[url] = [(callback, error_callback)]
        self._queue.append(url)
        self._pump_queue()


    def _pump_queue(self):
        while self._active_downloads < self._max_parallel and self._queue:
            url = self._queue.pop(0)
            if url not in self._pending:
                continue
            self._active_downloads += 1
            self._download(url)

    def _download_finished(self):
        self._active_downloads = max(0, self._active_downloads - 1)
        self._pump_queue()

    @staticmethod
    def _valid_image_bytes(data):
        if not data or len(data) < 128:
            return False
        head = data[:16]
        return (
            head.startswith(b"\xff\xd8\xff")
            or head.startswith(b"\x89PNG\r\n\x1a\n")
            or head[:6] in (b"GIF87a", b"GIF89a")
            or (len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP")
        )

    def is_valid_path(self, path):
        if not path or not os.path.isfile(path):
            return False
        try:
            if os.path.getsize(path) < 128:
                return False
            with open(path, "rb") as handle:
                return self._valid_image_bytes(handle.read(128))
        except Exception:
            return False

    @staticmethod
    def _safe_remove(path):
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    def invalidate_path(self, path):
        self._safe_remove(path)

    def _should_retry(self, msg):
        text = str(msg or "")
        return not (text.startswith("HTTP 4") and not text.startswith(("HTTP 408", "HTTP 429")))

    def _retry_url(self, url):
        if url not in self._pending:
            return
        if url not in self._queue:
            self._queue.append(url)
        self._pump_queue()

    def _prune_limits(self):
        if not os.path.isdir(self.cache_dir):
            return
        entries = []
        total = 0
        for name in os.listdir(self.cache_dir):
            path = os.path.join(self.cache_dir, name)
            if ".part-" in name:
                self._safe_remove(path)
                continue
            try:
                if not os.path.isfile(path):
                    continue
                size = os.path.getsize(path)
                entries.append((os.path.getmtime(path), path, size))
                total += size
            except OSError:
                pass
        entries.sort()
        while entries and (len(entries) > PERSISTENT_CACHE_MAX_FILES or total > PERSISTENT_CACHE_MAX_BYTES):
            _mtime, path, size = entries.pop(0)
            self._safe_remove(path)
            total = max(0, total - size)

    def _path_for_url(self, url):
        h = hashlib.sha1(self._stable_cache_key(url).encode("utf-8")).hexdigest()
        ext = ".png" if url.lower().split("?", 1)[0].endswith(".png") else ".jpg"
        return os.path.join(self.cache_dir, h + ext)

    @staticmethod
    def _stable_cache_key(url):
        """r52: Cache-Schluessel ohne den volatilen api_key-Parameter.

        get_image_url() haengt seit r51 das Jellyfin/Emby-Sessiontoken als
        api_key an jede Poster-URL an (behebt HTTP 401 bei abgesicherten
        Servern). Der Token aendert sich bei jedem Login - wuerde er mit in
        den Cache-Hash einfliessen, bekaeme dasselbe Cover bei jedem
        Boxneustart/erneuten Login einen neuen Dateinamen und wuerde immer
        wieder komplett neu heruntergeladen ("Cover laden langsam/gar
        nicht"). Fuer den Cache zaehlt nur, WELCHES Bild in WELCHER Groesse
        angefragt wird - nicht, mit welchem Token.
        """
        try:
            from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
            parts = urlsplit(url)
            query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                     if k.lower() != "api_key"]
            return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))
        except Exception:
            return url

    def _download(self, url):
        from twisted.web.client import readBody
        from twisted.internet import reactor
        agent = self._get_agent()
        d = agent.request(b"GET", url.encode("utf-8"))
        state = {"done": False}

        def finish_once(fn, *args):
            if state["done"]:
                return
            state["done"] = True
            if timeout_call.active():
                timeout_call.cancel()
            fn(*args)

        def on_response(response):
            if response.code >= 400:
                finish_once(self._fail, url, "HTTP %d" % response.code)
                return
            d2 = readBody(response)
            d2.addCallback(lambda data: finish_once(self._on_body, url, data))
            d2.addErrback(lambda f: finish_once(self._fail, url, str(f.getErrorMessage())))

        d.addCallback(on_response)
        d.addErrback(lambda f: finish_once(self._fail, url, str(f.getErrorMessage())))

        def on_timeout():
            if state["done"]:
                return
            state["done"] = True
            try:
                d.cancel()
            except Exception:
                pass
            self._fail(url, "Timeout nach %ds" % self.timeout)

        timeout_call = reactor.callLater(self.timeout, on_timeout)

    def _on_body(self, url, data):
        local_path = self._path_for_url(url)
        tmp_path = "%s.part-%d" % (local_path, os.getpid())
        if not self._valid_image_bytes(data):
            self._safe_remove(tmp_path)
            self._fail(url, "ungueltige Bilddaten")
            return
        try:
            with open(tmp_path, "wb") as handle:
                handle.write(data)
                try:
                    handle.flush()
                    os.fsync(handle.fileno())
                except Exception:
                    pass
            if not self.is_valid_path(tmp_path):
                raise IOError("geschriebene Bilddatei ungueltig")
            try:
                os.replace(tmp_path, local_path)
            except AttributeError:
                self._safe_remove(local_path)
                os.rename(tmp_path, local_path)
            try:
                os.chmod(local_path, 0o600)
            except Exception:
                pass
        except Exception as exc:
            self._safe_remove(tmp_path)
            self._fail(url, str(exc))
            return
        self._retry_counts.pop(url, None)
        callbacks = self._pending.pop(url, [])
        for callback, _ in callbacks:
            try:
                callback(local_path)
            except Exception as exc:
                log.warning("PosterCache callback fehlgeschlagen: %s", exc)
        try:
            self._prune_limits()
        except Exception:
            pass
        self._download_finished()

    def _fail(self, url, msg):
        retries = int(self._retry_counts.get(url, 0) or 0)
        if url in self._pending and retries < 1 and self._should_retry(msg):
            self._retry_counts[url] = retries + 1
            log.warning("Poster-Download fehlgeschlagen; ein Retry folgt: %s", msg)
            self._download_finished()
            try:
                from twisted.internet import reactor
                reactor.callLater(0.8, self._retry_url, url)
            except Exception:
                self._retry_url(url)
            return
        self._retry_counts.pop(url, None)
        log.warning("Poster-Download endgueltig fehlgeschlagen: %s", msg)
        callbacks = self._pending.pop(url, [])
        for _, error_callback in callbacks:
            if error_callback:
                try:
                    error_callback(msg)
                except Exception:
                    pass
        self._download_finished()

    def cleanup_old_entries(self):
        now = time.time()
        max_age = CACHE_MAX_AGE_DAYS * 86400
        if not os.path.isdir(self.cache_dir):
            return
        for fname in os.listdir(self.cache_dir):
            fpath = os.path.join(self.cache_dir, fname)
            try:
                if not os.path.isfile(fpath):
                    continue
                if ".part-" in fname or now - os.path.getmtime(fpath) > max_age or not self.is_valid_path(fpath):
                    self._safe_remove(fpath)
            except OSError:
                pass
        self._prune_limits()

# Modulweiter Singleton - Konstruktor selbst macht KEINEN twisted-Import
# und KEINE reactor-Nutzung mehr (siehe _get_agent), daher hier weiterhin
# sicher auf Modulebene instanziierbar.
image_cache = ImageCache()
