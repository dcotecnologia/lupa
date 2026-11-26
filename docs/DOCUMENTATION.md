# Documentation

## How it works

`src/spotlight.py` is a single-file `Gtk.Application` with the application id
`dev.local.SpotlightLauncher`. GTK registers that id on the session D-Bus, so a second
run of the command does not start a new process: it triggers `activate` in the running
one, which toggles the window. That is why one global shortcut can both open and close it.

The window is built once and hidden/shown afterwards, which keeps opening instant.

### Search pipeline

Typing is debounced by 80 ms, then `refresh()` builds a list of `Result` objects
(`title`, `subtitle`, `icon`, `action`) in this order:

1. **Calculator** (`calc`): the text is parsed with `ast` and evaluated by a whitelist
   evaluator. Only numbers, `+ - * / % // **`, unary signs, `pi`, `e` and the
   one-argument math functions are allowed; exponents above 1000 are rejected.
   Nothing is passed to `eval`.
2. **Applications** (`search_apps`): `Gio.AppInfo.get_all()`, skipping hidden entries.
   Ranked: name prefix, name substring, then generic name or keywords. Max 8.
3. **Files** (`search_files`): `plocate -i -b` limited to 40 hits, filtered to paths under
   `$HOME` without hidden components, first 5 shown. Needs 3+ characters.
4. **Web** (`WEB` constant): always the last row.

Selecting a row runs its `action` after hiding the window.

## Configuration

There is no config file; edit the constants at the top of `src/spotlight.py` and rerun
`./install.sh`:

| Constant | Meaning |
| --- | --- |
| `WEB` | Search URL prefix (default Google; try `https://duckduckgo.com/?q=`) |
| `MAX_ROWS` | Max application rows |
| `CSS` | Colors, radius, font sizes |

## The install script

`install.sh` checks for PyGObject, copies the script to `~/.local/bin/spotlight`, and on
Cinnamon registers a custom keybinding named `spotlight` via `gsettings`
(`org.cinnamon.desktop.keybindings`). It also removes `<Super>space` from
`wm switch-input-source`, because Cinnamon binds it to layout switching by default.
`uninstall.sh` reverses all of it and resets that key to its default.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Shortcut does nothing | Run the command in a terminal to see errors. Check no other app grabs Super+Space. Re-login or `cinnamon --replace &`. |
| `No module named 'gi'` | Install `python3-gi gir1.2-gtk-3.0`. The launcher must use `/usr/bin/python3`, not a virtualenv. |
| No file results | Install `plocate`, run `sudo updatedb`. Only files under `$HOME` are shown. |
| Opaque, boxy window | No compositor / RGBA visual; the launcher still works. |
| Window does not take focus | Press the shortcut again; some X11 setups restrict focus stealing. |
| Can't switch keyboard layout anymore | Set another combo in Settings → Keyboard → Layouts, or run `./uninstall.sh`. |

## Limitations

Linux with X11 is the tested target. GTK3 on Wayland does not allow global placement or
guaranteed focus. The global shortcut is only automated for Cinnamon.

## Development

```bash
/usr/bin/python3 src/spotlight.py          # run from the checkout
/usr/bin/python3 -I -c "import importlib.util as u; s=u.spec_from_file_location('sp','src/spotlight.py'); m=u.module_from_spec(s); s.loader.exec_module(m); print(m.calc('2*(3+4)'))"
```

The second command exercises the pure logic (calculator, search) without opening a window.

## Tests and linting

The project uses [uv](https://docs.astral.sh/uv/). PyGObject comes from the system, so the
virtual environment must see the system packages; `make sync` does that.

```bash
make sync   # venv with system site packages + dev dependencies
make test   # pytest, 100% coverage required
make lint   # pre-commit on all files (ruff, yamllint, gitleaks, actionlint, ...)
```

The window class (`Launcher`) needs a display and is excluded from coverage; check it by
hand by running `src/spotlight.py`. Everything it calls is unit tested.
Install the git hook once with `uv run pre-commit install`.

## Releases

Commits follow [Conventional Commits](https://www.conventionalcommits.org/). To release:

1. Move the `[Unreleased]` notes of `CHANGELOG.md` under a new `## [X.Y.Z] - date` heading
   and bump `version` in `pyproject.toml` (then `uv lock`).
2. Merge to `main`, then push the tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.

The Release workflow runs the tests, checks that the tag matches `pyproject.toml`, validates
the changelog, and publishes a GitHub release with the changelog section as its notes, a
source tarball and its `SHA256SUMS`. A tag with a dash (`v0.2.0-rc1`) is a pre-release.
