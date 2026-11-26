# Security Policy

## Supported versions

lupa is young: security fixes go to the latest release.

## Reporting a vulnerability

Please do not open a public issue for a security problem.

- Use GitHub's private reporting: **Security → Report a vulnerability** on the
  [repository](https://github.com/dcotecnologia/lupa/security/advisories/new).
- Or email <danilogcarolino@gmail.com> with the subject `lupa security`.

Include what you found, the version, your distribution and desktop, and the steps to
reproduce it. You can expect an acknowledgement within a few days.

## How lupa handles what you type

- **The calculator never uses `eval`.** The text is parsed with `ast` and evaluated by a
  whitelist of numbers, arithmetic operators, `pi`, `e` and a few one-argument math
  functions. Exponents above 1000 are refused so a typed `9**9**9` cannot freeze the window.
- **Nothing you type is run as a command.** Applications are started through
  `Gio.AppInfo`, files and links through the default handler of the desktop, and
  `plocate` receives your text as a single argument after `--`, never through a shell.
- **File search stays in your home.** Results outside `$HOME` and inside hidden folders
  (`.cache`, `.ssh`, ...) are dropped, and `plocate` only lists what your user may see.
- **No telemetry and no network of its own.** The "search the web" row only opens your
  browser with the text in the URL; the launcher itself sends nothing.
- **Nothing is stored.** There is no history, cache or settings file.
- **The install scripts only touch their own files.** `install.sh` writes
  `~/.local/bin/lupa` and, on Cinnamon, the `lupa` custom keybinding and the
  layout-switch shortcut it frees; `uninstall.sh` undoes exactly that. Neither uses `sudo`.
