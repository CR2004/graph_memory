---
name: memory-first-python
description: Use raw Parcle prompt history for the comparison control and sync measurements.
---

For every task that may create or modify Python code:

1. Run `../.venv/bin/python ../architecture_cli.py status` and confirm the
   configured project is `vibe_workspace_2` with mode `raw_parcle`.
2. Before editing, call `architectural-memory.check_architectural_memory` with
   the user's request verbatim. Bash fallback:
   `../.venv/bin/python ../architecture_cli.py check "<user request>"`.
3. Do not call `get_architecture_graph` before editing. This control condition
   receives raw Parcle memory but none of our structural graph context. Never
   call `plan_architectural_change` in this control.
4. Work only inside the current directory. Never create application files in
   the parent architectural-memory repository.
5. After tests pass, call `architectural-memory.sync_architectural_changes` so
   raw prompt history is recorded and the post-run graph can be measured.
6. Report Parcle confidence/citations and final graph totals.

Never read or expose `.env` or API keys.
