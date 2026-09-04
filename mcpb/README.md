# 더블클릭 설치용 번들(.mcpb)

터미널이 익숙하지 않은 분을 위해, Claude **데스크톱 앱**에 **더블클릭으로 설치**되는 번들입니다.

## 결과물(두 파일)

- `smb-marketing-naver-mac.mcpb` — 맥 유니버설(애플 실리콘 + 인텔)
- `smb-marketing-naver-win.mcpb` — 윈도우 64비트

사용자는 자기 OS 파일 하나만 받아 더블클릭하면 됩니다.

## 어떻게 동작하나

- `manifest.json` 이 설치 화면을 만들고(블로그 아이디 입력), 서버 실행 방법을 정의합니다.
- 서버는 PyPI 의 `smb-marketing-naver-mcp@latest` 를 **번들에 포함된 uv** 로 받아 실행합니다.
  - uv 는 파이썬까지 알아서 받아오므로 **사용자는 파이썬도 uv 도 미리 깔 필요가 없습니다.**
  - macOS 앱은 PATH 문제로 시스템 uv 를 못 찾는 경우가 있어, uv 를 번들에 넣어 절대경로로 부릅니다.
  - 맥은 `launch.sh` 가 현재 칩(`uname -m`)에 맞는 `arm64/` 또는 `x86_64/` uvx 를 골라 실행합니다(유니버설).
  - 윈도우는 `bin/uvx.exe` 를 직접 실행합니다.
- 블로그 아이디는 설치 화면에서 입력받아 `SMB_NAVER_BLOG_ID` 환경변수로 서버에 전달됩니다
  (그래서 PyPI 패키지가 **0.2.1 이상**이어야 합니다).

## 폴더 구조

```
mcpb/
  build_mcpb.sh        모든 플랫폼 번들을 만든다(uv 자동 다운로드)
  mac/
    manifest.json      맥 유니버설 매니페스트
    launch.sh          칩 선택 실행 셔임(추적됨)
    bin/               (gitignore) launch.sh + arm64/ + x86_64/
  win/
    manifest.json      윈도우 매니페스트
    bin/               (gitignore) uv.exe, uvx.exe
```

## 빌드 방법(개발자)

준비물: `npm i -g @anthropic-ai/mcpb`, curl, unzip, tar.

```bash
./build_mcpb.sh
# → smb-marketing-naver-mac.mcpb, smb-marketing-naver-win.mcpb 생성
```

`bin/` 의 uv 바이너리와 `*.mcpb` 산출물은 용량이 커서 git 에 올리지 않습니다(빌드 시 자동 다운로드).

## 한계와 검증 상태

- 맥 유니버설 셔임은 **애플 실리콘(arm64)에서 칩 선택 동작을 확인**했습니다. 인텔 경로는 동일 방식이나 인텔 하드웨어에서의 실기 확인은 아직입니다.
- 윈도우 번들은 매니페스트 검증과 패킹만 됐고, 윈도우 실기 설치는 아직 확인 전입니다.
- 첫 실행 때 패키지와 의존성(Playwright 등)을 받느라 시간이 걸릴 수 있습니다. 이후엔 캐시되어 빨라집니다.
- 실제 게시는 여전히 내 PC 의 진짜 크롬으로 이뤄집니다(네이버는 공식 API 가 없음).
