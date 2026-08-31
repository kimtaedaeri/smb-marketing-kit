"""naver-marketing-mcp MCP 서버 (FastMCP).

Claude Desktop/Code 에서 로컬로 실행되며 네이버 블로그 게시·파워링크 입찰 도구를 노출한다.
P0 골격: 도구 인터페이스와 안전장치(승인 게이트·페이싱 상한·dry-run)를 확정하고,
실제 자동화 로직은 TODO 로 표시한다.
"""

from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

from .policy import load_policy
from .safety import check_daily_cap, human_delay

mcp = FastMCP("naver-marketing")


# ────────────────────────────────────────────────────────────
# 계정 연결
# ────────────────────────────────────────────────────────────
@mcp.tool()
def connect_naver() -> str:
    """네이버 로그인(최초 1회). 브라우저 창을 띄워 사용자가 직접 로그인하고,
    세션(storage_state)을 OS 키체인 경로에 저장한다. 비밀번호는 저장하지 않는다.

    반환: 연결 상태 메시지.
    """
    # TODO(P0): Playwright 로 로그인 창 → storage_state 저장 (naver_blog.save_session)
    raise NotImplementedError(
        "connect_naver 는 다음 단계에서 구현됩니다. "
        "로그인 창을 띄우고 세션을 키체인에 저장합니다."
    )


# ────────────────────────────────────────────────────────────
# 네이버 블로그 게시 — 승인 게이트 내장
# ────────────────────────────────────────────────────────────
@mcp.tool()
def naver_blog_publish(
    title: str,
    body_markdown: str,
    tags: list[str] | None = None,
    image_paths: list[str] | None = None,
    approve: bool = False,
) -> dict:
    """네이버 블로그에 글을 게시한다.

    ⚠️ 안전 기본값: approve=False 이면 **게시하지 않고 초안 미리보기만** 반환한다.
    사용자가 초안을 확인하고 approve=True 로 다시 호출해야 실제 게시된다.

    또한 policy.yaml 의 daily_cap(naver_blog)·min_interval_min 을 서버가 강제한다.

    Args:
        title: 글 제목 (SEO 고려).
        body_markdown: 본문(마크다운). 네이버 에디터 형식으로 변환되어 입력된다.
        tags: 태그 목록.
        image_paths: 첨부할 로컬 이미지 경로(Higgsfield 생성물 등).
        approve: True 여야 실제 게시. 기본 False(초안만).

    Returns:
        approve=False → {"status": "draft", "preview": {...}}
        approve=True  → {"status": "published", "post_url": "..."}
    """
    policy = load_policy()
    preview = {
        "title": title,
        "body_markdown": body_markdown,
        "tags": tags or [],
        "image_count": len(image_paths or []),
    }

    if not approve:
        return {
            "status": "draft",
            "preview": preview,
            "next": "초안을 확인한 뒤 approve=True 로 다시 호출하면 게시됩니다.",
        }

    # 안전장치: 일일 상한 확인
    check_daily_cap(policy, platform="naver_blog")
    human_delay(policy)  # 랜덤 지연으로 봇 탐지 회피

    # TODO(P0): naver_blog.publish(preview, session) 로 실제 Playwright 게시
    raise NotImplementedError(
        "실제 게시 로직은 다음 단계에서 구현됩니다. "
        "지금은 승인 게이트·상한·지연 골격까지 동작합니다."
    )


# ────────────────────────────────────────────────────────────
# 파워링크 입찰 (퍼포먼스)
# ────────────────────────────────────────────────────────────
@mcp.tool()
def powerlink_bidding(dry_run: bool = True) -> dict:
    """네이버 파워링크 키워드 입찰을 1회 실행한다.

    keywords.yaml 정책(목표순위·입찰범위·조정폭)에 따라 단계적으로 입찰가를 수렴시킨다.
    naver-powerlink-bidding 오픈소스를 통합한다.

    Args:
        dry_run: True(기본)면 실제 입찰가를 바꾸지 않고 변경 예정 내역만 반환.

    Returns:
        {"dry_run": bool, "changes": [{keyword, current, target, action}, ...]}
    """
    # TODO(P0): naver-powerlink-bidding 을 의존성으로 통합해 1 사이클 실행
    raise NotImplementedError(
        "powerlink_bidding 은 naver-powerlink-bidding 통합 단계에서 연결됩니다."
    )


# ────────────────────────────────────────────────────────────
# 성과 수집 (P1)
# ────────────────────────────────────────────────────────────
@mcp.tool()
def collect_performance(days: int = 7) -> dict:
    """최근 N일 네이버 블로그·파워링크 성과를 수집한다. (P1)"""
    raise NotImplementedError("collect_performance 는 P1 에서 구현됩니다.")


def main() -> None:
    """콘솔 스크립트 진입점. stdio 트랜스포트로 MCP 서버 실행."""
    mcp.run()


if __name__ == "__main__":
    main()
