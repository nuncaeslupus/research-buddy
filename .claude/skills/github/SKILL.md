---
name: github
description: Apply git/GitHub conventions for commits, branches, and PRs in this project.
user-invocable: false
---

# GitHub Conventions Skill

## When to use

Invoke when creating commits, branches, or pull requests.

## Branch Naming

- Main branch: `main`
- Feature branches: `feat/<short-description>`
- Fix branches: `fix/<short-description>`

## Commit Format (Conventional Commits)

```
<type>(scope): description
```

### Types

`feat` | `fix` | `refactor` | `test` | `docs` | `chore` | `ci`

### Scope

- `feat(build): add custom theme support`
- `fix(schema): validate changelog entry ids`
- `test(cli): add init command tests`
- `docs: update README`

### Rules

- Imperative mood ("add", "fix", not "added", "fixes")
- No period at end
- First line under 72 characters
- Body (optional) separated by blank line, explains "why" not "what"

## Pre-Commit Checklist

Before every commit:

```bash
make format
make lint
```

Both must pass before committing.
