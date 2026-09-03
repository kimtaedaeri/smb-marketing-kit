# Instagram Login API 전환 설계 (실행 대기)

리서치 결론: 2025년 **"Instagram API with Instagram Login"** 은 **페이스북 페이지 없이** 인스타
비즈니스/크리에이터 계정에 게시할 수 있다. 지금 코드는 페이스북 페이지 연동(Facebook Login) 기반이라,
초보자 최대 마찰(페이지 생성·연결)을 없애려면 이 API 로 전환한다.

> 라이브 검증이 필요한 OAuth 라, **앱 준비 시점에 네이버처럼 검증하며 전환**한다(지금 블라인드 구현 X).
> 아래는 그때 빠르게 실행하기 위한 설계.

## 무엇이 달라지나
| | 지금(Facebook Login) | 전환(Instagram Login) |
| --- | --- | --- |
| 전제 | IG ↔ 페이스북 페이지 연결 필요 | **페이지 불필요**, IG 프로페셔널(비즈/크리에이터)만 |
| OAuth | facebook.com/dialog/oauth | instagram.com/oauth/authorize |
| 스코프 | instagram_basic, pages_*, instagram_content_publish | `instagram_business_basic`, `instagram_business_content_publish` |
| 토큰 | 유저토큰→페이지토큰 | **IG 유저 토큰** 직접 |
| 게시 | graph.facebook.com/{ig}/media (+page token) | graph.instagram.com/{ig-user-id}/media |

## 흐름 (전환 후)
1. authorize: `https://www.instagram.com/oauth/authorize?client_id={IG_APP_ID}&redirect_uri={cb}&scope=instagram_business_basic,instagram_business_content_publish&response_type=code`
2. 단기 토큰: `POST https://api.instagram.com/oauth/access_token` (client_id, client_secret, code, redirect_uri) → `{access_token, user_id}`
3. 장기(60일): `GET https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret=..&access_token=..`
4. 게시: `POST https://graph.instagram.com/{user_id}/media` (image_url, caption) → creation_id → `.../media_publish`
   - 캐러셀: children 컨테이너 → CAROUSEL 컨테이너 → publish (기존 로직 동일, 도메인만 graph.instagram.com)

## 코드 변경 지점
- `meta_auth.py`: 브로커/개발자 플로우의 authorize URL·토큰 교환을 IG 엔드포인트로. state 저장에 `ig_user_id`, `ig_access_token` 저장(페이지 개념 제거).
- `instagram.py`: base 를 `graph.instagram.com/{ig_user_id}`, access_token 은 IG 유저 토큰. (컨테이너/캐러셀/publish 로직 재사용)
- `meta-connect-service/app.py`: OAuth·토큰 교환 엔드포인트를 IG 로. 스코프 교체.
- 페이스북 페이지 게시(`facebook.py`)는 별도 — FB 페이지를 쓰는 사용자만. IG/스레드와 분리.
- 심사 권한: `instagram_business_content_publish` (App Review). `docs/META_APP_REVIEW.md` 갱신.

## 검증 순서(앱 준비 후)
1. IG 앱(Instagram 제품·비즈니스 로그인) 생성 → client_id/secret.
2. 개발자 모드에서 본인 IG 크리에이터 계정으로 authorize → 토큰 → 이미지 1장 게시 검증.
3. 되면 브로커에 이식 → 원클릭.
