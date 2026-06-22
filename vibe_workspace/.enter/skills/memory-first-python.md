---
name: memory-first-python
description: Use Parcle and architectural graph context around every Python coding change.
---

For every task that may create or modify Python code:

1. Run `../.venv/bin/python ../architecture_cli.py status` to identify the
   experiment mode and configured project.
2. Before editing, make exactly one planning call:
   `architectural-memory.plan_architectural_change` with the user's request
   verbatim. Do not also call `check_architectural_memory` or
   `get_architecture_graph`. Bash fallback:
   `../.venv/bin/python ../architecture_cli.py plan "<user request>"`.
3. Read only the token-budgeted `recommended_reads`. Treat `neighbor_hints` as
   metadata, not automatic reads. Expand one file only for a failing test,
   unresolved symbol, or unknown contract. If `capability.status` is
   `likely_exists`, verify the capability before editing.
4. Work only inside the current directory. Never create application files in
   the parent architectural-memory repository.
5. After tests pass, call `architectural-memory.sync_architectural_changes`
   with paths relative to the current directory plus a concise decision and
   rationale. Bash fallback:
   `../.venv/bin/python ../architecture_cli.py sync ...`.
6. Report Parcle citations, focused-vs-full context tokens, and graph totals.

Never read or expose `.env` or API keys.
