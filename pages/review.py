import streamlit as st

from core import content, progress, schedule, tts, ui
from core.storage import get_storage

storage = get_storage()
today = schedule.today()
plan = schedule.get_plan(today)
sentences = progress.sentences(storage)
available = progress.available_sentences(sentences, today, progress.unlocked(storage))
available_ids = {s["id"] for s in available}

st.title("복습")

weeks = sorted({s["week"] for s in available})
if not weeks:
    ui.empty_state("🗂️", "아직 복습할 문장이 없어요", "첫 복습은 11/7(토)이에요.")
    st.stop()

CONFUSED_DECK = progress.CONFUSED_DECK

prog = storage.get_progress()
confused = [s for s in available if prog.get(s["id"], {}).get("status") == "confused"]
decks = ([CONFUSED_DECK] if confused else []) + weeks

if st.session_state.get("review_week") not in decks:
    st.session_state["review_week"] = plan["week"] if plan["week"] in weeks else weeks[-1]


def _deck_label(w: int) -> str:
    if w == CONFUSED_DECK:
        return f"🤔 헷갈리는 문장 모음 ({len(confused)}개)"
    return f"{w}주차 · {content.get_week(w)['theme']}"


week = st.selectbox("주차", decks, format_func=_deck_label, key="review_week")
deck_name = "헷갈리는 문장" if week == CONFUSED_DECK else f"{week}주차"

deck_key = f"review_deck_{week}"
if week == CONFUSED_DECK:
    # '외웠어요'를 누르면 상태가 바뀌어 목록에서 빠지므로, 한 바퀴 동안 카드 목록을 고정한다
    deck_ids = st.session_state.setdefault(deck_key, [s["id"] for s in confused])
    cards = [sentences[i - 1] for i in deck_ids]
else:
    cards = [s for s in sentences if s["week"] == week and s["id"] in available_ids]

direction = st.radio(
    "카드 방향",
    ["뜻 → 일본어 (말하기 연습)", "일본어 → 뜻"],
    horizontal=True,
    key="review_direction",
)
speak_mode = direction.startswith("뜻")

idx_key, flip_key = f"review_idx_{week}", f"review_flip_{week}"
idx = st.session_state.setdefault(idx_key, 0)
flipped = st.session_state.setdefault(flip_key, False)


def _move(step: int) -> None:
    st.session_state[idx_key] = st.session_state[idx_key] + step
    st.session_state[flip_key] = False


def _mark(sentence_id: int, status: str) -> None:
    storage.set_status(sentence_id, status)
    _move(1)


def _restart() -> None:
    st.session_state[idx_key] = 0
    st.session_state[flip_key] = False
    st.session_state.pop(deck_key, None)


if idx >= len(cards):
    # ---------- 한 바퀴 끝 ----------
    statuses = [prog.get(s["id"], {}).get("status", "new") for s in cards]
    st.success(
        f"{deck_name} 복습 끝! 외웠어요 {statuses.count('mastered')}개 · 헷갈려요 {statuses.count('confused')}개"
    )
    st.caption("헷갈리는 문장은 '헷갈리는 문장 모음'과 다음 테스트에 다시 나와요.")
    st.button("처음부터 다시", width="stretch", on_click=_restart)
else:
    card = cards[idx]
    st.progress((idx + 1) / len(cards), text=f"{idx + 1} / {len(cards)}")
    status = prog.get(card["id"], {}).get("status", "new")
    if status in ("mastered", "confused"):
        st.caption("지난 표시: " + ("외웠어요 👍" if status == "mastered" else "헷갈려요 🤔"))

    if not flipped:
        ui.sentence_card(card, ("meaning",) if speak_mode else ("jp",), css_class="sentence-card flash-card")
        st.caption("소리 내어 말해 본 뒤 카드를 뒤집어 확인하세요." if speak_mode else "뜻을 떠올려 본 뒤 카드를 뒤집어 확인하세요.")
        st.button("카드 뒤집기", type="primary", width="stretch", icon=":material/flip:",
                  on_click=lambda: st.session_state.update({flip_key: True}))
    else:
        ui.sentence_card(card, css_class="sentence-card flash-card")
        tts.play(card["japanese"], slow=bool(storage.get_setting(progress.TTS_SLOW, False)))
        # st.columns 는 휴대폰에서 세로로 쌓이므로 가로 컨테이너로 나란히 둔다
        with st.container(horizontal=True):
            st.button("외웠어요 👍", width="stretch", type="primary", on_click=_mark, args=(card["id"], "mastered"))
            st.button("헷갈려요 🤔", width="stretch", on_click=_mark, args=(card["id"], "confused"))

    with st.container(horizontal=True):
        st.button("이전", width="stretch", disabled=idx == 0, on_click=_move, args=(-1,))
        st.button("건너뛰기", width="stretch", on_click=_move, args=(1,))

st.divider()
st.subheader(f"{deck_name} 전체 듣기")
tts.play_many([s["japanese"] for s in cards])
with st.expander("문장 목록"):
    for s in cards:
        st.markdown(f"**{s['japanese']}** · {s['korean_pron']} · {s['meaning']}")

if week == schedule.TOTAL_WEEKS and progress.FINAL_KEY in progress.available_tests(today, progress.unlocked(storage)):
    st.divider()
    st.subheader("🏁 최종 테스트")
    st.caption("55문장 중 20문항이 나와요. 복습을 마쳤다면 도전해 보세요.")
    if st.button("최종 테스트 보러 가기", type="primary", width="stretch"):
        st.session_state["test_select"] = progress.FINAL_KEY
        st.switch_page("pages/test.py")
