"""Meta 원클릭 연결 브로커 (FastAPI).

목적: 여러 SMB 사용자가 각자 로컬 MCP 에서 "인스타 연결"만 누르면, 이 서버가 Meta OAuth 를
대행한다. **앱 시크릿은 이 서버에만** 있고 사용자 기기·오픈소스에 노출되지 않는다.

흐름:
  1) 로컬 MCP 가 localhost:8765 리스너를 열고 브라우저를 {BROKER}/connect/start?session=<id> 로 연다
  2) 이 서버가 Meta OAuth 로 리다이렉트(사용자는 로그인·동의만)
  3) /connect/callback 에서 code→토큰 교환·장기토큰·페이지토큰·IG계정ID 조회 후
     session 키로 잠시 저장하고, 브라우저를 http://localhost:8765/done?session=<id> 로 되돌린다
  4) 로컬 MCP 가 {BROKER}/connect/claim?session=<id> 로 토큰을 1회 수령(서버는 즉시 폐기)

필수 환경변수:
  META_APP_ID, META_APP_SECRET, BROKER_PUBLIC_URL(예: https://connect.example.com)

Meta 앱에 등록할 값:
  - 유효한 OAuth 리디렉션 URI: {BROKER_PUBLIC_URL}/connect/callback
  - 개인정보처리방침 URL: {BROKER_PUBLIC_URL}/privacy
  - 데이터 삭제 요청 콜백 URL: {BROKER_PUBLIC_URL}/data-deletion
  - 연결 해제 콜백 URL: {BROKER_PUBLIC_URL}/deauthorize
"""

from __future__ import annotations

import os
import secrets
import time
import urllib.parse
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

GRAPH = "https://graph.facebook.com/v21.0"
OAUTH_DIALOG = "https://www.facebook.com/v21.0/dialog/oauth"
SCOPES = [
    "instagram_basic",
    "instagram_content_publish",
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_posts",
    "business_management",
]
SESSION_TTL = 600  # 초

app = FastAPI(title="Meta Connect Broker")

# session_id → {"state": ..., "tokens": {...}|None, "created": ts}
_sessions: dict[str, dict[str, Any]] = {}


def _cfg(key: str) -> str:
    v = os.environ.get(key)
    if not v:
        raise HTTPException(500, f"서버 환경변수 {key} 미설정")
    return v


def _gc() -> None:
    now = time.time()
    for sid in [s for s, v in _sessions.items() if now - v["created"] > SESSION_TTL]:
        _sessions.pop(sid, None)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/connect/start")
def connect_start(session: str) -> RedirectResponse:
    """로컬 MCP 가 연 브라우저를 Meta 동의 화면으로 보낸다."""
    _gc()
    state = secrets.token_urlsafe(16)
    _sessions[session] = {"state": state, "tokens": None, "created": time.time()}
    params = {
        "client_id": _cfg("META_APP_ID"),
        "redirect_uri": f"{_cfg('BROKER_PUBLIC_URL')}/connect/callback",
        "scope": ",".join(SCOPES),
        "response_type": "code",
        "state": f"{session}:{state}",
    }
    return RedirectResponse(f"{OAUTH_DIALOG}?{urllib.parse.urlencode(params)}")


