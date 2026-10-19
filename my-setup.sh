#!/usr/bin/env bash
# my-setup.sh — dispatcher to my-launcher.py for markitdown-mcp daemon management.
#
# Usage:
#   ./my-setup.sh install              # create .venv, install packages, register daemon
#   ./my-setup.sh uninstall            # stop and remove daemon registration
#   ./my-setup.sh start                # start registered daemon
#   ./my-setup.sh stop                 # stop running daemon
#   ./my-setup.sh status               # show daemon status
#
# Options forwarded to my-launcher.py:
#   --port N     HTTP port (default: 8940)
#   --host H     Bind host (default: 127.0.0.1)
#
# Requires: uv  (https://docs.astral.sh/uv/)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
LAUNCHER="$REPO_DIR/my-launcher.py"

# ---------------------------------------------------------------------------
# Prefer uv run so my-launcher.py gets a clean Python 3.12 without needing
# a pre-existing system Python or an activated venv.
# ---------------------------------------------------------------------------
if command -v uv >/dev/null 2>&1; then
    exec uv run --python 3.12 "$LAUNCHER" "$@"
fi

# ---------------------------------------------------------------------------
# Fallback: find Python 3.10+ on PATH
# ---------------------------------------------------------------------------
PYTHON=""
for candidate in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        ok=$("$candidate" -c "import sys; print(sys.version_info >= (3,10))" 2>/dev/null || echo "False")
        if [[ "$ok" == "True" ]]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    echo "ERROR: Python 3.10+ not found and uv is not installed."
    echo "       Install uv from https://docs.astral.sh/uv/ and retry."
    exit 1
fi

exec "$PYTHON" "$LAUNCHER" "$@"
