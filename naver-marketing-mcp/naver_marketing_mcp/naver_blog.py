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

# ✅ 실제 로그인 세션에서 검증 완료 (SmartEditor ONE, 2026-09)
SELECTORS = {
    "editor_iframe": "iframe#mainFrame",
    "title_area": ".se-section-documentTitle .se-text-paragraph",
    "body_area": ".se-section-text .se-text-paragraph",
    "photo_btn": "button.se-image-toolbar-button",  # 로컬 사진 추가 → OS 파일창
    "image_component": ".se-image",                 # 업로드된 이미지 컴포넌트
    "publish_open_btn": "button.publish_btn__m9KHH",
    "tag_input": "input#tag-input",                 # 발행 패널 태그 입력
    "private_radio": 'label[for="open_private"]',
    "publish_confirm_btn": "button.confirm_btn__WEaBq",
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


def _insert_images(page: Any, frame: Any, image_paths: list[str]) -> int:
    """본문 커서 위치에 로컬 이미지들을 삽입한다. 삽입된 이미지 컴포넌트 수 반환.

    '사진' 버튼 클릭 → OS 파일 선택창을 Playwright 가 가로채 파일을 넣는다(한 번에 여러 장).
    업로드 완료(이미지 컴포넌트 등장)를 기다린다.
    """
    init = frame.locator(SELECTORS["image_component"]).count()
    for path in image_paths:
        _insert_one_image(page, frame, path)
    return frame.locator(SELECTORS["image_component"]).count() - init


def _insert_one_image(page: Any, frame: Any, path: str) -> None:
    """이미지 1장을 현재 커서 위치에 삽입한다(멀티 첨부 팝업 회피 위해 항상 한 장씩)."""
    prev = frame.locator(SELECTORS["image_component"]).count()
    with page.expect_file_chooser(timeout=15000) as fc:
        frame.locator(SELECTORS["photo_btn"]).first.click()
    fc.value.set_files(path)
    deadline = time.time() + 40
    while time.time() < deadline:
        if frame.locator(SELECTORS["image_component"]).count() > prev:
            break
        time.sleep(1.0)
    _human_pause(1.0, 2.0)


def _add_tags(page: Any, frame: Any, tags: list[str]) -> int:
    """발행 패널 태그 입력에 태그를 추가한다(각 태그 입력 후 Enter). 추가한 개수 반환."""
    added = 0
    inp = frame.locator(SELECTORS["tag_input"])
    inp.click()
    for t in tags[:30]:
        t = t.lstrip("#").strip()
        if not t:
            continue
        page.keyboard.type(t, delay=random.uniform(*_TYPE_DELAY) * 1000)
        page.keyboard.press("Enter")
        time.sleep(0.3)
        added += 1
    return added


def format_draft(
    title: str,
    body_markdown: str,
    tags: list[str] | None = None,
    image_paths: list[str] | None = None,
) -> dict[str, Any]:
    """자동 발행 대신 '붙여넣기용 초안'을 만든다(수동 어시스트 · 정지 리스크 회피 폴백).

    브라우저를 건드리지 않는다. 사장님이 네이버 글쓰기에 직접 붙여넣으면 된다.
    """
    tag_line = " ".join(f"#{t.lstrip('#').strip()}" for t in (tags or []) if t.strip())
    parts = [f"[제목]\n{title}", f"[본문]\n{body_markdown.strip()}"]
    if tag_line:
        parts.append(f"[태그]\n{tag_line}")
    copy_text = "\n\n".join(parts)
    return {
        "status": "draft",
        "mode": "assist",
        "copy_text": copy_text,
        "image_paths": image_paths or [],
        "how": "네이버 블로그 글쓰기에 위 [제목]/[본문]을 붙여넣고, 이미지는 직접 첨부한 뒤 발행하세요. "
               "자동 발행보다 안전합니다(계정 보호).",
    }


def _type_text(page: Any, text: str) -> None:
    """포커스된 contenteditable 에 사람 같은 지연으로 타이핑(여러 줄 지원)."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line:
            page.keyboard.type(line, delay=random.uniform(*_TYPE_DELAY) * 1000)
        if i < len(lines) - 1:
            page.keyboard.press("Enter")


def publish(
    blog_id: str,
    title: str,
    body_markdown: str = "",
    tags: list[str] | None = None,
    image_paths: list[str] | None = None,
    blocks: list[dict[str, Any]] | None = None,  # [{type:text,text}|{type:image,path}] 순서대로
    private: bool = True,      # 기본 비공개(안전). 공개는 명시적으로 False.
    headless: bool = False,    # CDP attach 방식에선 실제 창을 띄운다(무시됨)
) -> dict[str, Any]:
    """저장된 쿠키를 주입한 진짜 크롬으로 네이버 블로그 글을 게시한다.

    SmartEditor ONE(iframe#mainFrame) 구조:
      - 제목: .se-section-documentTitle .se-text-paragraph
      - 본문: .se-section-text .se-text-paragraph
      - 발행 패널 열기: button.publish_btn__m9KHH
      - 공개범위 비공개: label[for="open_private"]
      - 최종 발행: button.confirm_btn__WEaBq
    """
    if not session_exists():
        raise RuntimeError("네이버 세션이 없습니다. 먼저 connect_naver 로 로그인해 주세요.")

    from playwright.sync_api import sync_playwright

    proc = launch_real_chrome()
    shot = _AUTH_DIR / "last_write_screen.png"
    post_url = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            ctx = browser.contexts[0]
            _apply_saved_cookies(ctx)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.on("dialog", lambda d: d.accept())  # 확인 팝업 자동 수락
            page.goto(WRITE_URL.format(blog_id=blog_id), wait_until="domcontentloaded")
            time.sleep(6)  # SmartEditor 로딩

            frame = page.frame_locator(SELECTORS["editor_iframe"])

            # 이어쓰기(작성 중 글) 팝업 dismiss — '취소'(se-popup-button-cancel)로 새 글 시작
            try:
                mf_el = page.query_selector("iframe#mainFrame")
                mff = mf_el.content_frame() if mf_el else None
                if mff:
                    btn = mff.wait_for_selector("button.se-popup-button-cancel", timeout=4000)
                    if btn:
                        btn.click(force=True)
                        _human_pause(0.6, 1.1)
            except Exception:  # noqa: BLE001
                pass

            # 제목 입력
            frame.locator(SELECTORS["title_area"]).first.click()
            _human_pause(0.4, 0.9)
            _type_text(page, title)

            # 본문 입력
            frame.locator(SELECTORS["body_area"]).first.click()
            _human_pause(0.4, 0.9)
            inserted_images = 0
            if blocks:
                # 글→이미지→글→이미지… 순서대로 삽입 (자연스러운 배치)
                for blk in blocks:
                    if blk.get("type") == "image" and blk.get("path"):
                        _insert_one_image(page, frame, blk["path"])
                        inserted_images += 1
                        page.keyboard.press("Enter")  # 이미지 뒤 새 줄
                    else:
                        _type_text(page, blk.get("text", ""))
                        page.keyboard.press("Enter")
                    _human_pause(0.3, 0.7)
            else:
                _type_text(page, body_markdown)
                _human_pause(0.6, 1.2)
                if image_paths:
                    inserted_images = _insert_images(page, frame, image_paths)
                    _human_pause(0.6, 1.2)

            # 발행 설정 패널 열기
            frame.locator(SELECTORS["publish_open_btn"]).first.click()
            time.sleep(2.0)

            # 태그 추가
            tags_added = 0
            if tags:
                tags_added = _add_tags(page, frame, tags)
                _human_pause(0.3, 0.7)

            # 공개범위: 비공개(기본) / False 면 전체공개(기본 선택) 유지
            if private:
                frame.locator(SELECTORS["private_radio"]).click()
                _human_pause(0.3, 0.7)

            # 최종 발행
            frame.locator(SELECTORS["publish_confirm_btn"]).click()

            # 발행 후 글 URL 로 이동 대기. 편집기가 iframe 이라 발행 시 top page 가 아니라
            # 하위 프레임이 글 페이지로 이동한다 → 모든 프레임에서 글 URL 패턴을 스캔.
            def _looks_post(u: str) -> bool:
                if not u or "Write" in u or "PostWriteForm" in u:
                    return False
                last = u.rstrip("/").split("/")[-1].split("?")[0]
                return "logNo=" in u or "PostView" in u or (blog_id in u and last.isdigit())

            def _find_post_url() -> str | None:
                for f in page.frames:
                    if _looks_post(f.url):
                        return f.url
                # og:url / canonical (게시 후 글 페이지)
                for f in page.frames:
                    try:
                        og = f.evaluate(
                            "() => { const m=document.querySelector('meta[property=\"og:url\"]');"
                            " const c=document.querySelector('link[rel=canonical]');"
                            " return (m&&m.content)||(c&&c.href)||''; }"
                        )
                        if _looks_post(og):
                            return og
                    except Exception:  # noqa: BLE001
                        pass
                return None

            deadline = time.time() + 20
            while time.time() < deadline:
                post_url = _find_post_url()
                if post_url:
                    break
                time.sleep(1.0)
            try:
                page.screenshot(path=str(shot))
            except Exception:  # noqa: BLE001
                pass
            browser.close()
    finally:
        _stop_chrome(proc)

    return {
        "status": "published",
        "private": private,
        "post_url": post_url,
        "images_inserted": inserted_images,
        "tags_added": tags_added,
        "screenshot": str(shot),
    }
