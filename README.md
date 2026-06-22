# Architectural Memory Graph

This project gives vibe-coded Python projects a memory. Static AST
analysis supplies ground truth about modules, definitions, and imports; Parcle
stores the intent behind those modules so a future coding prompt can discover
prior decisions before generating conflicting code.

The system keeps those two layers deliberately separate:

- `ast_extractor.py` parses code without executing it.
- `graph_store.py` maintains a directed NetworkX graph of local imports.
- `graph_visualizer.py` creates a dependency-free interactive SVG visualization.
- `memory_client.py` maps project decisions onto Parcle dialogs and searches.
- `token_utils.py` compares a full-repository read with a focused memory call.
- `enter_mcp_server.py` exposes a combined semantic-intent/change-planning tool,
  graph inspection, and post-edit synchronization directly to Enter Code.
- `architecture_cli.py` exposes the identical operations as a dependable Enter
  Bash-tool fallback if a particular Enter version does not inject custom MCP
  tools into the model's active toolset.

## Install

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the focused tests with:

```bash
python -m unittest discover -v
```

## Configure Parcle

The runtime always uses the real Parcle SDK. Provide the API key and project ID:

```bash
export PARCLE_API_KEY="pk_live_..."
export PARCLE_PROJECT_ID="vibe_workspace"
```

The project also loads these values from a local `.env` file. That file is
git-ignored so credentials are not committed. Explicit shell environment
variables take precedence over values in `.env`.

`PARCLE_PROJECT_ID` is the remote memory namespace. Use a new value for each
clean experiment because deleting local code does not erase remote Parcle
sessions.

The repository name is intentionally used as Parcle's `user_id`, because the
current Parcle primitives do not expose native project or module scopes.

## Use with Enter Pro

Install the Enter Code CLI and project dependencies, then launch it from this
repository:

```bash
npm install -g @enter-pro/enter-code
pip install -r requirements.txt
enter
```

The committed `.enter/settings.json` registers the local architectural-memory
MCP server. In treatment mode, the project skill makes one planning call that
combines Parcle's semantic intent with ranked AST modules and their one-hop
dependency neighborhood. Only the top token-budgeted files are recommended for
reading; neighboring modules remain compact metadata hints and are promoted one
at a time only for unresolved symbols, contracts, or failing tests. After editing, Enter calls the sync tool to
record the decision and rebuild both graph artifacts. Inside Enter, `/mcp` shows
the connection and `/skills` shows the active workflow.

For a quick, non-mutating integration check from Enter or a regular terminal:

```bash
.venv/bin/python architecture_cli.py graph
```

The live Enter workflow targets the directory configured by
`ARCH_MEMORY_PROJECT_ROOT` in `.env`—currently `vibe_workspace`. Parcle uses the
directory name as its isolated project ID.

## Vibe coding

Launch Enter from this repository and provide an ordinary product request:

```bash
enter
```

The project Skill automatically checks Parcle before Enter edits Python code and
syncs changed modules, decisions, and graph artifacts after verification. You do
not need to mention the Skill or architectural-memory workflow in each prompt.

The combined planner is also available without Enter:

```bash
.venv/bin/python architecture_cli.py plan "Add category spending summaries"
```

Its response reports likely change targets, existing-capability evidence,
initial files to read, metadata-only neighbors, and an honest token comparison:
compact packet plus recommended source versus the full repository. Defaults are
three initial files and a 1,500-source-token budget.

## Hackathon demo

Launch the visual showcase:

```bash
.venv/bin/python demo_app.py
```

Open `http://127.0.0.1:8765`. **Replay sample** is deterministic and consumes no
credits. **Analyze next change** runs only the combined Parcle + AST planner.
The dashboard highlights semantic memory, duplicate-capability evidence, ranked
targets, progressive reads, graph neighbors, and honest context savings.

The dashboard is an observer, not an agent runner. Copy its displayed command
into a terminal and use Enter normally inside the isolated
`hackathon_workspace`. The dashboard polls the workspace, animates nodes and
imports after every Python edit, highlights files touched by repeated prompts,
and reads actual provider usage from Enter's persisted session. This observer
adds zero Enter-token overhead. Override the fresh Parcle namespace with:

```bash
export HACKATHON_PARCLE_PROJECT_ID=hackathon_demo_fresh_run
```

## A/B test our contribution

Parcle stays active in both conditions. Run the architectural-memory treatment:

```bash
ARCH_MEMORY_PROJECT_ROOT=vibe_workspace \
PARCLE_PROJECT_ID=PARCLE_PROJECT_ID_1 \
ARCH_MEMORY_MODE=architectural \
enter
```

Run the same prompts with raw, unstructured Parcle memory:

```bash
ARCH_MEMORY_PROJECT_ROOT=vibe_workspace_2 \
PARCLE_PROJECT_ID=PARCLE_PROJECT_ID_2 \
ARCH_MEMORY_MODE=raw_parcle \
enter
```

The treatment stores module, decision, and rationale records and supplies the AST
graph before generation. The control stores generic prompt/response history in
Parcle and receives no AST graph during planning. Both conditions still sync a
post-run graph so outcomes can be measured consistently. After identical prompts:

```bash
.venv/bin/python compare_workspaces.py
.venv/bin/python compare_workspaces.py --prompt "Add spending threshold alerts"
```

The comparison script also reads Enter's provider-reported token fields from
the newest session persisted for each workspace under `~/.enter/projects/`.
It reports uncached input, cache creation, cache reads, output, model calls,
and total tokens. If automatic selection is ambiguous, pin the two sessions:

```bash
.venv/bin/python compare_workspaces.py \
  --contribution-session <session-id> \
  --raw-parcle-session <session-id>
```

Use the same number of prompts and the same session pattern in both conditions.
The report warns when persisted prompt counts differ. Provider token totals are
exact model-usage measurements, but they are not Enter-credit totals because
cached and output tokens may have different billing weights.
