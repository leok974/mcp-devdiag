"""MCP server for TasteOS development diagnostics."""

from __future__ import annotations
import json
from typing import Any, Dict, List

import httpx
from fastmcp import FastMCP
from mcp_devdiag.schema import StatusResponse, TailResponse, EnvStateResponse
from mcp_devdiag.analyzer import build_status, LOG_DIR, BACKEND_LOG, FRONTEND_LOG, ENV_JSON
from mcp_devdiag.tail import tail_lines

NETWORK_LOG = LOG_DIR / "network.jsonl"

# Create FastMCP app
app = FastMCP("mcp-devdiag")


@app.tool()
def get_status() -> StatusResponse:
    """Get comprehensive development diagnostics including backend/frontend log status."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return build_status()


@app.tool()
def get_backend_logs(n: int = 300) -> TailResponse:
    """Tail the last n lines from backend.log."""
    lines = tail_lines(BACKEND_LOG, n=n)
    return TailResponse(lines=lines)


@app.tool()
def get_frontend_logs(n: int = 300) -> TailResponse:
    """Tail the last n lines from frontend.log."""
    lines = tail_lines(FRONTEND_LOG, n=n)
    return TailResponse(lines=lines)


@app.tool()
def get_env_state() -> EnvStateResponse:
    """Return env.json snapshot."""
    env = {}
    if ENV_JSON.exists():
        try:
            env = json.loads(ENV_JSON.read_text())
        except Exception:
            env = {}
    return EnvStateResponse(env=env)


@app.tool()
def get_request_diagnostics(
    url: str, method: str = "GET", timeout_s: float = 3.0
) -> Dict[str, Any]:
    """Actively probe a URL for status/CORS headers."""
    try:
        with httpx.Client(follow_redirects=False, timeout=timeout_s) as client:
            resp = client.request(method.upper(), url, headers={"Origin": "http://localhost:5173"})
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return {
                "ok": True,
                "status": resp.status_code,
                "reason": resp.reason_phrase,
                "headers": {
                    "access-control-allow-origin": headers.get("access-control-allow-origin"),
                    "access-control-allow-credentials": headers.get(
                        "access-control-allow-credentials"
                    ),
                    "vary": headers.get("vary"),
                    "content-type": headers.get("content-type"),
                },
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.tool()
def get_network_log(n: int = 200) -> Dict[str, List[str]]:
    """Get the last n lines from network.jsonl."""
    lines: List[str] = []
    if NETWORK_LOG.exists():
        # Simple tail without loading entire file in memory
        with NETWORK_LOG.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            block = 4096
            data = b""
            while size > 0 and len(lines) < n:
                step = min(block, size)
                size -= step
                f.seek(size)
                data = f.read(step) + data
                parts = data.split(b"\n")
                lines = [p.decode("utf-8", "ignore") for p in parts if p.strip()]
                if len(lines) >= n:
                    break
            lines = lines[-n:]
    return {"lines": lines}


@app.tool()
def get_network_summary(n: int = 500) -> Dict[str, Any]:
    """Get summary statistics from the last n network log entries."""
    log_result = get_network_log(n=n)  # type: ignore[operator]
    lines = log_result.get("lines", [])
    total = 0
    buckets = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "other": 0}
    fails: Dict[str, int] = {}
    slow: List[Dict[str, Any]] = []

    for line in lines:
        try:
            ev = json.loads(line)
        except Exception:
            continue
        total += 1
        st = int(ev.get("status") or 0)
        dur = int(ev.get("dur_ms") or 0)
        url = str(ev.get("url") or "")
        bucket = "other"
        if 200 <= st < 300:
            bucket = "2xx"
        elif 300 <= st < 400:
            bucket = "3xx"
        elif 400 <= st < 500:
            bucket = "4xx"
            fails[url] = fails.get(url, 0) + 1
        elif 500 <= st < 600:
            bucket = "5xx"
            fails[url] = fails.get(url, 0) + 1
        buckets[bucket] += 1
        if dur >= 1000:
            slow.append({"url": url, "dur_ms": dur, "status": st})

    slow.sort(key=lambda x: x["dur_ms"], reverse=True)
    top_fails = sorted(fails.items(), key=lambda kv: kv[1], reverse=True)[:10]

    return {"total": total, "buckets": buckets, "top_fails": top_fails, "slow": slow[:10]}


def main():
    """Console entrypoint: `mcp-devdiag --stdio`."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
