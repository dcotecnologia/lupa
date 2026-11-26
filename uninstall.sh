#!/bin/sh
# Remove lupa, its Cinnamon shortcut, and restore layout switching.
#
#   curl -fsSL https://raw.githubusercontent.com/dcotecnologia/lupa/main/uninstall.sh | sh
#
# Option: --prefix DIR, if you installed the command somewhere else than ~/.local/bin.

set -eu

PREFIX="${HOME:?HOME is not set}/.local/bin"
if [ "${1:-}" = --prefix ]; then
  [ $# -ge 2 ] || { echo "uninstall.sh: --prefix needs a directory" >&2; exit 1; }
  PREFIX="$2"
fi

rm -f "$PREFIX/lupa"
echo "Removed $PREFIX/lupa"
# the AppImage installed by install.sh lives in the data folder
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/lupa"
if [ -d "$DATA_DIR" ]; then
  rm -f "$DATA_DIR"/Lupa-*-x86_64.AppImage
  rmdir "$DATA_DIR" 2>/dev/null || true
  echo "Removed the AppImage in $DATA_DIR"
fi
# the .deb belongs to the system: apt removes it
if command -v dpkg-query >/dev/null 2>&1 &&
  [ "$(dpkg-query -W -f='${db:Status-Abbrev}' lupa 2>/dev/null)" = "ii " ]; then
  echo "The .deb package is still installed; remove it with: sudo apt remove lupa"
fi
# the project used to be called spotlight-linux
if [ -f "$PREFIX/spotlight" ] && grep -q 'SpotlightLauncher' "$PREFIX/spotlight"; then
  rm -f "$PREFIX/spotlight"
  echo "Removed $PREFIX/spotlight (the old name)"
fi

KB=org.cinnamon.desktop.keybindings
if command -v gsettings >/dev/null 2>&1 &&
  gsettings list-schemas | grep -qx org.cinnamon.desktop.keybindings; then
  LIST=$(gsettings get "$KB" custom-list)
  for NAME in lupa spotlight; do
    case "$LIST" in
      *"'$NAME'"*)
        LIST=$(printf '%s\n' "$LIST" |
          sed -e "s/, '$NAME'//" -e "s/'$NAME', //" -e "s/'$NAME'//")
        [ "$LIST" = "[]" ] && LIST="@as []"
        gsettings set "$KB" custom-list "$LIST"
        gsettings reset-recursively \
          "$KB.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/$NAME/" \
          2>/dev/null || true
        gsettings reset "$KB.wm" switch-input-source
        echo "Removed the shortcut $NAME and restored the default layout switcher."
        ;;
    esac
  done
fi
