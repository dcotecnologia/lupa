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
