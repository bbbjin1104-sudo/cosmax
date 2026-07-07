import base64
import io
import math
import random
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFilter

# ------------------------------------------------------------
# 페이지 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="런치콕(LunchKok) - 점심메뉴 고민 끝, 3초만에 맛집 찾기",
    page_icon="🍽️",
    layout="wide",
)

# Streamlit 기본 여백/헤더를 최대한 제거해서 원본 HTML 디자인이 그대로 보이게 함
st.markdown(
    """
    <style>
        .block-container {padding: 0 !important; max-width: 100% !important;}
        header[data-testid="stHeader"] {display: none;}
        iframe {border: none;}
    </style>
    """,
    unsafe_allow_html=True,
)

BASE_DIR = Path(__file__).parent
HTML_PATH = BASE_DIR / "index.html"
IMAGE_PATH = BASE_DIR / "baby.png"


def _to_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")


def _blob_mask(size: int, cx: int, cy: int, rx: int, ry: int, seed: int) -> Image.Image:
    """찌그러진 여러 타원을 합쳐 자연스러운 뭉치 실루엣을 만든다."""
    rnd = random.Random(seed)
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    lumps = [(0, 0, 1.0, 1.0)]
    for _ in range(8):
        angle = rnd.uniform(0, math.tau)
        dist = rnd.uniform(0.15, 0.5)
        lumps.append((math.cos(angle) * dist, math.sin(angle) * dist, rnd.uniform(0.5, 0.75), rnd.uniform(0.5, 0.75)))
    for dx, dy, sx, sy in lumps:
        lx, ly = cx + dx * rx, cy + dy * ry
        draw.ellipse([lx - rx * sx, ly - ry * sy, lx + rx * sx, ly + ry * sy], fill=255)
    return mask.filter(ImageFilter.GaussianBlur(size * 0.012))


@st.cache_data
def make_rice_image() -> str:
    """플랫한 이모지 대신, 낱알과 음영이 있는 흰 쌀밥 뭉치를 직접 그려서 base64로 반환한다."""
    size, scale = 220, 3
    s = size * scale
    cx, cy = s // 2, int(s * 0.55)
    rx, ry = int(s * 0.40), int(s * 0.30)

    canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(
        [cx - rx * 0.8, cy + ry * 0.55, cx + rx * 0.8, cy + ry * 1.15], fill=(40, 20, 10, 120)
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(s * 0.03)))

    mask = _blob_mask(s, cx, cy, rx, ry, seed=5)

    grad = Image.new("L", (s, s), 128)
    gdraw = ImageDraw.Draw(grad)
    gdraw.ellipse([cx - rx * 1.4, cy - ry * 1.6, cx + rx * 0.4, cy + ry * 0.3], fill=210)
    gdraw.ellipse([cx - rx * 0.3, cy - ry * 0.1, cx + rx * 1.5, cy + ry * 1.6], fill=70)
    grad = grad.filter(ImageFilter.GaussianBlur(s * 0.1)).load()

    warm, cool = (250, 246, 235), (205, 196, 174)
    tone = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    tone_px = tone.load()
    for y in range(0, s, 2):
        for x in range(0, s, 2):
            t = grad[x, y] / 255
            rgba = (
                int(cool[0] + (warm[0] - cool[0]) * t),
                int(cool[1] + (warm[1] - cool[1]) * t),
                int(cool[2] + (warm[2] - cool[2]) * t),
                255,
            )
            for yy in (y, y + 1):
                for xx in (x, x + 1):
                    if xx < s and yy < s:
                        tone_px[xx, yy] = rgba

    body = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    body.paste(tone, (0, 0), mask)
    canvas.alpha_composite(body)

    rnd = random.Random(42)
    grains = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    for _ in range(70):
        gx = cx + rnd.uniform(-rx * 0.85, rx * 0.85)
        gy = cy + rnd.uniform(-ry * 0.85, ry * 0.85)
        nx, ny = (gx - cx) / rx, (gy - cy) / ry
        if nx * nx + ny * ny > 0.95:
            continue
        gw = rnd.uniform(0.05, 0.075) * s
        gh = gw * rnd.uniform(0.4, 0.48)
        cell = Image.new("RGBA", (int(gw * 1.6), int(gh * 1.6)), (0, 0, 0, 0))
        cdraw = ImageDraw.Draw(cell)
        cxg, cyg = cell.width / 2, cell.height / 2
        alpha = max(0, 26 + rnd.randint(-10, 18))
        cdraw.ellipse([cxg - gw / 2, cyg - gh / 2, cxg + gw / 2, cyg + gh / 2], fill=(255, 250, 240, alpha))
        cell = cell.filter(ImageFilter.GaussianBlur(gh * 0.15))
        cell = cell.rotate(rnd.uniform(-60, 60), expand=True, resample=Image.BICUBIC)
        grains.alpha_composite(cell, (int(gx - cell.width / 2), int(gy - cell.height / 2)))

    grains_masked = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    grains_masked.paste(grains, (0, 0), mask)
    canvas.alpha_composite(grains_masked)

    return _to_data_uri(canvas.resize((size, size), Image.LANCZOS))


