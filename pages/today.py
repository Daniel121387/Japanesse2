import streamlit as st

from core import content, progress, schedule, tts, ui
from core.storage import get_storage

REPEAT_GOAL = 5

storage = get_storage()
today = schedule.today()
plan = schedule.get_plan(today)
sentences = progress.sentences(storage)
prog = storage.get_progress()
available = progress.available_sentences(sentences, today, progress.unlocked(storage))

st.title("오늘의 문장")

if not available:
    ui.empty_state("🌱", "아직 공개된 문장이 없어요", "첫 문장은 11/2(월)에 열려요.")
    st.page_link("pages/orientation.py", label="그동안 발음 기초 보기", icon=":material/school:")
    st.stop()

if plan["activity"] != "lesson":
    st.info(f"오늘({today:%m/%d})은 **{schedule.ACTIVITY_LABELS[plan['activity']]}** 날이에요. 지난 문장을 골라 다시 볼 수 있어요.")

ids = [s["id"] for s in available]
if st.session_state.get("today_select") not in ids:
    overdue = progress.overdue_sentences(available, prog, today)
    if plan["activity"] == "lesson" and plan["sentence_id"] in ids:
        st.session_state["today_select"] = plan["sentence_id"]
    elif overdue:
        st.session_state["today_select"] = overdue[0]["id"]
    else:
        st.session_state["today_select"] = ids[-1]


def _option_label(sid: int) -> str:
    s = sentences[sid - 1]
    done = "✅ " if prog.get(sid, {}).get("learned_at") else ""
    return f"{done}{sid}. {s['date'][5:]}({s['day']}) {s['japanese']}"


sid = st.selectbox("문장 선택", ids, format_func=_option_label, key="today_select")
sentence = sentences[sid - 1]
week = content.get_week(sentence["week"])
row = prog.get(sid, {})

ui.chip(f"{sentence['week']}주차 · {week['theme']} · {sentence['id']}/{schedule.TOTAL_SENTENCES}")
ui.sentence_card(sentence)

slow_default = bool(storage.get_setting(progress.TTS_SLOW, False))
speed = st.segmented_control(
    "🔊 발음 듣기", ["보통", "느리게"], default="느리게" if slow_default else "보통", key=f"speed_{sid}",
)
tts.play(sentence["japanese"], slow=speed == "느리게")

ui.tip(sentence["tip"])
with st.expander("단어 풀이"):
    ui.words(sentence)

# ---------- 따라 말하기 ----------
st.subheader("따라 말하기")
count = row.get("repeat_count", 0)
dots = "●" * min(count, REPEAT_GOAL) + "○" * max(REPEAT_GOAL - count, 0)
st.markdown(
    f'<div class="dots">{dots}</div><div class="muted">{count}회 / 목표 {REPEAT_GOAL}회</div>',
    unsafe_allow_html=True,
)
if st.button("소리 내어 한 번 말했어요 +1", width="stretch", icon=":material/record_voice_over:"):
    storage.set_repeat_count(sid, count + 1)
    st.rerun()

# ---------- 학습 완료 ----------


def _complete(sentence_id: int) -> None:
    storage.mark_learned(sentence_id, at=schedule.now())
    # 선택 상자는 고른 항목의 라벨(✅ 포함)을 브라우저 쪽에 들고 있으므로,
    # 값을 다시 지정해 새 라벨로 바뀌게 한다
    st.session_state["today_select"] = sentence_id


if row.get("learned_at"):
    st.success(f"학습 완료 ✅ ({row['learned_at'][:10]})")
else:
    st.button("학습 완료", type="primary", width="stretch", icon=":material/check:",
              on_click=_complete, args=(sid,))

# ---------- 이번 주 문장 ----------
week_sentences = [s for s in available if s["week"] == sentence["week"] and s["id"] != sid]
if week_sentences:
    st.subheader(f"{sentence['week']}주차 다른 문장")
    for s in week_sentences:
        st.button(
            f"{s['day']} · {s['japanese']} — {s['meaning']}",
            key=f"week_{s['id']}",
            width="stretch",
            on_click=lambda i=s["id"]: st.session_state.update(today_select=i),
        )
