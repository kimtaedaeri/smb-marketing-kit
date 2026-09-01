"""평범한 Chrome(CDP attach)으로 네이버 로그인 창을 띄우고 세션을 프로파일에 유지한다.

- 비밀번호 저장 안 함(세션 쿠키는 Chrome 전용 프로파일 안에만).
- 로그인 후 블로그 아이디를 자동 감지해 출력한다(DETECTED_BLOG_ID=...).
- 실행: .venv/bin/python -m scripts.login_naver
"""

from __future__ import annotations

from naver_marketing_mcp.naver_blog import login


def main() -> None:
    print(">> 평범한 Chrome 창을 엽니다. 네이버에 직접 로그인해 주세요 (최대 5분 대기)...", flush=True)
    result = login(timeout_sec=300)
    print(">> 로그인/세션 저장 완료.", flush=True)
    print(f"DETECTED_BLOG_ID={result.get('blog_id', '')}", flush=True)


if __name__ == "__main__":
    main()
