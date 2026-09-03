"""게시 안전장치: 일일 상한 · 사람 같은 랜덤 지연.

계정 정지 리스크를 줄이기 위한 서버측 강제 장치. 실제 게시 경로에서만 호출된다.
"""

from __future__ import annotations

import random
import time
from typing import Any

from .db import count_posts_today


class DailyCapExceeded(Exception):
    """오늘 해당 플랫폼 게시 상한을 초과했을 때."""


# 플랫폼 절대 상한(계정 보호·ToS). policy 설정과 무관하게 이 이상은 막는다.
#  - instagram/facebook: Meta Graph API 콘텐츠 게시 한도(~50/24h)
#  - threads: 250/24h
#  - naver_blog: 저품질/정지 리스크가 커 보수적으로 낮게(하루 소량 권장)
PLATFORM_HARD_CAP = {
    "instagram": 50,
    "facebook": 50,
    "threads": 250,
    "naver_blog": 5,
}


def effective_cap(policy: dict[str, Any], platform: str) -> int | None:
    """policy 상한과 플랫폼 하드 캡 중 더 낮은 값. 둘 다 없으면 None."""
    policy_cap = policy.get("content", {}).get("daily_cap", {}).get(platform)
    hard = PLATFORM_HARD_CAP.get(platform)
    caps = [c for c in (policy_cap, hard) if c is not None]
    return min(caps) if caps else None


def check_daily_cap(policy: dict[str, Any], platform: str) -> None:
    """오늘 published 건수를 유효 상한(policy ∧ 플랫폼 하드캡)과 비교. 도달 시 차단."""
    cap = effective_cap(policy, platform)
    if cap is None:
        return
    today = count_posts_today(platform)
    if today >= cap:
        raise DailyCapExceeded(
            f"{platform} 오늘 게시 {today}건으로 일일 상한({cap}건) 도달. "
            f"계정 보호를 위해 게시를 중단합니다. 내일 다시 시도하거나 policy.yaml 의 "
            f"daily_cap.{platform} 을 조정하세요."
        )


def human_delay(policy: dict[str, Any]) -> None:
    """게시 직전 랜덤 지연(초). 봇처럼 즉시/규칙적으로 게시하지 않도록 한다.

    배치 간격(min_interval_min)은 스케줄러가 관리하고, 여기서는 게시 직전 지터만 추가한다.
    """
    time.sleep(random.uniform(2.0, 6.0))
