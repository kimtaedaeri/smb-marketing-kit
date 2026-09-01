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


def test_channel_validate_length(_tmp: Path) -> None:
    from naver_marketing_mcp.channels import validate_post
    r = validate_post("x", "가" * 300, image_count=1)  # 280 초과
    assert not r["ok"] and r["errors"], "X 280자 초과인데 통과됨"


def test_channel_instagram_requires_image(_tmp: Path) -> None:
    from naver_marketing_mcp.channels import validate_post
    r = validate_post("instagram", "짧은 캡션", hashtags=["a"], image_count=0)
    assert not r["ok"], "인스타 이미지 0장인데 통과됨"
    r2 = validate_post("instagram", "짧은 캡션", hashtags=["a"], image_count=1)
    assert r2["ok"], "인스타 이미지 1장인데 실패"


def test_channel_assemble_and_alias(_tmp: Path) -> None:
    from naver_marketing_mcp.channels import assemble_caption, get_spec
    cap = assemble_caption("ig", "본문입니다", ["#a", "b", "c", "d", "e", "f"])
    assert cap.count("#") == 5, "인스타 해시태그 5개로 절제 안 됨"
    assert get_spec("twitter")["channel"] == "x", "별칭 정규화 실패"


def _run() -> None:
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            with tempfile.TemporaryDirectory() as d:
                fn(Path(d) / "runs.db")
            print(f"  ✓ {name}")
    print("모든 스모크 테스트 통과")


if __name__ == "__main__":
    _run()
