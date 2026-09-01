# Meta Connect Broker

여러 SMB 사용자가 각자 로컬 MCP 에서 **"인스타 연결"만 누르면** 되도록, Meta OAuth 토큰 교환을
대행하는 작은 서버. **앱 시크릿은 이 서버에만** 존재해 사용자 기기/오픈소스에 노출되지 않는다.

## 왜 필요한가
- Blotato 같은 유료 서비스가 파는 "원클릭 연결" 경험을 무료로 제공하기 위함.
- 공유 Meta 앱 1개 + 이 브로커 → 사용자는 로그인·동의만, 앱 생성·토큰 교환 불필요.

## 배포 (예: Railway)
1. 이 폴더를 배포(도커). 공개 URL 확보(예: `https://connect.yourdomain.com`).
2. 환경변수 설정:
   ```
   META_APP_ID=...
   META_APP_SECRET=...
   BROKER_PUBLIC_URL=https://connect.yourdomain.com
   ```
3. Meta 앱에 등록:
   - 유효한 OAuth 리디렉션 URI: `{BROKER_PUBLIC_URL}/connect/callback`
   - 개인정보처리방침 URL: `{BROKER_PUBLIC_URL}/privacy`
   - 데이터 삭제 콜백: `{BROKER_PUBLIC_URL}/data-deletion`
   - 연결 해제 콜백: `{BROKER_PUBLIC_URL}/deauthorize`
4. 로컬 MCP 의 `.env` 에 `META_BROKER_URL={BROKER_PUBLIC_URL}` 설정.

## 엔드포인트
| 경로 | 용도 |
| --- | --- |
| `GET /connect/start?session=` | Meta 동의 화면으로 리다이렉트 |
| `GET /connect/callback` | code→토큰 교환(서버가 대행) → localhost 로 복귀 |
| `GET /connect/claim?session=` | 로컬 MCP 가 토큰 1회 수령(즉시 폐기) |
| `GET /privacy` `GET /terms` | 심사 필수 페이지 |
| `POST /data-deletion` `GET/POST /deauthorize` | Meta 필수 콜백 |
| `GET /health` | 헬스체크 |

## 보안
- 토큰은 세션(최대 10분) 후 즉시 폐기, 영구 저장 없음.
- 앱 시크릿은 서버 환경변수로만. 커밋 금지.
