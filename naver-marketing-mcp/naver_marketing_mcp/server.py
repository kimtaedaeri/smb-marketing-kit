"""naver-marketing-mcp MCP 서버 (FastMCP).

Claude Desktop/Code 에서 로컬로 실행되며 네이버 블로그 게시·파워링크 입찰 도구를 노출한다.
안전장치(승인 게이트·일일 상한·랜덤 지연·dry-run)는 서버에서 강제한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import channels, facebook, instagram, meta_auth, naver_blog, powerlink
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


# ────────────────────────────────────────────────────────────
# Meta(인스타·페북) 무료 게시 — Blotato 없이 직접
# ────────────────────────────────────────────────────────────
@mcp.tool()
def meta_preflight() -> dict:
    """인스타·페북 연결 준비 상태를 점검하고, 초보자용으로 '지금 뭘 하면 되는지' 알려준다.
    connect_meta 전에 먼저 불러 상태를 확인하는 용도.
    """
    return meta_auth.preflight()


@mcp.tool()
def connect_meta() -> dict:
    """인스타그램·페이스북 연결(OAuth). 브라우저 창이 뜨면 로그인·동의만 하면 되고,
    토큰 발급·장기토큰 변환·IG 계정 조회는 자동으로 처리해 로컬에 저장한다.
    사전: docs/META_SETUP.md 로 앱 1회 생성 후 .env 에 META_APP_ID/META_APP_SECRET 설정.
    """
    return meta_auth.connect()


@mcp.tool()
def instagram_publish(image_urls: list[str], caption: str, approve: bool = False) -> dict:
    """인스타그램 게시(무료 Graph API). image_urls 는 공개 URL(예: Higgsfield 생성물).
    approve=False 면 게시하지 않고 미리보기만 반환(승인 게이트).
    """
    if not approve:
        return {"status": "draft", "platform": "instagram",
                "preview": {"caption": caption, "image_count": len(image_urls)},
                "next": "approve=True 로 다시 호출하면 게시됩니다."}
    policy = load_policy()
    try:
        check_daily_cap(policy, "instagram")
    except DailyCapExceeded as e:
        return {"status": "blocked", "reason": str(e)}
    try:
        result = instagram.publish(image_urls, caption)
    except Exception as e:  # noqa: BLE001
        record_post("instagram", status="failed", title=caption[:40], error=str(e))
        return {"status": "failed", "error": str(e)}
    record_post("instagram", status="published", title=caption[:40],
                post_url=result.get("post_url"))
    return result


@mcp.tool()
def facebook_publish(image_urls: list[str], caption: str, approve: bool = False) -> dict:
    """페이스북 페이지 게시(무료 Graph API). approve=False 면 미리보기만."""
    if not approve:
        return {"status": "draft", "platform": "facebook",
                "preview": {"caption": caption, "image_count": len(image_urls)},
                "next": "approve=True 로 다시 호출하면 게시됩니다."}
    policy = load_policy()
    try:
        check_daily_cap(policy, "facebook")
    except DailyCapExceeded as e:
        return {"status": "blocked", "reason": str(e)}
    try:
        result = facebook.publish(image_urls, caption)
    except Exception as e:  # noqa: BLE001
        record_post("facebook", status="failed", title=caption[:40], error=str(e))
        return {"status": "failed", "error": str(e)}
    record_post("facebook", status="published", title=caption[:40],
                post_url=result.get("post_url"))
    return result


# ────────────────────────────────────────────────────────────
# 멀티 SNS 재가공: 채널 규격·검증
# ────────────────────────────────────────────────────────────
@mcp.tool()
def channel_spec(channel: str | None = None) -> dict:
    """채널별 재가공 규격(길이·해시태그·이미지·톤)을 반환한다.

    블로그 글을 인스타·링크드인·X·스레드·페이스북에 재가공할 때 각 채널 규칙을 확인용.
    channel 미지정 시 전체.
    """
    if channel:
        return channels.get_spec(channel)
    return {"channels": {c: channels.get_spec(c) for c in channels.CHANNELS}}


@mcp.tool()
def validate_channel_post(
    channel: str,
    caption: str,
    hashtags: list[str] | None = None,
    image_count: int = 0,
) -> dict:
    """재가공한 채널별 초안이 규칙(길이·해시태그·이미지)에 맞는지 검증한다.
    Blotato 로 배포하기 전에 호출해 위반을 걸러낸다.
    """
    return channels.validate_post(channel, caption, hashtags, image_count)


@mcp.tool()
def assemble_channel_caption(
    channel: str, body: str, hashtags: list[str] | None = None
) -> dict:
    """채널 규칙에 맞게 본문+해시태그를 최종 캡션으로 조립한다."""
    return {"channel": channels.normalize_channel(channel),
            "caption": channels.assemble_caption(channel, body, hashtags)}


def main() -> None:
    """콘솔 스크립트 진입점. stdio 트랜스포트로 MCP 서버 실행."""
    mcp.run()


if __name__ == "__main__":
    main()
