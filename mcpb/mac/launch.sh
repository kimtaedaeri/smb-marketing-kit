#!/bin/sh
# 맥 유니버설: 현재 칩(arm64/x86_64)에 맞는 uvx 를 골라 실행한다.
DIR=$(cd "$(dirname "$0")" && pwd)
exec "$DIR/$(uname -m)/uvx" "$@"
