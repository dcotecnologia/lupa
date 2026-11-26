"""Tests of the .deb and AppImage builders (the appimagetool itself is not
run)."""

import shutil
import subprocess

import pytest

from tools import build_appimage, build_deb, package_info

pytestmark = pytest.mark.unit

needs_dpkg = pytest.mark.skipif(
    shutil.which("dpkg-deb") is None, reason="dpkg-deb is not installed"
)


@pytest.mark.parametrize(
    ("version", "expected"),
    [("1.3.0", "1.3.0"), ("1.3.0rc1", "1.3.0~rc1"), ("2.0.0a2", "2.0.0~a2")],
)
def test_debian_version_orders_prereleases_first(version, expected):
    assert package_info.debian_version(version) == expected


def test_control_names_the_package_and_its_dependencies():
    metadata = {
        "version": "1.2.3",
        "description": "A launcher",
        "authors": [
            {"name": "Someone", "email": "someone@example.com"},
            {"name": "The Team", "email": "team@example.com"},
        ],
    }

    control = build_deb.control_text(metadata, 12)

    assert "Package: lupa\n" in control
    assert "Version: 1.2.3\n" in control
    assert "Architecture: all\n" in control
    assert "Depends: python3 (>= 3.12), python3-gi, gir1.2-gtk-3.0\n" in control
    assert "Recommends: plocate\n" in control
    assert "Maintainer: The Team <team@example.com>\n" in control
    assert "Description: A launcher\n" in control


def test_copyright_carries_the_license_of_the_project():
    text = build_deb.copyright_text()

    assert "Upstream-Name: Lupa" in text
    assert "License: MIT" in text
    assert "Permission is hereby granted" in text


@needs_dpkg
def test_deb_has_the_files_and_the_metadata(tmp_path):
    deb = build_deb.build(tmp_path / "dist", tmp_path / "staging")

    version = package_info.project_metadata()["version"]
    assert deb.name == f"lupa_{version}_all.deb"
    fields = subprocess.run(
        ["dpkg-deb", "-f", str(deb)], capture_output=True, text=True, check=True
    ).stdout
    assert "Package: lupa" in fields
    assert f"Version: {version}" in fields
    listing = subprocess.run(
        ["dpkg-deb", "-c", str(deb)], capture_output=True, text=True, check=True
    ).stdout
    for path in (
        "./usr/bin/lupa",
        "./usr/share/applications/lupa.desktop",
        "./usr/share/doc/lupa/copyright",
        "./usr/share/doc/lupa/changelog.gz",
        "./usr/share/icons/hicolor/48x48/apps/lupa.png",
        "./usr/share/icons/hicolor/512x512/apps/lupa.png",
    ):
        assert path in listing
    binary = next(
        line for line in listing.splitlines() if line.endswith("usr/bin/lupa")
    )
    assert binary.startswith("-rwxr-xr-x root/root")


@needs_dpkg
def test_deb_is_built_again_from_scratch(tmp_path):
    first = build_deb.build(tmp_path / "dist", tmp_path / "staging")
    second = build_deb.build(tmp_path / "dist", tmp_path / "staging")

    assert first == second
    assert second.is_file()


def test_md5sums_skips_the_control_files(tmp_path):
    (tmp_path / "usr").mkdir()
    (tmp_path / "usr" / "file").write_text("x")
    (tmp_path / "DEBIAN").mkdir()
    (tmp_path / "DEBIAN" / "control").write_text("y")

    lines = build_deb.md5sums(tmp_path).splitlines()

    assert len(lines) == 1
    assert lines[0].endswith("  usr/file")


def test_appdir_has_the_app_run_the_menu_entry_and_the_icons(tmp_path):
    appdir = build_appimage.build_appdir(tmp_path / "Lupa.AppDir")

    assert (appdir / "usr" / "bin" / "lupa").read_bytes() == (
        package_info.SCRIPT.read_bytes()
    )
    assert (appdir / "lupa.png").is_file()
    assert (appdir / ".DirIcon").is_file()
    assert "Exec=lupa" in (appdir / "lupa.desktop").read_text()
    app_run = appdir / "AppRun"
    assert app_run.stat().st_mode & 0o111
    assert '"$HERE/usr/bin/lupa"' in app_run.read_text()
    assert (appdir / "usr/share/icons/hicolor/256x256/apps/lupa.png").is_file()


def test_appdir_replaces_an_old_one(tmp_path):
    appdir = tmp_path / "Lupa.AppDir"
    appdir.mkdir()
    (appdir / "stale").write_text("old")

    build_appimage.build_appdir(appdir)

    assert not (appdir / "stale").exists()


def test_appimage_is_named_after_the_version_and_updates_from_github():
    assert "Lupa-*-x86_64.AppImage.zsync" in build_appimage.UPDATE_INFORMATION
    assert build_appimage.TOOL_URL.endswith("/appimagetool-x86_64.AppImage")
