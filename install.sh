#!/bin/sh
# Install or update Lupa for the current user.
#
#   curl -fsSL https://raw.githubusercontent.com/dcotecnologia/lupa/main/install.sh | sh
#
# Run from a checkout of the repository it installs that checkout; run anywhere else
# (or piped, as above) it picks the latest release, checks the download against the
# sha256 that GitHub publishes for it, and installs it, in this order of preference:
#
#   1. the .deb, where apt exists and you can use sudo (Debian, Ubuntu, Mint...)
#   2. the AppImage, where FUSE 2 and PyGObject are there
#   3. the script of the release, copied to ~/.local/bin
#
# Run it again to update. On Cinnamon it also binds Super+Space.
#
# Options:
#   --version X     install release X (for example 0.4.0) instead of the latest
#   --method M      deb, appimage or script; the default is the first that fits
#   --prefix DIR    install the command into DIR instead of ~/.local/bin
#   --no-shortcut   install the command only, do not touch any keyboard shortcut
#   --dry-run       show what would be done and change nothing
#   -h, --help      show this help
#
# For tests and mirrors: LUPA_REPO (owner/name) and LUPA_API (the API URL, https
# only except for localhost).

set -eu

REPO="${LUPA_REPO:-dcotecnologia/lupa}"
API="${LUPA_API:-https://api.github.com}"
PY=/usr/bin/python3
VERSION=latest
METHOD=auto
PREFIX="${HOME:?HOME is not set}/.local/bin"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/lupa"
SHORTCUT=1
DRY_RUN=0

say() { printf '%s\n' "$*"; }
die() {
  printf 'install.sh: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'USAGE'
Usage: install.sh [options]

Install or update Lupa from a checkout or from its GitHub release: the .deb where apt
and sudo exist, else the AppImage, else the script.

Options:
  --version X     install release X (for example 0.4.0) instead of the latest
  --method M      deb, appimage or script; the default is the first that fits
  --prefix DIR    install the command into DIR instead of ~/.local/bin
  --no-shortcut   install the command only, do not touch any keyboard shortcut
  --dry-run       show what would be done and change nothing
  -h, --help      show this help
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --version) [ $# -ge 2 ] || die "--version needs a value"; VERSION="${2#v}"; shift 2 ;;
    --method) [ $# -ge 2 ] || die "--method needs deb, appimage or script"; METHOD="$2"; shift 2 ;;
    --prefix) [ $# -ge 2 ] || die "--prefix needs a directory"; PREFIX="$2"; shift 2 ;;
    --no-shortcut) SHORTCUT=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h | --help) usage; exit 0 ;;
    *) die "unknown option: $1 (try --help)" ;;
  esac
done
case "$METHOD" in auto | deb | appimage | script) ;; *) die "--method is deb, appimage or script" ;; esac

[ "$(uname -s)" = Linux ] || die "Lupa runs on Linux only"
TARGET="$PREFIX/lupa"

has_gtk() { [ -x "$PY" ] && "$PY" -c "import gi; gi.require_version('Gtk', '3.0')" 2>/dev/null; }
have_privileges() { [ "$(id -u)" -eq 0 ] || command -v sudo >/dev/null 2>&1; }
have_apt() { command -v dpkg >/dev/null 2>&1 && command -v apt-get >/dev/null 2>&1 && have_privileges; }
have_fuse() {
  # an AppImage needs libfuse 2 to start without being unpacked
  case "$(uname -m)" in x86_64 | amd64) ;; *) return 1 ;; esac
  { command -v ldconfig >/dev/null 2>&1 && ldconfig -p 2>/dev/null | grep -q 'libfuse\.so\.2'; } ||
    [ -e /usr/lib/x86_64-linux-gnu/libfuse.so.2 ] || [ -e /lib/x86_64-linux-gnu/libfuse.so.2 ]
}
need_gtk() {
  has_gtk || die "PyGObject/GTK3 is missing for $PY; run: sudo apt install python3-gi gir1.2-gtk-3.0"
}

