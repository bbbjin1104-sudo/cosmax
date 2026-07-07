import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

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
IMAGE_PATH = BASE_DIR / "assets" / "baby.png"


@st.cache_data
def load_html() -> str:
    """index.html을 읽어오고, 로컬 이미지(assets/baby.png)는 base64로 인라인 처리한다.

    Streamlit Cloud의 컴포넌트 iframe은 상대경로의 로컬 파일을 직접 서빙하지
    못하기 때문에, 이미지를 data URI로 변환해 <img src="..."> 를 치환한다.
    """
    html = HTML_PATH.read_text(encoding="utf-8")

    if IMAGE_PATH.exists():
        img_b64 = base64.b64encode(IMAGE_PATH.read_bytes()).decode("utf-8")
        data_uri = f"data:image/png;base64,{img_b64}"
        html = html.replace("assets/baby.png", data_uri)

    return html


html_content = load_html()

# 원본 페이지가 세로로 긴 랜딩페이지이므로, 넉넉한 높이 + 내부 스크롤 허용
components.html(html_content, height=6000, scrolling=True)
