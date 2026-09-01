"""채널별 재가공 규격·검증·조립 (결정적 로직).

블로그 글을 여러 SNS에 재가공할 때, 채널마다 다른 제약(길이·해시태그·이미지)을 코드로 강제한다.
실제 요약/카피 문장 생성은 Claude(두뇌)가 브랜드보이스+아래 spec 을 보고 수행하고,
이 모듈은 그 결과가 규칙에 맞는지 검증·조립한다. 배포는 Blotato MCP 가 담당.

Blotato 지원 플랫폼 중 텍스트 재가공 대상만 정의(영상 전용 TikTok/YouTube 제외).
"""

from __future__ import annotations

from typing import Any

# 채널 규격. max_caption=하드 상한, target_length=권장 분량, hashtags=권장 개수.
CHANNELS: dict[str, dict[str, Any]] = {
    "instagram": {
        "max_caption": 2200,
        "target_length": 800,
        "hashtags": 5,
        "image_aspect": "1:1 또는 4:5",
        "images_required": True,
        "tone": "에너지 있고 친근한 톤, 첫 문장 훅, 이모지 적극, 해시태그 5개",
    },
    "linkedin": {
        "max_caption": 3000,
        "target_length": 1400,
        "hashtags": 3,
        "image_aspect": "1.91:1(가로) 또는 1:1",
        "images_required": False,
        "tone": "1인칭 비즈니스 스토리, 인사이트·배움 중심, 전문적, 해시태그 3개 이하",
    },
    "threads": {
        "max_caption": 500,
        "target_length": 300,
        "hashtags": 3,
        "image_aspect": "1:1 또는 4:5",
        "images_required": False,
        "tone": "대화체·짧고 리듬감, 후킹 첫 줄",
    },
    "x": {
        "max_caption": 280,
        "target_length": 240,
        "hashtags": 2,
        "image_aspect": "16:9 또는 1:1",
        "images_required": False,
        "tone": "한 문장 핵심, 압축, 해시태그 1~2개",
    },
    "facebook": {
        "max_caption": 2000,
        "target_length": 600,
        "hashtags": 2,
        "image_aspect": "1.91:1 또는 1:1",
        "images_required": False,
        "tone": "정보+공감, 링크 유도 가능",
    },
}

# 별칭
_ALIAS = {"ig": "instagram", "li": "linkedin", "twitter": "x", "fb": "facebook"}


def normalize_channel(channel: str) -> str:
    c = channel.strip().lower()
    return _ALIAS.get(c, c)


def get_spec(channel: str) -> dict[str, Any]:
    c = normalize_channel(channel)
    if c not in CHANNELS:
        raise ValueError(f"지원하지 않는 채널: {channel} (가능: {', '.join(CHANNELS)})")
    return {"channel": c, **CHANNELS[c]}


def assemble_caption(channel: str, body: str, hashtags: list[str] | None = None) -> str:
    """채널 규칙에 맞게 최종 캡션을 조립한다.

    - instagram/threads/x/facebook: 본문 + 빈 줄 + 해시태그
    - linkedin: 해시태그를 본문 끝에 붙이되 개수 절제
    """
    c = normalize_channel(channel)
    tags = [f"#{t.lstrip('#').strip()}" for t in (hashtags or []) if t.strip()]
    rec = CHANNELS.get(c, {}).get("hashtags", 0)
    tags = tags[:rec] if rec else []
    body = body.strip()
    if not tags:
        return body
    return f"{body}\n\n{' '.join(tags)}"


def validate_post(
    channel: str,
    caption: str,
    hashtags: list[str] | None = None,
    image_count: int = 0,
) -> dict[str, Any]:
    """채널 규칙 위반을 검사. {ok, errors[], warnings[]} 반환."""
    spec = get_spec(channel)
    errors: list[str] = []
    warnings: list[str] = []

    if len(caption) > spec["max_caption"]:
        errors.append(
            f"캡션 {len(caption)}자 > 상한 {spec['max_caption']}자 초과"
        )
    n_tags = len([t for t in (hashtags or []) if t.strip()])
    if n_tags > spec["hashtags"]:
        warnings.append(
            f"해시태그 {n_tags}개 > 권장 {spec['hashtags']}개"
        )
    if spec["images_required"] and image_count < 1:
        errors.append(f"{spec['channel']}는 이미지가 최소 1장 필요")

    return {"ok": not errors, "channel": spec["channel"], "errors": errors, "warnings": warnings}