# 1. Where the files come from -----------------------------------------
# a checkout when this script sits next to src/lupa.py, else the latest release
HERE=$(CDPATH='' cd -- "$(dirname -- "$0")" 2>/dev/null && pwd) || HERE=
SOURCE=
CMD=
if [ -n "$HERE" ] && [ -f "$HERE/src/lupa.py" ] && [ "$VERSION" = latest ] &&
  { [ "$METHOD" = auto ] || [ "$METHOD" = script ]; }; then
  METHOD=script
  SOURCE="$HERE/src/lupa.py"
  say "Installing from the checkout $HERE."
  if [ "$DRY_RUN" -eq 1 ]; then
    say "Dry run: would copy it to $TARGET. Nothing was changed."
    exit 0
  fi
  need_gtk
else
  case "$API" in
    https://*) PROTO='=https' ;;
    http://127.0.0.1* | http://localhost*) PROTO='=http,https' ;;
    *) die "LUPA_API must be an https URL" ;;
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

  # The tag, then the URL and the sha256 GitHub publishes for the script (tarball), the
  # .deb and the AppImage ("-" when the release has none), and the SHA256SUMS URL.
  INFO=$(printf '%s' "$RELEASE" | "$PY" -I -c '
import json, sys
release = json.load(sys.stdin)
tag = release["tag_name"]
version = tag.lstrip("v")
assets = {a["name"]: a for a in release.get("assets", [])}
print(tag)
for name in ("lupa-%s.tar.gz" % version, "lupa_%s_all.deb" % version,
             "Lupa-%s-x86_64.AppImage" % version):
    asset = assets.get(name)
    if asset is None:
        print("-"); print("-")
    else:
        print(asset["browser_download_url"])
        print((asset.get("digest") or "").removeprefix("sha256:") or "-")
print(assets.get("SHA256SUMS", {}).get("browser_download_url", "-"))
') || die "could not read the release information"
  TAG=$(printf '%s\n' "$INFO" | sed -n 1p)
  TARGET_VERSION="${TAG#v}"
  SCRIPT_URL=$(printf '%s\n' "$INFO" | sed -n 2p)
  SCRIPT_DIGEST=$(printf '%s\n' "$INFO" | sed -n 3p)
  DEB_URL=$(printf '%s\n' "$INFO" | sed -n 4p)
  DEB_DIGEST=$(printf '%s\n' "$INFO" | sed -n 5p)
  APP_URL=$(printf '%s\n' "$INFO" | sed -n 6p)
  APP_DIGEST=$(printf '%s\n' "$INFO" | sed -n 7p)
  SUMS_URL=$(printf '%s\n' "$INFO" | sed -n 8p)
  SCRIPT_FILE="lupa-$TARGET_VERSION.tar.gz"
  DEB_FILE="lupa_${TARGET_VERSION}_all.deb"
  APP_FILE="Lupa-$TARGET_VERSION-x86_64.AppImage"

  # 2. Which method: the .deb, then the AppImage, then the script ----------
  if [ "$METHOD" = auto ]; then
    if [ "$DEB_URL" != - ] && have_apt; then
      METHOD=deb
    elif [ "$APP_URL" != - ] && have_fuse && has_gtk; then
      METHOD=appimage
    elif [ "$SCRIPT_URL" != - ]; then
      METHOD=script
    else
      die "release $TAG has no file this system can use"
    fi
  fi
  case "$METHOD" in
    deb)
      [ "$DEB_URL" != - ] || die "release $TAG has no file named $DEB_FILE"
      have_apt || die "installing the .deb needs dpkg, apt and root or sudo; try --method appimage or script"
      FILE=$DEB_FILE; URL=$DEB_URL; DIGEST=$DEB_DIGEST
      WHERE="the system, with apt (it may ask for your password)"
      CMD=/usr/bin/lupa
      ;;
    appimage)
      [ "$APP_URL" != - ] || die "release $TAG has no file named $APP_FILE"
      FILE=$APP_FILE; URL=$APP_URL; DIGEST=$APP_DIGEST
      WHERE="$DATA_DIR, linked as $TARGET"
      CMD="$TARGET"
      ;;
    script)
      [ "$SCRIPT_URL" != - ] || die "release $TAG has no file named $SCRIPT_FILE"
      FILE=$SCRIPT_FILE; URL=$SCRIPT_URL; DIGEST=$SCRIPT_DIGEST
      WHERE="$TARGET"
      ;;
  esac

  # What is installed now, to say "up to date" instead of doing it again.
  CURRENT=
  case "$METHOD" in
    deb)
      status=$(dpkg-query -W -f='${db:Status-Abbrev}|${Version}' lupa 2>/dev/null || true)
      case "$status" in ii*\|*) CURRENT="${status#*|}" ;; esac
      ;;
    appimage) [ -f "$DATA_DIR/$APP_FILE" ] && CURRENT="$TARGET_VERSION" ;;
  esac
  if [ -n "$CURRENT" ] && [ "$CURRENT" = "$TARGET_VERSION" ] && [ "$DRY_RUN" -eq 0 ]; then
    say "Lupa $CURRENT is already installed and up to date ($METHOD)."
    UP_TO_DATE=1
  else
    UP_TO_DATE=0
  fi

  say "Installing Lupa $TARGET_VERSION ($METHOD)."
  say "  file:   $FILE"
  say "  from:   $URL"
  say "  to:     $WHERE"
  if [ "$DRY_RUN" -eq 1 ]; then
    say "Dry run: nothing was downloaded or changed."
    exit 0
  fi

  if [ "$UP_TO_DATE" -eq 0 ]; then
    [ "$METHOD" = deb ] || need_gtk
    TMP=$(mktemp -d)
    trap 'rm -rf "$TMP"' EXIT
    trap 'exit 1' INT TERM HUP
    say "Downloading..."
    fetch "$URL" "$TMP/$FILE" || die "the download failed"

    if [ "$DIGEST" = - ] && [ "$SUMS_URL" != - ]; then
      DIGEST=$(fetch "$SUMS_URL" | awk -v want="$FILE" '$2 == want { print $1; exit }')
    fi
    [ -n "$DIGEST" ] && [ "$DIGEST" != - ] ||
      die "no sha256 is published for $FILE, so the download cannot be checked"
    [ "$(sha256 "$TMP/$FILE")" = "$DIGEST" ] ||
      die "the sha256 of the download does not match what GitHub published; nothing was installed"
    say "Checked the sha256."

    case "$METHOD" in
      deb)
        # mktemp makes the folder private; apt downloads as the _apt user, which must be
        # able to reach the file or it falls back to root with a warning.
        chmod 755 "$TMP"
        chmod 644 "$TMP/$FILE"
        if [ "$(id -u)" -eq 0 ]; then
          apt-get install -y "$TMP/$FILE"
        else
          sudo apt-get install -y "$TMP/$FILE"
        fi
        say "Installed the package lupa $TARGET_VERSION."
        ;;
      appimage)
        mkdir -p "$DATA_DIR" "$PREFIX"
        install -m 755 "$TMP/$FILE" "$DATA_DIR/$FILE"
        ln -sf "$DATA_DIR/$FILE" "$TARGET"
        for old in "$DATA_DIR"/Lupa-*-x86_64.AppImage; do
          if [ -e "$old" ] && [ "$old" != "$DATA_DIR/$FILE" ]; then rm -f "$old"; fi
        done
        say "Installed $DATA_DIR/$FILE, linked as $TARGET"
        ;;
      script)
        tar -xzf "$TMP/$FILE" -C "$TMP"
        SOURCE="$TMP/lupa-$TARGET_VERSION/src/lupa.py"
        [ -f "$SOURCE" ] || die "the release has no src/lupa.py"
        ;;
    esac
  fi
