#!/bin/sh
# Remove spotlight-linux, its Cinnamon shortcut, and restore layout switching.
#
#   curl -fsSL https://raw.githubusercontent.com/dcotecnologia/spotlight-linux/main/uninstall.sh | sh
#
# Option: --prefix DIR, if you installed the command somewhere else than ~/.local/bin.

set -eu

PREFIX="${HOME:?HOME is not set}/.local/bin"
if [ "${1:-}" = --prefix ]; then
  [ $# -ge 2 ] || { echo "uninstall.sh: --prefix needs a directory" >&2; exit 1; }
  PREFIX="$2"
fi

rm -f "$PREFIX/spotlight"
echo "Removed $PREFIX/spotlight"

KB=org.cinnamon.desktop.keybindings
if command -v gsettings >/dev/null 2>&1 &&
  gsettings list-schemas | grep -qx org.cinnamon.desktop.keybindings; then
  LIST=$(gsettings get "$KB" custom-list)
  case "$LIST" in
    *"'spotlight'"*)
      NEW=$(printf '%s\n' "$LIST" |
        sed -e "s/, 'spotlight'//" -e "s/'spotlight', //" -e "s/'spotlight'//")
      [ "$NEW" = "[]" ] && NEW="@as []"
      gsettings set "$KB" custom-list "$NEW"
      gsettings reset-recursively \
        "$KB.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/spotlight/" \
        2>/dev/null || true
      gsettings reset "$KB.wm" switch-input-source
      echo "Removed the shortcut and restored the default layout switcher."
      ;;
  esac
fi
