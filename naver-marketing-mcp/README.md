# naver-marketing-mcp

Claude에서 **네이버 블로그 게시**와 **파워링크 입찰**을 대화로 호출하는 **로컬** MCP 서버.
Blotato·Higgsfield가 못 하는 한국 갭만 담당합니다.

## 왜 로컬인가
- 네이버 블로그는 공식 게시 API가 없어 **브라우저 자동화(Playwright)** 가 필요합니다.
- 로컬·**사장님 자기 IP·단일 계정**으로 돌면 봇 탐지/정지 리스크가 서버 실행보다 훨씬 낮습니다.
- 로그인 세션·비밀번호는 **OS 키체인**에만 저장하고 절대 외부로 보내지 않습니다.

## 도구 (P0)

| 도구 | 설명 | 상태 |
| --- | --- | --- |
| `connect_naver` | 네이버 로그인(최초 1회, 세션 저장) | 🔨 스텁 |
| `naver_blog_publish` | 블로그 글 게시 — 기본 **승인 게이트**(초안 미리보기 후 게시) | 🔨 스텁 |
| `powerlink_bidding` | 파워링크 입찰 1회 실행(dry-run 지원) | 🔨 스텁 (naver-powerlink-bidding 통합 예정) |
| `collect_performance` | 네이버 성과 수집 | 🔜 P1 |

> 🔨 = 인터페이스·안전장치 골격 완성, 실제 자동화 로직은 다음 단계에서 구현.

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
