# my-setup.ps1 — Windows dispatcher to my-launcher.py for markitdown-mcp daemon management.
#
# Usage:
#   .\my-setup.ps1 install              # create .venv, install packages, register daemon
#   .\my-setup.ps1 uninstall            # stop and remove daemon registration
#   .\my-setup.ps1 start                # start registered daemon
#   .\my-setup.ps1 stop                 # stop running daemon
#   .\my-setup.ps1 status               # show daemon status
#
# Options:
#   -Port <N>     HTTP port (default: 8940)
#   -Host <H>     Bind host (default: 127.0.0.1)
#
# Requires: uv  (https://docs.astral.sh/uv/)
#
# If script execution is blocked, run once as Administrator:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("install", "uninstall", "start", "stop", "status")]
    [string]$Command,

    [int]$Port = 8940,
    [string]$BindHost = "127.0.0.1"
)

$RepoDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Launcher = Join-Path $RepoDir "my-launcher.py"

# Build forwarded argument list
$fwd = @($Command)
if ($Port    -ne 8940)        { $fwd += "--port", $Port }
if ($BindHost -ne "127.0.0.1") { $fwd += "--host", $BindHost }

# ---------------------------------------------------------------------------
# Prefer uv run — bundles its own Python, no system install required
# ---------------------------------------------------------------------------
if (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv run --python 3.12 $Launcher @fwd
    exit $LASTEXITCODE
}

# ---------------------------------------------------------------------------
# Fallback: find Python 3.10+ on PATH
# ---------------------------------------------------------------------------
$Python = $null
foreach ($candidate in @("python3.12", "python3.11", "python3.10", "python3", "python")) {
    try {
        $ok = & $candidate -c "import sys; print(sys.version_info >= (3,10))" 2>$null
        if ($ok -eq "True") { $Python = $candidate; break }
    } catch {}
}

if (-not $Python) {
    Write-Error "ERROR: Python 3.10+ not found and uv is not installed."
    Write-Error "       Install uv from https://docs.astral.sh/uv/ and retry."
    exit 1
}

& $Python $Launcher @fwd
exit $LASTEXITCODE
