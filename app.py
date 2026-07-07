import base64
import io
import math
import random
from pathlib import Path

import numpy as np
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


def _blob_mask(size: int, cx: int, cy: int, rx: int, ry: int, seed: int,
                n_lumps: int = 8, dist_range=(0.15, 0.5), scale_range=(0.5, 0.75)) -> Image.Image:
    """찌그러진 여러 타원을 합쳐 자연스러운 뭉치 실루엣을 만든다."""
    rnd = random.Random(seed)
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    lumps = [(0, 0, 1.0, 1.0)]
    for _ in range(n_lumps):
        angle = rnd.uniform(0, math.tau)
        dist = rnd.uniform(*dist_range)
        lumps.append((math.cos(angle) * dist, math.sin(angle) * dist,
                      rnd.uniform(*scale_range), rnd.uniform(*scale_range)))
    for dx, dy, sx, sy in lumps:
        lx, ly = cx + dx * rx, cy + dy * ry
        draw.ellipse([lx - rx * sx, ly - ry * sy, lx + rx * sx, ly + ry * sy], fill=255)
    return mask.filter(ImageFilter.GaussianBlur(size * 0.012))


@st.cache_data
def make_dimsum_image() -> str:
    """이모지 대신, 주름과 광택이 있는 찐만두(딤섬) 사진 느낌의 이미지를 그려서 base64로 반환한다."""
    size, scale = 220, 4
    s = size * scale
    cx, cy = s // 2, int(s * 0.56)
    rx, ry = int(s * 0.37), int(s * 0.32)

    canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(
        [cx - rx * 0.85, cy + ry * 0.55, cx + rx * 0.85, cy + ry * 1.2], fill=(35, 18, 8, 130)
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(s * 0.03)))

    mask = _blob_mask(s, cx, cy, rx, ry, seed=14, n_lumps=7,
                       dist_range=(0.08, 0.28), scale_range=(0.78, 0.94))

    yy, xx = np.mgrid[0:s, 0:s]
    nx = (xx - (cx - rx * 0.35)) / (rx * 1.25)
    ny = (yy - (cy - ry * 0.55)) / (ry * 1.25)
    light = np.clip(1 - (nx ** 2 + ny ** 2), 0, 1) ** 1.3

    nx2 = (xx - (cx + rx * 0.5)) / (rx * 1.05)
    ny2 = (yy - (cy + ry * 0.55)) / (ry * 1.05)
    shadow_amt = np.clip(1 - (nx2 ** 2 + ny2 ** 2), 0, 1) ** 1.5

    base = np.array([247, 240, 225], dtype=np.float32)
    highlight = np.array([255, 253, 247], dtype=np.float32)
    shade = np.array([210, 184, 148], dtype=np.float32)

    rgb = base[None, None, :] * np.ones((s, s, 1), dtype=np.float32)
    rgb = rgb + (highlight - base)[None, None, :] * light[..., None]
    rgb = rgb + (shade - base)[None, None, :] * shadow_amt[..., None] * 0.75
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    canvas.alpha_composite(Image.fromarray(np.dstack([rgb, np.array(mask)]), "RGBA"))

    # 상단에 모이는 만두 주름(pleats)
    pleats = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pleats)
    knot_x, knot_y = cx, cy - ry * 0.88
    n_pleats = 8
    for i in range(n_pleats):
        t = i / (n_pleats - 1)
        angle = math.radians(-158 + t * 316)
        ex = cx + math.cos(angle) * rx * 0.62
        ey = knot_y + ry * 0.62 + math.sin(angle) * ry * 0.18
        ctrl_x = cx + math.cos(angle) * rx * 0.32
        ctrl_y = knot_y + ry * 0.22
        pts, steps = [], 20
        for j in range(steps + 1):
            u = j / steps
            bx = (1 - u) ** 2 * knot_x + 2 * (1 - u) * u * ctrl_x + u ** 2 * ex
            by = (1 - u) ** 2 * knot_y + 2 * (1 - u) * u * ctrl_y + u ** 2 * ey
            pts.append((bx, by))
        pd.line(pts, fill=(158, 130, 98, 130), width=max(2, int(s * 0.0055)))
        pts2 = [(px + s * 0.004, py - s * 0.004) for px, py in pts]
        pd.line(pts2, fill=(255, 250, 240, 120), width=max(1, int(s * 0.003)))

    pd.ellipse(
        [knot_x - s * 0.03, knot_y - s * 0.022, knot_x + s * 0.03, knot_y + s * 0.036],
        fill=(230, 210, 182, 255),
    )

    pleats_masked = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    pleats_masked.paste(pleats, (0, 0), mask)
    canvas.alpha_composite(pleats_masked)

    # 촉촉한 찐만두 표면의 하이라이트
    spec = Image.new("L", (s, s), 0)
    ImageDraw.Draw(spec).ellipse(
        [cx - rx * 0.5, cy - ry * 0.8, cx + rx * 0.05, cy - ry * 0.1], fill=95
    )
    spec = spec.filter(ImageFilter.GaussianBlur(s * 0.045))
    spec_masked = Image.new("L", (s, s), 0)
    spec_masked.paste(spec, (0, 0), mask)
    spec_layer = Image.new("RGBA", (s, s), (255, 255, 255, 255))
    spec_layer.putalpha(spec_masked)
    canvas.alpha_composite(spec_layer)

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

    html = html.replace("dimsum.png", make_dimsum_image())
    html = html.replace("chopsticks.png", make_chopsticks_image())

    return html


html_content = load_html()

# st.iframe은 HTML 문자열을 넣으면 콘텐츠 높이에 맞춰 자동으로 사이즈를 잡아준다
# (components.html처럼 height를 직접 어림짐작해서 넣을 필요가 없음)
st.iframe(html_content, height="content", width="stretch")
