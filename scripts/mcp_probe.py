#!/usr/bin/env python3
"""
scripts/mcp_probe.py

Tiny MCP->CLI wrapper for CI:
- spawns `mcp-devdiag --stdio`
- JSON-RPC handshake ("initialize" / "initialized")
- lists tools and calls the `probe` tool with args
- prints JSON result to stdout
- exits nonzero on errors or too many problems (optional policy)

Requires: Python 3.11+
"""

from __future__ import annotations
import argparse, json, os, sys, subprocess, threading, time, queue, uuid, shlex

# --- JSON-RPC helpers --------------------------------------------------------

def _rpc(msg_id: str, method: str, params: dict | None = None) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}}

def _notif(method: str, params: dict | None = None) -> dict:
    return {"jsonrpc": "2.0", "method": method, "params": params or {}}

def _content_bytes(obj: dict) -> bytes:
    body = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body

def _parse_headers(s: bytes) -> tuple[int, int]:
    # returns (content_length, header_len)
    i = s.find(b"\r\n\r\n")
    if i < 0:
        return (-1, -1)
    headers = s[:i].decode("ascii", errors="ignore").split("\r\n")
    clen = -1
    for h in headers:
        if h.lower().startswith("content-length:"):
            clen = int(h.split(":", 1)[1].strip())
            break
    return (clen, i + 4)

class StdioClient:
    def __init__(self, cmd: list[str], timeout_s: int = 180):
        self.cmd = cmd
        self.timeout_s = timeout_s
        self.proc: subprocess.Popen | None = None
        self._buf = bytearray()
        self._q: queue.Queue[dict] = queue.Queue()
        self._reader: threading.Thread | None = None

    def start(self):
        self.proc = subprocess.Popen(
            self.cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        if not self.proc.stdin or not self.proc.stdout:
            raise RuntimeError("failed to spawn MCP server")
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self):
        assert self.proc and self.proc.stdout
        f = self.proc.stdout
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            self._buf.extend(chunk)
            while True:
                clen, header_len = _parse_headers(self._buf)
                if clen < 0:
                    break
                if len(self._buf) < header_len + clen:
                    break
                body = self._buf[header_len:header_len + clen]
                del self._buf[:header_len + clen]
                try:
                    obj = json.loads(body.decode("utf-8"))
                    self._q.put(obj)
                except Exception:
                    # drop malformed
                    pass

    def send(self, obj: dict):
        assert self.proc and self.proc.stdin
        self.proc.stdin.write(_content_bytes(obj))
        self.proc.stdin.flush()

    def recv(self, id_: str | None = None, until: float | None = None) -> dict:
        # wait for response matching id_ (if provided), else first response
        t0 = time.time()
        while True:
            try:
                rem = None if until is None else max(0.0, until - time.time())
                msg = self._q.get(timeout=rem if until else 0.1)
            except queue.Empty:
                if until and time.time() > until:
                    raise TimeoutError("timeout waiting for response")
                continue
            if id_ is None:
                return msg
            if msg.get("id") == id_:
                return msg
            # not ours; stash or drop; here we drop other notifications
            # (tool logs / progress events may arrive)

    def stop(self):
        try:
            if self.proc:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
        except Exception:
            pass

# --- MCP call flow -----------------------------------------------------------

def mcp_probe(url: str, preset: str, suppress: list[str], tool_name: str, timeout_s: int) -> dict:
    cmd = shlex.split(os.getenv("MCP_DEV_DIAG_BIN", "mcp-devdiag")) + ["--stdio"]
    client = StdioClient(cmd, timeout_s=timeout_s)
    client.start()
    try:
        # initialize
        init_id = str(uuid.uuid4())
        client.send(_rpc(init_id, "initialize", {
            "protocolVersion": "2024-11-01",  # best-effort; server should accept a known version
            "clientInfo": {"name": "mcp-probe", "version": "0.1.0"},
            "capabilities": {"tools": {"listChanged": True}}
        }))
        client.recv(init_id, until=time.time() + 15)

        # notify initialized (some servers require this)
        client.send(_notif("initialized", {}))

        # list tools
        list_id = str(uuid.uuid4())
        client.send(_rpc(list_id, "tools/list", {}))
        tools = client.recv(list_id, until=time.time() + 15).get("result", {}).get("tools", [])
        names = [t.get("name") for t in tools]
        if tool_name not in names:
            raise RuntimeError(f"tool '{tool_name}' not found; available: {names}")

        # call probe
        call_id = str(uuid.uuid4())
        args = {"url": url, "preset": preset}
        if suppress:
            args["suppress"] = suppress
        client.send(_rpc(call_id, "tools/call", {"name": tool_name, "arguments": args}))
        res = client.recv(call_id, until=time.time() + timeout_s)
        if "error" in res:
            raise RuntimeError(f"tools/call error: {res['error']}")
        return res.get("result") or res
    finally:
        client.stop()

# --- CLI ---------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Run a DevDiag probe via MCP stdio")
    ap.add_argument("--url", required=True, help="Target URL to diagnose")
    ap.add_argument("--preset", default="app", choices=["chat", "embed", "app", "full"])
    ap.add_argument("--suppress", nargs="*", default=[], help="Problem codes to suppress")
    ap.add_argument("--tool", default="probe", help="Tool name to call (default: probe)")
    ap.add_argument("--timeout", type=int, default=int(os.getenv("MCP_PROBE_TIMEOUT_S", "180")))
    ap.add_argument("--max-problems", type=int, default=-1, help="Fail if problem count >= N (negative disables)")
    ap.add_argument("--pretty", action="store_true", help="Pretty print JSON")
    args = ap.parse_args()

    try:
        result = mcp_probe(args.url, args.preset, args.suppress, args.tool, args.timeout)
        # Common result shapes: either { problems: [...] } or nested
        problems = []
        if isinstance(result, dict):
            if "problems" in result:
                problems = result.get("problems") or []
            elif "output" in result and isinstance(result["output"], dict):
                problems = result["output"].get("problems") or []
        out = result
        if args.pretty:
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(out, separators=(",", ":"), ensure_ascii=False))

        if args.max_problems >= 0 and len(problems) >= args.max_problems:
            sys.exit(2)
        sys.exit(0)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
