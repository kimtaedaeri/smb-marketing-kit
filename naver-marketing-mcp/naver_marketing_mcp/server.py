"""naver-marketing-mcp MCP 서버 (FastMCP).

Claude Desktop/Code 에서 로컬로 실행되며 네이버 블로그 게시·파워링크 입찰 도구를 노출한다.
안전장치(승인 게이트·일일 상한·랜덤 지연·dry-run)는 서버에서 강제한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import (
    channels, db, facebook, instagram, meta_auth, naver_blog, powerlink,
    runner, scheduler, threads,
)
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

    # 수동 어시스트 모드(policy naver.mode=assist): 자동 발행 대신 붙여넣기용 초안 반환(정지 리스크 회피)
    if policy.get("naver", {}).get("mode") == "assist":
        return naver_blog.format_draft(title, body_markdown, tags, image_paths)

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
def naver_blog_draft(
    title: str,
    body_markdown: str,
    tags: list[str] | None = None,
    image_paths: list[str] | None = None,
) -> dict:
    """자동 발행 대신 '붙여넣기용 초안'을 만든다(수동 어시스트). 브라우저를 건드리지 않아 가장 안전.
    계정 정지 리스크가 부담될 때, 또는 자동화가 막혔을 때 폴백으로 사용.
    """
    return naver_blog.format_draft(title, body_markdown, tags, image_paths)


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
    """최근 N일 네이버 블로그·파워링크 성과를 수집한다. (도달·참여 지표는 계정 연결 후 확장)"""
    return {"status": "planned", "message": "도달·참여 지표는 계정 연결 후 확장됩니다. "
            "지금은 weekly_report 로 발행 이력 요약을 볼 수 있어요."}


# ────────────────────────────────────────────────────────────
# P1 무인화: 예약 발행 큐 + 러너 + 주간 리포트
# ────────────────────────────────────────────────────────────
@mcp.tool()
def schedule_post(platform: str, scheduled_at: str, payload: dict) -> dict:
    """게시물을 예약 큐에 넣는다(예약=승인). 러너가 시각이 되면 실제 발행한다.

    Args:
        platform: naver_blog | instagram | facebook
        scheduled_at: ISO 시각 'YYYY-MM-DDTHH:MM:SS' (로컬)
        payload: 플랫폼별 인자
            naver_blog: {title, body_markdown, tags?, image_paths?, private?, blog_id?}
            instagram/facebook: {image_urls, caption}
    """
    item_id = scheduler.add_scheduled(platform, payload, scheduled_at)
    return {"status": "scheduled", "id": item_id, "platform": platform, "scheduled_at": scheduled_at}


@mcp.tool()
def list_scheduled(status: str = "scheduled") -> dict:
    """예약된(또는 상태별) 게시물 목록. status: scheduled|published|failed|canceled|all"""
    return {"items": scheduler.list_scheduled(None if status == "all" else status)}


@mcp.tool()
def cancel_scheduled(item_id: int) -> dict:
    """예약 게시물 취소."""
    ok = scheduler.cancel_scheduled(item_id)
    return {"canceled": ok, "id": item_id}


@mcp.tool()
def run_scheduled_due() -> dict:
    """예약 시각이 지난 항목을 지금 발행한다(수동 실행/테스트용). 무인 실행은 launchd/cron 이 담당."""
    return runner.run_due()


@mcp.tool()
def weekly_report(days: int = 7) -> dict:
    """최근 N일 발행 이력 요약(플랫폼별 건수)."""
    return db.summary(days)


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
def set_instagram_token(access_token: str) -> dict:
    """수동 발급한 인스타 토큰(IGAA…로 시작)으로 연결한다. 계정 확인 후 저장.
    Instagram 설정 페이지의 '액세스 토큰 생성'에서 받은 토큰을 붙여넣을 때 사용.
    자세한 발급법: docs/인스타그램_연결_가이드.md
    """
    return meta_auth.set_instagram_token(access_token)


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
def set_threads_token(access_token: str) -> dict:
    """수동 발급한 스레드 토큰으로 연결한다(인스타와 별개 계정). Threads 설정의 '액세스 토큰 생성'에서 받은 토큰."""
    return meta_auth.set_threads_token(access_token)


@mcp.tool()
def threads_publish(text: str, image_urls: list[str] | None = None, approve: bool = False) -> dict:
    """스레드 게시. 텍스트만도 가능(이미지 없으면). approve=False 면 미리보기만."""
    if not approve:
        return {"status": "draft", "platform": "threads",
                "preview": {"text": text, "image_count": len(image_urls or [])},
                "next": "approve=True 로 다시 호출하면 게시됩니다."}
    policy = load_policy()
    try:
        check_daily_cap(policy, "threads")
    except DailyCapExceeded as e:
        return {"status": "blocked", "reason": str(e)}
    try:
        result = threads.publish(text, image_urls)
    except Exception as e:  # noqa: BLE001
        record_post("threads", status="failed", title=text[:40], error=str(e))
        return {"status": "failed", "error": str(e)}
    record_post("threads", status="published", title=text[:40], post_url=result.get("post_id"))
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
