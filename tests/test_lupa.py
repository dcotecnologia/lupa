"""Unit tests for the pure logic of the launcher (no display needed)."""

import subprocess
from types import SimpleNamespace

import pytest

import lupa

pytestmark = pytest.mark.unit


# -- calc -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1+1", "2"),
        ("2*(3+4)^2", "98"),
        ("1,5*2", "3"),
        ("4/2", "2"),
        ("7/2", "3.5"),
        ("0.1+0.2", "0.3"),
        ("7%4", "3"),
        ("7//2", "3"),
        ("-3+5", "2"),
        ("+3", "3"),
        ("sqrt(16)+1", "5"),
        ("pi*2", "6.2831853072"),
        ("e^2", "7.3890560989"),
    ],
)
def test_calc_evaluates(text, expected):
    assert lupa.calc(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "hello",  # no digit at all
        "pi",  # a name without digits is not math
        "1/0",  # division by zero
        "2**5000",  # exponent above the limit
        "10.0**999",  # float overflow
        "1+",  # syntax error
        "x+1",  # unknown name
        "__import__(1)",  # call to a function that is not allowed
        "sqrt(4)(1)",  # call of something that is not a plain function name
        "'a'+1",  # not a number
        "1 if 1 else 2",  # unsupported syntax
        "sqrt(-1)",  # math domain error
    ],
)
def test_calc_rejects(text):
    assert lupa.calc(text) is None


# -- search_apps ------------------------------------------------------------


class FakeApp:
    def __init__(self, name, *, generic=None, keywords=None, desc=None, show=True):
        self.name, self.generic, self.keywords = name, generic, keywords
        self.desc, self.show = desc, show
        self.launched = False

    def should_show(self):
        return self.show

    def get_display_name(self):
        return self.name

    def get_generic_name(self):
        return self.generic

    def get_keywords(self):
        return self.keywords

    def get_description(self):
        return self.desc

    def get_icon(self):
        return None

    def launch(self, files, context):
        self.launched = True


def fake_gio(monkeypatch, apps):
    monkeypatch.setattr(
        lupa, "Gio", SimpleNamespace(AppInfo=SimpleNamespace(get_all=lambda: apps))
    )


def test_search_apps_ranks_prefix_before_substring_before_keywords(monkeypatch):
    apps = [
        FakeApp("My Firefox"),
        FakeApp("Browser", generic="Web Browser", keywords=["fire"]),
        FakeApp("Firefox", desc="Web browser"),
        FakeApp("Unrelated"),
    ]
    fake_gio(monkeypatch, apps)

    results = lupa.search_apps("Fire")

    assert [r.title for r in results] == ["Firefox", "My Firefox", "Browser"]
    assert results[0].subtitle == "Web browser"
    assert results[1].subtitle == "Application"


def test_search_apps_matches_generic_name(monkeypatch):
    fake_gio(monkeypatch, [FakeApp("Files", generic="File Manager")])

    assert [r.title for r in lupa.search_apps("manager")] == ["Files"]


def test_search_apps_skips_hidden_and_non_matching(monkeypatch):
    fake_gio(monkeypatch, [FakeApp("Hidden", show=False), FakeApp("Other")])

    assert lupa.search_apps("hidden") == []


def test_search_apps_limits_rows_and_launches(monkeypatch):
    apps = [FakeApp(f"App {i:02d}") for i in range(lupa.MAX_ROWS + 5)]
    fake_gio(monkeypatch, apps)

    results = lupa.search_apps("app")
    results[0].action()

    assert len(results) == lupa.MAX_ROWS
    assert apps[0].launched


# -- search_files -----------------------------------------------------------


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def fake_plocate(monkeypatch, lines):
    def run(cmd, **kwargs):
        assert cmd[0] == "plocate"
        return SimpleNamespace(stdout="\n".join(lines))

    monkeypatch.setattr(lupa.subprocess, "run", run)


def test_search_files_needs_three_characters(home):
    assert lupa.search_files("ab") == []


def test_search_files_without_plocate(home, monkeypatch):
    monkeypatch.setattr(lupa.os.path, "exists", lambda _p: False)

    assert lupa.search_files("invoice") == []


