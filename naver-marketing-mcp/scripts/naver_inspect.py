"""네이버 글쓰기 페이지의 팝업/버튼을 덤프 + 스크린샷."""

from __future__ import annotations

import json
import time

from playwright.sync_api import sync_playwright

from naver_marketing_mcp.naver_blog import (
    CDP_URL, WRITE_URL, _AUTH_DIR, _apply_saved_cookies, _stop_chrome, launch_real_chrome,
)
from naver_marketing_mcp.policy import load_policy

blog_id = load_policy().get("naver", {}).get("blog_id") or "gyfhx"
JS = r"""
() => {
  const desc = e => ({tag:e.tagName.toLowerCase(), cls:(e.className||'').toString().slice(0,90), txt:(e.innerText||'').trim().slice(0,40)});
  const vis = e => e.offsetParent !== null;
  const pops = [...document.querySelectorAll('[class*="popup"],[class*="dim"],[class*="layer"]')].filter(vis).map(desc).slice(0,20);
  const btns = [...document.querySelectorAll('button')].filter(e=>vis(e) && (e.innerText||'').trim()).map(desc).slice(0,30);
  return {pops, btns};
}
"""

proc = launch_real_chrome()
try:
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        ctx = b.contexts[0]
        _apply_saved_cookies(ctx)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(WRITE_URL.format(blog_id=blog_id), wait_until="domcontentloaded")
        el = page.wait_for_selector("iframe#mainFrame", timeout=20000)
        time.sleep(6)
        mf = el.content_frame()
        if mf:
            print(json.dumps(mf.evaluate(JS), ensure_ascii=False, indent=1))
        page.screenshot(path=str(_AUTH_DIR / "naver_popup.png"))
        print("SHOT:", _AUTH_DIR / "naver_popup.png")
        b.close()
finally:
    _stop_chrome(proc)
