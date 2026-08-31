"""policy.yaml 로더.

키트 루트의 policy.yaml(사용자별 실제 파일)을 읽는다. 없으면 policy.example.yaml 을 폴백.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# naver-marketing-mcp/naver_marketing_mcp/policy.py → 키트 루트는 3단계 상위
_KIT_ROOT = Path(__file__).resolve().parents[2]


def load_policy() -> dict[str, Any]:
    """policy.yaml 우선, 없으면 policy.example.yaml 을 읽어 dict 로 반환."""
    for name in ("policy.yaml", "policy.example.yaml"):
        p = _KIT_ROOT / name
        if p.exists():
            with p.open(encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}
