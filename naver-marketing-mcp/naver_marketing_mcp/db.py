"""실행 로그 DB (SQLite).

모든 게시·입찰 이력을 키트 루트의 runs.db 에 남긴다. 일일 상한 강제의 근거로도 쓴다.
runs.db 는 .gitignore 로 커밋 차단된다.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterator

# db.py → naver_marketing_mcp → naver-marketing-mcp → 키트 루트(3단계 상위)
_KIT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = _KIT_ROOT / "runs.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS post_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    platform   TEXT    NOT NULL,
    title      TEXT,
    post_url   TEXT,
    status     TEXT    NOT NULL,          -- draft | published | failed
    error      TEXT,
    posted_on  TEXT    NOT NULL,          -- YYYY-MM-DD (일일 상한 계산용)
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_post_log_day
    ON post_log (platform, posted_on, status);
"""


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(DB_PATH)
    try:
        con.executescript(_SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()


def count_posts_today(platform: str, on: str | None = None) -> int:
    """오늘(local) 해당 플랫폼의 published 건수."""
    day = on or date.today().isoformat()
    with _conn() as con:
        (n,) = con.execute(
            "SELECT COUNT(*) FROM post_log "
            "WHERE platform = ? AND posted_on = ? AND status = 'published'",
            (platform, day),
        ).fetchone()
    return int(n)


def summary(days: int = 7) -> dict:
    """최근 N일 발행 요약(플랫폼×상태 건수). 성과 지표(도달·참여)는 계정 연결 후 확장."""
    from datetime import date, timedelta

    since = (date.today() - timedelta(days=days - 1)).isoformat()
    with _conn() as con:
        rows = con.execute(
            "SELECT platform, status, COUNT(*) FROM post_log WHERE posted_on >= ? "
            "GROUP BY platform, status",
            (since,),
        ).fetchall()
    by_platform: dict[str, dict[str, int]] = {}
    total_published = 0
    for platform, status, n in rows:
        by_platform.setdefault(platform, {})[status] = int(n)
        if status == "published":
            total_published += int(n)
    return {"since": since, "days": days,
            "total_published": total_published, "by_platform": by_platform}


def record_post(
    platform: str,
    status: str,
    title: str | None = None,
    post_url: str | None = None,
    error: str | None = None,
    on: str | None = None,
) -> int:
    """게시/시도 이력 1건 기록. 반환: row id."""
    day = on or date.today().isoformat()
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO post_log (platform, title, post_url, status, error, posted_on) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (platform, title, post_url, status, error, day),
        )
        return int(cur.lastrowid)
