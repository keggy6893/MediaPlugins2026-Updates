# -*- coding: utf-8 -*-
from io import BytesIO

from ..utils import log

# MEDIAPLUGINS2026_HTTP_LOG_REDACT1
def _safe_log_url(url):
    try:
        from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
        text = url.decode("utf-8", "replace") if isinstance(url, bytes) else str(url)
        parts = urlsplit(text)
        sensitive = {
            "x-plex-token", "api_key", "apikey", "token",
            "access_token", "auth", "authorization",
        }
        query = [
            (key, "***" if key.lower() in sensitive else value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
        ]
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    except Exception:
        return "<redacted-url>"


class HttpHelper(object):
    """Gemeinsamer async HTTP-Client fuer Emby/Jellyfin/Plex-Backends (Twisted).
    twisted-Imports bewusst lazy (siehe utils/image_cache.py fuer Details
    zum Verdacht auf Reactor-Kollision mit Enigma2)."""

    def __init__(self, timeout=10):
        self.timeout = timeout
        self._agent = None

    def _get_agent(self):
        if self._agent is None:
            from twisted.internet import reactor
            from twisted.web.client import Agent
            self._agent = Agent(reactor)
        return self._agent

    def get(self, url, headers=None, callback=None, error_callback=None):
        self._request(b"GET", url, headers, None, callback, error_callback)

    def post(self, url, payload, headers=None, callback=None, error_callback=None):
        from twisted.web.client import FileBodyProducer
        body = FileBodyProducer(BytesIO(payload)) if payload else None
        self._request(b"POST", url, headers, body, callback, error_callback)

    def delete(self, url, headers=None, callback=None, error_callback=None):
        self._request(b"DELETE", url, headers, None, callback, error_callback)

    def _request(self, method, url, headers, body, callback, error_callback):
        from twisted.web.client import readBody
        from twisted.web.http_headers import Headers
        from twisted.internet import reactor

        hdr_obj = Headers()
        if headers:
            for key, values in headers.items():
                hdr_obj.setRawHeaders(key, values)

        url_bytes = url.encode("utf-8") if isinstance(url, str) else url
        log.debug("HTTP %s %s", method.decode() if isinstance(method, bytes) else method, _safe_log_url(url))

        try:
            agent = self._get_agent()
            d = agent.request(method, url_bytes, hdr_obj, body)
        except Exception as e:
            log.exception("HTTP-Request konnte nicht gestartet werden (%s): %s", _safe_log_url(url), e)
            if error_callback:
                error_callback(str(e))
            return

        def on_response(response):
            if response.code >= 400:
                log.warning("HTTP %d bei %s", response.code, _safe_log_url(url))
                if error_callback:
                    error_callback("HTTP %d" % response.code)
                return
            d2 = readBody(response)
            d2.addCallback(on_body)
            d2.addErrback(on_error)

        def on_body(body_bytes):
            if callback:
                try:
                    callback(body_bytes.decode("utf-8"))
                except Exception as e:
                    log.exception("Fehler im Callback fuer %s: %s", _safe_log_url(url), e)

        def on_error(failure):
            log.warning("Netzwerkfehler bei %s: %s", _safe_log_url(url), failure.getErrorMessage())
            if error_callback:
                error_callback(str(failure.getErrorMessage()))

        d.addCallback(on_response)
        d.addErrback(on_error)

        timeout_call = reactor.callLater(self.timeout, lambda: d.cancel())

        def cancel_timeout(result):
            if timeout_call.active():
                timeout_call.cancel()
            return result

        d.addBoth(cancel_timeout)
