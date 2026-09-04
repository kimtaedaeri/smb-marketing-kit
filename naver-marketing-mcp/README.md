# naver-marketing-mcp

Claude에서 **네이버 블로그 게시**와 **파워링크 입찰**을 대화로 호출하는 **로컬** MCP 서버.
Blotato·Higgsfield가 못 하는 한국 갭만 담당합니다.

## 왜 로컬인가
- 네이버 블로그는 공식 게시 API가 없어 **브라우저 자동화(Playwright)** 가 필요합니다.
- 로컬·**사장님 자기 IP·단일 계정**으로 돌면 봇 탐지/정지 리스크가 서버 실행보다 훨씬 낮습니다.
- 로그인 세션은 로컬(`.auth/`)에만 저장하고, 비밀번호는 저장하지 않으며, 외부로 보내지 않습니다.

## 도구 (P0)

| 도구 | 설명 | 상태 |
| --- | --- | --- |
| `connect_naver` | 네이버 로그인(진짜 Chrome 창, 최초 1회, 쿠키 세션 저장) | ✅ 검증 |
| `naver_blog_publish` | 블로그 글 게시 — 제목·본문·**이미지·태그**·공개/비공개, 기본 **승인 게이트** | ✅ 검증 |
| `powerlink_bidding` | 파워링크 입찰 1회 실행(dry-run 지원) | 🔨 브리지(설치 시 연결) |
| `collect_performance` | 네이버 성과 수집 | 🔜 P1 |

> ✅ 실제 로그인 세션에서 발행까지 검증 완료(SmartEditor ONE). 🔨 = 골격.

### 네이버 블로그 발행 방식 (검증됨)

- **로그인**: Playwright 직접실행 대신 진짜 Chrome 을 원격디버깅 포트로 켜고 CDP attach → 자동화 탐지 회피. 세션은 쿠키 JSON(`.auth/naver_state.json`)으로 저장·주입.
- **에디터**: SmartEditor ONE(`iframe#mainFrame`) — 제목/본문 입력, 사진(로컬 업로드), 태그, 공개범위, 발행까지 자동.

## 설치

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium
claude mcp add naver-marketing -- python -m naver_marketing_mcp
```

## 안전장치 (코드에 내장)
- **승인 게이트**: `naver_blog_publish(approve=False)` 는 초안만 반환, `approve=True` 여야 실제 게시.
- **일일 상한 + 랜덤 지연**: `policy.yaml` 의 `daily_cap`·`min_interval_min` 을 서버가 강제.
- **dry-run**: 파워링크는 기본 `dry_run=True`.
