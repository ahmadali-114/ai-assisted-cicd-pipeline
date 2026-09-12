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
    prompt = f"""You are a cautious DevOps incident assistant.
Use only the diagnostic evidence below. Do not invent facts or credentials.
Return these sections: Incident summary; Evidence; Most likely cause with confidence;
Safe next troubleshooting commands. If evidence is insufficient, say so clearly.

DIAGNOSTIC SNAPSHOT START
{snapshot}
DIAGNOSTIC SNAPSHOT END
"""
    payload = json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode()
    request = Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode())
    except URLError as error:
        raise RuntimeError(f"Local Ollama API is unavailable: {error.reason}") from error
    return body["response"].strip()


if __name__ == "__main__":
    print(analyze(get_vm1_snapshot()))
