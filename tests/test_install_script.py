"""Tests of install.sh against a fake GitHub API served on localhost."""

import hashlib
import http.server
import io
import json
import os
import shutil
import subprocess
import tarfile
import threading
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "install.sh"


def make_tarball(version, body):
    """A release tarball like `git archive --prefix` makes."""
    buffer = io.BytesIO()
    data = body.encode()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        info = tarfile.TarInfo(f"lupa-{version}/src/lupa.py")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class FakeGitHub:
    """Serves /repos/<repo>/releases/...

    and the files of the releases.
    """

    def __init__(self, releases):
        self.releases = releases  # version -> {"body", "digest", "sums", "tamper"}
        self.requests = []
        self.tarballs = {}  # built once: gzip stores a timestamp, so a rebuild differs
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                outer.requests.append(self.path)
                status, payload = outer.route(self.path)
                self.send_response(status)
                self.end_headers()
                self.wfile.write(payload)

        self.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tarball(self, version):
        if version not in self.tarballs:
            body = self.releases[version]["body"]
            self.tarballs[version] = make_tarball(version, body)
        return self.tarballs[version]

    def route(self, path):
        base = "/repos/example/lupa/releases/"
        if path.startswith(base):
            tag = path.removeprefix(base)
            version = (
                max(self.releases) if tag == "latest" else tag.removeprefix("tags/v")
            )
            if version not in self.releases:
                return 404, b"{}"
            return 200, json.dumps(self.release(version)).encode()
        name = path.removeprefix("/files/")
        for version in self.releases:
            tarball = self.tarball(version)
            if name == f"lupa_{version}_all.deb":
                return 200, b"deb of " + version.encode()
            if name == f"Lupa-{version}-x86_64.AppImage":
                return 200, b"#!/bin/sh\n# AppImage of " + version.encode() + b"\n"
            if name == f"lupa-{version}.tar.gz":
                return 200, tarball
            if name == f"SHA256SUMS-{version}":
                digest = hashlib.sha256(tarball).hexdigest()
                line = f"{digest}  lupa-{version}.tar.gz\n"
                return 200, line.encode()
        return 404, b"{}"

    def release(self, version):
        data = self.releases[version]
        tarball = self.tarball(version)
        name = f"lupa-{version}.tar.gz"
        asset = {"name": name, "browser_download_url": f"{self.url}/files/{name}"}
        if data.get("digest", True):
            asset["digest"] = "sha256:" + hashlib.sha256(tarball).hexdigest()
        if data.get("tamper"):
            asset["digest"] = "sha256:" + "0" * 64
        assets = [asset]
        if data.get("packages"):
            for name, content in (
                (f"lupa_{version}_all.deb", b"deb of " + version.encode()),
                (
                    f"Lupa-{version}-x86_64.AppImage",
                    b"#!/bin/sh\n# AppImage of " + version.encode() + b"\n",
                ),
            ):
                assets.append(
                    {
                        "name": name,
                        "browser_download_url": f"{self.url}/files/{name}",
                        "digest": "sha256:" + hashlib.sha256(content).hexdigest(),
                    }
                )
        if data.get("sums"):
            assets.append(
                {
                    "name": "SHA256SUMS",
                    "browser_download_url": f"{self.url}/files/SHA256SUMS-{version}",
                }
            )
        return {"tag_name": f"v{version}", "assets": assets}

    def close(self):
        self.server.shutdown()


@pytest.fixture
def github():
    servers = []

    def start(releases):
        server = FakeGitHub(releases)
        servers.append(server)
        return server

    yield start
    for server in servers:
        server.close()


