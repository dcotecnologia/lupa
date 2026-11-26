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
