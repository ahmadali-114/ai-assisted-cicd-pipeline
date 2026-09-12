"""Analyze VM1 diagnostics using a local Ollama model on VM2."""

from __future__ import annotations

import asyncio
import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen

from mcp import Client

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = os.environ.get("AIOPS_OLLAMA_MODEL", "qwen2.5:1.5b")
MCP_URL = os.environ.get("AIOPS_MCP_URL", "http://127.0.0.1:8001/mcp")
OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("AIOPS_OLLAMA_TIMEOUT_SECONDS", "420"))
MAX_RESPONSE_TOKENS = int(os.environ.get("AIOPS_MAX_RESPONSE_TOKENS", "300"))


async def get_snapshot_via_mcp() -> str:
    """Retrieve diagnostics through the local MCP tool, not a direct SSH call."""
    async with Client(MCP_URL) as client:
        result = await client.call_tool("get_vm1_diagnostic_snapshot", {})

    text_parts = [item.text for item in result.content if hasattr(item, "text")]
    snapshot = "\n".join(text_parts)
    if not snapshot:
        raise RuntimeError("MCP tool returned no text diagnostic snapshot")
    return snapshot


def current_state_assessment(snapshot: str) -> tuple[str, str]:
    """Keep the current-state verdict deterministic instead of trusting an LLM."""
    active_incident_signals = (
        "jenkins=inactive",
        "jenkins=failed",
        "docker=inactive",
        "docker=failed",
        "system-monitor-api container not found",
        "curl: (7)",
        "curl: (22)",
        "(unhealthy)",
    )
    detected_failures = [signal for signal in active_incident_signals if signal in snapshot]
    if detected_failures:
        return (
            "ACTIVE INCIDENT",
            "Current diagnostic snapshot contains failure signals: "
            + ", ".join(detected_failures),
        )

    required_signals = (
        "jenkins=active",
        "docker=active",
        '"status":"healthy"',
        "system-monitor-api",
        "(healthy)",
    )
    missing_signals = [signal for signal in required_signals if signal not in snapshot]
    if not missing_signals:
        return (
            "NO ACTIVE INCIDENT",
            "Jenkins and Docker are active; the deployed API and its container health check are healthy.",
        )
    return (
        "INSUFFICIENT EVIDENCE",
        "Current health cannot be confirmed because these expected signals were absent: "
        + ", ".join(missing_signals),
    )


def analyze(snapshot: str) -> str:
    verdict, deterministic_evidence = current_state_assessment(snapshot)
    prompt = f"""You are a cautious DevOps incident assistant for an authorized learning lab.
The user explicitly authorizes analysis of this bounded and redacted diagnostic snapshot.
Do the diagnosis; do not refuse merely because the data contains operational logs.
Use only the diagnostic evidence below. Do not invent facts, failures, credentials,
or missing files. A historical Jenkins start/stop message is not an active incident
when the current service status is active and healthy.

The deterministic current-state verdict is: {verdict}.
Its evidence is: {deterministic_evidence}
Do not override this verdict. Historical log errors must be labelled historical and must
not be presented as a current outage. Return: Historical observations; Evidence (quote
exact snapshot facts); Safe read-only next troubleshooting commands. Never recommend
downloading or replacing Jenkins files unless the snapshot explicitly proves they are
missing or corrupted.

DIAGNOSTIC SNAPSHOT START
{snapshot}
DIAGNOSTIC SNAPSHOT END
"""
    payload = json.dumps(
        {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "10m",
            "options": {"temperature": 0, "num_predict": MAX_RESPONSE_TOKENS},
        }
    ).encode()
    request = Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=OLLAMA_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode())
    except URLError as error:
        raise RuntimeError(f"Local Ollama API is unavailable: {error.reason}") from error
    except TimeoutError as error:
        raise RuntimeError(
            f"Local Ollama API exceeded its {OLLAMA_TIMEOUT_SECONDS}-second response budget"
        ) from error
    return (
        f"AUTOMATED CURRENT-STATE VERDICT: {verdict}\n"
        f"AUTOMATED EVIDENCE: {deterministic_evidence}\n\n"
        "AI ADVISORY ANALYSIS (validate before making changes):\n"
        + body["response"].strip()
    )


if __name__ == "__main__":
    print(analyze(asyncio.run(get_snapshot_via_mcp())))
