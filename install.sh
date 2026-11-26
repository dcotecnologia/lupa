#!/bin/sh
# Install or update spotlight-linux for the current user.
#
#   curl -fsSL https://raw.githubusercontent.com/dcotecnologia/spotlight-linux/main/install.sh | sh
#
# Run from a checkout of the repository it installs that checkout; run anywhere else
# (or piped, as above) it picks the latest release, checks the download against the
# sha256 that GitHub publishes for it, and installs it. Run it again to update.
# On Cinnamon it also binds Super+Space.
#
# Options:
#   --version X     install release X (for example 0.1.0) instead of the latest
#   --prefix DIR    install the command into DIR instead of ~/.local/bin
#   --no-shortcut   install the command only, do not touch any keyboard shortcut
#   --dry-run       show what would be done and change nothing
#   -h, --help      show this help
#
# For tests and mirrors: SPOTLIGHT_REPO (owner/name) and SPOTLIGHT_API (the API URL,
# https only except for localhost).

set -eu

REPO="${SPOTLIGHT_REPO:-dcotecnologia/spotlight-linux}"
API="${SPOTLIGHT_API:-https://api.github.com}"
PY=/usr/bin/python3
VERSION=latest
PREFIX="${HOME:?HOME is not set}/.local/bin"
SHORTCUT=1
DRY_RUN=0

say() { printf '%s\n' "$*"; }
die() {
  printf 'install.sh: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: install.sh [options]

Install or update spotlight-linux from a checkout or from its GitHub release.

Options:
  --version X     install release X (for example 0.1.0) instead of the latest
  --prefix DIR    install the command into DIR instead of ~/.local/bin
  --no-shortcut   install the command only, do not touch any keyboard shortcut
  --dry-run       show what would be done and change nothing
  -h, --help      show this help
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --version) [ $# -ge 2 ] || die "--version needs a value"; VERSION="${2#v}"; shift 2 ;;
    --prefix) [ $# -ge 2 ] || die "--prefix needs a directory"; PREFIX="$2"; shift 2 ;;
    --no-shortcut) SHORTCUT=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h | --help) usage; exit 0 ;;
    *) die "unknown option: $1 (try --help)" ;;
  esac
done

[ "$(uname -s)" = Linux ] || die "spotlight-linux runs on Linux only"
TARGET="$PREFIX/spotlight"

# 1. Dependencies -------------------------------------------------------
[ -x "$PY" ] || die "$PY is needed (sudo apt install python3 python3-gi gir1.2-gtk-3.0)"
"$PY" -c "import gi; gi.require_version('Gtk', '3.0')" 2>/dev/null ||
  die "PyGObject/GTK3 is missing for $PY; run: sudo apt install python3-gi gir1.2-gtk-3.0"
command -v plocate >/dev/null 2>&1 ||
  say "Note: 'plocate' not found; file search is disabled (sudo apt install plocate)."

# 2. Where the files come from -------------------------------------------
# a checkout when this script sits next to src/spotlight.py, else the latest release
HERE=$(CDPATH='' cd -- "$(dirname -- "$0")" 2>/dev/null && pwd) || HERE=
if [ -n "$HERE" ] && [ -f "$HERE/src/spotlight.py" ] && [ "$VERSION" = latest ]; then
  SOURCE="$HERE/src/spotlight.py"
  say "Installing from the checkout $HERE."
  [ "$DRY_RUN" -eq 1 ] && { say "Dry run: would copy it to $TARGET. Nothing was changed."; exit 0; }
