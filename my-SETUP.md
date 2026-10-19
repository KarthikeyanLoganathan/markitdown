# MarkItDown MCP — Quick Setup

Runs the [markitdown-mcp](packages/markitdown-mcp) HTTP MCP server as a **persistent background daemon** that auto-starts on login.

Once running, any MCP client can connect via:

| Transport | URL |
|-----------|-----|
| Streamable HTTP | `http://127.0.0.1:8940/mcp` |
| SSE | `http://127.0.0.1:8940/sse` |

The server exposes one tool — `convert_to_markdown(uri)` — which accepts any `http:`, `https:`, `file:`, or `data:` URI and returns Markdown.

---

## Prerequisites

Install **uv** (handles Python + package management — no separate Python install needed):

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## macOS

```bash
# 1 — clone (if you haven't already)
git clone https://github.tools.sap/I014309/microsoft-markitdown.git
cd microsoft-markitdown

# 2 — install: creates .venv, installs packages, registers launchd daemon
./my-setup.sh install

# Day-to-day
./my-setup.sh status       # is it running?
./my-setup.sh stop
./my-setup.sh start
./my-setup.sh uninstall    # remove daemon (leaves .venv)
```

The daemon registers under `com.markitdown.mcp` in `~/Library/LaunchAgents/` and appears in
**System Settings › General › Login Items**. Logs stream to `/tmp/markitdown-mcp.log`.

```bash
tail -f /tmp/markitdown-mcp.log
```

---

## Windows

Open **PowerShell** (no admin required for Task Scheduler; NSSM install needs admin):

```powershell
# Allow local scripts if not already set (one-time)
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 1 — clone
git clone https://github.tools.sap/I014309/microsoft-markitdown.git
cd microsoft-markitdown

# 2 — install: creates .venv, installs packages, registers scheduled task / NSSM service
.\my-setup.ps1 install

# Day-to-day
.\my-setup.ps1 status
.\my-setup.ps1 stop
.\my-setup.ps1 start
.\my-setup.ps1 uninstall
```

**Backend selection** (automatic):

| Available | Backend used |
|-----------|--------------|
| [NSSM](https://nssm.cc/) on PATH | Windows Service (survives logoff, visible in `services.msc`) |
| No NSSM | Task Scheduler `ONLOGON` task (user session only, no admin needed) |

Logs are written to `C:\Temp\markitdown-mcp.log`.

---

## Custom port or host

```bash
# macOS / Linux
./my-setup.sh install --port 9000 --host 0.0.0.0

# Windows
.\my-setup.ps1 install -Port 9000 -BindHost 0.0.0.0
```

> **Security note**: binding to `0.0.0.0` exposes the server on the network.
> The server has no authentication. Use the default `127.0.0.1` unless you understand the implications.

---

## All capabilities

`markitdown[all]` is installed automatically. Supported conversions:

| Format | Notes |
|--------|-------|
| PDF | Built-in extraction |
| Word (`.docx`) | Built-in |
| PowerPoint (`.pptx`) | Built-in |
| Excel (`.xlsx`, `.xls`) | Built-in |
| Images | EXIF metadata + optional LLM description |
| Audio | EXIF metadata + speech transcription |
| HTML | Built-in |
| CSV / JSON / XML | Built-in |
| ZIP | Iterates over contents |
| YouTube URLs | Transcript extraction |
| EPub | Built-in |
| Azure Document Intelligence | Pass `--docintel-endpoint` or `MARKITDOWN_DOCINTEL_ENDPOINT` |
| Azure Content Understanding | Pass `--cu-endpoint` or `MARKITDOWN_CU_ENDPOINT` |

Plugins (e.g. `markitdown-ocr`) can be enabled by setting `MARKITDOWN_ENABLE_PLUGINS=true`
in the environment before starting the daemon.
