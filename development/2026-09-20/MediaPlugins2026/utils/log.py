# -*- coding: utf-8 -*-
import logging
import traceback
import os

# r70: mehrere Kandidatenpfade probieren statt blind auf /tmp zu vertrauen -
# auf manchen Boxen/Images ist /tmp eingeschraenkt oder wird durch andere
# Prozesse belegt, wodurch bislang GAR KEIN Log geschrieben wurde und der
# Fehler wegen des stummen except/pass unbemerkt blieb.
_CANDIDATE_PATHS = [
    "/tmp/mediaplugins2026.log",
    "/media/hdd/mediaplugins2026.log",
    "/home/root/mediaplugins2026.log",
    "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026/mediaplugins2026.log",
]

LOG_PATH = _CANDIDATE_PATHS[0]

_logger = logging.getLogger("MediaPlugins2026")
_logger.setLevel(logging.DEBUG)

if not _logger.handlers:
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")

    file_handler = None
    for path in _CANDIDATE_PATHS:
        try:
            fh = logging.FileHandler(path, mode="a", encoding="utf-8")
            fh.setFormatter(fmt)
            fh.emit(logging.LogRecord(
                "MediaPlugins2026", logging.INFO, __file__, 0,
                "--- Log gestartet (%s) ---" % path, None, None
            ))
            fh.flush()
            file_handler = fh
            LOG_PATH = path
            break
        except Exception:
            continue

    if file_handler is not None:
        _logger.addHandler(file_handler)

    # zusätzlich auf stdout, damit es auch im enigma2-Crashlog/Log auftaucht,
    # das enigma2 selbst ueber print()/stdout mitschneidet
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    _logger.addHandler(stream_handler)


def debug(msg, *args):
    _logger.debug(_fmt(msg, args))


def info(msg, *args):
    _logger.info(_fmt(msg, args))


def warning(msg, *args):
    _logger.warning(_fmt(msg, args))


def error(msg, *args):
    _logger.error(_fmt(msg, args))


def exception(msg, *args):
    """Loggt eine Fehlermeldung inkl. vollständigem Traceback."""
    _logger.error(_fmt(msg, args))
    _logger.error(traceback.format_exc())


def _fmt(msg, args):
    try:
        return msg % args if args else msg
    except Exception:
        return msg


def safe_call(func, *args, **kwargs):
    """Führt func aus, loggt aber jede Exception statt das Plugin abstürzen
    zu lassen. Für Callback-Aufrufe aus Twisted-Deferreds gedacht, wo eine
    unbehandelte Exception sonst nur still im Reactor verschwindet."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        exception("Unerwarteter Fehler in %s: %s", getattr(func, "__name__", str(func)), e)
        return None


def log_path():
    return LOG_PATH
