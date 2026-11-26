"""Package the launcher as a Debian .deb (architecture all).

The package holds the script, the menu entry and the icons. PyGObject
and GTK come from the system, so they are dependencies and are not
bundled.
"""

import gzip
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

try:  # as a module (the tests) or as a script (tools/ is then the import path)
    from tools import package_info
except ImportError:
    import package_info  # type: ignore[no-redef]

ROOT = package_info.ROOT
DIST = ROOT / "dist"
STAGING = ROOT / "build" / "deb"

DEPENDS = ("python3 (>= 3.12)", "python3-gi", "gir1.2-gtk-3.0")
RECOMMENDS = ("plocate",)


def write(path: Path, content: str, mode: int = 0o644) -> None:
    """Write a text file, creating its folder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)


def copyright_text() -> str:
    """The Debian copyright file, with the MIT text of the project."""
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    return (
        "Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/\n"
        "Upstream-Name: Lupa\n"
        "Upstream-Contact: DCO Tecnologia\n"
        "Source: https://github.com/dcotecnologia/lupa\n\n"
        "Files: *\n"
        "Copyright: 2026 DCO Tecnologia\n"
        "License: MIT\n"
        + "".join(
            f" {line}\n" if line.strip() else " .\n"
            for line in license_text.splitlines()[2:]
        )
    )


def md5sums(root: Path) -> str:
    """The md5sums file: every file of the package but the control ones."""
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink() and "DEBIAN" not in path.parts:
            digest = hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()
            lines.append(f"{digest}  {path.relative_to(root).as_posix()}")
    return "\n".join(lines) + "\n"


def control_text(metadata: dict, size_kib: int) -> str:
    """The DEBIAN/control file."""
    version = package_info.debian_version(metadata["version"])
    maintainer = metadata["authors"][-1]
    return (
        "Package: lupa\n"
        f"Version: {version}\n"
        "Section: utils\n"
        "Priority: optional\n"
        "Architecture: all\n"
        f"Depends: {', '.join(DEPENDS)}\n"
        f"Recommends: {', '.join(RECOMMENDS)}\n"
        f"Installed-Size: {size_kib}\n"
        f"Maintainer: {maintainer['name']} <{maintainer['email']}>\n"
        "Homepage: https://lupa.dcotecnologia.com\n"
        f"Description: {metadata['description']}\n"
        " Lupa opens a search box with a shortcut: type a few letters to start an\n"
        " application, find a file in your home folder, or do a quick calculation.\n"
        " Bind a key to the lupa command to open it.\n"
    )


def build(output_dir: Path = DIST, staging: Path = STAGING) -> Path:
    """Build the .deb in output_dir and return its path."""
    metadata = package_info.project_metadata()
    version = metadata["version"]
    package = staging / f"lupa_{version}_all"
    if staging.exists():
        shutil.rmtree(staging)

    binary = package / "usr" / "bin" / "lupa"
    binary.parent.mkdir(parents=True)
    shutil.copyfile(package_info.SCRIPT, binary)
    write(package / "usr/share/applications/lupa.desktop", package_info.DESKTOP_ENTRY)
    write(package / "usr/share/doc/lupa/copyright", copyright_text())
    changelog = package / "usr/share/doc/lupa/changelog.gz"
    # the time is fixed, so the same text always gives the same bytes
    changelog.write_bytes(gzip.compress((ROOT / "CHANGELOG.md").read_bytes(), mtime=0))
    package_info.render_icons(package / "usr" / "share")

    # Debian policy: directories 755, executables 755, everything else 644
    for path in [package, *package.rglob("*")]:
        if path.is_dir() or path == binary:
            path.chmod(0o755)
        else:
            path.chmod(0o644)

    size_kib = sum(p.stat().st_size for p in package.rglob("*") if p.is_file()) // 1024
    write(package / "DEBIAN" / "control", control_text(metadata, size_kib))
    write(package / "DEBIAN" / "md5sums", md5sums(package))
    (package / "DEBIAN").chmod(0o755)

    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"lupa_{version}_all.deb"
    subprocess.run(
        [
            "dpkg-deb",
            "--root-owner-group",
            "-Zxz",
            "--build",
            str(package),
            str(output),
        ],
        check=True,
    )
    return output


def main() -> int:
    if sys.platform != "linux" or not shutil.which("dpkg-deb"):
        raise SystemExit("Building a .deb needs Linux with dpkg-deb installed")
    output = build()
    print(f"Created {output} ({output.stat().st_size / 1024:.0f} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
