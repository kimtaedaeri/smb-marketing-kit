"""policy.yaml 로더 + 사용자 데이터 위치 결정.

- 소스(개발) 실행: 키트 루트(.git/policy.yaml 있는 곳)에 데이터를 둔다.
- uvx 등으로 설치: 홈 폴더 ~/.smb-marketing/ 에 둔다(설치 캐시는 지워질 수 있으므로).
- SMB_DATA_DIR 환경변수로 강제 지정 가능.

블로그 아이디 같은 가벼운 설정은 데이터 폴더의 .auth/config.json 에 저장한다.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

# naver-marketing-mcp/naver_marketing_mcp/policy.py → 키트 루트는 3단계 상위
_KIT_ROOT = Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    """로그인 세션과 설정을 저장할 폴더. 개발이면 키트 루트, 설치면 홈 폴더."""
    env = os.environ.get("SMB_DATA_DIR")
    if env:
        return Path(env).expanduser()
    # 소스 체크아웃에서 실행 중이면(개발) 그대로 키트 루트 사용
    if (_KIT_ROOT / ".git").exists() or (_KIT_ROOT / "policy.yaml").exists():
        return _KIT_ROOT
    # 설치 사용자: 홈 폴더(설치 캐시가 지워져도 로그인 유지)
    return Path.home() / ".smb-marketing"


def _config_path() -> Path:
    return data_dir() / ".auth" / "config.json"


def read_config() -> dict[str, Any]:
    """가벼운 사용자 설정(블로그 아이디 등)을 읽는다. 없으면 빈 dict."""
    p = _config_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            return {}
    return {}


def write_config(**kv: Any) -> None:
    """사용자 설정을 병합 저장한다(예: write_config(naver_blog_id='gyfhx'))."""
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    cur = read_config()
    cur.update({k: v for k, v in kv.items() if v is not None})
    p.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")


def load_policy() -> dict[str, Any]:
    """policy.yaml 우선, 없으면 policy.example.yaml 을 읽어 dict 로 반환.

    설치 사용자는 policy 파일이 없을 수 있으므로 빈 dict 를 돌려주고,
    블로그 아이디는 config.json/환경변수에서 별도로 해결한다.
    """
    for base in (data_dir(), _KIT_ROOT):
        for name in ("policy.yaml", "policy.example.yaml"):
            p = base / name
            if p.exists():
                with p.open(encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
    return {}
