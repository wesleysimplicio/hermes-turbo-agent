#!/usr/bin/env python3
"""Install the macOS LaunchAgent for Tota's daily Hermes sync."""

from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LABEL = "com.wesleysimplicio.tota-agent.hermes-daily-update"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
STATE_DIR = Path.home() / ".local" / "state" / "tota-agent" / "hermes-sync"


def _launchctl(*args: str) -> None:
    subprocess.run(["launchctl", *args], check=False)


def _launchd_uid() -> int:
    if not hasattr(os, "getuid"):
        raise SystemExit("This LaunchAgent installer requires macOS or another POSIX runtime.")
    return os.getuid()  # windows-footgun: ok - guarded above; LaunchAgent is macOS-only.


def install(hour: int, minute: int, python_version: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    python_bin = "/opt/homebrew/bin/python3.14"
    if not Path(python_bin).exists():
        python_bin = "/usr/bin/python3"
    program = (
        f"cd {REPO_ROOT} && "
        f"{python_bin} scripts/tota_hermes_daily_update.py "
        f"--repo {REPO_ROOT} --python-version {python_version}"
    )
    payload = {
        "Label": LABEL,
        "ProgramArguments": ["/bin/zsh", "-lc", program],
        "WorkingDirectory": str(REPO_ROOT),
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StandardOutPath": str(STATE_DIR / "launchd.out.log"),
        "StandardErrorPath": str(STATE_DIR / "launchd.err.log"),
        "EnvironmentVariables": {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "TOTA_HOME": str(Path.home() / ".tota"),
            "HERMES_HOME": str(Path.home() / ".tota"),
        },
        "RunAtLoad": False,
    }
    with PLIST_PATH.open("wb") as fh:
        plistlib.dump(payload, fh, sort_keys=False)
    uid = _launchd_uid()
    _launchctl("bootout", f"gui/{uid}", str(PLIST_PATH))
    _launchctl("bootstrap", f"gui/{uid}", str(PLIST_PATH))
    _launchctl("enable", f"gui/{uid}/{LABEL}")
    print(f"Installed LaunchAgent: {PLIST_PATH}")
    print(f"Daily schedule: {hour:02d}:{minute:02d}")
    print(f"Latest report: {STATE_DIR / 'latest.md'}")


def uninstall() -> None:
    uid = _launchd_uid()
    _launchctl("bootout", f"gui/{uid}", str(PLIST_PATH))
    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
    print(f"Removed LaunchAgent: {PLIST_PATH}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hour", type=int, default=6)
    parser.add_argument("--minute", type=int, default=30)
    parser.add_argument("--python-version", default="3.14.5")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    if args.uninstall:
        uninstall()
    else:
        install(args.hour, args.minute, args.python_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
