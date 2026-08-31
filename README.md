# SMB Marketing Kit

> 소상공인 사장님이 **Claude Desktop / Claude Code에 설치**해, **대화만으로**
> 네이버 검색광고 입찰과 인스타·링크드인·**네이버 블로그** 콘텐츠 발행을 자동화하는 로컬 키트.

이 키트는 "전부 직접 만들기"가 아니라 **최고 도구를 오케스트레이션**하는 접근입니다.
생성(Higgsfield)과 글로벌 배포(Blotato)는 이미 훌륭한 호스티드 MCP가 있으니 **커넥터로 연결만** 하고,
우리는 그들이 못 하는 **한국 갭**(네이버 블로그 자동 게시 · 네이버 파워링크 입찰)만 코드로 채웁니다.

---

## 두 갈래 안내

### 🧑‍💼 사장님이라면 (비개발자)

코드를 몰라도 됩니다. Claude에게 이렇게만 말하세요:

```
이 폴더의 셋업 마법사로 나 마케팅 자동화 셋업해줘
```

Claude가 브랜드 보이스 인터뷰 → 계정 연결 → 첫 게시 미리보기까지 대화로 안내합니다.
자세한 건 [`docs/QUICKSTART_사장님.md`](docs/QUICKSTART_사장님.md).

### 🧑‍💻 개발자라면

로컬 MCP 서버(`naver-marketing-mcp/`)를 설치하고 커넥터 2개를 등록합니다.
[`connectors.md`](connectors.md) → [`naver-marketing-mcp/README.md`](naver-marketing-mcp/README.md).

---

## 무엇을 하나 (릴스 4단계 → 이 키트)

| 단계 | 이 키트의 구현 |
| --- | --- |
| 1️⃣ **브랜드 보이스 이식** | 인터뷰형 추출 → [`brand_voice.template.md`](brand_voice.template.md) → 프로젝트에 상시 로드 |
| 2️⃣ **MCP 도구 연결** | [Higgsfield](https://higgsfield.ai/mcp)(생성) · [Blotato](https://www.blotato.com/mcp)(9플랫폼 배포) 커넥터 등록 + `naver-marketing-mcp` 로컬 설치 |
| 3️⃣ **카루셀 제작 + 게시** | Higgsfield 생성 → Blotato(IG·링크드인) **+ 네이버 블로그(이 키트)** |
| 4️⃣ **루틴 무인화** | "매주 월 8시 7개 생성·예약" — 스케줄러 + **승인 게이트** |
| ➕ **퍼포먼스(유료)** | 네이버 **파워링크 입찰 자동화** (릴스엔 없는, 유료광고 자동화) |

## 아키텍처

```
Claude Desktop/Code  = 브레인 + 브랜드보이스 + 루틴
   ├── [커넥터·등록만] Higgsfield MCP   → 이미지·영상 생성 (Nano Banana Pro / Veo 3.1)
   ├── [커넥터·등록만] Blotato MCP      → 글로벌 9플랫폼 게시 (공식 API)
   └── [이 레포가 만드는 유일한 코드] naver-marketing-mcp (로컬)
         • naver_blog_publish   Playwright · 세션재사용 · 페이싱상한 · 승인게이트
         • powerlink_bidding    파워링크 입찰 (naver-powerlink-bidding 통합)
         • collect_performance  네이버 성과 수집 (P1)
```

로컬·자기 IP·단일 계정 실행이라 네이버 브라우저 자동화의 계정 정지 리스크를 구조적으로 억제합니다.
Blotato는 각 플랫폼 공식 API 기반이라 안전합니다.

## 안전 원칙 (중요)

- **기본은 반자동**: 생성 → 미리보기 → **사장님 승인** → 게시. 전자동은 명시적 opt-in.
- **크리덴셜은 로컬만**: OS 키체인 저장, 클라우드로 절대 전송 안 함. `.env`·세션 파일은 커밋 금지.
- **게시 페이싱 상한**: 일일 게시 수 제한 + 랜덤 지연으로 봇 탐지 회피.
- 본인 계정으로 **본인 사업**을 마케팅하는 정당 용도 한정. 스팸·대량계정 기능 없음.

## 로드맵

- **P0** — 브랜드보이스 셋업 · 커넥터 연결 · 네이버 블로그 반자동 게시 · 파워링크 입찰 · 셋업 마법사
- **P1** — 루틴 무인화(스케줄러) · 성과 폐루프(수집→개선제안) · 콘텐츠 캘린더
- **P2** — 전자동 opt-in · 멀티 유료채널(Meta·카카오) · 성과 대시보드 · 제품화

## 라이선스

MIT — [`LICENSE`](LICENSE)
