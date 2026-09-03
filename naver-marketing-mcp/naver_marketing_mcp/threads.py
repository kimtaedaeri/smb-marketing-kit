"""스레드(Threads) 게시 (graph.threads.net). 텍스트 또는 이미지(공개 URL).

전제: meta_auth.set_threads_token 으로 연결돼 있어야 함. 인스타와 별개 계정/토큰.
"""

from __future__ import annotations

import time
from typing import Any

import requests

from .meta_auth import TH_GRAPH, load_threads_state


def _require_state() -> dict[str, Any]:
    s = load_threads_state()
    if not s or not s.get("threads_user_id"):
        raise RuntimeError("스레드 연결이 없습니다. set_threads_token 으로 먼저 연결하세요.")
    return s


def publish(text: str, image_urls: list[str] | None = None) -> dict[str, Any]:
    """스레드 글 게시. image_urls 가 있으면 첫 이미지 첨부(공개 URL), 없으면 텍스트만."""
    s = _require_state()
    uid = s["threads_user_id"]
    token = s["threads_access_token"]
    base = f"{TH_GRAPH}/{uid}"

    params: dict[str, Any] = {"access_token": token, "text": text}
    if image_urls:
        params["media_type"] = "IMAGE"
        params["image_url"] = image_urls[0]
    else:
        params["media_type"] = "TEXT"

    r = requests.post(f"{base}/threads", params=params, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"컨테이너 생성 실패: {r.status_code} {r.text[:200]}")
    creation_id = r.json()["id"]

    time.sleep(3)  # 처리 대기
    r2 = requests.post(f"{base}/threads_publish",
                       params={"creation_id": creation_id, "access_token": token}, timeout=30)
    if r2.status_code != 200:
        raise RuntimeError(f"게시 실패: {r2.status_code} {r2.text[:200]}")
    return {"status": "published", "platform": "threads", "post_id": r2.json()["id"]}
