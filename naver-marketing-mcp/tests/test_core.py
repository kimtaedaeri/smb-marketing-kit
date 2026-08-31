"""핵심 로직 스모크 테스트 (네트워크·브라우저 불필요).

db 카운트/기록, 일일 상한 강제, policy 로딩만 검증한다.
실행: cd naver-marketing-mcp && python -m tests.test_core
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from naver_marketing_mcp import db
from naver_marketing_mcp.safety import DailyCapExceeded, check_daily_cap


def test_record_and_count(tmp_db: Path) -> None:
    db.DB_PATH = tmp_db
    assert db.count_posts_today("naver_blog") == 0
    db.record_post("naver_blog", status="published", title="t1")
    db.record_post("naver_blog", status="failed", title="t2")  # 실패는 카운트 제외
    assert db.count_posts_today("naver_blog") == 1


def test_daily_cap_blocks(tmp_db: Path) -> None:
    db.DB_PATH = tmp_db
    policy = {"content": {"daily_cap": {"naver_blog": 1}}}
    db.record_post("naver_blog", status="published", title="t1")
    try:
        check_daily_cap(policy, "naver_blog")
    except DailyCapExceeded:
        pass
    else:
        raise AssertionError("상한 도달인데 차단되지 않음")


def test_cap_none_passes(tmp_db: Path) -> None:
    db.DB_PATH = tmp_db
    check_daily_cap({"content": {"daily_cap": {}}}, "naver_blog")  # 예외 없어야 함


def _run() -> None:
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            with tempfile.TemporaryDirectory() as d:
                fn(Path(d) / "runs.db")
            print(f"  ✓ {name}")
    print("모든 스모크 테스트 통과")


if __name__ == "__main__":
    _run()
