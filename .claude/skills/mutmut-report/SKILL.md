---
name: mutmut-report
description: Analyze mutmut surviving mutants for a Python project and produce an actionable report
argument-hint: "--module MODULE --max N"
user-invocable: true
---

# mutmut Survivors Report

Run the analysis script, then report findings.

## Step 1 — Run the script

Run from the project root so `mutmut results` can find the `mutants/`
directory. Pass any user flags (e.g. `--module validate`, `--max 30`)
through as `$ARGUMENTS`:

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel) && cd "$PROJECT_ROOT" && python "$PROJECT_ROOT/.claude/skills/mutmut-report/analyze_mutmut.py" $ARGUMENTS
```

## Step 2 — Present results

After running, report concisely:
1. Which modules have **Real gaps** and how many
2. For each real gap: what the fix is (tighter assertion, missing test case, etc.)
3. Which are **Equivalent** or **Untestable** — just confirm these are accepted, no detail needed
4. Suggest the top 2-3 fixes to implement next

Do not re-explain what mutmut is. Just report findings and fixes.