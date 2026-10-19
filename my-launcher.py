#!/usr/bin/env python3
"""
my-launcher.py — Platform-aware daemon manager for markitdown-mcp HTTP MCP server.

Usage:
    python my-launcher.py <command> [options]

Commands:
    install     Create .venv via uv, install packages, register OS daemon (auto-start on login)
    uninstall   Stop and remove OS daemon registration (leaves .venv intact)
    start       Start the daemon (must be installed first)
    stop        Stop the running daemon
    status      Show whether the daemon is running

Options:
    --port N    Port for HTTP MCP server (default: 8940)
    --host H    Host to bind (default: 127.0.0.1)

Platform backends:
    macOS    launchd (~/Library/LaunchAgents/com.markitdown.mcp.plist)
    Windows  Task Scheduler (schtasks) with ONLOGON trigger; NSSM if present
    Linux    systemd user service (~/.config/systemd/user/markitdown-mcp.service)

MCP endpoints once running:
    Streamable HTTP : http://<host>:<port>/mcp
    SSE             : http://<host>:<port>/sse
"""

import argparse
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_PORT = 8940
DEFAULT_HOST = "127.0.0.1"
LABEL = "com.markitdown.mcp"
LOG_FILE = "/tmp/markitdown-mcp.log"          # macOS / Linux
WIN_LOG_FILE = r"C:\Temp\markitdown-mcp.log"  # Windows
WIN_TASK_NAME = "MarkItDown MCP Server"

REPO_DIR = Path(__file__).parent.resolve()
VENV_DIR = REPO_DIR / ".venv"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _venv_bin(name: str) -> Path:
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / (name + ".exe" if not name.endswith(".exe") else name)
    return VENV_DIR / "bin" / name


