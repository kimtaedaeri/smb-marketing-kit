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


def check_daily_cap(policy: dict[str, Any], platform: str) -> None:
    """policy 의 content.daily_cap[platform] 과 오늘 published 건수를 비교.

    상한 도달 시 DailyCapExceeded 를 던져 게시를 막는다.
    상한 미설정(None)이면 통과하되, 설정을 권장한다.
    """
    cap = policy.get("content", {}).get("daily_cap", {}).get(platform)
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
