"""naver-marketing-mcp MCP 서버 (FastMCP).

Claude Desktop/Code 에서 로컬로 실행되며 네이버 블로그 게시·파워링크 입찰 도구를 노출한다.
안전장치(승인 게이트·일일 상한·랜덤 지연·dry-run)는 서버에서 강제한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import naver_blog, powerlink
from .db import record_post
from .policy import load_policy
from .safety import DailyCapExceeded, check_daily_cap, human_delay

mcp = FastMCP("naver-marketing")


def _blog_id(policy: dict) -> str:
    bid = policy.get("naver", {}).get("blog_id")
    if not bid:
        raise ValueError(
            "policy.yaml 에 naver.blog_id 가 없습니다. 블로그 아이디를 설정하세요."
        )
    return bid


# ────────────────────────────────────────────────────────────
# 계정 연결
# ────────────────────────────────────────────────────────────
@mcp.tool()
def connect_naver() -> str:
    """네이버 로그인(최초 1회). 브라우저 창을 띄워 사용자가 직접 로그인하고,
    세션을 로컬 .auth/ 에 저장한다. 비밀번호는 저장하지 않는다(세션 쿠키만).
    """
    policy = load_policy()
    return naver_blog.save_session(blog_id=_blog_id(policy))


# ────────────────────────────────────────────────────────────
# 네이버 블로그 게시 — 승인 게이트 내장
# ────────────────────────────────────────────────────────────
@mcp.tool()
def naver_blog_publish(
    title: str,
    body_markdown: str,
    tags: list[str] | None = None,
    image_paths: list[str] | None = None,
    private: bool = True,
    approve: bool = False,
) -> dict:
    """네이버 블로그에 글을 게시한다.

    ⚠️ 안전 기본값: approve=False 이면 **게시하지 않고 초안 미리보기만** 반환한다.
    사용자가 초안을 확인하고 approve=True 로 다시 호출해야 실제 게시된다.
    또한 policy.yaml 의 daily_cap(naver_blog)·랜덤 지연을 서버가 강제한다.

    Args:
        title: 글 제목 (SEO 고려).
        body_markdown: 본문(마크다운).
        tags: 태그 목록.
        image_paths: 첨부할 로컬 이미지 경로(Higgsfield 생성물 등).
        approve: True 여야 실제 게시. 기본 False(초안만).
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

    # ── 안전장치 ──
    try:
        check_daily_cap(policy, platform="naver_blog")
    except DailyCapExceeded as e:
        record_post("naver_blog", status="failed", title=title, error=str(e))
        return {"status": "blocked", "reason": str(e)}

    human_delay(policy)  # 봇 탐지 회피용 랜덤 지연

    try:
        result = naver_blog.publish(
            blog_id=_blog_id(policy),
            title=title,
            body_markdown=body_markdown,
            tags=tags,
            image_paths=image_paths,
            private=private,
        )
    except Exception as e:  # noqa: BLE001 — 사용자에게 원인 전달 후 로그
        record_post("naver_blog", status="failed", title=title, error=str(e))
        return {"status": "failed", "error": str(e)}

    status = "published" if result.get("status") == "published" else "draft"
    record_post(
        "naver_blog",
        status=status,
        title=title,
        post_url=result.get("post_url"),
        error=None if status == "published" else result.get("message"),
    )
    return result


# ────────────────────────────────────────────────────────────
# 파워링크 입찰 (퍼포먼스)
# ────────────────────────────────────────────────────────────
@mcp.tool()
def powerlink_bidding(dry_run: bool = True) -> dict:
    """네이버 파워링크 키워드 입찰을 1회 실행한다(naver-powerlink-bidding 통합).

    keywords.yaml 정책(목표순위·입찰범위·조정폭)에 따라 단계적으로 입찰가를 수렴시킨다.

    Args:
        dry_run: True(기본)면 실제 입찰가를 바꾸지 않고 변경 예정 내역만 반환.
    """
    return powerlink.run_bidding(dry_run=dry_run)


# ────────────────────────────────────────────────────────────
# 성과 수집 (P1)
# ────────────────────────────────────────────────────────────
@mcp.tool()
def collect_performance(days: int = 7) -> dict:
    """최근 N일 네이버 블로그·파워링크 성과를 수집한다. (P1 예정)"""
    return {"status": "planned", "message": "collect_performance 는 P1 에서 구현됩니다."}


def main() -> None:
    """콘솔 스크립트 진입점. stdio 트랜스포트로 MCP 서버 실행."""
    mcp.run()


if __name__ == "__main__":
    main()
