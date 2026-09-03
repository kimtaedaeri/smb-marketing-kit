"""Threads 토큰으로 연결 + 텍스트 게시 검증. MG_TOKEN 환경변수로 토큰을 받는다."""

from __future__ import annotations

import os
import sys

from naver_marketing_mcp import meta_auth, threads

TOKEN = os.environ.get("MG_TOKEN", "")
if not TOKEN:
    sys.exit("MG_TOKEN 필요")

conn = meta_auth.set_threads_token(TOKEN)
print("CONNECT:", conn)
if conn.get("status") != "connected":
    sys.exit(1)

try:
    res = threads.publish("smb-marketing-kit 스레드 자동 게시 검증 🧵 #테스트")
    print("PUBLISH:", res)
except Exception as e:  # noqa: BLE001
    print("PUBLISH_ERR:", repr(e))
