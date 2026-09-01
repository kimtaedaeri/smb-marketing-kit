"""네이버 블로그 브라우저 자동화 (Playwright + CDP attach + 쿠키 주입).

네이버는 Playwright 가 '직접 실행'한 Chrome(--enable-automation)을 자동화로 탐지해 로그인을
막고 "지원되지 않는 명령줄 플래그" 경고를 띄운다. 그래서 **우리가 평범한 Chrome 을 직접 켜고
(원격 디버깅 포트만 열고), Playwright 가 CDP 로 attach** 한다 — 네이버 입장에선 일반 크롬.

세션 유지: macOS 키체인 암호화 탓에 Chrome 프로파일 디스크 저장이 재실행 때 안 풀리는 이슈가
있어, **로그인 시 쿠키를 우리 JSON(.auth/naver_state.json)에 저장**하고, 게시/확인 때 그 쿠키를
진짜 크롬에 **주입**한다(키체인 비의존). JSON 은 .gitignore 로 커밋 차단.

⚠️ 셀렉터는 SELECTORS 에 격리. SmartEditor ONE 본문 입력은 로그인 세션에서 1회 검증 필요.
"""

from __future__ import annotations

import json
import random
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

_KIT_ROOT = Path(__file__).resolve().parents[2]
_AUTH_DIR = _KIT_ROOT / ".auth"
PROFILE_DIR = _AUTH_DIR / "chrome-profile"        # 임시 Chrome 프로파일
SESSION_JSON = _AUTH_DIR / "naver_state.json"     # 실제 세션(쿠키) 저장처 — 이게 진짜 소스

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CDP_PORT = 9222
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"

LOGIN_URL = "https://nid.naver.com/nidlogin.login"
WRITE_URL = "https://blog.naver.com/{blog_id}?Redirect=Write&"

SELECTORS = {
    "editor_iframe": "iframe#mainFrame",
    "title_area": ".se-title-text .se-text-paragraph",
    "body_area": ".se-component.se-text .se-text-paragraph",
    "publish_open_btn": "button.publish_btn__m9KHH, button:has-text('발행')",
    "publish_confirm_btn": "button.confirm_btn__WEaBq, button:has-text('발행'):visible",
    "tag_input": "input#tag-input, .tag_input__rvUB5",
}

_TYPE_DELAY = (0.03, 0.12)


def _human_pause(a: float = 0.4, b: float = 1.2) -> None:
    time.sleep(random.uniform(a, b))


# ── 세션(쿠키) 저장/로드 ──────────────────────────────────────
def session_exists() -> bool:
    return SESSION_JSON.exists()


def _save_state(ctx: Any) -> None:
    _AUTH_DIR.mkdir(parents=True, exist_ok=True)
    ctx.storage_state(path=str(SESSION_JSON))


def _apply_saved_cookies(ctx: Any) -> None:
    """저장된 쿠키를 현재 컨텍스트에 주입."""
    if not SESSION_JSON.exists():
        return
    state = json.loads(SESSION_JSON.read_text(encoding="utf-8"))
    cookies = state.get("cookies", [])
    if cookies:
        ctx.add_cookies(cookies)


def _is_logged_in(ctx: Any) -> bool:
    """네이버 로그인 쿠키(NID_AUT) 존재로 로그인 여부 판정."""
    try:
        return any(c.get("name") == "NID_AUT" for c in ctx.cookies())
    except Exception:  # noqa: BLE001
        return False


def _detect_blog_id(ctx: Any) -> str:
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://blog.naver.com/MyBlog.naver", wait_until="domcontentloaded")
        time.sleep(2.0)
        tail = page.url.split("blog.naver.com/")[-1]
        return tail.split("?")[0].split("/")[0].strip()
    except Exception:  # noqa: BLE001
        return ""


# ── Chrome 실행/종료 ─────────────────────────────────────────
def _wait_for_cdp(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=1)
            return
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    raise RuntimeError("Chrome 원격 디버깅 포트(CDP) 준비 실패.")


