"""잽콜 네이버 블로그 — 글→이미지→글→이미지 번갈아 배치(블록). 검증용 비공개."""

from __future__ import annotations

from naver_marketing_mcp import naver_blog
from naver_marketing_mcp.policy import load_policy
from scripts.jabcall_repurpose import NAVER_TITLE, NB_TAGS

IMG = "/Users/macrent/Downloads/IMG_43{}.PNG"

P1 = (
    "안녕하세요. 곧 출시하는 복싱 트레이닝 앱 ‘잽콜(JABCALL)’을 소개합니다.\n\n"
    "잽콜은 내 복싱 영상에 코치가 함께 들어가는 앱입니다. 세컨(코치 음성)이 “잽, 스트레이트, 슬립!” 하고 "
    "동작 이름으로 콤보를 불러주면 그대로 따라 치면 됩니다. 녹화를 켜면 라운드 타이머, 콜아웃 자막, 벨, "
    "목소리가 세로 영상에 그대로 새겨져 저장됩니다. 편집이나 저장 대기 없이 바로 공유할 수 있습니다."
)
P2 = (
    "주요 기능은 다음과 같습니다.\n"
    "- 라운드 타이머: 기본 3R×3분, 복싱·킥복싱·무에타이·타바타 프리셋, 콜 속도 3단계\n"
    "- 콜아웃 워크아웃 12세트와 콤보 116개, 전면·후면 카메라로 내 콤보 직접 제작\n"
    "- 주간 목표와 연속 기록, 운동 알림\n"
    "- 로그인 없이 바로 사용. 영상은 서버로 전송하지 않으며 광고·추적이 없습니다."
)
P3 = (
    "체육관 가는 날 사이의 자율 훈련부터 릴스 챌린지까지, 세컨과 함께 시작해보세요. 출시 소식은 곧 전해드리겠습니다."
)

blocks = [
    {"type": "text", "text": P1},
    {"type": "image", "path": IMG.format("08")},   # 홈
    {"type": "text", "text": P2},
    {"type": "image", "path": IMG.format("09")},   # 내 콤보
    {"type": "text", "text": P3},
    {"type": "image", "path": IMG.format("10")},   # 나의 운동
]

blog_id = load_policy().get("naver", {}).get("blog_id") or "gyfhx"
res = naver_blog.publish(blog_id=blog_id, title=NAVER_TITLE, blocks=blocks,
                         tags=NB_TAGS, private=True)
print("RESULT:", res)