def test_search_files_survives_plocate_failure(home, monkeypatch):
    def boom(*_a, **_k):
        raise subprocess.TimeoutExpired("plocate", 1.5)

    monkeypatch.setattr(lupa.os.path, "exists", lambda _p: True)
    monkeypatch.setattr(lupa.subprocess, "run", boom)

    assert lupa.search_files("invoice") == []


def test_search_files_keeps_visible_paths_under_home(home, monkeypatch):
    (home / "docs").mkdir()
    (home / "docs" / "invoice.pdf").write_text("x")
    (home / ".cache").mkdir()
    (home / ".cache" / "invoice.tmp").write_text("x")
    monkeypatch.setattr(lupa.os.path, "exists", lambda _p: True)
    fake_plocate(
        monkeypatch,
        [
            str(home / "docs" / "invoice.pdf"),
            str(home / ".cache" / "invoice.tmp"),  # hidden folder
            "/var/lib/invoice.log",  # outside home
        ],
    )

    results = lupa.search_files("invoice")

    assert [r.title for r in results] == ["invoice.pdf"]
    assert results[0].subtitle == "~/docs/invoice.pdf"


def test_search_files_shows_five_and_opens_uri(home, monkeypatch):
    folder = home / "reports"
    folder.mkdir()
    for i in range(7):
        (folder / f"report{i}.txt").write_text("x")
    paths = [str(p) for p in sorted(folder.iterdir())]
    opened = []
    monkeypatch.setattr(lupa.os.path, "exists", lambda _p: True)
    fake_plocate(monkeypatch, [str(folder), *paths])
    monkeypatch.setattr(lupa, "open_uri", opened.append)

    results = lupa.search_files("report")
    results[0].action()  # the directory itself
    results[1].action()

    assert len(results) == 5
    assert opened == [f"file://{folder}", f"file://{paths[0]}"]


def test_open_uri_uses_the_default_application(monkeypatch):
    launched = []
    monkeypatch.setattr(
        lupa,
        "Gio",
        SimpleNamespace(
            AppInfo=SimpleNamespace(
                launch_default_for_uri=lambda uri, ctx: launched.append((uri, ctx))
            )
        ),
    )

    lupa.open_uri("https://example.com")

    assert launched == [("https://example.com", None)]


def test_result_keeps_its_fields():
    result = lupa.Result("t", "s", None, lambda: 1)

    assert (result.title, result.subtitle, result.icon) == ("t", "s", None)
    assert result.action() == 1


# -- version and options ------------------------------------------------------


def test_version_is_the_one_of_the_project():
    from tools import package_info

    assert lupa.__version__ == package_info.project_metadata()["version"]


def test_version_text_shows_the_metadata(monkeypatch):
    monkeypatch.setattr(lupa, "BUILD", "abc1234")

    lines = lupa.version_text().splitlines()

    assert lines[0] == f"lupa {lupa.__version__} (build abc1234)"
    assert "Author: DCO Developers <dev@dcotecnologia.com>" in lines
    assert "Repository: https://github.com/dcotecnologia/lupa" in lines
    assert "Website: https://lupa.dcotecnologia.com" in lines
    assert "License: MIT" in lines


def test_build_hash_comes_from_git_when_it_was_not_written_in(monkeypatch):
    monkeypatch.setattr(lupa, "BUILD", "$Format:%h$")
    seen = []

    def run(cmd, **kwargs):
        seen.append(cmd)
        return SimpleNamespace(returncode=0, stdout="1234abc\n")

    monkeypatch.setattr(lupa.subprocess, "run", run)

    assert lupa.build_hash() == "1234abc"
    assert seen[0][0] == "git"


@pytest.mark.parametrize(
    "result",
    [
        SimpleNamespace(returncode=128, stdout=""),  # not a git checkout
        SimpleNamespace(returncode=0, stdout="\n"),  # no commit
    ],
)
def test_build_hash_is_unknown_without_a_commit(monkeypatch, result):
    monkeypatch.setattr(lupa, "BUILD", "$Format:%h$")
    monkeypatch.setattr(lupa.subprocess, "run", lambda *_a, **_k: result)

    assert lupa.build_hash() == "unknown"


