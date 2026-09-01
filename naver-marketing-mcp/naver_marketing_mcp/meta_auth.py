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
import secrets
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
    code: str | None = None            # 개발자 모드: OAuth code 직접 수신
    done_session: str | None = None    # 브로커 모드: /done?session= 수신

    def _ok(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<h2>연결 완료. 이 창을 닫아도 됩니다.</h2>".encode())

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/callback":
            _CallbackHandler.code = (qs.get("code") or [None])[0]
            self._ok()
        elif parsed.path == "/done":
            _CallbackHandler.done_session = (qs.get("session") or [None])[0]
            self._ok()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args: Any) -> None:  # 로그 억제
        return


def connect(timeout_sec: int = 300) -> dict[str, Any]:
    """인스타·페북 연결. 사용자는 로그인·동의만.

    - META_BROKER_URL 이 있으면 **원클릭 브로커 모드**(앱 시크릿이 사용자 기기에 없음, 권장).
    - 없고 META_APP_ID/SECRET 이 있으면 개발자 모드(본인 앱 직접).
    """
    _load_env()
    broker = os.environ.get("META_BROKER_URL")
    if broker:
        return _connect_via_broker(broker.rstrip("/"), timeout_sec)

    app_id = os.environ.get("META_APP_ID")
    app_secret = os.environ.get("META_APP_SECRET")
    if not app_id or not app_secret:
        return {
            "status": "no_app",
            "message": "META_BROKER_URL(권장) 또는 META_APP_ID/META_APP_SECRET 가 .env 에 없습니다. "
            "docs/META_SETUP.md 참고.",
        }
    return _connect_dev(app_id, app_secret, timeout_sec)


def _connect_via_broker(broker: str, timeout_sec: int) -> dict[str, Any]:
    """원클릭: 브라우저를 브로커로 보내 로그인·동의만 받고, 토큰은 브로커가 대행 후 수령."""
    import requests

    session_id = secrets.token_urlsafe(12)
    _CallbackHandler.done_session = None
    server = HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    proc = launch_real_chrome(f"{broker}/connect/start?session={session_id}")
    try:
        deadline = time.time() + timeout_sec
        while time.time() < deadline and _CallbackHandler.done_session != session_id:
            time.sleep(1.0)
    finally:
        server.shutdown()
        _stop_chrome(proc)

    if _CallbackHandler.done_session != session_id:
        return {"status": "timeout", "message": "로그인·동의가 완료되지 않았습니다."}

    r = requests.get(f"{broker}/connect/claim", params={"session": session_id}, timeout=30)
    if r.status_code != 200:
        return {"status": "error", "message": f"토큰 수령 실패({r.status_code})"}
    data = r.json()
    return _finalize(data.get("long_lived_user_token"), data.get("pages", []))


def _connect_dev(app_id: str, app_secret: str, timeout_sec: int) -> dict[str, Any]:
    """개발자 모드: 본인 앱으로 직접 토큰 교환(앱 시크릿이 로컬 .env 에 있음)."""
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

    # 3) 페이지들 + 각 페이지의 IG 계정
    raw = _get(f"{GRAPH}/me/accounts", {"access_token": long_lived}).get("data", [])
    pages = []
    for pg in raw:
        ig = _get(f"{GRAPH}/{pg['id']}",
                  {"fields": "instagram_business_account", "access_token": pg["access_token"]}
                  ).get("instagram_business_account")
        pages.append({"page_id": pg["id"], "page_name": pg.get("name"),
                      "page_access_token": pg["access_token"],
                      "ig_user_id": ig["id"] if ig else None})
    return _finalize(long_lived, pages)


