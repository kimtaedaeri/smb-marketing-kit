"""이미지 전처리(채널 비율) + 공개 호스팅.

인스타 게시는 이미지가 **공개 URL**이어야 하고 비율 제약(4:5~1.91:1)이 있다. 폰 스크린샷 등은
그대로는 거부되므로, 검은 배경에 맞춰 비율을 만들고 공개 URL로 호스팅한다.
"""

from __future__ import annotations

from .naver_blog import _AUTH_DIR

ASPECTS = {"4:5": (1080, 1350), "1:1": (1080, 1080), "1.91:1": (1080, 566)}


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def _fit(src: str, size: tuple[int, int]):
    from PIL import Image

    im = Image.open(src).convert("RGB")
    w, h = size
    canvas = Image.new("RGB", (w, h), (0, 0, 0))
    ratio = min(w / im.width, h / im.height)
    nw, nh = max(1, int(im.width * ratio)), max(1, int(im.height * ratio))
    canvas.paste(im.resize((nw, nh)), ((w - nw) // 2, (h - nh) // 2))
    return canvas


def _host(path: str) -> str:
    import requests

    with open(path, "rb") as f:
        r = requests.post("https://catbox.moe/user/api.php",
                          data={"reqtype": "fileupload"},
                          files={"fileToUpload": f}, timeout=120)
    url = r.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"이미지 호스팅 실패: {url[:120]}")
    return url


def prep_for_instagram(paths: list[str], aspect: str = "4:5") -> list[str]:
    """로컬 이미지들을 채널 비율로 변환하고 공개 URL 로 호스팅해 반환.
    이미 http URL 이면 그대로 통과(예: Higgsfield 생성물)."""
    size = ASPECTS.get(aspect, ASPECTS["4:5"])
    _AUTH_DIR.mkdir(parents=True, exist_ok=True)
    urls: list[str] = []
    for i, p in enumerate(paths):
        if is_url(p):
            urls.append(p)
            continue
        canvas = _fit(p, size)
        dst = _AUTH_DIR / f"ig_prep_{i}.jpg"
        canvas.save(dst, "JPEG", quality=88)
        urls.append(_host(str(dst)))
    return urls
