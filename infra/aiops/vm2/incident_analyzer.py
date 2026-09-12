"""Analyze VM1 diagnostics using a local Ollama model on VM2."""

from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen

from vm1_snapshot import get_vm1_snapshot

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = os.environ.get("AIOPS_OLLAMA_MODEL", "qwen2.5:1.5b")


def analyze(snapshot: str) -> str:
    prompt = f"""You are a cautious DevOps incident assistant for an authorized learning lab.
The user explicitly authorizes analysis of this bounded and redacted diagnostic snapshot.
Do the diagnosis; do not refuse merely because the data contains operational logs.
Use only the diagnostic evidence below. Do not invent facts, failures, credentials,
or missing files. A historical Jenkins start/stop message is not an active incident
when the current service status is active and healthy.

Start with exactly one verdict: ACTIVE INCIDENT, NO ACTIVE INCIDENT, or
INSUFFICIENT EVIDENCE. You may select ACTIVE INCIDENT only when the snapshot
contains a current unhealthy/inactive state, an explicit error, or a failed command.
Then return: Evidence (quote exact snapshot facts); Most likely cause with confidence;
Safe read-only next troubleshooting commands. Never recommend downloading or replacing
Jenkins files unless the snapshot explicitly proves they are missing or corrupted.

DIAGNOSTIC SNAPSHOT START
{snapshot}
DIAGNOSTIC SNAPSHOT END
"""
    payload = json.dumps(
        {"model": MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0}}
    ).encode()
    request = Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode())
    except URLError as error:
        raise RuntimeError(f"Local Ollama API is unavailable: {error.reason}") from error
    return body["response"].strip()


if __name__ == "__main__":
    print(analyze(get_vm1_snapshot()))
