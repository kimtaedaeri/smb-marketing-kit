"""잽콜 스크린샷을 인스타 4:5(1080x1350)로 변환하고 공개 호스팅(catbox)."""

from __future__ import annotations

import json

import requests
from PIL import Image

from naver_marketing_mcp.naver_blog import _AUTH_DIR

SRC = {
    "home": "/Users/macrent/Downloads/IMG_4308.PNG",
    "combo": "/Users/macrent/Downloads/IMG_4309.PNG",
    "stats": "/Users/macrent/Downloads/IMG_4310.PNG",
}
W, H = 1080, 1350

_AUTH_DIR.mkdir(parents=True, exist_ok=True)
out: dict[str, str] = {}
local: dict[str, str] = {}
for k, src in SRC.items():
    im = Image.open(src).convert("RGB")
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    ratio = min(W / im.width, H / im.height)
    nw, nh = int(im.width * ratio), int(im.height * ratio)
    canvas.paste(im.resize((nw, nh), Image.LANCZOS), ((W - nw) // 2, (H - nh) // 2))
    dst = _AUTH_DIR / f"jab_{k}.jpg"
    canvas.save(dst, "JPEG", quality=88)
    local[k] = str(dst)
    with open(dst, "rb") as f:
        r = requests.post("https://catbox.moe/user/api.php",
                          data={"reqtype": "fileupload"},
                          files={"fileToUpload": f}, timeout=120)
    url = r.text.strip()
    out[k] = url
    print(f"{k}: {url}")

(_AUTH_DIR / "jab_urls.json").write_text(json.dumps({"urls": out, "local": local}, ensure_ascii=False))
print("SAVED jab_urls.json")
