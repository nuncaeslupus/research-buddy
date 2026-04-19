---
name: mutmut-report
description: Analyze mutmut surviving mutants for a Python project and produce an actionable report
argument-hint: "--module MODULE --max N"
user-invocable: true
---

# mutmut Survivors Report

Run the analysis script, then report findings.

## Step 1 — Run the script

Invoke from the project directory that owns the `mutants/` workspace (i.e. the one where `mutmut run` was executed). `$ARGUMENTS` is forwarded verbatim to the script — pass flags like `--module validate`, `--max 20`, or `--venv .venv`.

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel) && python "$PROJECT_ROOT/.claude/skills/mutmut-report/analyze_mutmut.py" $ARGUMENTS
```

If the target project is a different checkout, `cd` to it first, then run the command above — `$PROJECT_ROOT` still resolves via this repo because the script is launched by absolute path.

## Step 2 — Present results

After running, report concisely:
1. Which modules have **Real gaps** and how many
2. For each real gap: what the fix is (tighter assertion, missing test case, etc.)
3. Which are **Equivalent** or **Untestable** — just confirm these are accepted, no detail needed
4. Suggest the top 2-3 fixes to implement next

Do not re-explain what mutmut is. Just report findings and fixes.