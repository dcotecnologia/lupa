# Commit Guidelines

This repository follows the [Conventional Commits](https://www.conventionalcommits.org/) specification.

Consistent commit messages improve:

- changelog generation
- release automation
- code review readability
- traceability of functional and non-functional changes

## Commit Message Format

Use the following structure:

```text
<type>(<optional-scope>): <subject>

<optional body>

<optional footer>
```

### Header Rules

- `type` is required.
- `scope` is optional and should represent a module or domain.
- `subject` is required.
- Use imperative mood in subject and body (for example: `add`, `fix`, `remove`).
- Do not end the subject with a period.

## Allowed Types

- `feat`: new feature
- `fix`: bug fix
- `refactor`: internal change without behavior change
- `perf`: performance improvement
- `style`: formatting/style changes only
- `test`: test additions or updates
- `docs`: documentation-only changes
- `build`: build/dependency/CI changes
- `ops`: infrastructure/deployment/operational changes
- `chore`: maintenance tasks

## Scope Guidance

Recommended scopes in this repository include:

- `calc`
- `apps`
- `files`
- `ui`
- `install`
- `tests`
- `ci`
- `release`
- `deps`

Examples:

```text
feat(files): show the folder of each file result
fix(calc): reject exponents above 1000
docs(readme): add a screenshot
```

## Body and Footer

Use the body to explain **why** the change is needed, especially for non-obvious behavior.

Use the footer for issue references and breaking changes:

```text
BREAKING CHANGE: rename the launcher command from spotlight to spotlight-linux
Refs: #12
```

## Examples

```text
feat(ui): run the Nth result with Ctrl+N
```

```text
fix(files): skip hidden folders in the results

Files under dot-folders (caches, configs) are noise for a launcher,
so they are filtered out after plocate returns.
Refs: #3
```

```text
refactor(apps): share one ranking between name, generic name and keywords
```

```text
docs(commiting): rewrite commit guidelines in english
```

## Optional Local Hook

You can enforce commit format locally with a `commit-msg` hook.

### Create `.git-hooks/commit-msg`

```sh
#!/usr/bin/env sh
commit_message="$1"
git-conventional-commits commit-msg-hook "$commit_message"
```

### Make it executable

```sh
chmod +x .git-hooks/commit-msg
```

### Configure Git to use repository hooks

```sh
git config core.hooksPath .git-hooks
```

Recommended tool:

- <https://github.com/qoomon/git-conventional-commits>
