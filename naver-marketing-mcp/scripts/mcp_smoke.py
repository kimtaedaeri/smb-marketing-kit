"""MCP 서버가 stdio로 실제로 뜨는지 검증: initialize → tools/list 핸드셰이크."""

from __future__ import annotations

import json
import subprocess
import sys
import time

proc = subprocess.Popen(
    [sys.executable, "-m", "naver_marketing_mcp"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
)


def send(obj: dict) -> None:
    proc.stdin.write(json.dumps(obj) + "\n")
    proc.stdin.flush()


send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                 "clientInfo": {"name": "smoke", "version": "1"}}})
init = proc.stdout.readline()
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
tools_line = proc.stdout.readline()
time.sleep(0.3)
proc.terminate()

try:
    init_obj = json.loads(init)
    server_name = init_obj.get("result", {}).get("serverInfo", {}).get("name")
    tools = json.loads(tools_line).get("result", {}).get("tools", [])
    print("initialize OK · serverInfo:", server_name)
    print("tools/list OK · 도구 수:", len(tools))
    print("예시 도구:", [t["name"] for t in tools[:6]])
except Exception as e:  # noqa: BLE001
    print("파싱 실패:", e)
    print("init:", init[:200])
    print("tools:", tools_line[:200])
