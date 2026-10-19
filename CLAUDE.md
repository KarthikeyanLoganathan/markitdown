# CLAUDE.md — Project instructions for Claude Code

## Project overview

This is a local fork of [microsoft/markitdown](https://github.com/microsoft/markitdown).
Work happens on the `my-enhancements` branch. All custom additions live at the repo root
and must not touch the upstream package structure under `packages/`.

## Core rules

- **Pure additions only.** Never edit files under `packages/`, `Dockerfile`, `README.md`,
  `CODE_OF_CONDUCT.md`, `LICENSE`, `SECURITY.md`, or `SUPPORT.md`. Create new files at the
  repo root instead.
- **No changes to existing project structure.** If a capability needs adjustment, add a new
  file; do not patch upstream source.

## Custom tooling (my-* files)

| File | Purpose |
|------|---------|
| `my-setup.sh` | macOS / Linux shell dispatcher — primary user entry point |
| `my-setup.ps1` | Windows PowerShell dispatcher — equivalent entry point for Windows |
| `my-launcher.py` | Platform-aware daemon manager (install / uninstall / start / stop / status) |
| `my-SETUP.md` | User-facing quick-start guide for macOS and Windows |

### How they work together

`my-setup.sh` (macOS/Linux) and `my-setup.ps1` (Windows) both find `uv` (preferred) or a
system Python 3.10+ and forward all arguments to `my-launcher.py`. Never modify the
dispatcher scripts; extend `my-launcher.py` instead.

### my-launcher.py design

- Uses `uv venv --python=3.12 .venv` for the local venv (never system pip).
- Installs via `uv pip install -e packages/markitdown[all] -e packages/markitdown-mcp`.
- Launches `markitdown-mcp --http --host 127.0.0.1 --port 8940` as the daemon process.
- Platform dispatch: macOS → launchd, Windows → NSSM or Task Scheduler, Linux → systemd user.

### Key constants (my-launcher.py top of file)

- `DEFAULT_PORT = 8940`
- `DEFAULT_HOST = "127.0.0.1"`
- `LABEL = "com.markitdown.mcp"` (launchd label / service name stem)
- `VENV_DIR = REPO_DIR / ".venv"`

## MCP server quick reference

Once the daemon is running:

| Transport | URL |
|-----------|-----|
| Streamable HTTP | `http://127.0.0.1:8940/mcp` |
| SSE | `http://127.0.0.1:8940/sse` |

Implemented in `packages/markitdown-mcp/src/markitdown_mcp/__main__.py`:
- `convert_to_markdown(uri)` tool (L20) — accepts `http:`, `https:`, `file:`, `data:` URIs
- `create_starlette_app()` (L58) — mounts both Streamable HTTP and SSE routes
- `main()` (L83) — parses `--http --host --port` and calls `uvicorn.run()`

## Knowledge graph

A graphify knowledge graph exists at `graphify-out/graph.json` (1792 nodes).
**Always query it before making code decisions:**

```
graphify query "<question>"
graphify explain "<symbol>"
graphify path "<A>" "<B>"
```

The graph is the authoritative map of this codebase. Do not rebuild it unless asked.

## uv usage

All Python operations must use `uv`:

```bash
uv venv --python=3.12 .venv          # create venv
uv pip install -e packages/markitdown[all]  # install from local source
uv run --python 3.12 script.py       # run a one-off script
```

Never use bare `pip install` or `python -m pip install`.

## Workflow

1. Query the graphify graph to understand structure before writing code.
2. Add new files at the repo root; never modify files under `packages/`.
3. Test with `./my-setup.sh status` (macOS/Linux) or `.\my-setup.ps1 status` (Windows) after changes.
