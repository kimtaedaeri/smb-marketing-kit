"""예약 발행 큐 (SQLite). 플랫폼 독립적인 저장소.

P1 무인화의 핵심: 사용자(+Claude)가 미리 만들고 승인한 게시물을 시간과 함께 큐에 넣으면,
러너(runner.py)가 예약 시각이 된 것을 골라 실제 발행한다. 발행 자체는 결정적이라 Claude 없이도 돈다.

큐는 db.DB_PATH(runs.db)에 별도 테이블로 저장한다.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

from . import db

_SCHEMA = """
CREATE TABLE IF NOT EXISTS scheduled_post (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    platform     TEXT    NOT NULL,          -- naver_blog | instagram | facebook
    payload_json TEXT    NOT NULL,          -- 플랫폼별 게시 인자
    scheduled_at TEXT    NOT NULL,          -- ISO 'YYYY-MM-DDTHH:MM:SS' (로컬)
    status       TEXT    NOT NULL DEFAULT 'scheduled', -- scheduled|published|failed|canceled
    result_json  TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_sched_due ON scheduled_post (status, scheduled_at);
"""


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(db.DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(_SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()


def add_scheduled(platform: str, payload: dict[str, Any], scheduled_at: str) -> int:
    """예약 항목 추가. scheduled_at 은 ISO 문자열. 반환: id."""
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO scheduled_post (platform, payload_json, scheduled_at) VALUES (?,?,?)",
            (platform, json.dumps(payload, ensure_ascii=False), scheduled_at),
        )
        return int(cur.lastrowid)


def _row(r: sqlite3.Row) -> dict[str, Any]:
    d = dict(r)
    d["payload"] = json.loads(d.pop("payload_json") or "{}")
    if d.get("result_json"):
        d["result"] = json.loads(d.pop("result_json"))
    else:
        d.pop("result_json", None)
    return d


def list_scheduled(status: str | None = "scheduled") -> list[dict[str, Any]]:
    with _conn() as con:
        if status:
            rows = con.execute(
                "SELECT * FROM scheduled_post WHERE status=? ORDER BY scheduled_at", (status,)
            ).fetchall()
        else:
            rows = con.execute("SELECT * FROM scheduled_post ORDER BY scheduled_at").fetchall()
    return [_row(r) for r in rows]


def cancel_scheduled(item_id: int) -> bool:
    with _conn() as con:
        cur = con.execute(
            "UPDATE scheduled_post SET status='canceled' WHERE id=? AND status='scheduled'",
            (item_id,),
        )
        return cur.rowcount > 0


def due_items(now: str | None = None) -> list[dict[str, Any]]:
    """예약 시각이 지난(<=now) scheduled 항목. now 미지정 시 현재 로컬시각."""
    now = now or datetime.now().isoformat(timespec="seconds")
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM scheduled_post WHERE status='scheduled' AND scheduled_at<=? "
            "ORDER BY scheduled_at",
            (now,),
        ).fetchall()
    return [_row(r) for r in rows]


def mark(item_id: int, status: str, result: dict[str, Any] | None = None) -> None:
    with _conn() as con:
        con.execute(
            "UPDATE scheduled_post SET status=?, result_json=? WHERE id=?",
            (status, json.dumps(result, ensure_ascii=False) if result else None, item_id),
        )