def _draw_chopstick(s: int, rot_deg: float) -> Image.Image:
    stick = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(stick)
    length = s * 0.9
    top_w, bottom_w = s * 0.018, s * 0.045
    x0, y0 = s / 2, s * 0.06
    y1 = y0 + length
    poly = [
        (x0 - top_w / 2, y0),
        (x0 + top_w / 2, y0),
        (x0 + bottom_w / 2, y1),
        (x0 - bottom_w / 2, y1),
    ]
    draw.polygon(poly, fill=(190, 142, 88, 255))
    draw.line([(x0 - top_w * 0.1, y0 + 4), (x0 - bottom_w * 0.28, y1 - 8)],
              fill=(235, 200, 150, 190), width=max(1, int(s * 0.006)))
    draw.line([(x0 + top_w * 0.25, y0 + 4), (x0 + bottom_w * 0.32, y1 - 8)],
              fill=(120, 82, 42, 140), width=max(1, int(s * 0.004)))
    draw.ellipse([x0 - bottom_w / 2, y1 - bottom_w * 0.6, x0 + bottom_w / 2, y1 + bottom_w * 0.4],
                 fill=(170, 122, 70, 255))
    return stick.rotate(rot_deg, resample=Image.BICUBIC, center=(x0, y0 + s * 0.05))


@st.cache_data
def make_chopsticks_image() -> str:
    """이모지 대신 나무 질감 음영이 있는 젓가락 한 쌍을 그려서 base64로 반환한다."""
    size, scale = 220, 3
    s = size * scale
    canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    canvas.alpha_composite(_draw_chopstick(s, -4), (int(-s * 0.015), 0))
    canvas.alpha_composite(_draw_chopstick(s, 4), (int(s * 0.015), 0))
    return _to_data_uri(canvas.resize((size, size), Image.LANCZOS))


@st.cache_data
def load_html() -> str:
    """index.html을 읽어오고, 로컬/생성 이미지를 base64로 인라인 처리한다.

    Streamlit Cloud의 컴포넌트 iframe은 상대경로의 로컬 파일을 직접 서빙하지
    못하기 때문에, 이미지를 data URI로 변환해 <img src="..."> 를 치환한다.
    """
    html = HTML_PATH.read_text(encoding="utf-8")

    if IMAGE_PATH.exists():
        img_b64 = base64.b64encode(IMAGE_PATH.read_bytes()).decode("utf-8")
        html = html.replace("baby.png", f"data:image/png;base64,{img_b64}")

    html = html.replace("rice.png", make_rice_image())
    html = html.replace("chopsticks.png", make_chopsticks_image())

    return html


html_content = load_html()

# st.iframe은 HTML 문자열을 넣으면 콘텐츠 높이에 맞춰 자동으로 사이즈를 잡아준다
# (components.html처럼 height를 직접 어림짐작해서 넣을 필요가 없음)
st.iframe(html_content, height="content", width="stretch")