def run_install(tmp_path, api, *args, script=INSTALL):
    prefix = tmp_path / "bin"
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "LUPA_REPO": "example/lupa",
        "LUPA_API": api,
        "XDG_DATA_HOME": str(tmp_path / "data"),
    }
    result = subprocess.run(
        ["sh", str(script), "--no-shortcut", "--prefix", str(prefix), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return result, prefix / "lupa"


@pytest.fixture
def lone_script(tmp_path):
    """install.sh alone in a folder, as when it is piped from the web."""
    folder = tmp_path / "lone"
    folder.mkdir()
    script = folder / "install.sh"
    script.write_bytes(INSTALL.read_bytes())
    return script


def test_installs_the_latest_release(tmp_path, github, lone_script):
    server = github({"0.1.0": {"body": "old"}, "0.2.0": {"body": "new"}})

    result, target = run_install(tmp_path, server.url, script=lone_script)

    assert result.returncode == 0, result.stderr
    assert target.read_text() == "new"
    assert os.access(target, os.X_OK)
    assert "Checked the sha256" in result.stdout
    assert "Installed" in result.stdout


def test_running_it_again_updates(tmp_path, github, lone_script):
    server = github({"0.1.0": {"body": "old"}})
    run_install(tmp_path, server.url, script=lone_script)
    server.releases["0.2.0"] = {"body": "new"}

    same, _ = run_install(
        tmp_path, server.url, "--version", "0.1.0", script=lone_script
    )
    updated, target = run_install(tmp_path, server.url, script=lone_script)
    again, _ = run_install(tmp_path, server.url, script=lone_script)

    assert "already installed and up to date" in same.stdout
    assert "Updated" in updated.stdout
    assert target.read_text() == "new"
    assert "already installed and up to date" in again.stdout


def test_installs_a_chosen_version(tmp_path, github, lone_script):
    server = github({"0.1.0": {"body": "old"}, "0.2.0": {"body": "new"}})

    result, target = run_install(
        tmp_path, server.url, "--version", "v0.1.0", script=lone_script
    )

    assert result.returncode == 0, result.stderr
    assert target.read_text() == "old"


def test_uses_the_sums_file_when_github_gives_no_digest(tmp_path, github, lone_script):
    server = github({"0.1.0": {"body": "x", "digest": False, "sums": True}})

    result, target = run_install(tmp_path, server.url, script=lone_script)

    assert result.returncode == 0, result.stderr
    assert target.read_text() == "x"


def test_refuses_a_download_that_does_not_match(tmp_path, github, lone_script):
    server = github({"0.1.0": {"body": "x", "tamper": True}})

    result, target = run_install(tmp_path, server.url, script=lone_script)

    assert result.returncode != 0
    assert "does not match" in result.stderr
    assert not target.exists()


def test_refuses_a_download_nobody_can_check(tmp_path, github, lone_script):
    server = github({"0.1.0": {"body": "x", "digest": False}})

    result, target = run_install(tmp_path, server.url, script=lone_script)

    assert result.returncode != 0
    assert "cannot be checked" in result.stderr
    assert not target.exists()


def test_unknown_version_fails(tmp_path, github, lone_script):
    server = github({"0.1.0": {"body": "x"}})

    result, target = run_install(
        tmp_path, server.url, "--version", "9.9.9", script=lone_script
    )

    assert result.returncode != 0
    assert "could not read the release" in result.stderr
    assert not target.exists()


def test_dry_run_changes_nothing(tmp_path, github, lone_script):
    server = github({"0.1.0": {"body": "x"}})

    result, target = run_install(tmp_path, server.url, "--dry-run", script=lone_script)

    assert result.returncode == 0, result.stderr
    assert "Dry run" in result.stdout
    assert not target.exists()
    assert not [p for p in server.requests if p.startswith("/files/")]


def test_plain_http_is_only_for_localhost(tmp_path, lone_script):
    result, target = run_install(tmp_path, "http://example.com", script=lone_script)

    assert result.returncode != 0
    assert "must be an https URL" in result.stderr
    assert not target.exists()


def test_installs_from_a_checkout(tmp_path):
    result, target = run_install(tmp_path, "http://127.0.0.1:1")

    assert result.returncode == 0, result.stderr
    assert "from the checkout" in result.stdout
    assert target.read_bytes() == (ROOT / "src" / "lupa.py").read_bytes()


def test_rejects_an_unknown_option(tmp_path):
    result, _ = run_install(tmp_path, "http://127.0.0.1:1", "--nope")

    assert result.returncode != 0
    assert "unknown option" in result.stderr


def test_removes_the_command_of_the_old_name(tmp_path):
    old = tmp_path / "bin" / "spotlight"
    old.parent.mkdir()
    old.write_text("application_id='dev.local.SpotlightLauncher'")

    result, target = run_install(tmp_path, "http://127.0.0.1:1")

    assert result.returncode == 0, result.stderr
    assert "Removed the old command" in result.stdout
    assert not old.exists()
    assert target.exists()


def test_keeps_a_spotlight_command_that_is_not_ours(tmp_path):
    other = tmp_path / "bin" / "spotlight"
    other.parent.mkdir()
    other.write_text("#!/bin/sh\necho somebody else's tool\n")

    result, _ = run_install(tmp_path, "http://127.0.0.1:1")

    assert result.returncode == 0, result.stderr
    assert other.read_text().startswith("#!/bin/sh")


def test_appimage_is_installed_in_the_data_folder_and_linked(
    tmp_path, github, lone_script
):
    server = github({"0.4.0": {"body": "x", "packages": True}})

    result, target = run_install(
        tmp_path, server.url, "--method", "appimage", script=lone_script
    )

    assert result.returncode == 0, result.stderr
    image = tmp_path / "data" / "lupa" / "Lupa-0.4.0-x86_64.AppImage"
    assert image.read_bytes().startswith(b"#!/bin/sh")
    assert os.access(image, os.X_OK)
    assert target.is_symlink()
    assert target.resolve() == image.resolve()


def test_appimage_update_replaces_the_old_one(tmp_path, github, lone_script):
    server = github({"0.4.0": {"body": "x", "packages": True}})
    run_install(tmp_path, server.url, "--method", "appimage", script=lone_script)
    server.releases["0.5.0"] = {"body": "y", "packages": True}

    result, _ = run_install(
        tmp_path, server.url, "--method", "appimage", script=lone_script
    )
    again, _ = run_install(
        tmp_path, server.url, "--method", "appimage", script=lone_script
    )

    folder = tmp_path / "data" / "lupa"
    assert result.returncode == 0, result.stderr
    assert [p.name for p in folder.iterdir()] == ["Lupa-0.5.0-x86_64.AppImage"]
    assert "already installed and up to date" in again.stdout


def test_script_method_still_works_when_the_release_has_packages(
    tmp_path, github, lone_script
):
    server = github({"0.4.0": {"body": "the script", "packages": True}})

    result, target = run_install(
        tmp_path, server.url, "--method", "script", script=lone_script
    )

    assert result.returncode == 0, result.stderr
    assert not target.is_symlink()
    assert target.read_text() == "the script"


@pytest.mark.parametrize("method", ["deb", "appimage"])
def test_a_method_the_release_has_no_file_for_fails(
    tmp_path, github, lone_script, method
):
    server = github({"0.1.0": {"body": "x"}})

    result, target = run_install(
        tmp_path, server.url, "--method", method, script=lone_script
    )

    assert result.returncode != 0
    assert "has no file named" in result.stderr
    assert not target.exists()


def test_an_unknown_method_is_rejected(tmp_path):
    result, _ = run_install(tmp_path, "http://127.0.0.1:1", "--method", "rpm")

    assert result.returncode != 0
    assert "--method is deb, appimage or script" in result.stderr


@pytest.mark.skipif(
    shutil.which("dpkg") is None or shutil.which("apt-get") is None,
    reason="needs a Debian family system",
)
def test_the_deb_is_the_first_choice_where_apt_exists(tmp_path, github, lone_script):
    server = github({"0.4.0": {"body": "x", "packages": True}})

    result, target = run_install(tmp_path, server.url, "--dry-run", script=lone_script)

    privileges = os.getuid() == 0 or shutil.which("sudo")
    assert result.returncode == 0, result.stderr
    assert ("(deb)" in result.stdout) == bool(privileges)
    assert not target.exists()


def test_piped_into_sh_it_ignores_a_checkout_in_the_current_folder(tmp_path, github):
    server = github({"0.1.0": {"body": "from the release"}})
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "LUPA_REPO": "example/lupa",
        "LUPA_API": server.url,
        "XDG_DATA_HOME": str(tmp_path / "data"),
    }

    result = subprocess.run(
        ["sh", "-s", "--", "--no-shortcut", "--prefix", str(tmp_path / "bin")],
        input=INSTALL.read_text(),
        cwd=ROOT,  # a checkout: it has src/lupa.py
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "from the checkout" not in result.stdout
    assert (tmp_path / "bin" / "lupa").read_text() == "from the release"
