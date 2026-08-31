"""게시 안전장치: 일일 상한 · 사람 같은 랜덤 지연.

계정 정지 리스크를 줄이기 위한 서버측 강제 장치. 실제 게시 경로에서만 호출된다.
"""

from __future__ import annotations

import time
from typing import Any

# NOTE: 결정론적 랜덤이 필요 없으므로 표준 random 사용.
import random


class DailyCapExceeded(Exception):
    """오늘 해당 플랫폼 게시 상한을 초과했을 때."""


def check_daily_cap(policy: dict[str, Any], platform: str) -> None:
    """policy 의 content.daily_cap[platform] 과 오늘 게시 수를 비교.

    TODO(P0): runs.db(SQLite)에서 오늘 게시 건수를 조회해 상한과 비교.
    지금은 상한값 존재 여부만 확인하는 골격.
    """
    cap = (
        policy.get("content", {})
        .get("daily_cap", {})
        .get(platform)
    )
    if cap is None:
        return  # 상한 미설정 → 통과 (단, 설정 권장)
    # TODO: today_count = count_posts_today(platform); if today_count >= cap: raise
    return


def human_delay(policy: dict[str, Any]) -> None:
    """게시 직전 랜덤 지연(초). min_interval_min 을 기준으로 소폭 무작위화.

    봇처럼 즉시/규칙적으로 게시하지 않도록 한다.
    """
    base_min = policy.get("content", {}).get("min_interval_min", 0)
    if not base_min:
        # 최소한의 자연스러운 지연
        time.sleep(random.uniform(1.5, 4.0))
        return
    # 실제 배치 스케줄러에서 간격을 관리하되, 게시 직전 소량 지터만 추가
    time.sleep(random.uniform(2.0, 6.0))
