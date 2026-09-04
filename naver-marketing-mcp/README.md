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
| `naver_blog_publish` | 블로그 글 게시 — 제목, 본문, 이미지, 태그, 소제목/인용구/구분선 서식, 글꼴, 카테고리, 공개범위, 예약발행. 기본 **승인 게이트** | ✅ 검증 |
| `naver_blog_draft` | 붙여넣기용 초안만 생성(브라우저 미사용, 가장 안전한 폴백) | ✅ 검증 |
| `naver_health_check` | 글쓰기 화면을 열어 핵심 버튼과 입력창이 그대로인지 점검(발행 안 함) | ✅ 검증 |
| `powerlink_bidding` | 파워링크 입찰 1회 실행(dry-run 지원) | 🔨 브리지(설치 시 연결) |
| `collect_performance` | 네이버 성과 수집 | 🔜 P1 |

> ✅ 실제 로그인 세션에서 발행까지 검증 완료(SmartEditor ONE). 🔨 = 골격.

### 네이버 블로그 발행 방식 (검증됨)

- **로그인**: Playwright 직접실행 대신 진짜 Chrome 을 원격디버깅 포트로 켜고 CDP attach → 자동화 탐지 회피. 세션은 쿠키 JSON(`.auth/naver_state.json`)으로 저장·주입.
- **에디터**: SmartEditor ONE(`iframe#mainFrame`) — 제목/본문 입력, 사진(로컬 업로드), 태그, 공개범위, 발행까지 자동.

### 감성 서식과 발행 옵션 (검증됨)

- **서식 블록**: `blocks` 로 본문, 소제목, 인용구, 구분선, 사진을 원하는 순서대로 배치. 글과 사진이 번갈아 나오는 자연스러운 글을 만든다.
- **글꼴**: `font` 로 본문 기본 글꼴 지정. 기본서체, 나눔고딕, 나눔명조, 나눔바른고딕, 나눔스퀘어, 마루부리, 다시시작해, 바른히피, 우리딸손글씨 중 선택. 블록마다 `{"font":"..."}` 로 다르게 줄 수도 있다(예: 인용구만 손글씨체).
- **카테고리와 공개범위**: `category`(블로그의 카테고리 이름과 정확히 일치), `visibility`(public/neighbor/both/private).
- **예약발행**: `schedule_at="YYYY-MM-DD HH:MM"` 으로 네이버 네이티브 예약. 네이버 서버가 그 시각에 자동 발행하므로 PC를 켜 둘 필요가 없다. 분은 10분 단위로 반올림되며 지금부터 최소 10분 뒤여야 한다.

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
