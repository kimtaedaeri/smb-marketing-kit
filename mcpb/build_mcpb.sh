#!/usr/bin/env bash
# 더블클릭 설치용 .mcpb 번들을 만든다(맥 유니버설 + 윈도우).
# uv 실행파일을 astral 릴리스에서 내려받아 번들에 넣으므로, 사용자는 파이썬도 uv 도 미리 안 깔아도 된다.
# 준비물: mcpb CLI(npm i -g @anthropic-ai/mcpb), curl, unzip, tar.
set -euo pipefail
cd "$(dirname "$0")"

UV_VERSION="${UV_VERSION:-0.12.9}"
BASE="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "uv ${UV_VERSION} 바이너리 내려받는 중..."
curl -sSL -o "$TMP/mac-arm.tar.gz" "$BASE/uv-aarch64-apple-darwin.tar.gz"
curl -sSL -o "$TMP/mac-x64.tar.gz" "$BASE/uv-x86_64-apple-darwin.tar.gz"
curl -sSL -o "$TMP/win-x64.zip"    "$BASE/uv-x86_64-pc-windows-msvc.zip"
tar xzf "$TMP/mac-arm.tar.gz" -C "$TMP"
tar xzf "$TMP/mac-x64.tar.gz" -C "$TMP"
unzip -oq "$TMP/win-x64.zip" -d "$TMP/win-x64"

# 맥(유니버설): 칩별 uvx 를 launch.sh 가 골라 실행
mkdir -p mac/bin/arm64 mac/bin/x86_64
cp mac/launch.sh mac/bin/launch.sh
cp "$TMP/uv-aarch64-apple-darwin/uv" "$TMP/uv-aarch64-apple-darwin/uvx" mac/bin/arm64/
cp "$TMP/uv-x86_64-apple-darwin/uv"  "$TMP/uv-x86_64-apple-darwin/uvx"  mac/bin/x86_64/
chmod +x mac/bin/arm64/uv mac/bin/arm64/uvx mac/bin/x86_64/uv mac/bin/x86_64/uvx mac/bin/launch.sh

# 윈도우(x64)
mkdir -p win/bin
cp "$TMP/win-x64/uv.exe" "$TMP/win-x64/uvx.exe" win/bin/

mcpb validate mac/manifest.json
mcpb validate win/manifest.json
mcpb pack mac smb-marketing-naver-mac.mcpb
mcpb pack win smb-marketing-naver-win.mcpb
echo "완료:"
echo "  $(pwd)/smb-marketing-naver-mac.mcpb  (애플 실리콘 + 인텔 맥)"
echo "  $(pwd)/smb-marketing-naver-win.mcpb  (윈도우 64비트)"
