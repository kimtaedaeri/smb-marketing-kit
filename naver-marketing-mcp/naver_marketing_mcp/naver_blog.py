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
import os
import platform
import random
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

_KIT_ROOT = Path(__file__).resolve().parents[2]
_AUTH_DIR = _KIT_ROOT / ".auth"
PROFILE_DIR = _AUTH_DIR / "chrome-profile"        # 임시 Chrome 프로파일
SESSION_JSON = _AUTH_DIR / "naver_state.json"     # 실제 세션(쿠키) 저장처 — 이게 진짜 소스

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
    "divider_btn": ".se-insert-horizontal-line-default-toolbar-button",  # 구분선
    "quote_btn": ".se-insert-quotation-default-toolbar-button",          # 인용구(삽입 블록)
    # 문단 스타일(본문/소제목/인용구)
    "style_trigger": "button.se-text-format-toolbar-button",
    "style_text": ".se-toolbar-option-text-format-text-button",
    "style_heading": ".se-toolbar-option-text-format-sectionTitle-button",
    "style_quote": ".se-toolbar-option-text-format-quotation-button",
    "font_trigger": "button.se-font-family-toolbar-button",  # 글꼴 바꾸기
    "publish_open_btn": "button.publish_btn__m9KHH",
    "tag_input": "input#tag-input",                 # 발행 패널 태그 입력
    "category_trigger": "button.selectbox_button__jb1Dt",  # 발행 패널 카테고리
    "publish_confirm_btn": "button.confirm_btn__WEaBq",
}

# 공개 설정 라디오 id 매핑
_VISIBILITY = {
    "public": "open_public", "neighbor": "open_neighbor",
    "both": "open_both_neighbor", "private": "open_private",
}

# 글꼴 이름 → 옵션 버튼 접미사 (SmartEditor ONE, 2026-09 실측)
# 나눔손글씨 계열(다시시작해, 바른히피, 우리딸손글씨)은 감성 글에 잘 어울린다.
_FONTS = {
    "기본서체": "system",
    "나눔고딕": "nanumgothic",
    "나눔명조": "nanummyeongjo",
    "나눔바른고딕": "nanumbarungothic",
    "나눔스퀘어": "nanumsquare",
    "마루부리": "nanummaruburi",
    "다시시작해": "nanumdasisijaghae",
    "바른히피": "nanumbareunhipi",
    "우리딸손글씨": "nanumuriddalsongeulssi",
}

_TYPE_DELAY = (0.03, 0.12)


def _human_pause(a: float = 0.4, b: float = 1.2) -> None:
    time.sleep(random.uniform(a, b))


def find_chrome() -> str:
    """OS별로 설치된 Google Chrome 실행파일을 찾는다(네이버 자동화용)."""
    system = platform.system()
    if system == "Darwin":
        cands = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    elif system == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        cands = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                 r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]
        if local:
            cands.append(local + r"\Google\Chrome\Application\chrome.exe")
    else:
        cands = ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
                 "/opt/google/chrome/chrome"]
    for c in cands:
        if Path(c).exists():
            return c
    for name in ("google-chrome", "google-chrome-stable", "chrome",
                 "chromium", "chromium-browser"):
        p = shutil.which(name)
        if p:
            return p
    raise RuntimeError(
        "Google Chrome 를 찾을 수 없습니다. 네이버 자동화에는 Chrome 이 필요합니다 — "
        "https://www.google.com/chrome 에서 설치 후 다시 시도해 주세요."
    )


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


_LOCK_FILE = _AUTH_DIR / "chrome.lock"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except Exception:  # noqa: BLE001
        return False


def _acquire_lock() -> None:
    """동시 브라우저 작업을 막는다(포트 9222·프로파일 충돌 방지)."""
    if _LOCK_FILE.exists():
        try:
            pid = int(_LOCK_FILE.read_text().strip())
        except Exception:  # noqa: BLE001
            pid = 0
        if pid and pid != os.getpid() and _pid_alive(pid):
            raise RuntimeError(
                "다른 네이버/브라우저 작업이 실행 중이에요. 끝난 뒤 다시 시도해 주세요."
            )
    _AUTH_DIR.mkdir(parents=True, exist_ok=True)
    _LOCK_FILE.write_text(str(os.getpid()))


def _release_lock() -> None:
    try:
        _LOCK_FILE.unlink()
    except Exception:  # noqa: BLE001
        pass


