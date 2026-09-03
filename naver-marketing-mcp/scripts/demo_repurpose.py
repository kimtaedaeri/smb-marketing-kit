"""엔드투엔드 데모(미리보기): 하나의 소재를 채널별로 재가공하고 규격 검증까지.

샘플 상품: 동네 베이커리 '흑임자 크로플' 신메뉴. 브랜드 보이스는 따뜻·친근·솔직 가정.
실게시는 하지 않는다(검증·미리보기만).
"""

from __future__ import annotations

from naver_marketing_mcp import channels

# 브랜드 보이스(따뜻·친근·솔직)로 채널별 재가공한 초안
INSTAGRAM = (
    "오늘부터 만나요 🖤 겉바속촉 크로플에 고소한 흑임자 크림 듬뿍!\n"
    "한 입 베어물면 스르륵 녹는 이 조합… 위험합니다 😳\n"
    "딱 이번 주, 매장에서만 맛볼 수 있어요. 따뜻한 커피랑 세트면 완벽 ☕"
)
IG_TAGS = ["흑임자크로플", "신메뉴", "동네베이커리", "디저트스타그램", "오늘의간식"]

THREADS = (
    "흑임자 크로플 오늘 나왔어요 🧵\n"
    "겉은 바삭, 안은 촉촉, 크림은 고소. 이번 주만 매장 한정인데 벌써 반응이 좋네요.\n"
    "다들 커피랑 드시더라고요 ☕"
)
TH_TAGS = ["흑임자크로플", "신메뉴"]

NAVER_TITLE = "겉바속촉 흑임자 크로플, 이번 주 신메뉴로 만나보세요"
NAVER_BODY = (
    "안녕하세요. 오늘은 이번 주에만 선보이는 신메뉴 '흑임자 크로플'을 소개해요.\n\n"
    "겉은 바삭하게 구워 결이 살아있고, 안은 촉촉하게 남겼습니다. 여기에 직접 만든 흑임자 크림을 "
    "듬뿍 채워, 한 입 베어물면 고소한 향이 은은하게 퍼져요. 너무 달지 않아 커피와도 잘 어울립니다.\n\n"
    "흑임자는 예로부터 즐겨 먹던 재료인데, 크로플과 만나니 익숙하면서도 새로운 맛이 났어요. "
    "매일 아침 매장에서 구워 준비하고, 수량이 한정되어 소진되면 마감됩니다.\n\n"
    "이번 주 한정 메뉴예요. 따뜻한 커피 한 잔과 함께, 편하게 들러 맛보세요."
)
NB_TAGS = ["흑임자크로플", "신메뉴", "동네베이커리", "디저트"]


def show(channel: str, caption: str, tags: list, image_count: int) -> None:
    cap = channels.assemble_caption(channel, caption, tags)
    v = channels.validate_post(channel, cap, tags, image_count)
    print(f"\n===== {channel.upper()} =====")
    print(cap)
    print(f"[검증] ok={v['ok']} len={len(cap)} tags={len(tags)} "
          f"warn={v['warnings']} err={v['errors']}")


if __name__ == "__main__":
    show("instagram", INSTAGRAM, IG_TAGS, image_count=1)
    show("threads", THREADS, TH_TAGS, image_count=0)
    print("\n===== NAVER_BLOG =====")
    print(f"[제목] {NAVER_TITLE}")
    print(NAVER_BODY)
    print(f"[검증] 본문 {len(NAVER_BODY)}자 · 태그 {NB_TAGS}")
