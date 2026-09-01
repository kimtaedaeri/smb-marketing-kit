"""비공개 글 발행 엔드투엔드 테스트. blog_id 는 policy.yaml 에서 읽는다."""

from __future__ import annotations

from naver_marketing_mcp.naver_blog import _AUTH_DIR, publish
from naver_marketing_mcp.policy import load_policy

TITLE = "[테스트] 마케팅 자동화 키트 이미지 발행 테스트"
BODY = (
    "이 글은 smb-marketing-kit 의 네이버 블로그 자동 발행 + 이미지 첨부 검증용 비공개 글입니다.\n"
    "제목·본문 입력 후 이미지가 본문에 삽입되고 비공개로 발행되는지 확인합니다.\n"
    "확인 후 삭제해도 됩니다."
)


def main() -> None:
    blog_id = load_policy().get("naver", {}).get("blog_id")
    if not blog_id:
        raise SystemExit("policy.yaml 에 naver.blog_id 를 설정하세요.")
    img = _AUTH_DIR / "test_image.png"
    images = [str(img)] if img.exists() else None
    result = publish(
        blog_id=blog_id, title=TITLE, body_markdown=BODY,
        image_paths=images, tags=["마케팅자동화", "테스트", "smb"], private=True,
    )
    print("RESULT:", result)


if __name__ == "__main__":
    main()
