"""Generate TennisLab Expo icon / splash / favicon PNGs (no third-party deps)."""
import math
import os
import struct
import zlib

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")

NAVY = (30, 58, 138, 255)
BALL = (206, 237, 67)
SEAM = (255, 255, 255)


def write_png(path, width, height, pixels):
    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        raw.extend(pixels[y * stride : (y + 1) * stride])

    with open(path, "wb") as handle:
        handle.write(b"\x89PNG\r\n\x1a\n")
        handle.write(chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)))
        handle.write(chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
        handle.write(chunk(b"IEND", b""))


def blend(dst, src, alpha):
    alpha = max(0.0, min(1.0, alpha))
    return tuple(int(d * (1.0 - alpha) + s * alpha) for d, s in zip(dst, src))


def tennis_ball_pixels(size, background, pad_ratio):
    pixels = bytearray(size * size * 4)
    cx = cy = (size - 1) / 2.0
    radius = size * (0.5 - pad_ratio)
    seam_w = max(1.5, radius * 0.075)

    for y in range(size):
        for x in range(size):
            dx = x - cx
            dy = y - cy
            dist = math.hypot(dx, dy)
            edge = dist - radius
            idx = (y * size + x) * 4

            if background[3] == 0 and edge > 1.6:
                pixels[idx : idx + 4] = bytes(background)
                continue

            cover = 1.0 if edge <= -1.2 else (0.0 if edge >= 1.2 else 0.5 - edge / 2.4)
            nx = dx / radius if radius else 0.0
            ny = dy / radius if radius else 0.0
            light = max(0.0, 1.0 - 0.38 * ((nx + 0.28) ** 2 + (ny + 0.38) ** 2))
            ball = tuple(min(255, int(c * (0.80 + 0.20 * light))) for c in BALL)

            d1 = abs(math.hypot(dx + 0.58 * radius, dy) - 0.95 * radius)
            d2 = abs(math.hypot(dx - 0.58 * radius, dy) - 0.95 * radius)
            seam = 0.0
            if dist <= radius + 1.2:
                seam = max(0.0, 1.0 - d1 / seam_w, 1.0 - d2 / seam_w) ** 1.15
                seam *= max(0.0, min(1.0, (radius - dist) / 1.6 + 1.0))

            color = blend(ball, SEAM, seam)
            hx = dx + 0.22 * radius
            hy = dy + 0.26 * radius
            highlight = math.exp(-(hx * hx + hy * hy) / (2.0 * (radius * 0.22) ** 2)) * 0.22
            color = tuple(min(255, int(c + 255 * highlight)) for c in color)

            if background[3] == 0:
                out = (color[0], color[1], color[2], int(255 * cover))
            else:
                mixed = blend(background[:3], color, cover)
                out = mixed + (255,)

            pixels[idx : idx + 4] = bytes(out)

    return pixels


def main():
    os.makedirs(ASSETS, exist_ok=True)

    icon = tennis_ball_pixels(1024, NAVY, pad_ratio=0.16)
    write_png(os.path.join(ASSETS, "icon.png"), 1024, 1024, icon)

    adaptive = tennis_ball_pixels(1024, (0, 0, 0, 0), pad_ratio=0.22)
    write_png(os.path.join(ASSETS, "adaptive-icon.png"), 1024, 1024, adaptive)

    splash = tennis_ball_pixels(1024, (0, 0, 0, 0), pad_ratio=0.18)
    write_png(os.path.join(ASSETS, "splash-icon.png"), 1024, 1024, splash)

    favicon = tennis_ball_pixels(48, NAVY, pad_ratio=0.12)
    write_png(os.path.join(ASSETS, "favicon.png"), 48, 48, favicon)

    print("Wrote TennisLab Expo assets to", os.path.abspath(ASSETS))


if __name__ == "__main__":
    main()