# ── 결과 정리 + 초보자용 친절 안내 ────────────────────────────
LINK_HELP = (
    "인스타를 페이스북 페이지에 연결하면 돼요:\n"
    "1) 인스타 앱 → 설정 및 개인정보 → 비즈니스/크리에이터 도구\n"
    "2) 'Facebook 연결'(또는 페이지 연결) → 페이지 선택\n"
    "페이지가 없으면 먼저 무료로 만드세요(페이스북 → 페이지 → 새 페이지 만들기).\n"
    "연결 후 다시 '인스타 연결해줘'라고 하면 제가 확인할게요."
)


def _finalize(long_lived: str | None, pages: list[dict[str, Any]]) -> dict[str, Any]:
    """페이지 목록에서 IG 연결된 페이지를 골라 저장하고, 초보자용 결과 메시지를 만든다."""
    if not pages:
        return {
            "status": "no_page",
            "message": "로그인은 됐는데 연결된 페이스북 페이지가 없어요.",
            "how": "페이스북에서 페이지를 무료로 만들고(페이스북 → 페이지 → 새 페이지), "
                   "인스타를 그 페이지에 연결한 뒤 다시 '인스타 연결해줘'라고 해주세요.",
        }
    page = next((p for p in pages if p.get("ig_user_id")), pages[0])
    state = {
        "long_lived_user_token": long_lived,
        "page_id": page["page_id"],
        "page_access_token": page["page_access_token"],
        "ig_user_id": page.get("ig_user_id"),
        "obtained_at": int(time.time()),
    }
    _AUTH_DIR.mkdir(parents=True, exist_ok=True)
    STATE_JSON.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")

    name = page.get("page_name") or page["page_id"]
    if page.get("ig_user_id"):
        return {"status": "connected", "ig_linked": True, "page_id": page["page_id"],
                "ig_user_id": page["ig_user_id"],
                "message": f"연결 완료! 페이지 '{name}'와 인스타 계정까지 잡혔어요. "
                           "이제 인스타·페이스북에 게시할 수 있어요."}
    return {"status": "page_not_linked", "ig_linked": False, "page_id": page["page_id"],
            "message": f"거의 다 됐어요! 페이스북 페이지 '{name}'는 찾았는데, "
                       "인스타가 그 페이지에 아직 연결 안 돼 있어요. (페이스북 게시는 지금도 가능)",
            "how": LINK_HELP}


def preflight() -> dict[str, Any]:
    """연결 준비 상태를 점검해 '지금 뭘 하면 되는지'를 평이하게 알려준다(초보자용)."""
    _load_env()
    state = load_state()
    if state and state.get("ig_user_id"):
        return {"ready": True, "step": "connected",
                "message": "이미 인스타까지 연결돼 있어요. 바로 게시할 수 있어요."}
    if state and not state.get("ig_user_id"):
        return {"ready": False, "step": "page_not_linked",
                "message": "페이스북 페이지는 연결됐는데 인스타가 페이지에 아직 연결 안 돼 있어요.",
                "how": LINK_HELP}
    if os.environ.get("META_BROKER_URL"):
        return {"ready": True, "step": "ready_to_connect", "mode": "one_click",
                "message": "준비됐어요. '인스타 연결해줘'라고 하면 로그인 창이 떠요. 로그인만 하면 끝이에요."}
    if os.environ.get("META_APP_ID") and os.environ.get("META_APP_SECRET"):
        return {"ready": True, "step": "ready_to_connect", "mode": "developer",
                "message": "준비됐어요(개발자 모드). '인스타 연결해줘'라고 하면 로그인 창이 떠요."}
    return {"ready": False, "step": "need_setup", "mode": "none",
            "message": "아직 인스타 연결 준비가 안 됐어요.",
            "how": "일반 사용자용 원클릭은 .env 에 META_BROKER_URL 한 줄이면 됩니다. "
                   "지금 직접 테스트라면 docs/META_SETUP.md 로 앱을 한 번 만들어 키를 넣으세요."}


def load_state() -> dict[str, Any] | None:
    if STATE_JSON.exists():
        return json.loads(STATE_JSON.read_text(encoding="utf-8"))
    return None
