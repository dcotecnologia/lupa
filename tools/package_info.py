"""What the .deb and the AppImage have in common (needs Pillow for the
icons)."""

import re
import subprocess
import tomllib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "lupa.py"
ICON = ROOT / "docs" / "assets" / "icon.png"
ICON_SIZES = (48, 64, 128, 256, 512)

DESKTOP_ENTRY = """[Desktop Entry]
Type=Application
Name=Lupa
GenericName=Launcher
Comment=Open apps, find files and do quick math from one search box
Exec=lupa
Icon=lupa
Terminal=false
Categories=Utility;
Keywords=launcher;search;calculator;apps;files;
"""


def project_metadata() -> dict:
    """The [project] table of pyproject.toml."""
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]


def debian_version(version: str) -> str:
    """The version as Debian orders it.

    A release candidate is before its release: 1.3.0~rc1 comes before 1.3.0, while
    1.3.0rc1 would come after it.
    """
    return re.sub(r"(\d)(a|b|rc)(\d+)$", r"\1~\2\3", version)


def script_text() -> str:
    """The launcher with the hash of the current commit written in as its
    build."""
    text = SCRIPT.read_text(encoding="utf-8")
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    commit = result.stdout.strip()
    if result.returncode != 0 or not commit:
        return text
    return text.replace('BUILD = "$Format:%h$"', f'BUILD = "{commit}"', 1)


def render_icons(share: Path) -> None:
    """Write the icon in every size under share/icons/hicolor/<size>/apps."""
    source = Image.open(ICON).convert("RGBA")
    for size in ICON_SIZES:
        target = share / "icons" / "hicolor" / f"{size}x{size}" / "apps" / "lupa.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        source.resize((size, size), Image.Resampling.LANCZOS).save(target)