def _require_uv() -> str:
    result = subprocess.run(["which", "uv"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    # Windows
    result = subprocess.run(["where", "uv"], capture_output=True, text=True, shell=True)
    if result.returncode == 0:
        return result.stdout.strip().splitlines()[0]
    print("ERROR: uv not found. Install from https://docs.astral.sh/uv/")
    sys.exit(1)


def _uv(*args: str, **kwargs) -> subprocess.CompletedProcess:
    uv = _require_uv()
    return subprocess.run([uv, *args], **kwargs)


# ---------------------------------------------------------------------------
# Install / sync
# ---------------------------------------------------------------------------


def cmd_install(args) -> None:
    port: int = args.port
    host: str = args.host

    # 1. Create local venv (skip if one already exists)
    if _venv_bin("python").exists():
        print(f"Using existing virtual environment at {VENV_DIR}")
    else:
        print(f"Creating virtual environment at {VENV_DIR} ...")
        _uv("venv", "--python=3.12", str(VENV_DIR), cwd=str(REPO_DIR), check=True)

    # 2. Install markitdown[all] and markitdown-mcp from local source
    python_bin = _venv_bin("python")
    print("Installing markitdown[all] and markitdown-mcp ...")
    _uv(
        "pip", "install",
        "--python", str(python_bin),
        "-e", f"{REPO_DIR}/packages/markitdown[all]",
        "-e", f"{REPO_DIR}/packages/markitdown-mcp",
        check=True,
    )

    # 3. Register platform daemon
    _dispatch_install(port, host)


# ---------------------------------------------------------------------------
# Platform dispatch
# ---------------------------------------------------------------------------


def _dispatch_install(port: int, host: str) -> None:
    system = platform.system()
    if system == "Darwin":
        _mac_install(port, host)
    elif system == "Windows":
        _win_install(port, host)
    else:
        _linux_install(port, host)


def cmd_uninstall(args) -> None:
    system = platform.system()
    if system == "Darwin":
        _mac_uninstall()
    elif system == "Windows":
        _win_uninstall()
    else:
        _linux_uninstall()


def cmd_start(args) -> None:
    system = platform.system()
    if system == "Darwin":
        _mac_start()
    elif system == "Windows":
        _win_start()
    else:
        _linux_start()


def cmd_stop(args) -> None:
    system = platform.system()
    if system == "Darwin":
        _mac_stop()
    elif system == "Windows":
        _win_stop()
    else:
        _linux_stop()


def cmd_status(args) -> None:
    system = platform.system()
    if system == "Darwin":
        _mac_status(args.port, args.host)
    elif system == "Windows":
        _win_status(args.port, args.host)
    else:
        _linux_status(args.port, args.host)


# ---------------------------------------------------------------------------
# macOS — launchd
# ---------------------------------------------------------------------------


def _mac_plist() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _mac_uid_domain() -> str:
    return f"gui/{os.getuid()}"


def _mac_is_loaded() -> bool:
    r = subprocess.run(
        ["launchctl", "print", f"{_mac_uid_domain()}/{LABEL}"],
        capture_output=True,
    )
    return r.returncode == 0


def _mac_bootout() -> None:
    plist = _mac_plist()
    domain = _mac_uid_domain()
    subprocess.run(["launchctl", "bootout", f"{domain}/{LABEL}"], capture_output=True)
    subprocess.run(["launchctl", "bootout", domain, str(plist)], capture_output=True)
    time.sleep(1)


def _mac_install(port: int, host: str) -> None:
    exec_path = _venv_bin("markitdown-mcp")
    if not exec_path.exists():
        print(f"ERROR: {exec_path} not found after install.")
        sys.exit(1)

    # Locate uv directory for PATH in plist
    uv_result = subprocess.run(["which", "uv"], capture_output=True, text=True)
    uv_dir = str(Path(uv_result.stdout.strip()).parent) if uv_result.returncode == 0 else "/usr/local/bin"
    home = Path.home()

    plist = _mac_plist()
    plist.parent.mkdir(parents=True, exist_ok=True)

    if _mac_is_loaded():
        print("Stopping existing daemon ...")
        _mac_bootout()

    plist.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exec_path}</string>
        <string>--http</string>
        <string>--host</string>
        <string>{host}</string>
        <string>--port</string>
        <string>{port}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{REPO_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{LOG_FILE}</string>
    <key>StandardErrorPath</key>
    <string>{LOG_FILE}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{uv_dir}:/usr/local/bin:/usr/bin:/bin:{home / '.local/bin'}</string>
        <key>HOME</key>
        <string>{home}</string>
    </dict>
</dict>
</plist>
""",
        encoding="utf-8",
    )

    subprocess.run(
        ["launchctl", "bootstrap", _mac_uid_domain(), str(plist)],
        check=True,
    )
    time.sleep(2)

    if _mac_is_loaded():
        print(f"✓ Daemon installed and running")
        print(f"  Streamable HTTP : http://{host}:{port}/mcp")
        print(f"  SSE             : http://{host}:{port}/sse")
        print(f"  Logs            : tail -f {LOG_FILE}")
        print(f"  Login Items     : System Settings › General › Login Items")
    else:
        print(f"✗ Daemon failed to start. Check: tail -f {LOG_FILE}")
        sys.exit(1)


def _mac_uninstall() -> None:
    plist = _mac_plist()
    if _mac_is_loaded():
        print("Stopping and unregistering daemon ...")
        _mac_bootout()
    if plist.exists():
        plist.unlink()
        print(f"Removed: {plist}")
    print("✓ markitdown-mcp daemon uninstalled.")
    print(f"  Log at {LOG_FILE} was left in place.")


def _mac_start() -> None:
    plist = _mac_plist()
    if not plist.exists():
        print("ERROR: Daemon not installed. Run: my-setup.sh install")
        sys.exit(1)
    if _mac_is_loaded():
        print("Daemon is already running.")
        return
    subprocess.run(
        ["launchctl", "bootstrap", _mac_uid_domain(), str(plist)],
        check=True,
    )
    print("✓ Daemon started.")


def _mac_stop() -> None:
    if not _mac_is_loaded():
        print("Daemon is not running.")
        return
    _mac_bootout()
    print("✓ Daemon stopped.")


def _mac_status(port: int, host: str) -> None:
    if _mac_is_loaded():
        print(f"✓ Running — http://{host}:{port}/mcp")
    else:
        print("✗ Not running")


# ---------------------------------------------------------------------------
# Windows — Task Scheduler (schtasks) / NSSM
# ---------------------------------------------------------------------------


def _win_nssm() -> str | None:
    r = subprocess.run(["where", "nssm"], capture_output=True, text=True, shell=True)
    if r.returncode == 0:
        return r.stdout.strip().splitlines()[0]
    return None


def _win_install(port: int, host: str) -> None:
    exec_path = _venv_bin("markitdown-mcp")
    if not exec_path.exists():
        print(f"ERROR: {exec_path} not found after install.")
        sys.exit(1)

    Path(WIN_LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

    nssm = _win_nssm()
    if nssm:
        _win_install_nssm(nssm, exec_path, port, host)
    else:
        _win_install_schtasks(exec_path, port, host)


def _win_install_nssm(nssm: str, exec_path: Path, port: int, host: str) -> None:
    svc = WIN_TASK_NAME
    subprocess.run(
        [nssm, "install", svc, str(exec_path),
         "--http", "--host", host, "--port", str(port)],
        check=True,
    )
    subprocess.run([nssm, "set", svc, "AppStdout", WIN_LOG_FILE], check=True)
    subprocess.run([nssm, "set", svc, "AppStderr", WIN_LOG_FILE], check=True)
    subprocess.run([nssm, "start", svc], check=True)
    print(f"✓ Windows service '{svc}' installed via NSSM and started.")
    print(f"  Streamable HTTP : http://{host}:{port}/mcp")


def _win_install_schtasks(exec_path: Path, port: int, host: str) -> None:
    cmd = f'"{exec_path}" --http --host {host} --port {port}'
    subprocess.run(
        [
            "schtasks", "/create",
            "/tn", WIN_TASK_NAME,
            "/tr", cmd,
            "/sc", "ONLOGON",
            "/f",
            "/rl", "HIGHEST",
        ],
        check=True,
        shell=True,
    )
    subprocess.run(["schtasks", "/run", "/tn", WIN_TASK_NAME], check=True, shell=True)
    print(f"✓ Task Scheduler task '{WIN_TASK_NAME}' created and started.")
    print(f"  Streamable HTTP : http://{host}:{port}/mcp")


def _win_uninstall() -> None:
    nssm = _win_nssm()
    if nssm:
        subprocess.run([nssm, "stop", WIN_TASK_NAME], capture_output=True)
        subprocess.run([nssm, "remove", WIN_TASK_NAME, "confirm"], check=True)
    else:
        subprocess.run(["schtasks", "/end", "/tn", WIN_TASK_NAME], capture_output=True, shell=True)
        subprocess.run(
            ["schtasks", "/delete", "/tn", WIN_TASK_NAME, "/f"],
            check=True,
            shell=True,
        )
    print(f"✓ '{WIN_TASK_NAME}' removed.")


def _win_start() -> None:
    nssm = _win_nssm()
    if nssm:
        subprocess.run([nssm, "start", WIN_TASK_NAME], check=True)
    else:
        subprocess.run(["schtasks", "/run", "/tn", WIN_TASK_NAME], check=True, shell=True)
    print("✓ Started.")


def _win_stop() -> None:
    nssm = _win_nssm()
    if nssm:
        subprocess.run([nssm, "stop", WIN_TASK_NAME], check=True)
    else:
        subprocess.run(["schtasks", "/end", "/tn", WIN_TASK_NAME], check=True, shell=True)
    print("✓ Stopped.")


def _win_status(port: int, host: str) -> None:
    nssm = _win_nssm()
    if nssm:
        r = subprocess.run([nssm, "status", WIN_TASK_NAME], capture_output=True, text=True)
        running = "SERVICE_RUNNING" in r.stdout
    else:
        r = subprocess.run(
            ["schtasks", "/query", "/tn", WIN_TASK_NAME, "/fo", "LIST"],
            capture_output=True, text=True, shell=True,
        )
        running = "Running" in r.stdout
    if running:
        print(f"✓ Running — http://{host}:{port}/mcp")
    else:
        print("✗ Not running")


# ---------------------------------------------------------------------------
# Linux — systemd user service
# ---------------------------------------------------------------------------


def _linux_svc_file() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / "markitdown-mcp.service"


def _linux_install(port: int, host: str) -> None:
    exec_path = _venv_bin("markitdown-mcp")
    if not exec_path.exists():
        print(f"ERROR: {exec_path} not found after install.")
        sys.exit(1)

    svc = _linux_svc_file()
    svc.parent.mkdir(parents=True, exist_ok=True)
    svc.write_text(
        f"""[Unit]
Description=MarkItDown MCP HTTP Server
After=network.target

[Service]
Type=simple
ExecStart={exec_path} --http --host {host} --port {port}
WorkingDirectory={REPO_DIR}
Restart=on-failure
RestartSec=5
StandardOutput=append:{LOG_FILE}
StandardError=append:{LOG_FILE}

[Install]
WantedBy=default.target
""",
        encoding="utf-8",
    )
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", "markitdown-mcp"], check=True)
    print("✓ systemd user service enabled and started.")
    print(f"  Streamable HTTP : http://{host}:{port}/mcp")
    print(f"  SSE             : http://{host}:{port}/sse")
    print(f"  Logs            : journalctl --user -u markitdown-mcp -f")


def _linux_uninstall() -> None:
    subprocess.run(
        ["systemctl", "--user", "disable", "--now", "markitdown-mcp"],
        capture_output=True,
    )
    svc = _linux_svc_file()
    if svc.exists():
        svc.unlink()
    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
    print("✓ markitdown-mcp service removed.")


def _linux_start() -> None:
    subprocess.run(["systemctl", "--user", "start", "markitdown-mcp"], check=True)
    print("✓ Service started.")


def _linux_stop() -> None:
    subprocess.run(["systemctl", "--user", "stop", "markitdown-mcp"], check=True)
    print("✓ Service stopped.")


def _linux_status(port: int, host: str) -> None:
    r = subprocess.run(
        ["systemctl", "--user", "is-active", "markitdown-mcp"],
        capture_output=True,
        text=True,
    )
    if r.stdout.strip() == "active":
        print(f"✓ Running — http://{host}:{port}/mcp")
    else:
        print("✗ Not running")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

COMMANDS = {
    "install": cmd_install,
    "uninstall": cmd_uninstall,
    "start": cmd_start,
    "stop": cmd_stop,
    "status": cmd_status,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage markitdown-mcp HTTP MCP server daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("command", choices=list(COMMANDS), help="Action to perform")
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"HTTP port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--host", default=DEFAULT_HOST,
        help=f"Bind host (default: {DEFAULT_HOST})",
    )
    args = parser.parse_args()
    COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
