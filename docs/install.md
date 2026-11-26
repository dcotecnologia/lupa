---
layout: page
title: Install
description: Install or update Spotlight for Linux with one command. It verifies the download with sha256 and binds Super+Space on Cinnamon.
permalink: /install/
---

## Install or update from the command line

One command installs the latest release and, run again, updates it. It checks the
download against the sha256 that GitHub publishes before installing anything.

```bash
curl -fsSL https://raw.githubusercontent.com/dcotecnologia/spotlight-linux/main/install.sh | sh
```

It puts the launcher in `~/.local/bin/spotlight`. On Cinnamon it also binds **Super+Space**
and frees that key from keyboard-layout switching; on other desktops, bind a key to
`/usr/bin/python3 ~/.local/bin/spotlight` yourself. You can read
[install.sh](https://github.com/dcotecnologia/spotlight-linux/blob/main/install.sh) first, and
choose a version or look before it acts with `--version 0.1.0` and `--dry-run`.

## Requirements

- Python 3 with PyGObject and GTK 3: `sudo apt install python3-gi gir1.2-gtk-3.0`
- Optional, for file search: `sudo apt install plocate`
- A compositing desktop, for the translucent window

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/dcotecnologia/spotlight-linux/main/uninstall.sh | sh
```

## Learn more

- [Tutorial]({{ '/tutorial/' | relative_url }}): a five-minute tour
- [Documentation]({{ '/documentation/' | relative_url }}): how it works, configuration and troubleshooting
