# PyPI 배포 (메인테이너용)

패키지를 PyPI에 올리면 사용자는 한 줄로 설치합니다:
```bash
claude mcp add smb-marketing -- uvx smb-marketing-naver-mcp
```

## 1회 준비
1. https://pypi.org 계정 생성 → **API 토큰** 발급(Account settings → API tokens).
2. `uv` 설치(없으면): `curl -LsSf https://astral.sh/uv/install.sh | sh`

## 배포 (버전 올릴 때마다)
```bash
cd naver-marketing-mcp
# 1) 버전 올리기: pyproject.toml 의 version 수정 (예: 0.1.0 → 0.1.1)
# 2) 빌드
uv build            # 또는: python -m build
# 3) 업로드 (토큰 입력)
uv publish          # 또는: twine upload dist/*
```
- `uv publish` 는 토큰을 물어보거나 `UV_PUBLISH_TOKEN` 환경변수를 사용합니다.
- 성공하면 몇 분 내 PyPI에 반영되고, 사용자는 다음 `uvx` 실행에서 최신 버전을 받습니다.

## 이름
- PyPI 배포명 = `smb-marketing-naver-mcp` (pyproject `[project].name`).
- 이미 사용 중이면 이름을 바꾸고 `[project.scripts]` 의 스크립트명도 동일하게 맞추세요(그래야 `uvx <이름>` 이 바로 실행됨).

## 사용자 안내(설치 후)
- **Google Chrome** 설치 필요(네이버 자동화). Playwright 크로미움 다운로드는 불필요(시스템 Chrome에 CDP attach).
- 연결: "네이버 로그인해줘" / "이 인스타 토큰으로 연결해줘: IGAA…"

## 발견성(선택)
- **공식 MCP 레지스트리**(registry.modelcontextprotocol.io)에 PyPI 링크로 등록(무료 PR)하면 Claude에서 검색됨.
- Smithery·mcp.so 등 디렉토리에도 등록 가능(발견용, 설치는 여전히 uvx).