fi

# 3. Install the script (a checkout, or the script of a release) ---------
if [ "$METHOD" = script ]; then
  CMD="$PY $TARGET"
  mkdir -p "$PREFIX"
  if [ -f "$TARGET" ] && ! [ -L "$TARGET" ] && cmp -s "$SOURCE" "$TARGET"; then
    say "Lupa is already installed and up to date ($TARGET)."
  elif [ -e "$TARGET" ]; then
    rm -f "$TARGET"
    install -m 755 "$SOURCE" "$TARGET"
    say "Updated $TARGET"
  else
    install -m 755 "$SOURCE" "$TARGET"
    say "Installed $TARGET"
  fi
fi

# The package puts lupa in /usr/bin: a script left in the home folder by an earlier
# install would come first in the PATH and hide it, so remove it if it is ours.
if [ "$METHOD" = deb ] && [ -f "$TARGET" ] && ! [ -L "$TARGET" ] &&
  grep -q 'com.dcotecnologia.Lupa' "$TARGET"; then
  rm -f "$TARGET"
  say "Removed the copy in $PREFIX, which the package replaces."
fi

# The project used to be called spotlight-linux: drop the command it installed under that name.
OLD_TARGET="$PREFIX/spotlight"
if [ -f "$OLD_TARGET" ] && grep -q 'SpotlightLauncher' "$OLD_TARGET"; then
  rm -f "$OLD_TARGET"
  say "Removed the old command $OLD_TARGET (the project is now called Lupa)."
