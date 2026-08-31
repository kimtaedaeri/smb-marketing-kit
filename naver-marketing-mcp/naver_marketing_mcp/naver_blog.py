"""네이버 블로그 브라우저 자동화 (Playwright).

네이버는 공식 블로그 게시 API가 없어 브라우저 자동화로 처리한다.
정지 리스크를 줄이기 위해 **로컬·헤드리스 아님(headed)·세션 재사용·사람 같은 지연**을 기본으로 한다.

⚠️ 셀렉터는 모두 이 파일 상단 SELECTORS 에 격리한다. 네이버 UI(SmartEditor ONE)는
iframe 중첩이 잦고 자주 바뀌므로, 여기만 고치면 되도록 한다. 본문 입력 플로우는
실제 로그인 세션에서 1회 검증(record → replay)이 필요하다 — 아래 publish() 주석 참조.
"""

from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any

# db.py 와 동일 규칙: 키트 루트 하위 .auth/ 에 세션 저장 (.gitignore 로 차단됨)
_KIT_ROOT = Path(__file__).resolve().parents[2]
_AUTH_DIR = _KIT_ROOT / ".auth"
SESSION_PATH = _AUTH_DIR / "naver_storage_state.json"

LOGIN_URL = "https://nid.naver.com/nidlogin.login"
BLOG_HOME = "https://blog.naver.com/{blog_id}"
WRITE_URL = "https://blog.naver.com/{blog_id}?Redirect=Write&"

# ── 셀렉터 격리 구역 (UI 변경 시 여기만 수정) ──────────────────
SELECTORS = {
    # SmartEditor ONE 은 mainFrame iframe 안에서 동작
    "editor_iframe": "iframe#mainFrame",
    "title_area": ".se-title-text .se-text-paragraph",
    "body_area": ".se-component.se-text .se-text-paragraph",
    "publish_open_btn": "button.publish_btn__m9KHH, button:has-text('발행')",
    "publish_confirm_btn": "button.confirm_btn__WEaBq, button:has-text('발행'):visible",
    "tag_input": "input#tag-input, .tag_input__rvUB5",
}

# 사람 같은 타이핑 지연(초) 범위
_TYPE_DELAY = (0.03, 0.12)


def _human_pause(a: float = 0.4, b: float = 1.2) -> None:
    time.sleep(random.uniform(a, b))


def session_exists() -> bool:
    return SESSION_PATH.exists()


def save_session(blog_id: str, timeout_sec: int = 180) -> str:
    """헤드풀 브라우저로 네이버 로그인 창을 띄우고, 사용자가 직접 로그인하면
    세션(storage_state)을 저장한다. 비밀번호는 저장하지 않는다(세션 쿠키만).

    보안·정지리스크 상 자동 로그인 타이핑은 하지 않고 **사용자 수동 로그인**을 기다린다.
    (네이버는 자동 입력 로그인에 캡차·2단계를 자주 요구한다.)
    """
    from playwright.sync_api import sync_playwright

    _AUTH_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(LOGIN_URL)

        # 로그인 완료(블로그 홈 접근 가능) 될 때까지 대기
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            if "nid.naver.com" not in page.url:
                break
            time.sleep(1.5)
        else:
            browser.close()
            raise TimeoutError(
                "제한 시간 안에 로그인이 완료되지 않았습니다. 다시 시도해 주세요."
            )

        ctx.storage_state(path=str(SESSION_PATH))
        browser.close()
    return f"네이버 세션 저장 완료: {SESSION_PATH.name} (blog_id={blog_id})"


def publish(
    blog_id: str,
    title: str,
    body_markdown: str,
    tags: list[str] | None = None,
    image_paths: list[str] | None = None,
    headless: bool = False,
) -> dict[str, Any]:
    """저장된 세션으로 블로그 글을 게시하고 URL 을 반환한다.

    실제 SmartEditor DOM 상호작용은 로그인 세션에서 1회 검증이 필요하다:
      1) `playwright codegen https://blog.naver.com/{id}?Redirect=Write` 로 실제 클릭/입력을 녹화
      2) 녹화된 셀렉터로 위 SELECTORS 를 확정
      3) 아래 TODO 블록을 그 셀렉터로 채운다
    검증 전까지는 글쓰기 페이지까지 열고 초안 데이터를 반환해 사람이 확인/게시하도록 한다.
    """
    if not session_exists():
        raise RuntimeError(
            "네이버 세션이 없습니다. 먼저 connect_naver 로 로그인해 주세요."
        )

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(storage_state=str(SESSION_PATH))
        page = ctx.new_page()
        page.goto(WRITE_URL.format(blog_id=blog_id))
        _human_pause(1.0, 2.5)

        frame = page.frame_locator(SELECTORS["editor_iframe"])

        # TODO(검증필요): 아래는 SmartEditor ONE 기준 초안. codegen 으로 셀렉터 확정 후 활성화.
        # frame.locator(SELECTORS["title_area"]).click()
        # page.keyboard.type(title, delay=random.uniform(*_TYPE_DELAY) * 1000)
        # _human_pause()
        # frame.locator(SELECTORS["body_area"]).click()
        # for line in md_to_lines(body_markdown):
        #     page.keyboard.type(line, delay=random.uniform(*_TYPE_DELAY) * 1000)
        #     page.keyboard.press("Enter")
        # if image_paths: _insert_images(page, frame, image_paths)
        # if tags: _fill_tags(frame, tags)
        # frame.locator(SELECTORS["publish_open_btn"]).click(); _human_pause()
        # frame.locator(SELECTORS["publish_confirm_btn"]).click()
        # post_url = _wait_for_post_url(page)

        # 검증 전 안전 폴백: 글쓰기 화면까지 열어두고 스크린샷 저장, 사람이 확인.
        shot = _AUTH_DIR / "last_write_screen.png"
        try:
            page.screenshot(path=str(shot))
        except Exception:
            pass
        browser.close()

    return {
        "status": "needs_verification",
        "message": (
            "글쓰기 화면까지 열었습니다. SmartEditor 셀렉터 검증(codegen) 후 자동 입력이 "
            "활성화됩니다. 그 전까지는 초안을 사람이 붙여넣어 게시하세요."
        ),
        "screenshot": str(shot),
        "draft": {"title": title, "body_markdown": body_markdown, "tags": tags or []},
    }
