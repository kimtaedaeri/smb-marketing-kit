"""Meta(인스타그램·페이스북) OAuth 토큰 자동 발급.

수동은 딱 하나: Meta 대시보드에서 앱을 1번 만들고 APP_ID/APP_SECRET 을 .env 에 넣는 것.
그 후는 전부 자동 — OAuth 로그인 창을 띄우고(사용자는 로그인·동의만), 코드↔토큰 교환,
60일 장기 토큰 변환, 페이지 토큰·IG 비즈니스 계정 ID 조회까지 하고 .auth/meta_state.json 에 저장.

필요 .env:
    META_APP_ID=...
    META_APP_SECRET=...
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from .naver_blog import _AUTH_DIR, _stop_chrome, launch_real_chrome

GRAPH = "https://graph.facebook.com/v21.0"
OAUTH_DIALOG = "https://www.facebook.com/v21.0/dialog/oauth"
REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
SCOPES = [
    "instagram_basic",
    "instagram_content_publish",
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_posts",
    "business_management",
]
STATE_JSON = _AUTH_DIR / "meta_state.json"


def _load_env() -> None:
    """키트 루트 .env 를 최소 파싱해 os.environ 에 주입(python-dotenv 없이)."""
    env = _AUTH_DIR.parent / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def _get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    q = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{q}", timeout=30) as r:
        return json.loads(r.read().decode())


class _CallbackHandler(BaseHTTPRequestHandler):
    code: str | None = None

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/callback":
            qs = urllib.parse.parse_qs(parsed.query)
            _CallbackHandler.code = (qs.get("code") or [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<h2>인증 완료. 이 창을 닫아도 됩니다.</h2>".encode()
            )
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args: Any) -> None:  # 로그 억제
        return


def connect(timeout_sec: int = 300) -> dict[str, Any]:
    """OAuth 로그인 창을 띄우고 토큰 일체를 발급·저장한다. 사용자는 로그인·동의만."""
    _load_env()
    app_id = os.environ.get("META_APP_ID")
    app_secret = os.environ.get("META_APP_SECRET")
    if not app_id or not app_secret:
        return {
            "status": "no_app",
            "message": "META_APP_ID / META_APP_SECRET 가 .env 에 없습니다. "
            "docs/META_SETUP.md 의 1회 앱 생성 단계를 먼저 진행하세요.",
        }

    # 로컬 콜백 서버 기동
    _CallbackHandler.code = None
    server = HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    auth_url = (
        f"{OAUTH_DIALOG}?"
        + urllib.parse.urlencode(
            {
                "client_id": app_id,
                "redirect_uri": REDIRECT_URI,
                "scope": ",".join(SCOPES),
                "response_type": "code",
            }
        )
    )

    proc = launch_real_chrome(auth_url)
    try:
        deadline = time.time() + timeout_sec
        while time.time() < deadline and _CallbackHandler.code is None:
            time.sleep(1.0)
    finally:
        server.shutdown()
        _stop_chrome(proc)

    code = _CallbackHandler.code
    if not code:
        return {"status": "timeout", "message": "동의(로그인)가 완료되지 않았습니다."}

    # 1) code → 단기 토큰
    short = _get(
        f"{GRAPH}/oauth/access_token",
        {"client_id": app_id, "redirect_uri": REDIRECT_URI,
         "client_secret": app_secret, "code": code},
    )["access_token"]

    # 2) 단기 → 장기(60일)
    long_lived = _get(
        f"{GRAPH}/oauth/access_token",
        {"grant_type": "fb_exchange_token", "client_id": app_id,
         "client_secret": app_secret, "fb_exchange_token": short},
    )["access_token"]

    # 3) 페이지 + 페이지 토큰
    pages = _get(f"{GRAPH}/me/accounts", {"access_token": long_lived}).get("data", [])
    if not pages:
        return {"status": "no_page", "message": "연결된 페이스북 페이지가 없습니다. "
                "인스타 비즈니스 계정을 페이지에 연결하세요."}
    page = pages[0]
    page_id = page["id"]
    page_token = page["access_token"]

    # 4) IG 비즈니스 계정 ID
    ig = _get(
        f"{GRAPH}/{page_id}",
        {"fields": "instagram_business_account", "access_token": page_token},
    ).get("instagram_business_account")
    ig_user_id = ig["id"] if ig else None

    state = {
        "long_lived_user_token": long_lived,
        "page_id": page_id,
        "page_access_token": page_token,
        "ig_user_id": ig_user_id,
        "obtained_at": int(time.time()),
    }
    _AUTH_DIR.mkdir(parents=True, exist_ok=True)
    STATE_JSON.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")

    return {
        "status": "connected",
        "page_id": page_id,
        "ig_user_id": ig_user_id,
        "ig_linked": ig_user_id is not None,
        "state_file": str(STATE_JSON),
    }


def load_state() -> dict[str, Any] | None:
    if STATE_JSON.exists():
        return json.loads(STATE_JSON.read_text(encoding="utf-8"))
    return None
