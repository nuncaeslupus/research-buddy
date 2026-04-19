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
- Feature branches: `feat/<short-description>` (e.g., `feat/django-stack`)
- Fix branches: `fix/<short-description>`

## Commit Format (Conventional Commits)

```
<type>(scope): description
```

### Types

`feat` | `fix` | `refactor` | `test` | `docs` | `chore` | `ci`

### Scope

Module or domain name:

- `feat(generator): add new field type support`
- `test(templates): add boundary tests`
- `fix(parser): handle missing optional fields`
- `docs: update next-session.md`
- `chore: update uv.lock`

### Rules

- Imperative mood in description ("add", "fix", "implement", not "added", "fixes")
- No period at end
- First line under 72 characters
- Body (optional) separated by blank line, explains "why" not "what"
- Always append the right agent, e.g.: `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`

## Pre-Commit Checklist

Before every commit, run:

```bash
make format   # ruff auto-fix + ruff format
make lint     # ruff check + mypy
```

Both must pass before committing.