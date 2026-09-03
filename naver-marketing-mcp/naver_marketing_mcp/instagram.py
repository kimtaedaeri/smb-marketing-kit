"""인스타그램 게시 (Meta Graph API, 무료). pick_agent/sns_service.py 방식 이식.

전제: meta_auth.connect() 로 토큰·ig_user_id 가 .auth/meta_state.json 에 저장돼 있어야 함.
이미지는 **공개 URL** 이어야 한다(Graph API 제약). Higgsfield 생성 이미지는 URL 로 오므로 그대로 사용.
"""

from __future__ import annotations

import time
from typing import Any

import requests

from .meta_auth import GRAPH, IG_GRAPH, load_state

IG_CAROUSEL_MAX = 10


def _require_state() -> dict[str, Any]:
    state = load_state()
    if not state or not state.get("ig_user_id"):
        raise RuntimeError(
            "인스타 연결이 없습니다. connect_meta 로 먼저 연결하세요(인스타 프로페셔널 계정 필요)."
        )
    return state


def _base_and_token(state: dict[str, Any]) -> tuple[str, str]:
    """Instagram Login(IG 유저 토큰)이면 graph.instagram.com, 아니면 페이지 토큰+graph.facebook.com."""
    ig = state["ig_user_id"]
    if state.get("ig_access_token"):
        return f"{IG_GRAPH}/{ig}", state["ig_access_token"]
    return f"{GRAPH}/{ig}", state["page_access_token"]


def publish(image_urls: list[str], caption: str) -> dict[str, Any]:
    """이미지 1장이면 단일, 여러 장이면 캐러셀로 게시. 게시 URL 반환."""
    state = _require_state()
    base, token = _base_and_token(state)

    if not image_urls:
        raise ValueError("게시할 이미지 URL 이 필요합니다.")
    urls = image_urls[:IG_CAROUSEL_MAX]

    if len(urls) == 1:
        creation_id = _create_container(base, token, urls[0], caption)
    else:
        children = [_create_container(base, token, u, is_child=True) for u in urls]
        creation_id = _create_carousel(base, token, children, caption)

    time.sleep(5)  # 미디어 처리 대기
    resp = requests.post(
        f"{base}/media_publish",
        params={"creation_id": creation_id, "access_token": token},
        timeout=30,
    )
    resp.raise_for_status()
    post_id = resp.json()["id"]
    return {"status": "published", "platform": "instagram",
            "post_id": post_id, "post_url": f"https://www.instagram.com/p/{post_id}/"}


def _create_container(base: str, token: str, image_url: str,
                      caption: str = "", is_child: bool = False) -> str:
    params: dict[str, Any] = {"image_url": image_url, "access_token": token}
    if is_child:
        params["is_carousel_item"] = "true"
    else:
        params["caption"] = caption
    resp = requests.post(f"{base}/media", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()["id"]


def _create_carousel(base: str, token: str, children: list[str], caption: str) -> str:
    resp = requests.post(
        f"{base}/media",
        params={"media_type": "CAROUSEL", "children": ",".join(children),
                "caption": caption, "access_token": token},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]