def test_build_hash_is_unknown_when_git_is_missing(monkeypatch):
    def run(*_args, **_kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(lupa, "BUILD", "$Format:%h$")
    monkeypatch.setattr(lupa.subprocess, "run", run)

    assert lupa.build_hash() == "unknown"


def test_build_hash_keeps_the_one_written_in(monkeypatch):
    monkeypatch.setattr(lupa, "BUILD", "feedbee")

    assert lupa.build_hash() == "feedbee"


@pytest.mark.parametrize("option", ["--version", "-V"])
def test_version_option_prints_and_does_not_start_the_window(
    monkeypatch, capsys, option
):
    started = []
    monkeypatch.setattr(lupa, "Launcher", lambda: started.append(1))

    status = lupa.main([option])

    assert status == 0
    assert capsys.readouterr().out.startswith(f"lupa {lupa.__version__} (build ")
    assert not started


@pytest.mark.parametrize("option", ["--help", "-h"])
def test_help_option_prints_the_usage(monkeypatch, capsys, option):
    monkeypatch.setattr(lupa, "Launcher", lambda: pytest.fail("must not start"))

    assert lupa.main([option]) == 0
    assert "Usage: lupa" in capsys.readouterr().out


def test_unknown_option_fails_with_the_usage(monkeypatch, capsys):
    monkeypatch.setattr(lupa, "Launcher", lambda: pytest.fail("must not start"))

    assert lupa.main(["--nope"]) == 2
    err = capsys.readouterr().err
    assert "unknown option: --nope" in err
    assert "Usage: lupa" in err


def test_no_option_runs_the_launcher(monkeypatch):
    class FakeLauncher:
        def run(self, argv):
            return 7

    monkeypatch.setattr(lupa, "Launcher", FakeLauncher)

    assert lupa.main([]) == 7


# -- update ---------------------------------------------------------------------


def fake_run(monkeypatch, download, calls):
    """Answer curl with `download` and record the other commands."""

    def run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        if cmd[0] in ("curl", "wget"):
            if isinstance(download, Exception):
                raise download
            return download
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(lupa.subprocess, "run", run)


def test_update_runs_the_install_script_it_downloaded(monkeypatch, capsys):
    calls = []
    fake_run(monkeypatch, SimpleNamespace(returncode=0, stdout=b"echo install"), calls)

    status = lupa.main(["update"])

    assert status == 0
    assert calls[0][0] == ["curl", "-fsSL", lupa.INSTALL_URL]
    assert calls[1][0] == ["sh", "-s", "--"]
    assert calls[1][1]["input"] == b"echo install"
    assert "Updating Lupa" in capsys.readouterr().out


def test_update_hands_its_options_to_the_script(monkeypatch):
    calls = []
    fake_run(monkeypatch, SimpleNamespace(returncode=0, stdout=b"x"), calls)

    lupa.main(["update", "--version", "0.4.0", "--dry-run"])

    assert calls[1][0] == ["sh", "-s", "--", "--version", "0.4.0", "--dry-run"]


def test_update_returns_the_status_of_the_script(monkeypatch):
    def run(cmd, **kwargs):
        if cmd[0] == "curl":
            return SimpleNamespace(returncode=0, stdout=b"x")
        return SimpleNamespace(returncode=3)

    monkeypatch.setattr(lupa.subprocess, "run", run)

    assert lupa.main(["update"]) == 3


def test_update_does_not_run_anything_when_the_download_fails(monkeypatch, capsys):
    calls = []
    fake_run(monkeypatch, SimpleNamespace(returncode=22, stdout=b""), calls)

    assert lupa.main(["update"]) == 1
    assert [c[0][0] for c in calls] == ["curl"]
    assert "could not download" in capsys.readouterr().err


def test_update_falls_back_to_wget_without_curl(monkeypatch):
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[0] == "curl":
            raise FileNotFoundError("curl")
        if cmd[0] == "wget":
            return SimpleNamespace(returncode=0, stdout=b"x")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(lupa.subprocess, "run", run)

    assert lupa.main(["update"]) == 0
    assert calls[1] == ["wget", "-qO-", lupa.INSTALL_URL]


def test_update_needs_curl_or_wget(monkeypatch, capsys):
    def run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(lupa.subprocess, "run", run)

    assert lupa.main(["update"]) == 1
    assert "curl or wget is needed" in capsys.readouterr().err
