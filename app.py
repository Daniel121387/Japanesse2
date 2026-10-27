from datetime import date
from pathlib import Path

import streamlit as st

from core import auth, progress, schedule
from core.storage import get_storage

ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="하루 한 문장 일본어", page_icon="🗾", layout="centered")

css = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

auth.gate()
auth.finish_login()

storage = get_storage()

# 저장해 둔 날짜 시뮬레이션 값은 세션이 시작될 때 한 번 불러온다 (새로고침해도 유지)
if "sim_loaded" not in st.session_state:
    saved = storage.get_setting(progress.SIMULATED_DATE)
    if saved:
        st.session_state[schedule.SIM_DATE_KEY] = date.fromisoformat(saved)
    st.session_state["sim_loaded"] = True

# style.css 가 쓰는 색 변수. config.toml 테마와 같은 색 계열로 라이트/다크를 나눈다
# accent: 글자색 강조 / solid: 흰 글씨를 올리는 채움 배경 (다크에서도 대비 유지)
PALETTES = {
    "light": {
        "accent": "#C2410C", "solid": "#C2410C", "solid-deep": "#9A3412", "accent-soft": "#FCE9DC",
        "text": "#2B2420", "muted": "#7A6E64", "card-bg": "#FFFFFF", "card-border": "#E6DCCF",
        "shadow": "rgba(80, 50, 20, 0.06)", "nav-bg": "#FBF8F3", "ok": "#2F7D4F", "ng": "#C0362C",
    },
    "dark": {
        "accent": "#FF8A5C", "solid": "#C2410C", "solid-deep": "#7C2D12", "accent-soft": "#3A2419",
        "text": "#F2EBE3", "muted": "#A99D92", "card-bg": "#24201D", "card-border": "#3A332E",
        "shadow": "rgba(0, 0, 0, 0.3)", "nav-bg": "#1B1816", "ok": "#5CC08A", "ng": "#FF7B6E",
    },
}
theme = st.context.theme.type if st.context.theme.type in PALETTES else "light"
css_vars = "".join(f"--{k}: {v};" for k, v in PALETTES[theme].items())
font_scale = storage.get_setting(progress.FONT_SCALE, 1.0)
st.markdown(f"<style>:root {{ {css_vars} --font-scale: {font_scale}; }}</style>", unsafe_allow_html=True)

# 여행 기간에는 첫 화면을 여행 모드로
in_trip = schedule.get_plan(schedule.today())["activity"] == "trip"

pages = {
    "": [
        st.Page("pages/home.py", title="홈", icon=":material/home:", default=not in_trip),
        st.Page("pages/today.py", title="오늘", icon=":material/menu_book:"),
        st.Page("pages/review.py", title="복습", icon=":material/style:"),
        st.Page("pages/test.py", title="테스트", icon=":material/quiz:"),
        st.Page("pages/travel.py", title="여행", icon=":material/flight:", default=in_trip),
    ],
    "더보기": [
        st.Page("pages/library.py", title="문장 · 오답 노트", icon=":material/list:"),
        st.Page("pages/orientation.py", title="발음 기초", icon=":material/school:"),
        st.Page("pages/settings.py", title="설정", icon=":material/settings:"),
    ],
}

nav = st.navigation(pages, position="top")

# 휴대폰 하단 메뉴 (CSS로 좁은 화면에서만 보인다)
with st.container(key="mobile_nav", horizontal=True):
    st.page_link("pages/home.py", label="홈", icon=":material/home:")
    st.page_link("pages/today.py", label="오늘", icon=":material/menu_book:")
    st.page_link("pages/review.py", label="복습", icon=":material/style:")
    st.page_link("pages/test.py", label="테스트", icon=":material/quiz:")
    st.page_link("pages/travel.py", label="여행", icon=":material/flight:")

nav.run()
