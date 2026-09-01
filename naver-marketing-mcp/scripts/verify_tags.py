"""발행 패널에서 태그 입력만 검증(발행 X): 태그 칩이 실제로 붙는지 스크린샷."""

from __future__ import annotations

import time

from playwright.sync_api import sync_playwright

from naver_marketing_mcp.naver_blog import (
    CDP_URL,
    SELECTORS,
    WRITE_URL,
    _AUTH_DIR,
    _add_tags,
    _apply_saved_cookies,
    _stop_chrome,
    launch_real_chrome,
)
from naver_marketing_mcp.policy import load_policy


def main() -> None:
    blog_id = load_policy().get("naver", {}).get("blog_id")
    proc = launch_real_chrome()
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            ctx = browser.contexts[0]
            _apply_saved_cookies(ctx)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(WRITE_URL.format(blog_id=blog_id), wait_until="domcontentloaded")
            page.wait_for_selector("iframe#mainFrame", timeout=20000)
            time.sleep(6)
            frame = page.frame_locator("iframe#mainFrame")
            frame.locator(SELECTORS["publish_open_btn"]).first.click()
            time.sleep(2)
            n = _add_tags(page, frame, ["마케팅자동화", "테스트", "smb"])
            time.sleep(1)
            page.screenshot(path=str(_AUTH_DIR / "verify_tags.png"))
            print("TAGS_ADDED:", n)
            browser.close()  # 발행하지 않고 종료
    finally:
        _stop_chrome(proc)


if __name__ == "__main__":
    main()