fi
case ":$PATH:" in
  *":$PREFIX:"*) ;;
  *) [ "$METHOD" = deb ] || say "Note: $PREFIX is not in your PATH (the shortcut uses the full path anyway)." ;;
esac

# 4. Keyboard shortcut --------------------------------------------------
if [ "$SHORTCUT" -eq 0 ]; then
  say "Skipped the shortcut. Bind this command yourself: $CMD"
  exit 0
fi
if ! command -v gsettings >/dev/null 2>&1 ||
  ! gsettings list-schemas | grep -qx org.cinnamon.desktop.keybindings; then
  say "Not running Cinnamon: bind a key manually to: $CMD"
  exit 0
fi

KB=org.cinnamon.desktop.keybindings
KEYS="$KB.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings"

# The shortcut of the old name is bound to the same keys: remove it, if it is the one we made.
case "$(gsettings get "$KB" custom-list)" in
  *"'spotlight'"*)
    case "$(gsettings get "$KEYS/spotlight/" command)" in
      *"/spotlight'"* | *"/spotlight\""*)
        OLD_LIST=$(gsettings get "$KB" custom-list |
          sed -e "s/, 'spotlight'//" -e "s/'spotlight', //" -e "s/'spotlight'//")
        [ "$OLD_LIST" = "[]" ] && OLD_LIST="@as []"
        gsettings set "$KB" custom-list "$OLD_LIST"
        gsettings reset-recursively "$KEYS/spotlight/" 2>/dev/null || true
        say "Removed the shortcut of the old name."
        ;;
    esac
    ;;
esac

ONE="$KEYS/lupa/"
gsettings set "$ONE" name 'Lupa'
gsettings set "$ONE" command "$CMD"
gsettings set "$ONE" binding "['<Super>space']"

LIST=$(gsettings get "$KB" custom-list)
case "$LIST" in
  *"'lupa'"*) ;;
  "@as []" | "[]") gsettings set "$KB" custom-list "['lupa']" ;;
  *) gsettings set "$KB" custom-list "${LIST%]}, 'lupa']" ;;
esac

# Super+Space is the default input-source switcher on Cinnamon; free it.
case "$(gsettings get "$KB.wm" switch-input-source)" in
  *"<Super>space"*)
    gsettings set "$KB.wm" switch-input-source "['XF86Keyboard']"
    say "Removed Super+Space from keyboard-layout switching (restore it with uninstall.sh)."
    ;;
esac
say "Shortcut set: Super+Space. Done."