def _require(locator: Any, name: str, timeout: int = 8000) -> None:
    """중요 요소를 짧은 타임아웃으로 클릭. 없으면 30초 행 대신 즉시 명확한 에러."""
    try:
        locator.first.click(timeout=timeout)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            f"네이버 화면에서 '{name}' 을(를) 찾지 못했어요. 에디터가 바뀌었을 수 있습니다."
        ) from e


def launch_real_chrome(start_url: str = "") -> subprocess.Popen:
    """평범한 Chrome 을 원격 디버깅 포트와 함께 직접 실행(자동화 플래그 없음)."""
    _acquire_lock()
    _AUTH_DIR.mkdir(parents=True, exist_ok=True)
    args = [
        find_chrome(),
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if start_url:
        args.append(start_url)
    try:
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _wait_for_cdp()
    except Exception:
        _release_lock()
        raise
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
    finally:
        _release_lock()


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


def _blocks_to_text(blocks: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """blocks 를 붙여넣기용 텍스트와 이미지 경로 목록으로 변환."""
    lines: list[str] = []
    images: list[str] = []
    for blk in blocks:
        t = blk.get("type", "text")
        txt = (blk.get("text") or "").strip()
        if t == "heading" and txt:
            lines.append(f"[소제목] {txt}")
        elif t == "quote" and txt:
            lines.append(f"[인용구] {txt}")
        elif t == "divider":
            lines.append("———")
        elif t == "image" and blk.get("path"):
            images.append(blk["path"])
            lines.append(f"[사진] {blk['path']}")
        elif txt:
            lines.append(txt)
    return "\n\n".join(lines), images


def format_draft(
    title: str,
    body_markdown: str = "",
    tags: list[str] | None = None,
    image_paths: list[str] | None = None,
    blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """자동 발행 대신 '붙여넣기용 초안'을 만든다(수동 어시스트, 정지 리스크 회피 폴백).

    브라우저를 건드리지 않는다. blocks 가 있으면 서식 구조를 그대로 담는다.
    """
    tag_line = " ".join(f"#{t.lstrip('#').strip()}" for t in (tags or []) if t.strip())
    if blocks:
        body, imgs = _blocks_to_text(blocks)
    else:
        body, imgs = body_markdown.strip(), list(image_paths or [])
    parts = [f"[제목]\n{title}", f"[본문]\n{body}"]
    if tag_line:
        parts.append(f"[태그]\n{tag_line}")
    return {
        "status": "draft",
        "mode": "assist",
        "copy_text": "\n\n".join(parts),
        "image_paths": imgs,
        "how": "네이버 블로그 글쓰기에 위 내용을 붙여넣고, 이미지는 직접 첨부한 뒤 발행하세요. "
               "자동 발행보다 안전합니다(계정 보호).",
    }


def _set_style(frame: Any, style_key: str) -> None:
    """현재 문단 스타일을 바꾼다. style_key: style_text|style_heading|style_quote."""
    frame.locator(SELECTORS["style_trigger"]).first.click()
    _human_pause(0.3, 0.6)
    frame.locator(SELECTORS[style_key]).first.click()
    _human_pause(0.3, 0.6)


def _set_font(frame: Any, font_name: str) -> None:
    """이후 입력할 텍스트의 글꼴을 바꾼다. 선택 영역이 없으면 다음 타이핑부터 적용된다."""
    key = _FONTS.get(font_name)
    if not key:
        raise ValueError(
            f"지원하지 않는 글꼴이에요: {font_name}. 가능한 글꼴: {', '.join(_FONTS)}"
        )
    frame.locator(SELECTORS["font_trigger"]).first.click()
    _human_pause(0.3, 0.6)
    frame.locator(f"button.se-toolbar-option-font-family-{key}-button").first.click()
    _human_pause(0.3, 0.6)


def _insert_divider(frame: Any) -> None:
    """구분선을 커서 위치에 삽입."""
    frame.locator(SELECTORS["divider_btn"]).first.click()
    _human_pause(0.4, 0.8)


def _insert_quote(page: Any, frame: Any, text: str) -> None:
    """인용구는 문단 스타일이 아니라 '인용구 삽입' 블록이다. 삽입 후 텍스트를 넣고 빠져나온다."""
    frame.locator(SELECTORS["quote_btn"]).first.click()
    _human_pause(0.5, 0.9)
    _type_text(page, text)
    page.keyboard.press("Enter")   # 인용구 블록 종료(빈 줄이면 블록 밖으로)
    _human_pause(0.2, 0.4)


def _type_text(page: Any, text: str) -> None:
    """포커스된 contenteditable 에 사람 같은 지연으로 타이핑(여러 줄 지원)."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line:
            page.keyboard.type(line, delay=random.uniform(*_TYPE_DELAY) * 1000)
        if i < len(lines) - 1:
            page.keyboard.press("Enter")


def health_check(blog_id: str) -> dict[str, Any]:
    """글쓰기 화면을 열어 핵심 셀렉터가 여전히 유효한지 점검한다(네이버 UI 변경 조기 감지)."""
    if not session_exists():
        return {"ok": False, "reason": "no_session",
                "message": "먼저 connect_naver 로 로그인하세요."}
    from playwright.sync_api import sync_playwright

    checks: dict[str, bool] = {}
    proc = launch_real_chrome()
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            ctx = browser.contexts[0]
            _apply_saved_cookies(ctx)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(WRITE_URL.format(blog_id=blog_id), wait_until="domcontentloaded")
            time.sleep(6)
            if "nid.naver.com" in page.url or "nidlogin" in page.url:
                browser.close()
                return {"ok": False, "reason": "session_expired",
                        "message": "세션 만료 — connect_naver 로 다시 로그인하세요."}
            frame = page.frame_locator(SELECTORS["editor_iframe"])
            try:
                frame.locator(SELECTORS["body_area"]).first.click(timeout=8000)
                _human_pause(0.3, 0.6)
            except Exception:  # noqa: BLE001
                pass
            for label, key in [("제목", "title_area"), ("본문", "body_area"),
                               ("사진", "photo_btn"), ("구분선", "divider_btn"),
                               ("인용구", "quote_btn"), ("문단스타일", "style_trigger")]:
                try:
                    checks[label] = frame.locator(SELECTORS[key]).count() > 0
                except Exception:  # noqa: BLE001
                    checks[label] = False
            browser.close()
    finally:
        _stop_chrome(proc)
    missing = [k for k, v in checks.items() if not v]
    return {"ok": not missing, "checks": checks, "missing": missing,
            "message": "모든 핵심 요소 정상" if not missing
                       else f"바뀐 것으로 보이는 요소: {', '.join(missing)}"}


def publish(
    blog_id: str,
    title: str,
    body_markdown: str = "",
    tags: list[str] | None = None,
    image_paths: list[str] | None = None,
    blocks: list[dict[str, Any]] | None = None,
    category: str | None = None,       # 발행 카테고리 이름(정확히 일치)
    visibility: str | None = None,     # public|neighbor|both|private (없으면 private 파라미터 사용)
    font: str | None = None,           # 본문 기본 글꼴(예: 마루부리, 우리딸손글씨). None 이면 네이버 기본
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

    # 브라우저를 띄우기 전에 글꼴 이름부터 빠르게 검증(잘못된 이름이면 즉시 안내)
    if font and font not in _FONTS:
        raise ValueError(
            f"지원하지 않는 글꼴이에요: {font}. 가능한 글꼴: {', '.join(_FONTS)}"
        )

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

            # 세션 만료 감지: 로그인 페이지로 튕겼으면 즉시 명확히 안내(30초 행 방지)
            if "nid.naver.com" in page.url or "nidlogin" in page.url:
                browser.close()
                raise RuntimeError(
                    "네이버 세션이 만료됐어요. connect_naver 로 다시 로그인해 주세요."
                )

            frame = page.frame_locator(SELECTORS["editor_iframe"])
            inserted_images = 0
            tags_added = 0
            blocks_failed: list[dict[str, Any]] = []
            category_applied: bool | None = None
            published = False   # 최종 발행 클릭 이후엔 실패로 보고하지 않는다
            try:
                # 이어쓰기(작성 중 글) 팝업 dismiss — '취소'로 새 글 시작
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

                # 제목
                _require(frame.locator(SELECTORS["title_area"]), "제목 입력칸")
                _human_pause(0.4, 0.9)
                _type_text(page, title)

                # 본문
                _require(frame.locator(SELECTORS["body_area"]), "본문 입력칸")
                _human_pause(0.4, 0.9)
                # 본문 기본 글꼴(타이핑 전에 지정해야 이후 입력에 적용된다)
                if font:
                    _set_font(frame, font)
                if blocks:
                    for i, blk in enumerate(blocks):
                        t = blk.get("type", "text")
                        txt = (blk.get("text") or "").strip()
                        try:
                            blk_font = blk.get("font")
                            if blk_font and t in ("text", "heading", "quote"):
                                _set_font(frame, blk_font)  # 문단별 글꼴 지정(예: 인용구만 손글씨)
                            if t == "image":
                                if not blk.get("path"):
                                    continue
                                _insert_one_image(page, frame, blk["path"])
                                inserted_images += 1
                                page.keyboard.press("Enter")
                            elif t == "divider":
                                _insert_divider(frame)
                            elif t == "quote":
                                if not txt:
                                    continue
                                _insert_quote(page, frame, txt)
                            elif t == "heading":
                                if not txt:
                                    continue
                                _set_style(frame, "style_heading")
                                _type_text(page, txt)
                                page.keyboard.press("Enter")
                                _set_style(frame, "style_text")  # 다음 문단은 본문
                            else:  # text
                                if not txt:
                                    continue
                                _type_text(page, txt)
                                page.keyboard.press("Enter")
                        except Exception as e:  # noqa: BLE001
                            blocks_failed.append({"index": i, "type": t, "error": str(e)[:80]})
                        _human_pause(0.3, 0.7)
                else:
                    _type_text(page, body_markdown)
                    _human_pause(0.6, 1.2)
                    if image_paths:
                        inserted_images = _insert_images(page, frame, image_paths)
                        _human_pause(0.6, 1.2)

                # 발행 설정 패널 열기
                _require(frame.locator(SELECTORS["publish_open_btn"]), "발행 설정 버튼")
                time.sleep(2.0)

                # 카테고리(정확 일치). 불일치/실패는 category_applied=False 로 알린다
                if category:
                    category_applied = False
                    try:
                        frame.locator(SELECTORS["category_trigger"]).first.click()
                        _human_pause(0.4, 0.8)
                        exact = re.compile(rf"^{re.escape(category)}$")
                        frame.locator("label.radio_label__mB6ia", has_text=exact
                                      ).first.click(timeout=3000)
                        category_applied = True
                        _human_pause(0.3, 0.6)
                    except Exception:  # noqa: BLE001
                        category_applied = False

                # 태그
                if tags:
                    tags_added = _add_tags(page, frame, tags)
                    _human_pause(0.3, 0.7)

                # 공개 범위: visibility 우선, 없으면 private. 전체공개는 기본 선택이라 스킵
                vis = visibility or ("private" if private else "public")
                if vis not in _VISIBILITY:
                    raise RuntimeError(
                        f"visibility 값이 잘못됐어요: {vis} (public/neighbor/both/private 중 하나)"
                    )
                if vis != "public":
                    frame.locator(f'label[for="{_VISIBILITY[vis]}"]').click()
                    _human_pause(0.3, 0.7)

                # 최종 발행 — 이 클릭 이후엔 후처리 실패가 있어도 이중발행하지 않도록 published 표시
                _require(frame.locator(SELECTORS["publish_confirm_btn"]), "최종 발행 버튼")
                published = True

                # 글 URL 회수(발행 시 하위 프레임이 글 페이지로 이동)
                def _looks_post(u: str) -> bool:
                    if not u or "Write" in u or "PostWriteForm" in u:
                        return False
                    last = u.rstrip("/").split("/")[-1].split("?")[0]
                    return "logNo=" in u or "PostView" in u or (blog_id in u and last.isdigit())

                def _find_post_url() -> str | None:
                    for f in page.frames:
                        if _looks_post(f.url):
                            return f.url
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

                try:
                    deadline = time.time() + 20
                    while time.time() < deadline:
                        post_url = _find_post_url()
                        if post_url:
                            break
                        time.sleep(1.0)
                    page.screenshot(path=str(shot))
                except Exception:  # noqa: BLE001
                    pass  # 발행은 끝났으니 후처리(URL·스크린샷) 실패는 무시
            except Exception:
                # 실패 시 진단용 스크린샷을 남긴다
                try:
                    page.screenshot(path=str(_AUTH_DIR / "last_error_screen.png"))
                except Exception:  # noqa: BLE001
                    pass
                if not published:
                    raise
                # 이미 발행됨 → 후처리 예외는 실패로 재발생시키지 않는다(이중발행 방지)
            browser.close()
    finally:
        _stop_chrome(proc)

    result = {
        "status": "published",
        "private": private,
        "visibility": visibility or ("private" if private else "public"),
        "post_url": post_url,
        "images_inserted": inserted_images,
        "tags_added": tags_added,
        "screenshot": str(shot),
    }
    if category is not None:
        result["category_applied"] = category_applied
    if blocks_failed:
        result["blocks_failed"] = blocks_failed
    return result
