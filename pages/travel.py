import html

import streamlit as st

from core import content, progress, schedule, tts, ui
from core.storage import get_storage

storage = get_storage()
today = schedule.today()
sentences = progress.available_sentences(progress.sentences(storage), today, progress.unlocked(storage))

st.title("✈️ 여행 모드")

if not sentences:
    ui.empty_state("🧳", "아직 공개된 문장이 없어요", "학습이 진행되면 여기에 상황별로 모여요.")
    st.stop()

category_of = {w["week"]: w["category"] for w in content.all_weeks()}
categories = list(dict.fromkeys(category_of[s["week"]] for s in sentences))
category = st.pills("상황", ["전체", *categories], default="전체", key="travel_category") or "전체"
shown = [s for s in sentences if category in ("전체", category_of[s["week"]])]

show_mode = st.toggle("보여주기 모드 (상대에게 화면 보여주기)", key="travel_show")

if show_mode:
    by_id = {s["id"]: s for s in shown}
    sid = st.selectbox(
        "문장", list(by_id),
        format_func=lambda i: f"{by_id[i]['meaning']} · {by_id[i]['japanese']}",
        key="travel_show_select",
    )
    s = by_id[sid]
    ui.sentence_card(s, ("jp",), css_class="show-card")
    st.caption(f"{s['korean_pron']} · {s['meaning']}")
    tts.play(s["japanese"])
else:
    for s in shown:
        with st.container(border=True):
            st.markdown(
                f'<div class="travel-meaning">{html.escape(s["meaning"])}</div>'
                f'<div class="travel-card"><div class="jp" lang="ja">{html.escape(s["japanese"])}</div></div>'
                f'<div class="travel-pron">{html.escape(s["korean_pron"])}</div>',
                unsafe_allow_html=True,
            )
            if st.button("🔊 듣기", key=f"travel_play_{s['id']}", width="stretch"):
                tts.play(s["japanese"], autoplay=True)
