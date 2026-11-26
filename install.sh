#!/usr/bin/env bash
# Installs the Spotlight-style launcher for the current user.
#
#   ./install.sh                 install + register Super+Space (Cinnamon only)
#   ./install.sh --no-shortcut   install the command only
#   ./install.sh --prefix DIR    install into DIR instead of ~/.local/bin
set -euo pipefail

PREFIX="${HOME}/.local/bin"
SHORTCUT=1
while [ $# -gt 0 ]; do
  case "$1" in
    --no-shortcut) SHORTCUT=0 ;;
    --prefix) PREFIX="${2:?--prefix needs a directory}"; shift ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${PREFIX}/spotlight"
PY=/usr/bin/python3

# 1. Dependencies -------------------------------------------------------
if ! "$PY" -c "import gi; gi.require_version('Gtk','3.0')" 2>/dev/null; then
  echo "Missing PyGObject/GTK3 for ${PY}. On Debian/Ubuntu/Mint run:" >&2
  echo "  sudo apt install python3-gi gir1.2-gtk-3.0" >&2
  exit 1
fi
command -v plocate >/dev/null 2>&1 ||
  echo "Note: 'plocate' not found; file search is disabled (sudo apt install plocate)."

# 2. Install the command ------------------------------------------------
install -Dm755 "${HERE}/src/spotlight.py" "${TARGET}"
echo "Installed ${TARGET}"
case ":${PATH}:" in
  *":${PREFIX}:"*) ;;
  *) echo "Note: ${PREFIX} is not in your PATH (the shortcut uses the full path anyway)." ;;
esac

# 3. Keyboard shortcut --------------------------------------------------
[ "${SHORTCUT}" -eq 1 ] || { echo "Skipped shortcut. Bind this command yourself: ${PY} ${TARGET}"; exit 0; }

if ! command -v gsettings >/dev/null 2>&1 ||
   ! grep -qx org.cinnamon.desktop.keybindings <<<"$(gsettings list-schemas)"; then
  echo "Not running Cinnamon: bind a key manually to: ${PY} ${TARGET}"
  exit 0
fi

KB=org.cinnamon.desktop.keybindings
ONE="${KB}.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/spotlight/"
gsettings set "${ONE}" name 'Spotlight'
gsettings set "${ONE}" command "${PY} ${TARGET}"
gsettings set "${ONE}" binding "['<Super>space']"

LIST="$(gsettings get ${KB} custom-list)"
if [[ "${LIST}" != *"'spotlight'"* ]]; then
  if [ "${LIST}" = "@as []" ] || [ "${LIST}" = "[]" ]; then
    gsettings set ${KB} custom-list "['spotlight']"
  else
    gsettings set ${KB} custom-list "${LIST%]}, 'spotlight']"
  fi
fi

# Super+Space is the default input-source switcher on Cinnamon; free it.
if gsettings get ${KB}.wm switch-input-source | grep -q '<Super>space'; then
  gsettings set ${KB}.wm switch-input-source "['XF86Keyboard']"
  echo "Removed Super+Space from keyboard-layout switching (restore: ./uninstall.sh)."
fi
echo "Shortcut set: Super+Space. Done."
