import html

import altair as alt
import pandas as pd
import streamlit as st

from core import content, progress, schedule, ui
from core.storage import get_storage

storage = get_storage()
today = schedule.today()
plan = schedule.get_plan(today)
sentences = progress.sentences(storage)
prog = storage.get_progress()

if st.session_state.get(schedule.SIM_DATE_KEY):
    st.warning("날짜 시뮬레이션 중이에요. 설정에서 끌 수 있어요.", icon=":material/science:")

# ---------- D-day ----------
d_day = schedule.days_until_trip(today)
d_text = f"D-{d_day}" if d_day > 0 else ("D-Day" if d_day == 0 else "여행 완료 🎉")
st.markdown(
    f"""<div class="hero">
      <div class="label">🗾 일본 여행까지</div>
      <div class="dday">{d_text}</div>
      <div class="sub">2027.1.19(화) ~ 1.23(토) · 오늘 {today:%m월 %d일}</div>
    </div>""",
    unsafe_allow_html=True,
)

# ---------- 오늘 할 일 ----------
activity = plan["activity"]
kind = f"{plan['week']}주차 · 오늘 할 일" if plan["week"] else "오늘 할 일"
title = schedule.ACTIVITY_LABELS[activity]
details = {
    "before_start": "11/1(일)에 시작해요. 발음 기초를 미리 봐 두세요.",
    "orientation": "앱 사용법과 발음 기초를 확인해요.",
    "review": "이번 주 5문장을 카드로 복습해요.",
    "final": "11주차 복습 후 55문장 최종 테스트에 도전해요.",
    "test": "이번 주 5문장 테스트예요. 목표는 80점!",
    "pre_trip": "테스트에서 틀리거나 헷갈린 문장을 모아 다시 외워요.",
    "trip": "상황별 문장을 꺼내 쓰세요. 즐거운 여행!",
    "after_trip": "배운 55문장을 다시 둘러봐요.",
}
if activity == "lesson":
    s = sentences[plan["sentence_id"] - 1]
    detail = f'<span lang="ja">{html.escape(s["japanese"])}</span> · {html.escape(s["meaning"])}'
else:
    detail = details[activity]
st.markdown(
    f"""<div class="todo-card">
      <div class="kind">{kind}</div>
      <div class="title">{title}</div>
      <div class="detail">{detail}</div>
    </div>""",
    unsafe_allow_html=True,
)

targets = {
    "before_start": ("pages/orientation.py", "발음 기초 미리 보기"),
    "orientation": ("pages/orientation.py", "오리엔테이션 시작"),
    "lesson": ("pages/today.py", "오늘의 문장 학습하기"),
    "review": ("pages/review.py", "복습 시작"),
    "final": ("pages/review.py", "복습 후 최종 테스트"),
    "test": ("pages/test.py", "테스트 보기"),
    "pre_trip": ("pages/review.py", "헷갈리는 문장 집중 복습"),
    "trip": ("pages/travel.py", "여행 모드 열기"),
    "after_trip": ("pages/library.py", "전체 문장 다시 보기"),
}
page, button_label = targets[activity]
if st.button(button_label, type="primary", width="stretch", icon=":material/arrow_forward:"):
    if activity == "lesson":
        ui.go_to_sentence(plan["sentence_id"])
    if activity == "test":
        st.session_state["test_select"] = f"w{plan['week']}"
    if activity in ("review", "final"):
        st.session_state["review_week"] = plan["week"]
    if activity == "pre_trip":
        st.session_state["review_week"] = progress.CONFUSED_DECK  # 없으면 복습 화면이 마지막 주차를 연다
    st.switch_page(page)

overdue = progress.overdue_sentences(sentences, prog, today)
if overdue:
    first = overdue[0]
    if st.button(
        f"밀린 학습 {len(overdue)}개 · {first['date'][5:].replace('-', '/')} 문장부터",
        width="stretch",
        icon=":material/schedule:",
    ):
        ui.go_to_sentence(first["id"])

# ---------- 진도 ----------
st.subheader("진도")
learned = progress.learned_count(prog)
st.progress(learned / schedule.TOTAL_SENTENCES, text=f"학습 완료 **{learned}** / {schedule.TOTAL_SENTENCES} 문장")

current = schedule.current_week(today)
cells = []
for w in content.all_weeks():
    n = sum(1 for s in sentences if s["week"] == w["week"] and prog.get(s["id"], {}).get("learned_at"))
    state = "done" if n == schedule.SENTENCES_PER_WEEK else ("partial" if n else "")
    if w["week"] == current:
        state += " current"
    cells.append(
        f'<div class="week-cell {state}" title="{w["week"]}주차 · {html.escape(w["theme"])}">'
        f'<b>{w["week"]}</b>{n}/5</div>'
    )
st.markdown(
    f'<div class="week-grid">{"".join(cells)}</div>'
    '<div class="legend">■ 완료 · □ 진행 중(굵은 테두리: 이번 주) · 숫자: 주차, 학습한 문장 수</div>',
    unsafe_allow_html=True,
)

# ---------- 테스트 점수 ----------
st.subheader("테스트 점수")
best: dict[int, int] = {}
for r in storage.get_test_results():
    best[r["week"]] = max(best.get(r["week"], 0), r["score"])

if best:
    df = pd.DataFrame(
        [{"주차": "최종" if w == progress.FINAL_TEST_WEEK else f"{w}주", "점수": score, "order": w}
         for w, score in sorted(best.items())]
    )
    accent = "#C2410C" if st.context.theme.type != "dark" else "#FF8A5C"
    bars = alt.Chart(df).mark_bar(color=accent, cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=28).encode(
        x=alt.X("주차:N", sort=alt.SortField("order"), title=None, axis=alt.Axis(labelAngle=0, ticks=False, domain=False)),
        y=alt.Y("점수:Q", scale=alt.Scale(domain=[0, 100]), title=None,
                axis=alt.Axis(values=[0, 80, 100], grid=False, ticks=False, domain=False)),
        tooltip=["주차", "점수"],
    )
    labels = bars.mark_text(dy=-8, fontWeight="bold").encode(text="점수:Q")
    goal = alt.Chart(pd.DataFrame({"y": [80]})).mark_rule(strokeDash=[4, 4], opacity=0.5).encode(y="y:Q")
    st.altair_chart((bars + labels + goal).properties(height=200), width="stretch")
    st.caption("최고 점수 기준 · 점선은 목표 80점")
else:
    ui.empty_state("📝", "아직 본 테스트가 없어요", "첫 주간 테스트는 11/8(일)이에요.")
