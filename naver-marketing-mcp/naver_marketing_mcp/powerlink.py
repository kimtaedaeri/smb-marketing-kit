"""네이버 파워링크 입찰 브리지.

퍼포먼스 마케팅 절반은 오픈소스 naver-powerlink-bidding(powerlink-pilot) 을 그대로 쓴다.
그 패키지가 설치돼 있으면 서브프로세스로 1 사이클 실행하고, 없으면 설치 안내를 반환한다.

설치:
    pip install "git+https://github.com/kimtaedaeri/naver-powerlink-bidding.git"
    # 또는 로컬 클론 후 pip install -e .
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_KIT_ROOT = Path(__file__).resolve().parents[2]
_KEYWORDS_FILE = _KIT_ROOT / "keywords.yaml"

_INSTALL_HINT = (
    "파워링크 입찰 엔진이 설치되어 있지 않습니다. 아래로 설치하세요:\n"
    '  pip install "git+https://github.com/kimtaedaeri/naver-powerlink-bidding.git"\n'
    "그리고 keywords.yaml(키워드·목표순위·입찰범위)과 .env(네이버 검색광고 API 키)를 준비하세요."
)


def _engine_available() -> bool:
    """powerlink_pilot 모듈이 import 가능한지 확인."""
    from importlib.util import find_spec

    try:
        return find_spec("powerlink_pilot") is not None
    except ModuleNotFoundError:
        return False


def run_bidding(dry_run: bool = True) -> dict[str, Any]:
    """파워링크 입찰 1 사이클 실행.

    naver-powerlink-bidding 의 CLI(`python -m powerlink_pilot`)를 호출한다.
    dry_run=True 면 실제 입찰가를 바꾸지 않는다.
    """
    if not _engine_available():
        return {"status": "not_installed", "message": _INSTALL_HINT}

    if not _KEYWORDS_FILE.exists():
        return {
            "status": "no_config",
            "message": f"{_KEYWORDS_FILE.name} 가 없습니다. examples/keywords.example.yaml 을 참고해 만드세요.",
        }

    cmd = [sys.executable, "-m", "powerlink_pilot", "run"]
    if dry_run:
        cmd.append("--dry-run")

    proc = subprocess.run(
        cmd, cwd=str(_KIT_ROOT), capture_output=True, text=True, timeout=300
    )
    return {
        "status": "ok" if proc.returncode == 0 else "error",
        "dry_run": dry_run,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-2000:],
    }
