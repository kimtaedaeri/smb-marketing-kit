"""잽콜 네이버 블로그 실게시(이미지 포함, 공개)."""

from __future__ import annotations

from naver_marketing_mcp import naver_blog
from naver_marketing_mcp.policy import load_policy
from scripts.jabcall_repurpose import NAVER_BODY, NAVER_TITLE, NB_TAGS

blog_id = load_policy().get("naver", {}).get("blog_id") or "gyfhx"
imgs = [
    "/Users/macrent/Downloads/IMG_4308.PNG",
    "/Users/macrent/Downloads/IMG_4309.PNG",
    "/Users/macrent/Downloads/IMG_4310.PNG",
]

res = naver_blog.publish(
    blog_id=blog_id, title=NAVER_TITLE, body_markdown=NAVER_BODY,
    tags=NB_TAGS, image_paths=imgs, private=False,
)
print("RESULT:", res)
