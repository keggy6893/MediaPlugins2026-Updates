#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MediaPlugins2026 poster-cache validation fix with mandatory pre-write backups.

Fixes the impossible validator path where is_valid_path() passed 16 bytes to
_valid_image_bytes(), although that validator requires at least 128 bytes.

Safety rule: before any write this patcher creates BOTH
1) a complete timestamped tar.gz backup of the whole plugin tree, and
2) a timestamped backup of every file it changes.
If either backup cannot be created and verified, the patch aborts without writing.
"""
from __future__ import print_function

import hashlib
import io
import os
import shutil
import sys
import tarfile
import time

ROOT_DEFAULT = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPlugins2026"
TARGET_REL = "utils/image_cache.py"
MARKER = "# MEDIAPLUGINS2026_POSTER_CACHE_VALIDATION_FIX2"
BAD = "return self._valid_image_bytes(handle.read(16))"
GOOD = "return self._valid_image_bytes(handle.read(128))"


def read(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def create_full_backup(root, stamp):
    if not os.path.isdir(root):
        raise RuntimeError("Pluginordner fehlt: %s" % root)

    backup = "/tmp/MediaPlugins2026_BEFORE_POSTER_CACHE_VALIDATION_FIX2_%s.tar.gz" % stamp
    base = os.path.basename(root.rstrip(os.sep)) or "MediaPlugins2026"

    with tarfile.open(backup, "w:gz") as archive:
        archive.add(root, arcname=base)

    if not os.path.isfile(backup) or os.path.getsize(backup) <= 0:
        raise RuntimeError("Komplettbackup wurde nicht korrekt angelegt: %s" % backup)

    expected = base + "/" + TARGET_REL
    with tarfile.open(backup, "r:gz") as archive:
        names = set(archive.getnames())
        if expected not in names:
            raise RuntimeError("Komplettbackup unvollstaendig; %s fehlt" % expected)

    return backup, sha256_file(backup)


def create_file_backup(target, stamp):
    backup = target + ".before_POSTER_CACHE_VALIDATION_FIX2_" + stamp
    if os.path.exists(backup):
        raise RuntimeError("Dateibackup existiert bereits: %s" % backup)
    shutil.copy2(target, backup)
    if not os.path.isfile(backup) or os.path.getsize(backup) != os.path.getsize(target):
        raise RuntimeError("Dateibackup konnte nicht verifiziert werden: %s" % backup)
    return backup


def add_marker(text):
    if MARKER in text:
        return text
    if text.startswith("# -*- coding: utf-8 -*-"):
        first, rest = text.split("\n", 1)
        return first + "\n" + MARKER + "\n" + rest
    return MARKER + "\n" + text


def patch(text):
    bad_count = text.count(BAD)
    good_count = text.count(GOOD)

    if bad_count > 1:
        raise RuntimeError(
            "Poster-Validator nicht eindeutig: %d fehlerhafte read(16)-Stellen" % bad_count
        )

    if bad_count == 1:
        text = text.replace(BAD, GOOD, 1)
    elif good_count == 0:
        raise RuntimeError(
            "Erwartete Validator-Stelle weder als read(16) noch als read(128) gefunden"
        )

    text = add_marker(text)
    compile(text, "image_cache.py", "exec")

    if BAD in text:
        raise RuntimeError("read(16)-Validator ist nach Patch noch vorhanden")
    if GOOD not in text:
        raise RuntimeError("read(128)-Validator fehlt nach Patch")
    if MARKER not in text:
        raise RuntimeError("Fix-Marker fehlt nach Patch")
    return text


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DEFAULT
    target = os.path.join(root, TARGET_REL)

    if not os.path.isfile(target):
        raise SystemExit("image_cache.py nicht gefunden: %s" % target)

    original = read(target)

    # Idempotenter No-op: kein Backup noetig, weil nichts geschrieben wird.
    if MARKER in original and GOOD in original and BAD not in original:
        compile(original, target, "exec")
        print("OK MEDIAPLUGINS2026_POSTER_CACHE_VALIDATION_FIX2 BEREITS_AKTIV")
        return 0

    patched = patch(original)
    compile(patched, target, "exec")

    # PFLICHT: erst ALLE Backups, danach darf geschrieben werden.
    stamp = time.strftime("%Y%m%d-%H%M%S")
    full_backup, full_sha256 = create_full_backup(root, stamp)
    file_backup = create_file_backup(target, stamp)

    try:
        write(target, patched)
        verify = read(target)
        compile(verify, target, "exec")
        if MARKER not in verify or GOOD not in verify or BAD in verify:
            raise RuntimeError("Live-Verifikation fehlgeschlagen")
    except Exception:
        # Datei sofort zurueck. Das vollstaendige tar.gz bleibt zusaetzlich erhalten.
        shutil.copy2(file_backup, target)
        raise

    print("OK MEDIAPLUGINS2026_POSTER_CACHE_VALIDATION_FIX2")
    print("- VOR dem Schreiben komplettes Pluginbackup angelegt und geprueft")
    print("- VOR dem Schreiben image_cache.py einzeln gesichert")
    print("- is_valid_path liest 128 Byte statt 16 Byte")
    print("- keine Provider-/Home-/Snapshot-/Player-Logik geaendert")
    print("Komplettbackup: %s" % full_backup)
    print("Komplettbackup SHA256: %s" % full_sha256)
    print("Dateibackup: %s" % file_backup)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
