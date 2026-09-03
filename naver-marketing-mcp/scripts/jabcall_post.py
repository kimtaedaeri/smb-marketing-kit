"""잽콜 홍보 실게시: 인스타 캐러셀 + 스레드(이미지)."""

from __future__ import annotations

import json

from naver_marketing_mcp import instagram, threads
from naver_marketing_mcp.naver_blog import _AUTH_DIR
from scripts.jabcall_repurpose import INSTAGRAM, IG_TAGS, THREADS
from naver_marketing_mcp import channels

data = json.loads((_AUTH_DIR / "jab_urls.json").read_text())
urls = data["urls"]
ordered = [urls["home"], urls["combo"], urls["stats"]]

ig_caption = channels.assemble_caption("instagram", INSTAGRAM, IG_TAGS)

print("=== INSTAGRAM (캐러셀 3장) ===")
try:
    print(instagram.publish(ordered, ig_caption))
except Exception as e:  # noqa: BLE001
    print("IG_ERR:", repr(e))

print("\n=== THREADS (이미지 1장) ===")
try:
    print(threads.publish(THREADS, [urls["home"]]))
except Exception as e:  # noqa: BLE001
    print("TH_ERR:", repr(e))
