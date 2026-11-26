#!/usr/bin/env bash
# Removes the launcher, its Cinnamon shortcut, and restores layout switching.
set -euo pipefail

PREFIX="${HOME}/.local/bin"
[ "${1:-}" = "--prefix" ] && PREFIX="${2:?--prefix needs a directory}"
rm -f "${PREFIX}/spotlight"
echo "Removed ${PREFIX}/spotlight"

KB=org.cinnamon.desktop.keybindings
if command -v gsettings >/dev/null 2>&1 &&
   grep -qx org.cinnamon.desktop.keybindings <<<"$(gsettings list-schemas)"; then
  LIST="$(gsettings get ${KB} custom-list)"
  if [[ "${LIST}" == *"'spotlight'"* ]]; then
    NEW="$(sed -E "s/, 'spotlight'//; s/'spotlight', //; s/'spotlight'//" <<<"${LIST}")"
    [ "${NEW}" = "[]" ] && NEW="@as []"
    gsettings set ${KB} custom-list "${NEW}"
    gsettings reset-recursively "${KB}.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/spotlight/" 2>/dev/null || true
    gsettings reset ${KB}.wm switch-input-source
    echo "Removed the shortcut and restored the default layout switcher."
  fi
fi
