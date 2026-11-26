# Tutorial

A five-minute tour. Install first (see the [README](../README.md)).

## 1. Open it

Press **Super+Space** (the Windows key plus Space). A search box appears in the
upper-middle of your screen. If nothing happens, run this in a terminal to rule out the shortcut:

```bash
/usr/bin/python3 ~/.local/bin/spotlight
```

## 2. Launch an app

Type `fire`. Applications whose name starts with your text come first, then names that
merely contain it. The first row is already selected, so press **Enter**.

## 3. Do quick math

Type `12*(3+4)` and the first row shows `= 84`. Enter copies `84` to the clipboard.
Supported: `+ - * / % ^ //`, parentheses, `pi`, `e`, and `sqrt sin cos tan log log10 exp floor ceil`.
A comma works as a decimal separator: `1,5*2`.

## 4. Find a file

Type at least three characters, e.g. `invoice`. Up to five matches from your home
directory appear with their folder. Enter opens the file in its default application.
Hidden files and folders are skipped. New files appear after the index updates:

```bash
sudo updatedb
```

## 5. Search the web

The last row is always `Search the web for "…"`. Arrow down to it and press Enter,
or jump straight to a row with Ctrl+1 … Ctrl+9.

## 6. Close it

Press **Esc**, click anywhere else, or press Super+Space again.
