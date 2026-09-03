"""사용자 액세스 토큰으로 연결 계정을 조회하고 meta_state.json 에 저장한다.

토큰은 환경변수 MG_TOKEN 으로만 받는다(파일/커밋에 남기지 않음).
실행: MG_TOKEN=... .venv/bin/python -m scripts.meta_token_setup
"""

from __future__ import annotations

import json
import os
import sys

import requests

from naver_marketing_mcp.meta_auth import GRAPH, STATE_JSON, _AUTH_DIR

TOKEN = os.environ.get("MG_TOKEN", "")
if not TOKEN:
    sys.exit("MG_TOKEN 환경변수가 필요합니다.")


def g(path: str, **params: str) -> dict:
    params["access_token"] = TOKEN
    return requests.get(f"{GRAPH}/{path}", params=params, timeout=30).json()


me = g("me", fields="id,name")
print("ME:", me.get("name"), me.get("id"), "| err:", me.get("error", {}).get("message"))

perms = g("me/permissions")
granted = [p["permission"] for p in perms.get("data", []) if p.get("status") == "granted"]
print("GRANTED:", granted)

accts = g("me/accounts", fields="name,access_token,instagram_business_account")
if accts.get("error"):
    print("ACCOUNTS_ERR:", accts["error"].get("message"))
pages = accts.get("data", [])
print("PAGES:", [(p.get("name"), bool(p.get("instagram_business_account"))) for p in pages])

page = next((p for p in pages if p.get("instagram_business_account")), None)
if not page:
    print("NO_IG_PAGE — 인스타가 연결된 페이스북 페이지가 없습니다.")
    if pages:
        # IG 없는 페이지라도 페북 게시용으로 저장
        p0 = pages[0]
        state = {"page_id": p0["id"], "page_access_token": p0["access_token"], "ig_user_id": None}
        _AUTH_DIR.mkdir(parents=True, exist_ok=True)
        STATE_JSON.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        print("SAVED_FB_ONLY page:", p0.get("name"))
    sys.exit(0)

ig = page["instagram_business_account"]["id"]
state = {
    "ig_user_id": ig, "page_id": page["id"],
    "page_access_token": page["access_token"], "obtained_at": 0,
}
_AUTH_DIR.mkdir(parents=True, exist_ok=True)
STATE_JSON.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
print("SAVED_IG:", ig, "| PAGE:", page.get("name"))