@app.get("/connect/callback")
def connect_callback(code: str = "", state: str = "") -> RedirectResponse:
    """code→토큰 교환 일체를 서버가 대행하고, 브라우저를 로컬로 되돌린다."""
    session, _, st = state.partition(":")
    sess = _sessions.get(session)
    if not sess or sess["state"] != st:
        raise HTTPException(400, "잘못되었거나 만료된 세션")

    app_id, app_secret = _cfg("META_APP_ID"), _cfg("META_APP_SECRET")
    redirect_uri = f"{_cfg('BROKER_PUBLIC_URL')}/connect/callback"

    with httpx.Client(timeout=30) as c:
        short = c.get(f"{GRAPH}/oauth/access_token", params={
            "client_id": app_id, "redirect_uri": redirect_uri,
            "client_secret": app_secret, "code": code}).json()["access_token"]
        long_lived = c.get(f"{GRAPH}/oauth/access_token", params={
            "grant_type": "fb_exchange_token", "client_id": app_id,
            "client_secret": app_secret, "fb_exchange_token": short}).json()["access_token"]
        pages = c.get(f"{GRAPH}/me/accounts", params={"access_token": long_lived}).json().get("data", [])
        tokens: dict[str, Any] = {"long_lived_user_token": long_lived, "pages": []}
        for pg in pages:
            ig = c.get(f"{GRAPH}/{pg['id']}", params={
                "fields": "instagram_business_account", "access_token": pg["access_token"],
            }).json().get("instagram_business_account")
            tokens["pages"].append({
                "page_id": pg["id"], "page_name": pg.get("name"),
                "page_access_token": pg["access_token"],
                "ig_user_id": ig["id"] if ig else None,
            })

    sess["tokens"] = tokens
    return RedirectResponse(f"http://localhost:8765/done?session={urllib.parse.quote(session)}")


@app.get("/connect/claim")
def connect_claim(session: str) -> JSONResponse:
    """로컬 MCP 가 토큰을 1회 수령. 수령 즉시 서버에서 폐기."""
    sess = _sessions.pop(session, None)
    if not sess or not sess.get("tokens"):
        raise HTTPException(404, "토큰 없음(만료되었거나 아직 미완료)")
    return JSONResponse(sess["tokens"])


# ── Meta 앱 심사 필수 페이지/콜백 ────────────────────────────
@app.get("/privacy", response_class=HTMLResponse)
def privacy() -> str:
    return _PRIVACY_HTML


@app.get("/terms", response_class=HTMLResponse)
def terms() -> str:
    return _TERMS_HTML


@app.post("/data-deletion")
async def data_deletion(request: Request) -> JSONResponse:
    """Meta 데이터 삭제 요청 콜백. 저장 데이터가 없으므로 확인 코드만 반환.

    (이 서버는 토큰을 세션 TTL 후 즉시 폐기하고 영구 저장하지 않는다.)
    """
    code = secrets.token_hex(8)
    return JSONResponse({
        "url": f"{os.environ.get('BROKER_PUBLIC_URL', '')}/data-deletion?code={code}",
        "confirmation_code": code,
    })


@app.get("/deauthorize")
@app.post("/deauthorize")
def deauthorize() -> JSONResponse:
    """Meta 연결 해제 콜백. 서버 영구 저장 없음 → 확인만."""
    return JSONResponse({"ok": True})


_PRIVACY_HTML = """<!doctype html><meta charset="utf-8"><title>개인정보처리방침</title>
<h1>개인정보처리방침</h1>
<p>본 서비스(Meta Connect)는 사용자가 자신의 인스타그램/페이스북 계정으로 자신의 콘텐츠를
게시하도록 돕는 연결 중개자입니다.</p>
<ul>
<li>수집: Meta 로그인 동의로 발급된 액세스 토큰 및 페이지/인스타 계정 식별자.</li>
<li>목적: 사용자가 지시한 게시물 발행에만 사용.</li>
<li>보관: 토큰은 연결 완료 후 사용자 로컬 기기로 전달되며, 서버는 단기 세션(최대 10분) 후 즉시 폐기하고 영구 저장하지 않습니다.</li>
<li>제3자 제공: 없음. 광고·분석 목적 사용 없음.</li>
<li>삭제/철회: Meta 설정의 앱 연결 해제 또는 데이터 삭제 요청으로 즉시 반영됩니다.</li>
</ul>
<p>문의: (연락 이메일 기입)</p>"""

_TERMS_HTML = """<!doctype html><meta charset="utf-8"><title>이용약관</title>
<h1>이용약관</h1>
<p>본 서비스는 사용자 본인 계정으로 본인 콘텐츠를 게시하는 것을 돕습니다. 스팸, 타인 사칭,
Meta 플랫폼 정책 위반 목적의 사용을 금합니다. 서비스는 "있는 그대로" 제공됩니다.</p>"""
