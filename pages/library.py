import streamlit as st

from core import content, progress, schedule, tts, ui
from core.storage import get_storage

storage = get_storage()
today = schedule.today()
sentences = progress.sentences(storage)
prog = storage.get_progress()
unlock = progress.unlocked(storage)
available_ids = {s["id"] for s in progress.available_sentences(sentences, today, unlock)}

st.title("문장 · 오답 노트")


def _play_button(s: dict, prefix: str) -> None:
    if st.button("🔊 듣기", key=f"{prefix}_play_{s['id']}"):
        tts.play(s["japanese"], autoplay=True)


def _sentence_detail(s: dict, prefix: str) -> None:
    st.markdown(f"**{s['korean_pron']}**  \n{s['reading']}")
    st.markdown(f"💡 {s['tip']}")
    ui.words(s)
    left, right = st.columns(2)
    with left:
        _play_button(s, prefix)
    with right:
        if st.button("학습 화면에서 보기", key=f"{prefix}_go_{s['id']}"):
            ui.go_to_sentence(s["id"])


all_tab, wrong_tab = st.tabs(["전체 문장", "오답 노트"])

with all_tab:
    weeks = content.all_weeks()
    week_filter = st.selectbox(
        "주차",
        [0] + [w["week"] for w in weeks],
        format_func=lambda w: "전체" if w == 0 else f"{w}주차 · {content.get_week(w)['theme']}",
    )
    query = st.text_input("검색 (일본어, 한국어 발음, 뜻)", placeholder="예: 얼마, ください").strip()

    shown = [s for s in sentences if week_filter in (0, s["week"])]
    if query:
        shown = [
            s for s in shown
            if s["id"] in available_ids
            and any(query in s[f] for f in ("japanese", "reading", "korean_pron", "meaning"))
        ]
    st.caption(f"{len(shown)}문장")

    for s in shown:
        if s["id"] not in available_ids:
            st.markdown(f"🔒 {s['id']}. {s['date'][5:]}({s['day']})에 공개돼요")
            continue
        status = prog.get(s["id"], {})
        mark = {"mastered": "👍 ", "confused": "🤔 "}.get(status.get("status"), "✅ " if status.get("learned_at") else "")
        with st.expander(f"{mark}{s['id']}. {s['japanese']} — {s['meaning']}"):
            _sentence_detail(s, "all")

with wrong_tab:
    note = progress.wrong_note(storage)
    open_ids = [sid for sid, state in note.items() if state == "open"]
    resolved_ids = [sid for sid, state in note.items() if state == "resolved"]

    if not open_ids:
        ui.empty_state("✨", "오답 노트가 비어 있어요", "테스트에서 틀린 문장이 여기에 모여요.")
    for sid in open_ids:
        s = sentences[sid - 1]
        with st.container(border=True):
            st.markdown(f"**{s['japanese']}** — {s['meaning']}")
            _sentence_detail(s, "wrong")
            st.button(
                "다시 외웠어요 (해결)", key=f"resolve_{sid}", type="primary", width="stretch",
                on_click=progress.resolve_wrong, args=(storage, sid),
            )

    if resolved_ids:
        with st.expander(f"해결한 문장 {len(resolved_ids)}개"):
            for sid in resolved_ids:
                s = sentences[sid - 1]
                st.markdown(f"- {s['japanese']} · {s['korean_pron']} · {s['meaning']}")
