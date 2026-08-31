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

로컬에서 실행합니다. [`naver-marketing-mcp/README.md`](naver-marketing-mcp/README.md) 참고.

```bash
cd naver-marketing-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium
```

Claude Desktop/Code 에 로컬 MCP로 등록:

```bash
claude mcp add naver-marketing -- python -m naver_marketing_mcp
```

## 연결 확인

Claude에게: `연결된 MCP 도구 목록 보여줘` → Higgsfield · Blotato · naver-marketing 3개가 보이면 완료.
