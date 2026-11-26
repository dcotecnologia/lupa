"""Package the launcher as a single-file AppImage.

It is a thin AppImage: the script, the menu entry and the icon. Python,
PyGObject and GTK 3 come from the host (see AppRun), as they do for the
.deb.
"""

import hashlib
import os
import shutil
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path

try:  # as a module (the tests) or as a script (tools/ is then the import path)
    from tools import package_info
except ImportError:
    import package_info  # type: ignore[no-redef]

ROOT = package_info.ROOT
DIST = ROOT / "dist"
APPDIR = ROOT / "build" / "Lupa.AppDir"
TOOL_DIR = ROOT / "vendor" / "appimagetool"

# Pinned release; GitHub publishes the SHA-256 of every asset.
TOOL_VERSION = "1.9.1"
TOOL_SHA256 = "ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0"
TOOL_URL = (
    "https://github.com/AppImage/appimagetool/releases/download/"
    f"{TOOL_VERSION}/appimagetool-x86_64.AppImage"
)

# Written into the AppImage, so AppImageUpdate fetches only what changed from the
# GitHub release; appimagetool also writes the .zsync file it reads (needs zsyncmake).
UPDATE_INFORMATION = (
    "gh-releases-zsync|dcotecnologia|lupa|latest|Lupa-*-x86_64.AppImage.zsync"
)

APP_RUN = """#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
PY=/usr/bin/python3
if ! "$PY" -c "import gi; gi.require_version('Gtk', '3.0')" 2>/dev/null; then
  message="Lupa needs PyGObject and GTK 3: sudo apt install python3-gi gir1.2-gtk-3.0"
  echo "$message" >&2
  command -v notify-send >/dev/null 2>&1 && notify-send "Lupa" "$message"
  exit 1
fi
exec "$PY" "$HERE/usr/bin/lupa" "$@"
"""


def fetch_appimagetool() -> Path:
    """Download the pinned appimagetool once and check its sha256."""
    tool = TOOL_DIR / f"appimagetool-{TOOL_VERSION}-x86_64.AppImage"
    if not tool.is_file():
        print(f"Downloading appimagetool {TOOL_VERSION}...")
        TOOL_DIR.mkdir(parents=True, exist_ok=True)
        partial = tool.with_suffix(".part")
        with urllib.request.urlopen(TOOL_URL, timeout=60) as response:
            partial.write_bytes(response.read())
        digest = hashlib.sha256(partial.read_bytes()).hexdigest()
        if digest != TOOL_SHA256:
            partial.unlink()
            raise SystemExit(f"appimagetool checksum mismatch: {digest}")
        partial.replace(tool)
    tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    return tool


def build_appdir(appdir: Path = APPDIR) -> Path:
    """Lay out the AppDir and return it."""
    if appdir.exists():
        shutil.rmtree(appdir)
    binary = appdir / "usr" / "bin" / "lupa"
    binary.parent.mkdir(parents=True)
    binary.write_text(package_info.script_text(), encoding="utf-8")
    binary.chmod(0o755)
    package_info.render_icons(appdir / "usr" / "share")
    icon = appdir / "usr/share/icons/hicolor/512x512/apps/lupa.png"
    shutil.copy(icon, appdir / "lupa.png")
    shutil.copy(icon, appdir / ".DirIcon")
    (appdir / "lupa.desktop").write_text(package_info.DESKTOP_ENTRY, encoding="utf-8")
    app_run = appdir / "AppRun"
    app_run.write_text(APP_RUN, encoding="utf-8")
    app_run.chmod(0o755)
    return appdir


def main() -> int:
    if sys.platform != "linux":
        raise SystemExit("AppImage can only be built on Linux")
    tool = fetch_appimagetool()
    appdir = build_appdir()
    version = package_info.project_metadata()["version"]
    output = DIST / f"Lupa-{version}-x86_64.AppImage"
    output.parent.mkdir(parents=True, exist_ok=True)
    # extract-and-run lets appimagetool work on machines without FUSE
    environment = {**os.environ, "ARCH": "x86_64", "APPIMAGE_EXTRACT_AND_RUN": "1"}
    command = [str(tool)]
    if shutil.which("zsyncmake"):
        command += ["--updateinformation", UPDATE_INFORMATION]
    else:
        print("zsyncmake not found: the AppImage is built without update information")
    subprocess.run([*command, str(appdir), str(output)], check=True, env=environment)
    print(f"Created {output} ({output.stat().st_size / 1024:.0f} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
