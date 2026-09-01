"""페이스북 페이지 게시 (Meta Graph API, 무료). pick_agent/sns_service.py 방식 이식.

전제: meta_auth.connect() 로 page_id·page_access_token 저장돼 있어야 함.
이미지는 공개 URL 사용.
"""

from __future__ import annotations

from typing import Any

import requests

from .meta_auth import GRAPH, load_state


def _require_state() -> dict[str, Any]:
    state = load_state()
    if not state or not state.get("page_id"):
        raise RuntimeError("페이스북 페이지 연결이 없습니다. connect_meta 로 먼저 연결하세요.")
    return state


def publish(image_urls: list[str], caption: str) -> dict[str, Any]:
    """여러 이미지를 한 피드 포스트로 게시. 이미지가 없으면 텍스트만 게시."""
    state = _require_state()
    page_id = state["page_id"]
    token = state["page_access_token"]
    base = f"{GRAPH}/{page_id}"

    if not image_urls:
        resp = requests.post(f"{base}/feed",
                             params={"message": caption, "access_token": token}, timeout=30)
        resp.raise_for_status()
        post_id = resp.json()["id"]
        return {"status": "published", "platform": "facebook", "post_id": post_id,
                "post_url": f"https://www.facebook.com/{post_id}"}

    # 1) 각 이미지를 미게시 업로드 → media_fbid
    photo_ids = []
    for url in image_urls:
        resp = requests.post(f"{base}/photos",
                             params={"url": url, "published": "false", "access_token": token},
                             timeout=30)
        resp.raise_for_status()
        photo_ids.append(resp.json()["id"])

    # 2) 피드 포스트로 묶어 게시
    attached = [{"media_fbid": pid} for pid in photo_ids]
    resp = requests.post(f"{base}/feed",
                         json={"message": caption, "attached_media": attached,
                               "access_token": token}, timeout=30)
    resp.raise_for_status()
    post_id = resp.json()["id"]
    return {"status": "published", "platform": "facebook", "post_id": post_id,
            "post_url": f"https://www.facebook.com/{post_id}"}
