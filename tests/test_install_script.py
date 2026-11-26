"""Tests of install.sh against a fake GitHub API served on localhost."""

import hashlib
import http.server
import io
import json
import os
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
        info = tarfile.TarInfo(f"spotlight-linux-{version}/src/spotlight.py")
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
        base = "/repos/example/spotlight/releases/"
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
            if name == f"spotlight-linux-{version}.tar.gz":
                return 200, tarball
            if name == f"SHA256SUMS-{version}":
                digest = hashlib.sha256(tarball).hexdigest()
                line = f"{digest}  spotlight-linux-{version}.tar.gz\n"
                return 200, line.encode()
        return 404, b"{}"

    def release(self, version):
        data = self.releases[version]
        tarball = self.tarball(version)
        name = f"spotlight-linux-{version}.tar.gz"
        asset = {"name": name, "browser_download_url": f"{self.url}/files/{name}"}
        if data.get("digest", True):
            asset["digest"] = "sha256:" + hashlib.sha256(tarball).hexdigest()
        if data.get("tamper"):
            asset["digest"] = "sha256:" + "0" * 64
        assets = [asset]
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
        "SPOTLIGHT_REPO": "example/spotlight",
        "SPOTLIGHT_API": api,
    }
    result = subprocess.run(
        ["sh", str(script), "--no-shortcut", "--prefix", str(prefix), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return result, prefix / "spotlight"


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
    assert target.read_bytes() == (ROOT / "src" / "spotlight.py").read_bytes()


def test_rejects_an_unknown_option(tmp_path):
    result, _ = run_install(tmp_path, "http://127.0.0.1:1", "--nope")

    assert result.returncode != 0
    assert "unknown option" in result.stderr
