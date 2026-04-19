---
name: mutmut-report
description: Analyze mutmut surviving mutants for a Python project and produce an actionable report
argument-hint: "--module MODULE --max N"
user-invocable: true
---

# mutmut Survivors Report

Run the analysis script, then report findings.

## Step 1 — Run the script

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel) && cd ${ARGUMENTS:-"."} && python "$PROJECT_ROOT/.claude/skills/mutmut-report/analyze_mutmut.py"
```

Any extra flags in `$ARGUMENTS` (e.g. `--module validate`) are passed through automatically since the `cd` only consumes the first token and the rest go to the script.

Actually: parse `$ARGUMENTS` yourself — the first token is the directory, remaining tokens are script flags.

## Step 2 — Present results

After running, report concisely:
1. Which modules have **Real gaps** and how many
2. For each real gap: what the fix is (tighter assertion, missing test case, etc.)
3. Which are **Equivalent** or **Untestable** — just confirm these are accepted, no detail needed
4. Suggest the top 2-3 fixes to implement next

Do not re-explain what mutmut is. Just report findings and fixes.