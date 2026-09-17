#!/bin/sh
set -u

BASE_URL="https://raw.githubusercontent.com/keggy6893/MediaPlugins2026-Updates/main/SafeUpdate2026"
META_URL="$BASE_URL/latest.json"
TMPDIR="/tmp/safeupdate2026-install"
ZIPFILE="$TMPDIR/SafeUpdate2026.zip"
EXTRACT="$TMPDIR/extract"
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/SafeUpdate2026"
BACKUP_DIR="/usr/lib/enigma2/python/Plugins/Extensions/SafeUpdate2026.before-install"

say() { echo "[SafeUpdate2026] $*"; }
fail() { say "FEHLER: $*"; exit 1; }

command -v wget >/dev/null 2>&1 || fail "wget fehlt."
command -v python3 >/dev/null 2>&1 || fail "python3 fehlt."

rm -rf "$TMPDIR"
mkdir -p "$EXTRACT" || fail "Temp-Verzeichnis konnte nicht erstellt werden."

say "Lade Versionsinformationen..."
wget -q -O "$TMPDIR/latest.json" "$META_URL" || fail "latest.json konnte nicht geladen werden."

VERSION=$(python3 -c 'import json; print(json.load(open("/tmp/safeupdate2026-install/latest.json"))["version"])') || fail "Version konnte nicht gelesen werden."
DOWNLOAD=$(python3 -c 'import json; print(json.load(open("/tmp/safeupdate2026-install/latest.json"))["download"])') || fail "Download-URL konnte nicht gelesen werden."
EXPECTED=$(python3 -c 'import json; print(json.load(open("/tmp/safeupdate2026-install/latest.json"))["sha256"])') || fail "SHA256 konnte nicht gelesen werden."

say "Version: $VERSION"
say "Lade Plugin..."
wget -q -O "$ZIPFILE" "$DOWNLOAD" || fail "Plugin-ZIP konnte nicht geladen werden."

ACTUAL=$(python3 -c 'import hashlib; print(hashlib.sha256(open("/tmp/safeupdate2026-install/SafeUpdate2026.zip","rb").read()).hexdigest())') || fail "SHA256-Prüfung fehlgeschlagen."
[ "$ACTUAL" = "$EXPECTED" ] || fail "SHA256 stimmt nicht. Installation abgebrochen."
say "SHA256: OK"

say "Entpacke Plugin..."
if command -v unzip >/dev/null 2>&1; then
    unzip -q -o "$ZIPFILE" -d "$EXTRACT" || fail "Entpacken fehlgeschlagen."
else
    python3 -m zipfile -e "$ZIPFILE" "$EXTRACT" || fail "Entpacken fehlgeschlagen."
fi

[ -f "$EXTRACT/SafeUpdate2026/plugin.py" ] || fail "plugin.py fehlt im Paket."
python3 -m py_compile "$EXTRACT/SafeUpdate2026/plugin.py" || fail "Python-Syntaxprüfung des Downloads fehlgeschlagen."
say "Python-Syntax: OK"

rm -rf "$BACKUP_DIR"
if [ -d "$PLUGIN_DIR" ]; then
    say "Sichere vorhandene Installation..."
    cp -a "$PLUGIN_DIR" "$BACKUP_DIR" || fail "Backup der alten Installation fehlgeschlagen."
fi

say "Installiere SafeUpdate2026..."
rm -rf "$PLUGIN_DIR"
cp -a "$EXTRACT/SafeUpdate2026" "$PLUGIN_DIR" || {
    say "Installation fehlgeschlagen - versuche Rollback..."
    rm -rf "$PLUGIN_DIR"
    [ -d "$BACKUP_DIR" ] && cp -a "$BACKUP_DIR" "$PLUGIN_DIR"
    fail "Installation fehlgeschlagen."
}

if ! python3 -m py_compile "$PLUGIN_DIR/plugin.py"; then
    say "Installierte Datei ist fehlerhaft - Rollback..."
    rm -rf "$PLUGIN_DIR"
    [ -d "$BACKUP_DIR" ] && cp -a "$BACKUP_DIR" "$PLUGIN_DIR"
    fail "Syntaxprüfung nach Installation fehlgeschlagen."
fi

sync
say "SafeUpdate2026 $VERSION wurde erfolgreich installiert."
say "Enigma2 wird neu gestartet..."
rm -rf "$TMPDIR"
init 4
sleep 3
init 3
