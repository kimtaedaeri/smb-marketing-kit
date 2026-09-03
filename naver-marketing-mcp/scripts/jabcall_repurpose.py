"""잽콜(JABCALL) 홍보 — 채널별 재가공 + 규격 검증(미리보기)."""

from __future__ import annotations

from naver_marketing_mcp import channels

INSTAGRAM = (
    "집에서도 코치가 붙습니다 🥊\n\n"
    "녹화를 켜면 세컨(코치)이 “잽, 스트레이트, 슬립!” 콤보를 불러주고 —\n"
    "타이머·콜아웃 자막·벨·목소리가 세로 영상에 그대로 새겨져 저장돼요.\n"
    "편집도, 저장 대기도 없이 바로 공유 🔥\n\n"
    "로그인 없이 바로 시작. 영상은 서버로 안 보내고 광고·추적도 없습니다.\n"
    "곧 출시 — 세컨과 함께 시작하세요."
)
IG_TAGS = ["잽콜", "JABCALL", "복싱", "홈트", "복싱앱"]

THREADS = (
    "집에서 복싱할 때 콤보 뭘 칠지 고민되죠 🥊\n"
    "잽콜은 세컨(코치)이 “잽 스트레이트 슬립!” 불러주고, 녹화하면 타이머·자막·벨까지 "
    "영상에 그대로 새겨져 저장돼요. 편집 없이 바로 공유. 로그인도 필요 없고요.\n"
    "곧 나옵니다 🔥"
)
TH_TAGS = ["잽콜", "복싱"]

NAVER_TITLE = "집에서 복싱, 코치가 콤보를 불러주는 앱 ‘잽콜(JABCALL)’ 곧 출시"
NAVER_BODY = (
    "안녕하세요. 곧 출시하는 복싱 트레이닝 앱 ‘잽콜(JABCALL)’을 소개합니다.\n\n"
    "잽콜은 내 복싱 영상에 코치가 함께 들어가는 앱입니다. 세컨(코치 음성)이 “잽, 스트레이트, "
    "슬립!” 하고 동작 이름으로 콤보를 불러주면 그대로 따라 치면 됩니다. 녹화를 켜면 라운드 타이머, "
    "콜아웃 자막, 벨, 목소리가 세로 영상에 그대로 새겨져 저장됩니다. 편집이나 저장 대기 없이 바로 "
    "공유할 수 있습니다.\n\n"
    "주요 기능은 다음과 같습니다.\n"
    "- 라운드 타이머: 기본 3R×3분, 자유 설정과 복싱·킥복싱·무에타이·타바타 프리셋, 콜 속도 3단계\n"
    "- 콜아웃 워크아웃 12세트와 콤보 116개, 전면·후면 카메라로 내 콤보 직접 제작\n"
    "- 주간 목표와 연속 기록, 운동 알림\n"
    "- 로그인 없이 바로 사용. 영상은 서버로 전송하지 않으며 광고·추적이 없습니다.\n\n"
    "체육관 가는 날 사이의 자율 훈련부터 릴스 챌린지까지, 세컨과 함께 시작해보세요. 출시 소식은 곧 전해드리겠습니다."
)
NB_TAGS = ["잽콜", "JABCALL", "복싱", "복싱앱", "홈트레이닝"]


def show(channel: str, caption: str, tags: list, image_count: int) -> None:
    cap = channels.assemble_caption(channel, caption, tags)
    v = channels.validate_post(channel, cap, tags, image_count)
    print(f"\n===== {channel.upper()} (검증 ok={v['ok']} len={len(cap)} err={v['errors']} warn={v['warnings']}) =====")
    print(cap)


if __name__ == "__main__":
    show("instagram", INSTAGRAM, IG_TAGS, image_count=1)
    show("threads", THREADS, TH_TAGS, image_count=0)
    print(f"\n===== NAVER_BLOG =====\n[제목] {NAVER_TITLE}\n{NAVER_BODY}\n[태그] {NB_TAGS} · 본문 {len(NAVER_BODY)}자")