else
  case "$API" in
    https://*) PROTO='=https' ;;
    http://127.0.0.1* | http://localhost*) PROTO='=http,https' ;;
    *) die "SPOTLIGHT_API must be an https URL" ;;
  esac
  if command -v curl >/dev/null 2>&1; then
    fetch() { # fetch URL [FILE]
      if [ $# -ge 2 ]; then
        curl -fsSL --proto "$PROTO" --tlsv1.2 -o "$2" "$1"
      else
        curl -fsSL --proto "$PROTO" --tlsv1.2 "$1"
      fi
    }
  elif command -v wget >/dev/null 2>&1; then
    fetch() {
      if [ $# -ge 2 ]; then wget -q -O "$2" "$1"; else wget -q -O - "$1"; fi
    }
  else
    die "curl or wget is needed to download the release"
  fi
  if command -v sha256sum >/dev/null 2>&1; then
    sha256() { sha256sum "$1" | cut -d' ' -f1; }
  elif command -v shasum >/dev/null 2>&1; then
    sha256() { shasum -a 256 "$1" | cut -d' ' -f1; }
  else
    die "sha256sum or shasum is needed to check the download"
  fi

  if [ "$VERSION" = latest ]; then
    RELEASE_URL="$API/repos/$REPO/releases/latest"
  else
    RELEASE_URL="$API/repos/$REPO/releases/tags/v$VERSION"
  fi
  RELEASE=$(fetch "$RELEASE_URL") ||
    die "could not read the release at $RELEASE_URL (does that version exist? is GitHub rate limiting you?)"

  # tag, tarball URL, sha256 GitHub publishes for it (or "-"), SHA256SUMS URL (or "-")
  INFO=$(printf '%s' "$RELEASE" | "$PY" -I -c '
import json, sys
release = json.load(sys.stdin)
tag = release["tag_name"]
name = "spotlight-linux-%s.tar.gz" % tag.lstrip("v")
assets = {a["name"]: a for a in release.get("assets", [])}
tarball = assets.get(name)
if tarball is None:
    sys.exit("release %s has no file named %s" % (tag, name))
digest = (tarball.get("digest") or "").removeprefix("sha256:") or "-"
sums = assets.get("SHA256SUMS", {}).get("browser_download_url", "-")
print(tag, tarball["browser_download_url"], digest, sums, sep="\n")
') || die "could not read the release information"
  TAG=$(printf '%s\n' "$INFO" | sed -n 1p)
  URL=$(printf '%s\n' "$INFO" | sed -n 2p)
  DIGEST=$(printf '%s\n' "$INFO" | sed -n 3p)
  SUMS_URL=$(printf '%s\n' "$INFO" | sed -n 4p)

  ASSET="spotlight-linux-${TAG#v}.tar.gz"
  say "Installing spotlight-linux ${TAG#v}."
  say "  file:   $ASSET"
  say "  from:   $URL"
  say "  to:     $TARGET"
  [ "$DRY_RUN" -eq 1 ] && { say "Dry run: nothing was downloaded or changed."; exit 0; }

  TMP=$(mktemp -d)
  trap 'rm -rf "$TMP"' EXIT
  trap 'exit 1' INT TERM HUP
  say "Downloading..."
  fetch "$URL" "$TMP/$ASSET" || die "the download failed"

  if [ "$DIGEST" = - ] && [ "$SUMS_URL" != - ]; then
    DIGEST=$(fetch "$SUMS_URL" | awk -v want="$ASSET" '$2 == want { print $1; exit }')
  fi
  [ -n "$DIGEST" ] && [ "$DIGEST" != - ] ||
    die "no sha256 is published for $ASSET, so the download cannot be checked"
  [ "$(sha256 "$TMP/$ASSET")" = "$DIGEST" ] ||
    die "the sha256 of the download does not match what GitHub published; nothing was installed"
  say "Checked the sha256."

  tar -xzf "$TMP/$ASSET" -C "$TMP"
  SOURCE="$TMP/spotlight-linux-${TAG#v}/src/spotlight.py"
  [ -f "$SOURCE" ] || die "the release has no src/spotlight.py"
fi

# 3. Install the command ------------------------------------------------
mkdir -p "$PREFIX"
if [ -f "$TARGET" ] && cmp -s "$SOURCE" "$TARGET"; then
  say "spotlight-linux is already installed and up to date ($TARGET)."
elif [ -f "$TARGET" ]; then
  install -m 755 "$SOURCE" "$TARGET"
  say "Updated $TARGET"
else
  install -m 755 "$SOURCE" "$TARGET"
  say "Installed $TARGET"
fi
case ":$PATH:" in
  *":$PREFIX:"*) ;;
  *) say "Note: $PREFIX is not in your PATH (the shortcut uses the full path anyway)." ;;
esac

# 4. Keyboard shortcut --------------------------------------------------
if [ "$SHORTCUT" -eq 0 ]; then
  say "Skipped the shortcut. Bind this command yourself: $PY $TARGET"
  exit 0
fi
if ! command -v gsettings >/dev/null 2>&1 ||
  ! gsettings list-schemas | grep -qx org.cinnamon.desktop.keybindings; then
  say "Not running Cinnamon: bind a key manually to: $PY $TARGET"
  exit 0
fi

KB=org.cinnamon.desktop.keybindings
ONE="$KB.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/spotlight/"
gsettings set "$ONE" name 'Spotlight'
gsettings set "$ONE" command "$PY $TARGET"
gsettings set "$ONE" binding "['<Super>space']"

LIST=$(gsettings get "$KB" custom-list)
case "$LIST" in
  *"'spotlight'"*) ;;
  "@as []" | "[]") gsettings set "$KB" custom-list "['spotlight']" ;;
  *) gsettings set "$KB" custom-list "${LIST%]}, 'spotlight']" ;;
esac

# Super+Space is the default input-source switcher on Cinnamon; free it.
case "$(gsettings get "$KB.wm" switch-input-source)" in
  *"<Super>space"*)
    gsettings set "$KB.wm" switch-input-source "['XF86Keyboard']"
    say "Removed Super+Space from keyboard-layout switching (restore it with uninstall.sh)."
    ;;
esac
say "Shortcut set: Super+Space. Done."
