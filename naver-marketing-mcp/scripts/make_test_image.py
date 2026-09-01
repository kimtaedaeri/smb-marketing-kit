"""의존성 없이 단색 PNG 테스트 이미지를 생성한다(.auth/test_image.png)."""

from __future__ import annotations

import struct
import zlib

from naver_marketing_mcp.naver_blog import _AUTH_DIR


def make_png(path: str, w: int = 1080, h: int = 1080, rgb: tuple[int, int, int] = (40, 200, 160)) -> None:
    def chunk(typ: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + typ
            + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    row = b"\x00" + bytes(rgb) * w
    idat = zlib.compress(row * h, 9)
    png = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


if __name__ == "__main__":
    _AUTH_DIR.mkdir(parents=True, exist_ok=True)
    out = _AUTH_DIR / "test_image.png"
    make_png(str(out))
    print("SAVED:", out)
