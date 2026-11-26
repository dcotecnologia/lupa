# AGENTS

Guide for agents (human and AI) working in this repository.
Goal: keep the code, tests and commit history consistent.

spotlight-linux is a Spotlight-style launcher for Linux desktops, built with
Python 3.12+ and GTK3 (PyGObject). It searches applications, files (through
`plocate`) and math expressions, and it never changes anything on the system besides
launching the thing the person picked.

## Project documents

Read the document that covers your task before you start, and follow it. When
two documents disagree, stop and ask instead of picking one.

| Document | Read it when | Rule |
| -------- | ------------ | ---- |
| [COMMITING.md](COMMITING.md) | You write any commit message | Source of truth for the commit format |
| [CONTRIBUTING.md](CONTRIBUTING.md) | You set up, branch, test, or open a PR | The workflow a change goes through |
| [SECURITY.md](SECURITY.md) | You touch the calculator, the file search, launching or the install scripts | Do not break its guarantees; update it when they change |
| [README.md](README.md) | You change user-facing behavior or requirements | Keep it accurate |
| [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md) | You change how the launcher works | Keep it true |

## 1) Architecture and responsibilities

`src/spotlight.py` is one module with a clear split:

- Pure logic, no GTK widgets and no display: `calc` (the whitelist evaluator),
  `search_apps`, `search_files`, `open_uri` and `Result`. Everything here is unit tested.
- `Launcher` (a `Gtk.Application`): the window, the debounce and the key handling. It
  needs a display, so it is the only part excluded from coverage.
- `install.sh` / `uninstall.sh`: install the command and register the shortcut. They
  must stay idempotent and must not touch what they did not create.
- `tests/` mirrors the module: `tests/test_spotlight.py`.
- `tools/screenshot.py` renders the screenshots of the README; run it with `make screenshot`.

Golden rule:

- New kind of result (a new search source) -> a function returning `list[Result]`,
  added to `Launcher.refresh`, with its own tests
- New preference or constant -> the constants at the top of the module
- Look of the window -> the `CSS` constant

## 2) Code standards

- Write code that reads like the surrounding code: match its naming, comment
  density, and idioms.
- Target Python 3.12 or newer (the system Python of Linux Mint 22 and Ubuntu 24.04).
- Prefer simple functions over class hierarchies. Use classes only where GTK requires them.
- Tests are plain `pytest` functions; avoid test classes unless clearly needed.
- Internal code keeps strict contracts (fail fast). Defensive validation belongs at the
  boundaries: the typed text, the output of `plocate`, the desktop entries.
- Never block the UI thread; keep external commands short (`plocate` has a timeout).
- Code, comments, identifiers, test names, and commit messages are in English.

## 3) Commits: follow COMMITING.md

[COMMITING.md](./COMMITING.md) is the source of truth for commit messages. Read it
before every commit; the points below only reinforce it. For the branch and PR
flow, follow [CONTRIBUTING.md](./CONTRIBUTING.md).

- Use Conventional Commits: `<type>(<optional-scope>): <subject>`.
- Allowed types: `feat`, `fix`, `refactor`, `perf`, `style`, `test`, `docs`,
  `build`, `ops`, `chore`.
- Subject in English, imperative mood, no trailing period.
- Use the body to explain why, and the footer for `BREAKING CHANGE:` or `Refs:`.
- One objective per commit. Do not mix refactor, feature, and fix.
- Behavior changes ship with their tests in the same commit.
- Documentation-only changes use `docs`, never `feat`.
- A version bump also updates `uv.lock` in the same commit.
- The user is the sole author. Never add an AI assistant as co-author, and never
  add attribution trailers such as `Co-Authored-By` to commits or PR descriptions.
- Never commit directly to `main`: create a branch and open a PR, even for small or
  documentation-only changes. Only commit when asked to.
- Before starting work, pull `origin/main` so the branch starts up to date.

## Running checks without freezing the machine

The full test suite and the type checker are heavy enough to freeze a developer's
computer. Agents follow these rules while they work:

- Never run the whole suite: no `make test`, no `pytest` without arguments. Run
  only the test file of the change:
  `nice -n 19 uv run pytest tests/test_x.py -q --no-cov`.
- Coverage only at the final gate. `--cov` (the required 100%) is the slowest part
  and is left to the human.
- One heavy command at a time. Never run `pytest` and `ruff` one after the other
  without waiting, or in parallel; wait for one to finish before the next.
- Check only what changed: `ruff check path/to/file.py` instead of `ruff check .`.
- Do not repeat a check when nothing changed since its last run.
- Ask before the full gate. `make test` and `make lint` (section 4) run once, at
  the end, and only after the agent asks for authorization.

## 4) Minimum quality before opening a PR

Run locally and make all of it pass (once, at the end, following the rules above):

- `make lint` (every pre-commit hook on all files, as CI runs them)
- `make test` (pytest, 100% coverage)

Requirements:

- The test suite passes. New behavior has tests; bug fixes have a regression test.
- Test coverage stays at 100%. `make test` enforces it (`--cov-fail-under=100`), so a
  change that leaves lines or branches uncovered fails. Cover the code with tests;
  never lower the threshold or widen the coverage exclusions to get green. The only
  exclusions are the `Launcher` window and the `__main__` guard, which need a display.
- Do not introduce `DeprecationWarning` or `PendingDeprecationWarning`. Fix them
  with the recommended API. Do not hide them with warning filters without a
  documented reason.
- Keep dependencies on their latest stable versions; pin an older one only with a
  documented reason.
- User-visible changes go in the `[Unreleased]` section of `CHANGELOG.md`.

## 5) Security

Follow [SECURITY.md](SECURITY.md); its guarantees are part of the product.

- Never use `eval`/`exec` on typed text; the calculator walks the `ast` with a whitelist.
- Run programs as an argument list, never as a shell string; treat file names and
  desktop entries as untrusted data.
- Do not add telemetry or network calls of the app's own. The web row only opens the
  browser.
- Never commit secrets or personal paths; the `gitleaks` hook must pass.
- When a change affects what SECURITY.md describes, update it in the same pull request.
- If you find a vulnerability while working, report it as SECURITY.md describes; do
  not describe it in a public issue, commit message, or PR.

## 6) Quick checklist for agents

- Keep the pure logic apart from the window, and the window thin.
- Add or update tests next to the code, in English and function-based, and keep
  coverage at 100%.
- Read the documents in the table above that apply, and follow them.
- Update README.md, CONTRIBUTING.md and the docs when setup or behavior changes.
- Run `make lint` and `make test` before finishing (after asking, see above).
- Write the commit message following [COMMITING.md](./COMMITING.md), with no
  AI co-author.
- Branch from an up-to-date `origin/main`, never commit to `main` directly, and only
  commit or push when asked.
