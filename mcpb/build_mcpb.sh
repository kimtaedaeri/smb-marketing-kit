#!/usr/bin/env bash
# .mcpb(더블클릭 설치 번들)를 만든다. macOS(arm64) 기준.
# 준비물: mcpb CLI(npm i -g @anthropic-ai/mcpb), uv(~/.local/bin/uv).
set -euo pipefail
cd "$(dirname "$0")"

UV_SRC="${UV_BIN:-$HOME/.local/bin/uv}"
UVX_SRC="${UVX_BIN:-$HOME/.local/bin/uvx}"
[ -x "$UV_SRC" ]  || { echo "uv 를 찾지 못했어요: $UV_SRC (curl -LsSf https://astral.sh/uv/install.sh | sh)"; exit 1; }
[ -x "$UVX_SRC" ] || { echo "uvx 를 찾지 못했어요: $UVX_SRC"; exit 1; }

mkdir -p bin
cp "$UV_SRC" "$UVX_SRC" bin/
chmod +x bin/uv bin/uvx

mcpb validate manifest.json
mcpb pack . smb-marketing-naver.mcpb
echo "완료: $(pwd)/smb-marketing-naver.mcpb"
