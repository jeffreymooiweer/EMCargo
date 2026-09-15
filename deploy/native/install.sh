#!/usr/bin/env bash
# Install EMCargo as a native service on a Debian/Ubuntu-like host.
#
# What it does, and only this:
#   1. creates the service user and the directories
#        /opt/emcargo          the releases (one directory per version) and the venv
#        /var/lib/emcargo      the data: database, uploads, branding, UN cards
#        /etc/emcargo          the environment file
#   2. downloads the native bundle of a release from GitHub (or unpacks a
#      local one), makes a virtual environment and installs the runtime
#        requirements into it
#   3. installs the systemd unit and starts the service
#
# Re-running it with a newer version is the update: the bundle is unpacked
# next to the old one and the `current` link is moved. Nothing under
# /var/lib/emcargo is touched by either.
#
#   sudo ./install.sh                  # the latest release
#   sudo ./install.sh 1.181.0          # a named release
#   sudo ./install.sh --bundle emcargo-1.181.0-native.tar.gz
set -euo pipefail

REPO="jeffreymooiweer/emcargo"
PREFIX="/opt/emcargo"
DATA_DIR="/var/lib/emcargo"
CONF_DIR="/etc/emcargo"
SERVICE_USER="emcargo"
PYTHON="${PYTHON:-python3}"

VERSION=""
BUNDLE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --bundle) BUNDLE="$2"; shift 2 ;;
    --help|-h) sed -n '2,20p' "$0"; exit 0 ;;
    *) VERSION="$1"; shift ;;
  esac
done

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this as root (sudo): it creates a user, directories and a systemd unit." >&2
  exit 1
fi

for tool in curl tar; do
  command -v "$tool" >/dev/null 2>&1 || { echo "Missing: $tool" >&2; exit 1; }
done
if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
  echo "EMCargo needs Python 3.11 or newer; found: $("$PYTHON" --version 2>&1 || echo none)." >&2
  echo "On Debian/Ubuntu: apt install python3 python3-venv" >&2
  exit 1
fi
"$PYTHON" -c 'import venv' 2>/dev/null || { echo "Python's venv module is missing (apt install python3-venv)." >&2; exit 1; }

# --- 1. user and directories ---------------------------------------------------
if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home-dir "$DATA_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi
mkdir -p "$PREFIX/releases" "$DATA_DIR" "$CONF_DIR"
chown "$SERVICE_USER:$SERVICE_USER" "$DATA_DIR"
chmod 750 "$DATA_DIR"

# --- 2. the bundle ---------------------------------------------------------------
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [ -z "$BUNDLE" ]; then
  if [ -z "$VERSION" ]; then
    VERSION="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
      | "$PYTHON" -c 'import json, sys; print(json.load(sys.stdin)["tag_name"].lstrip("v"))')"
  fi
  VERSION="${VERSION#v}"
  BUNDLE="$WORK/emcargo-$VERSION-native.tar.gz"
  URL="https://github.com/$REPO/releases/download/v$VERSION/emcargo-$VERSION-native.tar.gz"
  echo "Downloading $URL"
  curl -fsSL -o "$BUNDLE" "$URL"
else
  [ -f "$BUNDLE" ] || { echo "No such bundle: $BUNDLE" >&2; exit 1; }
  VERSION="$(tar -xzOf "$BUNDLE" --wildcards '*/VERSION' | tr -d '[:space:]')"
fi

RELEASE_DIR="$PREFIX/releases/$VERSION"
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"
tar -xzf "$BUNDLE" -C "$RELEASE_DIR" --strip-components=1
[ -f "$RELEASE_DIR/backend/requirements-runtime.txt" ] || { echo "The bundle has no backend/requirements-runtime.txt; not a native bundle." >&2; exit 1; }

# --- 3. the virtual environment ----------------------------------------------------
if [ ! -x "$PREFIX/venv/bin/python" ]; then
  "$PYTHON" -m venv "$PREFIX/venv"
fi
"$PREFIX/venv/bin/pip" install --quiet --upgrade pip
"$PREFIX/venv/bin/pip" install --quiet --require-hashes -r "$RELEASE_DIR/backend/requirements-runtime-lock.txt"
"$PREFIX/venv/bin/pip" uninstall --quiet -y PyMuPDF

# Use the new implementation to retain existing local templates before moving
# the current link. A fresh install has no previous release to migrate.
if [ -d "$PREFIX/current/backend" ]; then
  PYTHONPATH="$RELEASE_DIR/backend" DATA_DIR="$DATA_DIR" \
    "$PREFIX/venv/bin/python" -m app.migrate_templates "$PREFIX/current" --env-file "$CONF_DIR/emcargo.env"
fi

# --- 4. configuration, kept if present -----------------------------------------------
if [ ! -f "$CONF_DIR/emcargo.env" ]; then
  cp "$RELEASE_DIR/deploy/native/emcargo.env.example" "$CONF_DIR/emcargo.env"
  chmod 640 "$CONF_DIR/emcargo.env"
  chown root:"$SERVICE_USER" "$CONF_DIR/emcargo.env"
  echo "Wrote $CONF_DIR/emcargo.env — set ADMIN_PASSWORD and the addresses before the first start."
fi

# --- 5. the service ---------------------------------------------------------------------
ln -sfn "$RELEASE_DIR" "$PREFIX/current"
chown -R "$SERVICE_USER:$SERVICE_USER" "$PREFIX"
install -m 644 "$RELEASE_DIR/deploy/native/emcargo.service" /etc/systemd/system/emcargo.service
systemctl daemon-reload
systemctl enable emcargo >/dev/null
systemctl restart emcargo

echo
echo "EMCargo $VERSION is installed and running on http://127.0.0.1:8080"
echo "  data:      $DATA_DIR"
echo "  settings:  $CONF_DIR/emcargo.env"
echo "  logs:      journalctl -u emcargo -f"
echo "Put a reverse proxy with TLS in front of it; see docs/installation-native.md."
