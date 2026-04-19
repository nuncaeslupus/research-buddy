---
name: session-end
description: End-of-session checklist. Updates next-session.md with progress.
disable-model-invocation: true
user-invocable: true
---

# Session End Skill

## When to use

Invoke at the end of every work session, before closing.

## Steps

1. **Identify what was done**: List tasks completed or partially completed.

1. **Update `status/next-session.md`** with:

   - What was done: summary of this session's work
   - Next steps: what to work on next
   - Blockers: anything preventing progress

1. **Commit and push `status/next-session.md`**:

   ```bash
   git add status/next-session.md
   git commit -m "docs: update next-session.md for session end"
   git push
   ```

   If on a feature branch, push there. If on main, create or reuse a branch for session updates.

1. **Verify clean state**:

   - `git status` — no uncommitted changes left behind
   - If there are uncommitted changes, either commit them or note in blockers

1. **Update MEMORY.md** if any lasting insights were gained (user preferences, project conventions, feedback).

## Template for next-session.md

```markdown
## What was done in Session N
- <completed items>

## Next steps
1. <specific next actions>

## Blockers
- <or "None">
```
