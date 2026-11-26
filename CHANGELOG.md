# Changelog

All notable changes to this project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-26

### Changed

- The project is now called Lupa, to avoid confusion with the trademarks of others: the repository is `dcotecnologia/lupa`, the command is `lupa`, the keybinding is named `lupa` and the release file is `lupa-X.Y.Z.tar.gz`. Running `install.sh` again removes the command and the shortcut of the old name by @danilogco

### Added

- A website on GitHub Pages, with the install command, the tutorial and the documentation, and with SEO metadata: canonical URLs, Open Graph and Twitter cards, structured data, a sitemap and `robots.txt` by @danilogco

## [0.1.0] - 2026-11-26

### Added

- `install.sh` installs or updates from the latest GitHub release with one command (`curl -fsSL .../install.sh | sh`), checking its sha256, and `uninstall.sh` removes it by @danilogco
- Screenshots of the launcher in the README, rendered by `make screenshot` by @danilogco
- Project standards: `AGENTS.md`, `COMMITING.md`, `CONTRIBUTING.md`, `SECURITY.md`, a code of conduct, issue and pull request templates, a CodeQL scan and a `Makefile` by @danilogco
- A Spotlight-style launcher window (GTK3) that opens with a shortcut and closes with Esc, a click outside, or the same shortcut by @danilogco
- Search of installed applications, with icons, ranked by name prefix, name substring, then generic name and keywords by @danilogco
- A calculator with `+ - * / % // ^`, `pi`, `e` and the usual math functions, evaluated without `eval`; Enter copies the result by @danilogco
- File search in the home directory through `plocate`, and a web search row as the last result by @danilogco
- `install.sh` and `uninstall.sh`, which also bind and release Super+Space on Cinnamon by @danilogco
- Unit tests at 100% coverage, a pre-commit configuration, a CI pipeline and a release pipeline by @danilogco

[Unreleased]: https://github.com/dcotecnologia/lupa/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/dcotecnologia/lupa/releases/tag/v0.2.0
[0.1.0]: https://github.com/dcotecnologia/lupa/commit/d92cd3e
