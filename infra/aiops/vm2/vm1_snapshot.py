"""Read a bounded, read-only diagnostic snapshot from VM1."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

VM1_HOST = os.environ.get("AIOPS_VM1_HOST", "192.168.1.6")
VM1_USER = os.environ.get("AIOPS_VM1_USER", "aiops-reader")
SSH_KEY = Path(
    os.environ.get("AIOPS_SSH_KEY", "~/.ssh/aiops_vm1_ed25519")
).expanduser()
MAX_SNAPSHOT_CHARS = 12_000


def get_vm1_snapshot() -> str:
    """Run VM1's single approved read-only diagnostic command over SSH."""
    if not SSH_KEY.is_file():
        raise RuntimeError(f"AI operations SSH key was not found: {SSH_KEY}")

    command = [
        "ssh",
        "-i",
        str(SSH_KEY),
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "ConnectTimeout=10",
        f"{VM1_USER}@{VM1_HOST}",
        "sudo -n /usr/local/sbin/aiops-diagnostics",
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"VM1 diagnostic snapshot failed: {details}")

    snapshot = result.stdout.strip()
    if len(snapshot) > MAX_SNAPSHOT_CHARS:
        snapshot = (
            snapshot[:MAX_SNAPSHOT_CHARS]
            + "\n\n[Snapshot truncated to 12,000 characters before AI analysis.]"
        )
    return snapshot
