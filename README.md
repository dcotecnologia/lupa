# spotlight-linux

[![CI](https://github.com/dcotecnologia/spotlight-linux/actions/workflows/ci.yml/badge.svg)](https://github.com/dcotecnologia/spotlight-linux/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/dcotecnologia/spotlight-linux)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)
![Platform: Linux](https://img.shields.io/badge/platform-linux-lightgrey)
![GTK 3](https://img.shields.io/badge/GTK-3-4a86cf)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen)](https://github.com/pre-commit/pre-commit)

A small macOS-Spotlight-style launcher for Linux desktops, written in Python and GTK3.
Press a shortcut, type, hit Enter.

![Searching for an application](docs/screenshots/apps.png)
![Using the calculator](docs/screenshots/calculator.png)

- **Apps**: prefix/substring search over installed applications, with icons.
- **Calculator**: type `2*(3+4)^2` or `sqrt(16)`; Enter copies the result.
- **Files**: searches your home directory through `plocate` (3+ characters).
- **Web**: the last row searches the web for what you typed.
- **Toggle**: running the command again closes the window, so one shortcut does both.

## Requirements

- Python 3 with PyGObject and GTK 3 (`python3-gi`, `gir1.2-gtk-3.0`)
- Optional: `plocate` for file search
- A compositing desktop (for the translucent window). Tested on Linux Mint Cinnamon, X11.

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 plocate
```

## Install

The easiest way is the install script. It finds the latest release, checks it against
the sha256 that GitHub publishes for it, and installs it into `~/.local/bin`. Run the
same command again to update; it says when you already have the latest version.

```bash
curl -fsSL https://raw.githubusercontent.com/dcotecnologia/spotlight-linux/main/install.sh | sh
```

On Cinnamon it also binds **Super+Space** (and frees it from keyboard-layout switching).
On other desktops, bind a key to `/usr/bin/python3 ~/.local/bin/spotlight` yourself.

To choose a version or look before it acts, save the script and run it with
`--dry-run`, `--version 0.1.0`, `--prefix DIR` or `--no-shortcut`; `./install.sh --help`
lists them. A script that you pipe into a shell runs with your rights, so read it
first if you prefer: [install.sh](install.sh). The sha256 check catches a damaged or
swapped download; it trusts GitHub and this repository, as any download from them does.

### Install from a checkout

```bash
git clone https://github.com/dcotecnologia/spotlight-linux.git
cd spotlight-linux
./install.sh
```

Run from a checkout, the script installs that checkout instead of a release.

### Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/dcotecnologia/spotlight-linux/main/uninstall.sh | sh
```

It removes the command and the shortcut, and gives Super+Space back to the layout switcher.

## Usage

| Key | Action |
| --- | --- |
| Super+Space | Open / close |
| Type | Search apps, files, math |
| Up / Down | Move selection |
| Enter | Run the selected row |
| Ctrl+1 … Ctrl+9 | Run the Nth row directly |
| Esc, or click elsewhere | Close |

See [docs/TUTORIAL.md](docs/TUTORIAL.md) for a walkthrough and
[docs/DOCUMENTATION.md](docs/DOCUMENTATION.md) for internals, configuration and troubleshooting.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md) and [COMMITING.md](COMMITING.md);
report vulnerabilities as described in [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
