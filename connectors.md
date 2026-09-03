# 커넥터 연결 가이드

이 키트는 3개의 MCP를 씁니다. 2개는 **등록만**, 1개는 **로컬 설치**입니다.

| MCP | 역할 | 방식 | 비용 |
| --- | --- | --- | --- |
| [Higgsfield MCP](https://higgsfield.ai/mcp) | 이미지·영상 생성 (Nano Banana Pro, Veo 3.1, Seedance 2.0) | 호스티드 · OAuth 원클릭 | 유료(크레딧) |
| [Blotato MCP](https://www.blotato.com/mcp) | 글로벌 9플랫폼 게시 (IG·링크드인·X·틱톡·유튜브·스레드·페북·핀터레스트·블루스카이) | 호스티드 · 공식 API | 유료(구독) |
| **naver-marketing-mcp** (이 레포) | **네이버 블로그 게시 · 파워링크 입찰** | **로컬 설치** | 무료 |

> 왜 Blotato만으로 안 되나: Blotato 9플랫폼에 **네이버가 없습니다**(서구권 툴, 공식 API 기반).
> 네이버 블로그는 공식 게시 API가 없어 **로컬 브라우저 자동화**가 필요 → 이 키트의 핵심 차별점.

## 1. Higgsfield 연결 (생성)

1. https://higgsfield.ai → MCP and CLI 탭 → Claude connector 링크 복사
2. Claude → Settings → Connectors → Add Custom Connector → 붙여넣기 → 인증(OAuth)
3. 엔드포인트: `https://mcp.higgsfield.ai/mcp`

## 2. Blotato 연결 (배포)

1. https://www.blotato.com → 계정 생성 후 게시할 SNS 계정들 연결
2. MCP 엔드포인트 `https://mcp.blotato.com/mcp` 를 Claude 커넥터에 등록 → 인증
3. 참고: [Blotato MCP 셋업](https://help.blotato.com/api/mcp/setup)

## 3. naver-marketing-mcp 설치 (네이버 갭)

**한 줄 설치(권장, uvx):** `uv` 설치 후(`curl -LsSf https://astral.sh/uv/install.sh | sh`)
```bash
claude mcp add smb-marketing -- uvx smb-marketing-naver-mcp
```
클론·venv 불필요. **Google Chrome** 설치만 필요(네이버 자동화용).

개발자용 소스 설치는 [`naver-marketing-mcp/README.md`](naver-marketing-mcp/README.md) 참고.

## 로그인 방식 (플랫폼마다 다름 — 하이브리드)

"모든 플랫폼이 똑같이 로그인"하지 않습니다. 공식 API 유무에 따라 두 방식으로 갈립니다.

| 플랫폼 | 로그인 방식 | 흐름 |
| --- | --- | --- |
| **네이버 블로그** | **브라우저 로그인 창 팝업** (공식 게시 API 없음) | Claude에 `네이버 로그인해줘` → `connect_naver`가 **실제 네이버 로그인 창을 띄움** → 사장님이 **직접 로그인**(비번·2단계·캡차 본인이) → 세션만 로컬 `.auth/`에 저장(비번 저장 X) → 이후 게시는 세션 재사용, 재로그인 불필요 |
| **인스타·링크드인·X 등** | **Blotato 커넥터 연결** (공식 API) | blotato.com에서 **계정을 한 번 연결**(OAuth) → 이후 Claude가 Blotato를 통해 게시. 우리가 로그인 창을 띄우지 않음 |

> 왜 다른가: 인스타는 **공식 API가 있어** Blotato로 안전·안정적으로 처리되므로 브라우저 로그인 창이 불필요합니다.
> 네이버 블로그는 **공식 게시 API가 없어** 브라우저 로그인 창 방식이 유일한 길입니다. 이게 이 키트의 존재 이유(한국 갭)입니다.

## 연결 확인

Claude에게: `연결된 MCP 도구 목록 보여줘` → Higgsfield · Blotato · naver-marketing 3개가 보이면 완료.
