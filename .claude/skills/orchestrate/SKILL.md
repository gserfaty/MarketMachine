---
name: orchestrate
description: Run the planner → developer → evaluator loop to build or extend the michiganmen app. Use when asked to build, extend, or fix the app.
---

Orchestrate the three project agents. Pass work through files, not transcripts, to save tokens.

1. Spawn `planner` with the user's goal (or "fix the failures in docs/EVAL.md"). Wait for `PLAN READY`.
2. Spawn `developer`: "Implement docs/PLAN.md." Wait for `DEV DONE`.
3. Spawn `evaluator`: "Evaluate against docs/PLAN.md." Read only its VERDICT line.
4. On `VERDICT: FAIL`, spawn `developer` again: "Fix the items in docs/EVAL.md." Then re-run the evaluator. Stop after 3 fix rounds and report what still fails.
5. On `VERDICT: PASS`, summarize for the user in a few lines. Commit only if the user asked; never push without asking.

Do not read the full source yourself unless an agent is stuck; the agents' short replies and docs/EVAL.md are enough to steer.
