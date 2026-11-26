# Contributing to spotlight-linux

Thanks for helping. spotlight-linux is a Spotlight-style launcher for Linux written in
Python with GTK3. This page gets you from a clone to a pull request; the details live in
two other files:

- [AGENTS.md](AGENTS.md): architecture, code standards and the quality bar. It applies
  to people and AI assistants alike.
- [COMMITING.md](COMMITING.md): the commit message format (Conventional Commits).

## Set up

```bash
git clone https://github.com/dcotecnologia/spotlight-linux.git
cd spotlight-linux
sudo apt install python3-gi gir1.2-gtk-3.0 plocate
make setup          # venv with system packages, dev dependencies and the pre-commit hook
```

Run the launcher from the checkout with `make run`, and refresh the README screenshots
with `make screenshot`.

## Workflow

1. Pull the latest `main` and create a branch. Do not commit to `main` directly.
2. Make one focused change per commit, with its tests.
3. Run the checks below.
4. Open a pull request that says what changed and why. Link the issue if there is one.

## Checks

```bash
make lint     # every pre-commit hook on all files, as CI runs them
make test     # pytest, must stay at 100% coverage
```

CI runs the same pre-commit hooks and the tests. A pull request must be green.

## Commit messages

Follow [COMMITING.md](COMMITING.md):

```text
feat(files): show the folder of each file result
fix(calc): reject exponents above 1000
docs: add a screenshot to the README
```

English, imperative mood, no trailing period, and no AI assistant as co-author.

## Changelog

Every user-visible change adds a line to the `[Unreleased]` section of
[CHANGELOG.md](CHANGELOG.md), and each line ends with the GitHub user who wrote the
commit, like GitHub's own release notes do:

```text
- The window opens centered on the monitor of the pointer by @danilogco
```

The release workflow publishes the section of the tag as the release notes.

## Security

Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md), not in a
public issue.

## License

By contributing you agree that your work is released under the [MIT License](LICENSE).
