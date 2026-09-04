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


def test_scheduler_due_and_cancel(tmp_db: Path) -> None:
    db.DB_PATH = tmp_db
    from naver_marketing_mcp import scheduler
    past = scheduler.add_scheduled("naver_blog", {"title": "t"}, "2000-01-01T00:00:00")
    future = scheduler.add_scheduled("instagram", {"caption": "c"}, "2999-01-01T00:00:00")
    due = scheduler.due_items()
    assert [d["id"] for d in due] == [past], "지난 항목만 due 여야 함"
    assert scheduler.cancel_scheduled(future) is True
    assert scheduler.cancel_scheduled(future) is False, "이미 취소된 건 다시 취소 안 됨"
    assert {i["id"] for i in scheduler.list_scheduled("canceled")} == {future}


def test_hard_cap(tmp_db: Path) -> None:
    db.DB_PATH = tmp_db
    from naver_marketing_mcp.safety import DailyCapExceeded, check_daily_cap, effective_cap
    assert effective_cap({}, "instagram") == 50, "policy 없어도 하드캡 적용"
    assert effective_cap({"content": {"daily_cap": {"instagram": 3}}}, "instagram") == 3, "더 낮은 값"
    policy = {"content": {"daily_cap": {"instagram": 1}}}
    db.record_post("instagram", status="published")
    try:
        check_daily_cap(policy, "instagram")
    except DailyCapExceeded:
        pass
    else:
        raise AssertionError("상한 도달인데 통과")


def test_summary(tmp_db: Path) -> None:
    db.DB_PATH = tmp_db
    db.record_post("naver_blog", status="published")
    db.record_post("instagram", status="failed", error="x")
    s = db.summary(7)
    assert s["total_published"] == 1
    assert s["by_platform"]["naver_blog"]["published"] == 1


def test_naver_draft(_tmp: Path) -> None:
    from naver_marketing_mcp.naver_blog import format_draft
    d = format_draft("제목", "본문 내용", ["a", "#b"], ["/x.png"])
    assert d["status"] == "draft" and d["mode"] == "assist"
    assert "[제목]" in d["copy_text"] and "#a #b" in d["copy_text"]
    assert d["image_paths"] == ["/x.png"]


def test_images_url_passthrough(_tmp: Path) -> None:
    from naver_marketing_mcp import images
    assert images.is_url("https://x/y.jpg") and not images.is_url("/a/b.png")
    # URL 은 처리 없이 그대로 통과(네트워크 불필요)
    assert images.prep_for_instagram(["https://x/y.jpg"]) == ["https://x/y.jpg"]


def test_parse_schedule(_tmp: Path) -> None:
    from datetime import datetime, timedelta
    from naver_marketing_mcp.naver_blog import _parse_schedule
    far = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    # 10분 단위 반올림
    assert _parse_schedule(f"{far} 09:07").minute == 10
    assert _parse_schedule(f"{far} 09:02").minute == 0
    # 59분은 다음 시각 00분으로 올림
    d = _parse_schedule(f"{far} 09:56")
    assert d.hour == 10 and d.minute == 0
    # 과거와 형식 오류는 거부
    for bad in ["2020-01-01 09:00", "not-a-date"]:
        try:
            _parse_schedule(bad)
            raise AssertionError(f"거부돼야 함: {bad}")
        except ValueError:
            pass


def _run() -> None:
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            with tempfile.TemporaryDirectory() as d:
                fn(Path(d) / "runs.db")
            print(f"  ✓ {name}")
    print("모든 스모크 테스트 통과")


if __name__ == "__main__":
    _run()