def launch_real_chrome(start_url: str = "") -> subprocess.Popen:
    """평범한 Chrome 을 원격 디버깅 포트와 함께 직접 실행(자동화 플래그 없음)."""
    _AUTH_DIR.mkdir(parents=True, exist_ok=True)
    args = [
        CHROME_BIN,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if start_url:
        args.append(start_url)
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _wait_for_cdp()
    return proc


def _stop_chrome(proc: subprocess.Popen) -> None:
    try:
        proc.terminate()
        proc.wait(timeout=15)
    except Exception:  # noqa: BLE001
        try:
            proc.kill()
        except Exception:  # noqa: BLE001
            pass


# ── 로그인 / 세션 확인 / 게시 ────────────────────────────────
def login(timeout_sec: int = 300) -> dict[str, Any]:
    """평범한 Chrome 로그인 창을 띄우고, 로그인되면 쿠키를 JSON 에 저장한다.
    비밀번호는 저장하지 않는다. 로그인 후 블로그 아이디를 자동 감지해 반환.
    """
    from playwright.sync_api import sync_playwright

    proc = launch_real_chrome(LOGIN_URL)
    blog_id = ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            ctx = browser.contexts[0]

            deadline = time.time() + timeout_sec
            while time.time() < deadline:
                if _is_logged_in(ctx):
                    break
                time.sleep(1.5)
            else:
                raise TimeoutError("제한 시간 안에 로그인이 완료되지 않았습니다.")

            blog_id = _detect_blog_id(ctx)
            _save_state(ctx)  # 쿠키를 JSON 으로 저장 (진짜 소스)
            browser.close()
    finally:
        _stop_chrome(proc)

    return {"status": "logged_in", "blog_id": blog_id, "session_file": str(SESSION_JSON)}


def save_session(blog_id: str = "", timeout_sec: int = 300) -> str:
    """server.connect_naver 호환 래퍼."""
    result = login(timeout_sec=timeout_sec)
    detected = result.get("blog_id") or blog_id or "(미지정)"
    return f"네이버 세션 저장 완료. blog_id={detected}"


def check_session() -> dict[str, Any]:
    """저장된 쿠키를 주입해 현재 로그인 상태인지 빠르게 확인(대기 없음)."""
    from playwright.sync_api import sync_playwright

    if not session_exists():
        return {"status": "no_session"}
    proc = launch_real_chrome()
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            ctx = browser.contexts[0]
            _apply_saved_cookies(ctx)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("https://www.naver.com", wait_until="domcontentloaded")
            time.sleep(1.5)
            logged_in = _is_logged_in(ctx)
            blog_id = _detect_blog_id(ctx) if logged_in else ""
            browser.close()
    finally:
        _stop_chrome(proc)
    return {"status": "logged_in" if logged_in else "logged_out", "blog_id": blog_id}


def publish(
    blog_id: str,
    title: str,
    body_markdown: str,
    tags: list[str] | None = None,
    image_paths: list[str] | None = None,
    headless: bool = False,  # CDP attach 방식에선 실제 창을 띄운다(무시됨)
) -> dict[str, Any]:
    """저장된 쿠키를 주입한 진짜 크롬으로 글쓰기 페이지를 열고 게시한다.

    실제 SmartEditor DOM 상호작용은 로그인 세션에서 1회 검증 후 활성화(아래 TODO).
    검증 전까지는 글쓰기 페이지를 열고 초안/스크린샷을 반환한다.
    """
    if not session_exists():
        raise RuntimeError("네이버 세션이 없습니다. 먼저 connect_naver 로 로그인해 주세요.")

    from playwright.sync_api import sync_playwright

    proc = launch_real_chrome()
    shot = _AUTH_DIR / "last_write_screen.png"
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            ctx = browser.contexts[0]
            _apply_saved_cookies(ctx)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(WRITE_URL.format(blog_id=blog_id), wait_until="domcontentloaded")
            _human_pause(1.0, 2.5)

            frame = page.frame_locator(SELECTORS["editor_iframe"])  # noqa: F841 — 검증 후 사용

            # TODO(검증필요): SmartEditor ONE 셀렉터 확정 후 제목/본문/이미지/태그/발행 활성화.

            try:
                page.screenshot(path=str(shot))
            except Exception:  # noqa: BLE001
                pass
            browser.close()
    finally:
        _stop_chrome(proc)

    return {
        "status": "needs_verification",
        "message": "글쓰기 화면까지 열었습니다. SmartEditor 셀렉터 검증 후 자동 입력이 활성화됩니다.",
        "screenshot": str(shot),
        "draft": {"title": title, "body_markdown": body_markdown, "tags": tags or []},
    }
