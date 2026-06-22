---
name: memory-first-python
description: Use one focused Parcle plus AST planning packet around Python changes.
---

For every task that may create or modify Python code:

1. Run `../.venv/bin/python ../architecture_cli.py status` and confirm the
   configured project is `hackathon_workspace` in `architectural` mode.
2. Before editing, make exactly one call to
   `architectural-memory.plan_architectural_change` with the request verbatim.
   Do not also call the separate memory-check or whole-graph tools. Bash fallback:
   `../.venv/bin/python ../architecture_cli.py plan "<user request>"`.
3. Read only token-budgeted `recommended_reads`. Treat `neighbor_hints` as
   metadata and expand one file only for an unresolved symbol, unknown contract,
   or failing test.
4. Work only inside the current directory.
5. After verification, call `architectural-memory.sync_architectural_changes`
   with changed Python paths, decision, and rationale.
6. Report focused-vs-full context tokens and final graph totals.

Never read or expose `.env` or API keys.
