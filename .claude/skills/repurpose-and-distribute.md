---
name: repurpose-and-distribute
description: 네이버 블로그에 쓴 글을 여러 SNS(인스타·링크드인·X·스레드·페북)에 각 채널 컨셉으로 요약·재가공하고 이미지를 붙여 자동 배포한다. "이 블로그 글 SNS에도 올려줘", "인스타랑 링크드인에 맞게 바꿔서 배포해줘" 요청 시 사용.
---

# 블로그 → 멀티 SNS 재가공·배포

하나의 네이버 블로그 글을 소스로, 채널마다 다른 컨셉으로 재가공해 배포한다.
**핵심 원칙: 채널마다 "복붙"이 아니라 그 채널 사용자에게 맞는 형태로 다시 쓴다.**

## 사용하는 도구
- **브랜드 보이스**: `brand_voice.md` (없으면 setup-wizard 로 먼저 생성) — 모든 카피는 이 말투로.
- **채널 규격**: naver-marketing MCP `channel_spec` / `validate_channel_post` / `assemble_channel_caption` — 길이·해시태그·이미지 규칙을 코드로 강제.
- **이미지 생성**: Higgsfield MCP (채널별 비율 다름 — `channel_spec` 의 image_aspect 참고). 인스타는 **공개 URL** 필요.
- **배포(무료·직접)**: naver-marketing MCP —
  - 인스타그램 `instagram_publish` / 페이스북 `facebook_publish` (Meta 무료 Graph API, `connect_meta` 로 사전 연결)
  - 네이버 블로그 `naver_blog_publish`
  - *Blotato(유료) 없이 직접 게시. 다른 플랫폼은 추후 추가.*

## 절차

1. **소스 확보** — 방금 쓴/지정한 네이버 블로그 글의 제목·본문·이미지를 확보한다.

2. **대상 채널 결정** — `policy.yaml` 의 `content.platforms` 또는 사장님 요청 기준.

3. **채널별 재가공** — 각 채널마다:
   - `channel_spec(channel)` 로 규격(max_caption·hashtags·target_length·tone·image_aspect) 확인
   - 브랜드 보이스 + 그 톤으로 **다시 쓴다**:
     - 인스타 = 에너지 훅 + 이모지 + 해시태그 5개
     - 링크드인 = 1인칭 비즈니스 스토리 ~1,400자 + 해시태그 3개 이하
     - X = 한 문장 핵심(≤280자)
     - 스레드 = 짧고 대화체
     - 페북 = 정보+공감
   - 필요 이미지: 소스 이미지 재사용 or Higgsfield 로 채널 비율에 맞게 생성

4. **검증** — 각 초안을 `validate_channel_post(channel, caption, hashtags, image_count)` 로 확인.
   `ok=false` 면 고쳐서 다시 검증. `assemble_channel_caption` 으로 최종 캡션 조립.

5. **미리보기 → 승인 (필수 게이트)** — 채널별 최종 캡션·이미지를 사장님께 **한 번에 미리보기**로 보여주고
   승인받는다. 승인 전 배포 금지.

6. **배포** — 승인되면 `instagram_publish`(approve=True)·`facebook_publish`(approve=True)·
   `naver_blog_publish` 로 각 채널에 게시. 결과(채널별 게시 URL/상태)를 요약 보고한다.
   - **네이버 블로그는 `blocks` 로 글·이미지를 번갈아 배치**한다(글→이미지→글→이미지…) — 이미지를 본문 뒤에 몰지 말 것.
   - 인스타 이미지는 **공개 URL·4:5 권장**(폰 스크린샷은 4:5로 변환·호스팅 필요).

## 안전 규칙
- 사실·수치는 소스 글과 일치시킨다(과장·왜곡 금지).
- 배포 전 항상 미리보기·승인. 완전 자동은 사장님이 명시적으로 요청할 때만.
- Meta(인스타·페북) 미연결 시: 재가공·검증까지 하고, "connect_meta 로 연결 후 게시 가능"으로 안내(docs/META_SETUP.md).
