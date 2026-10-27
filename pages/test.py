import html
import random

import streamlit as st

from core import content, progress, quiz, schedule, tts, ui
from core.storage import get_storage

storage = get_storage()
today = schedule.today()
plan = schedule.get_plan(today)
unlock = progress.unlocked(storage)

st.title("테스트")

tests = progress.available_tests(today, unlock)
if not tests:
    ui.empty_state("📝", "아직 볼 수 있는 테스트가 없어요", "첫 주간 테스트는 11/8(일)이에요.")
    st.stop()

if st.session_state.get("test_select") not in tests:
    if plan["activity"] == "test" and f"w{plan['week']}" in tests:
        st.session_state["test_select"] = f"w{plan['week']}"
    else:
        st.session_state["test_select"] = tests[-1]

key = st.selectbox("테스트 선택", tests, format_func=progress.test_label, key="test_select")

quiz_key, result_key = f"quiz_{key}", f"quiz_result_{key}"

summary = progress.score_summary(storage, key)
if summary:
    st.caption(f"응시 {summary['attempts']}회 · 최초 점수 {summary['first']}점 · 최고 점수 {summary['best']}점")

# 문제와 보기는 응시 1회 동안 session_state에 고정한다 (rerun 때 섞이지 않도록)
if quiz_key not in st.session_state:
    sentences = progress.sentences(storage)
    rng = random.Random()
    if key == progress.FINAL_KEY:
        questions = quiz.final_test(sentences, schedule.TOTAL_WEEKS, progress.open_wrong_ids(storage), rng)
    else:
        review_ids = progress.confused_ids(storage.get_progress()) | progress.open_wrong_ids(storage)
        questions = quiz.weekly_test(progress.test_week(key), sentences, review_ids, rng)
    st.session_state[quiz_key] = {"questions": questions, "attempt": random.randrange(1 << 30)}

state = st.session_state[quiz_key]
questions = state["questions"]


def _retry() -> None:
    st.session_state.pop(quiz_key, None)
    st.session_state.pop(result_key, None)


QUESTION_TEXT = {
    "meaning": "이 문장의 뜻은?",
    "japanese": "이 뜻의 일본어는?",
    "listen": "음성을 듣고 뜻을 고르세요.",
    "build": "조각을 순서대로 골라 일본어 문장을 만드세요.",
}


def _question_header(i: int, q: dict) -> None:
    st.markdown(
        f'<div class="muted"><b>{i}</b> / {len(questions)} · {quiz.TYPE_LABELS[q["type"]]} · {QUESTION_TEXT[q["type"]]}</div>',
        unsafe_allow_html=True,
    )
    if q["type"] != "listen":
        lang = ' lang="ja"' if q["type"] == "meaning" else ""
        st.markdown(f'<div class="question"{lang}>{html.escape(q["prompt"])}</div>', unsafe_allow_html=True)


result = st.session_state.get(result_key)

if result is None:
    # ---------- 문제 풀기 ----------
    st.caption(f"{len(questions)}문항")
    with st.form(f"form_{key}_{state['attempt']}", border=False):
        answers = {}
        for i, q in enumerate(questions, 1):
            widget_key = f"{key}_{state['attempt']}_{q['qid']}"
            with st.container(border=True):
                _question_header(i, q)
                if q["type"] == "listen":
                    tts.play(q["prompt"])
                if q["type"] == "build":
                    # 자리마다 조각을 하나씩 고른다 (multiselect 는 'Select all' 이 붙어 순서 맞추기에 맞지 않음)
                    picks = [
                        st.radio(f"{n}번째 조각", q["choices"], index=None, horizontal=True, key=f"{widget_key}_{n}")
                        for n in range(1, len(q["choices"]) + 1)
                    ]
                    answers[q["qid"]] = "".join(picks) if None not in picks else None
                else:
                    answers[q["qid"]] = st.radio(
                        f"{i}번 답", q["choices"], index=None, key=widget_key, label_visibility="collapsed",
                    )
        submitted = st.form_submit_button("제출하기", type="primary", width="stretch")

    if submitted:
        missing = [i for i, q in enumerate(questions, 1) if answers[q["qid"]] is None]
        if missing:
            st.warning(f"아직 안 푼 문제가 있어요: {', '.join(map(str, missing))}번")
        else:
            result = quiz.grade(questions, answers)
            progress.record_test(storage, key, result)
            st.session_state[result_key] = result
            st.session_state["celebrate"] = result["score"] >= 80
            st.rerun()
else:
    # ---------- 결과 ----------
    st.markdown(
        f"""<div class="score">
          <div class="num">{result['score']}<small>점</small></div>
          <div class="sub">{result['total']}문항 중 {result['correct']}개 정답</div>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.session_state.pop("celebrate", False):
        st.balloons()
    if result["score"] >= 80:
        st.success("목표 80점 달성! 정말 잘했어요 🎉")
    else:
        st.info("틀린 문장은 오답 노트에 담았어요. 복습하고 다시 도전해 보세요.")

    if key == progress.FINAL_KEY:
        st.subheader("주제별 정답률")
        rows = [
            {"주차": f"{w}주", "주제": content.get_week(w)["theme"], "정답률": f"{c}/{t} ({round(c / t * 100)}%)"}
            for w, (c, t) in quiz.accuracy_by_week(result["results"]).items()
        ]
        st.dataframe(rows, hide_index=True, width="stretch")
        st.caption("정답률이 낮은 주제는 1/17~18에 집중 복습하세요.")

    st.subheader("문항별 결과")
    sentences = {s["id"]: s for s in progress.sentences(storage)}
    for i, r in enumerate(result["results"], 1):
        q, s = r["question"], sentences[r["question"]["sentence_id"]]
        mark = '<span class="ok">✅ 정답</span>' if r["correct"] else '<span class="ng">❌ 오답</span>'
        with st.container(border=True):
            st.markdown(f"{mark} <span class='muted'>{i}번 · {quiz.TYPE_LABELS[q['type']]}</span>", unsafe_allow_html=True)
            if q["type"] == "listen":
                st.markdown(f"들은 문장: {s['japanese']}")
            else:
                st.markdown(f"문제: {q['prompt']}")
            if not r["correct"]:
                st.markdown(f"내 답: ~~{r['chosen']}~~")
            st.markdown(f"정답: **{q['answer']}**")
            st.caption(f"{s['japanese']} · {s['korean_pron']} · {s['meaning']}")

    st.button("다시 풀기", type="primary", width="stretch", on_click=_retry, icon=":material/refresh:")
