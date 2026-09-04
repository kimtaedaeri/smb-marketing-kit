"""예약 발행 러너: 예약 시각이 된 항목을 실제 발행한다.

launchd/cron/GitHub Actions 가 주기적으로 호출한다(발행은 결정적이라 Claude 없이 돈다):
    python -m naver_marketing_mcp.runner

각 항목은 사용자가 미리 만들고 승인해 큐에 넣은 것이다(예약=승인). 일일 상한·페이싱은 여기서도 강제.
"""

from __future__ import annotations

from typing import Any

from . import scheduler
from .db import record_post
from .policy import load_policy
from .safety import DailyCapExceeded, check_daily_cap, human_delay


def _dispatch(platform: str, payload: dict[str, Any]) -> dict[str, Any]:
    if platform == "naver_blog":
        from . import naver_blog
        blog_id = payload.get("blog_id") or load_policy().get("naver", {}).get("blog_id")
        return naver_blog.publish(
            blog_id=blog_id, title=payload["title"],
            body_markdown=payload.get("body_markdown", ""), tags=payload.get("tags"),
            image_paths=payload.get("image_paths"), blocks=payload.get("blocks"),
            category=payload.get("category"), visibility=payload.get("visibility"),
            font=payload.get("font"), private=payload.get("private", False),
            # schedule_at 은 큐가 시각을 관리하므로 여기선 넘기지 않는다(즉시 발행)
        )
    if platform == "instagram":
        from . import instagram
        return instagram.publish(payload["image_urls"], payload["caption"])
    if platform == "facebook":
        from . import facebook
        return facebook.publish(payload["image_urls"], payload["caption"])
    raise ValueError(f"알 수 없는 플랫폼: {platform}")


def run_due(now: str | None = None) -> dict[str, Any]:
    """예약 시각이 된 항목을 발행하고 결과 요약을 반환."""
    policy = load_policy()
    items = scheduler.due_items(now)
    results = []
    for it in items:
        plat = it["platform"]
        try:
            check_daily_cap(policy, plat)
        except DailyCapExceeded as e:
            scheduler.mark(it["id"], "failed", {"reason": str(e)})
            record_post(plat, "failed", error=str(e))
            results.append({"id": it["id"], "platform": plat, "status": "blocked", "reason": str(e)})
            continue
        human_delay(policy)
        try:
            res = _dispatch(plat, it["payload"])
            scheduler.mark(it["id"], "published", res)
            record_post(plat, "published", post_url=res.get("post_url"))
            results.append({"id": it["id"], "platform": plat, "status": "published",
                            "post_url": res.get("post_url")})
        except Exception as e:  # noqa: BLE001
            scheduler.mark(it["id"], "failed", {"error": str(e)})
            record_post(plat, "failed", error=str(e))
            results.append({"id": it["id"], "platform": plat, "status": "failed", "error": str(e)})
    return {"processed": len(items), "results": results}


def main() -> None:
    import json
    print(json.dumps(run_due(), ensure_ascii=False))


if __name__ == "__main__":
    main()
