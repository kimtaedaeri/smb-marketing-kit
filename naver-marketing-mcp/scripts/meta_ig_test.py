"""Instagram Login 토큰으로 계정 확인 + 테스트 이미지 실게시.

MG_TOKEN 환경변수로 토큰을 받는다(파일/커밋에 남기지 않음).
"""

from __future__ import annotations

import json
import os
import sys

import requests

from naver_marketing_mcp import instagram
from naver_marketing_mcp.meta_auth import IG_GRAPH, STATE_JSON, _AUTH_DIR

TOKEN = os.environ.get("MG_TOKEN", "")
if not TOKEN:
    sys.exit("MG_TOKEN 필요")

# 1) 계정 확인 (Instagram Login → graph.instagram.com)
me = requests.get(f"{IG_GRAPH}/me",
                  params={"fields": "user_id,username", "access_token": TOKEN}, timeout=30).json()
print("ME:", me)
uid = str(me.get("user_id") or me.get("id") or "")
if not uid:
    sys.exit(f"user_id 를 못 찾음: {me}")

# 2) 상태 저장 (IG 유저 토큰 방식)
state = {"ig_user_id": uid, "ig_access_token": TOKEN, "login": "instagram"}
_AUTH_DIR.mkdir(parents=True, exist_ok=True)
STATE_JSON.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
print("SAVED uid:", uid, "| user:", me.get("username"))

# 3) 테스트 이미지 게시 (공개 URL 필요 — Google 샘플 JPG)
IMAGE = "https://www.gstatic.com/webp/gallery/1.jpg"
CAPTION = "[테스트] smb-marketing-kit 자동 게시 검증 🚀 #테스트"
try:
    res = instagram.publish([IMAGE], CAPTION)
    print("PUBLISH:", res)
except Exception as e:  # noqa: BLE001
    print("PUBLISH_ERR:", repr(e))
