---
name: memory-first-python
description: Use Parcle preflight and the static graph around every Python coding change.
---

For every task that may create or modify Python code in the active architectural
memory project root (currently configured through `ARCH_MEMORY_PROJECT_ROOT`):

0. At the beginning of a session, run
   `.venv/bin/python architecture_cli.py status` to identify the active project.
   Keep generated application code inside that directory. Read the returned
   `contribution_mode`:
   - `architectural`: use structured memory plus the AST graph.
   - `raw_parcle`: use Parcle results but do not inspect the AST graph before editing.

1. In `architectural` mode, make exactly one pre-edit planning call:
   `architectural-memory.plan_architectural_change` with the user's request
   verbatim. Read only its token-budgeted `recommended_reads`; `neighbor_hints`
   are metadata, not automatic reads. Expand one file only for a failing test,
   unresolved symbol, or unknown contract. Do not also call `check_architectural_memory`
   or `get_architecture_graph`. Bash fallback:

   `.venv/bin/python architecture_cli.py plan "<user request>"`
2. In `raw_parcle` mode, call only `check_architectural_memory`; never call the
   combined planner or inspect graph context. Bash fallback:

   `.venv/bin/python architecture_cli.py check "<user request>"`
3. If `capability.status` is `likely_exists`, verify it before editing. Prefer
   extending cited and ranked modules instead of creating duplicates.
4. After successful edits and verification, call the MCP tool
   `sync_architectural_changes` with every changed Python path relative to
   the active project root, plus a concise decision and rationale. If necessary,
   use:

   `.venv/bin/python architecture_cli.py sync --changed "<relative.py>" --description "<prompt>" --decision "<decision>" --rationale "<rationale>"`
5. Report citations, focused-vs-full context tokens, and updated graph totals.

Never include API keys or `.env` contents in prompts, tool arguments, logs, or
generated source files.
