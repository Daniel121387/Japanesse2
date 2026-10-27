from datetime import date

import streamlit as st

from core import auth, progress, schedule
from core.storage import SupabaseStorage, get_storage

storage = get_storage()

st.title("설정")

# ---------- 이름 ----------
st.subheader("내 이름")
st.caption("자기소개 문장 「私は○○です」에 들어가는 이름이에요.")
names = progress.user_names(storage)
with st.form("name_form"):
    jp = st.text_input("일본어 표기 (가타카나)", value=names[progress.NAME_JP], help="예: キム, イ, パク")
    pron = st.text_input("한국어 발음", value=names[progress.NAME_PRON], help="예: 키무, 이, 파쿠")
    ko = st.text_input("한국어 이름", value=names[progress.NAME_KO], help="예: 김, 이, 박")
    if st.form_submit_button("저장", width="stretch"):
        for key, value in ((progress.NAME_JP, jp), (progress.NAME_PRON, pron), (progress.NAME_KO, ko)):
            storage.set_setting(key, value.strip() or progress.DEFAULT_NAMES[key])
        st.success("저장했어요.")

# ---------- 학습 ----------
st.subheader("학습")

# 설정은 값이 바뀔 때만 저장한다 (Supabase 사용 시 매 화면 갱신마다 쓰기 요청이 가지 않도록)
current_slow = bool(storage.get_setting(progress.TTS_SLOW, False))
slow = st.toggle("발음을 기본으로 느리게 듣기", value=current_slow)
if slow != current_slow:
    storage.set_setting(progress.TTS_SLOW, slow)

FONT_SCALES = {"보통": 1.0, "크게": 1.2, "아주 크게": 1.4}
current_scale = storage.get_setting(progress.FONT_SCALE, 1.0)
font_label = st.segmented_control(
    "문장 글자 크기", list(FONT_SCALES),
    default=next((k for k, v in FONT_SCALES.items() if v == current_scale), "보통"),
)
if font_label and FONT_SCALES[font_label] != current_scale:
    storage.set_setting(progress.FONT_SCALE, FONT_SCALES[font_label])
    st.rerun()  # app.py가 새 글자 크기를 적용하도록

current_unlock = progress.unlocked(storage)
unlock = st.toggle(
    "미래 문장 잠금 해제", value=current_unlock,
    help="켜면 아직 날짜가 오지 않은 문장과 테스트도 미리 볼 수 있어요.",
)
if unlock != current_unlock:
    storage.set_setting(progress.UNLOCK_FUTURE, unlock)

# ---------- 날짜 시뮬레이션 ----------
st.subheader("날짜 시뮬레이션")
st.caption("특정 날짜로 앱이 어떻게 보이는지 확인하는 테스트용 기능이에요.")

simulated: date | None = st.session_state.get(schedule.SIM_DATE_KEY)
use_sim = st.toggle("날짜 시뮬레이션 사용", value=simulated is not None)

if use_sim:
    picked = st.date_input(
        "날짜",
        value=simulated or schedule.kst_today(),
        min_value=date(2026, 10, 1),
        max_value=date(2027, 1, 31),
    )
    st.session_state[schedule.SIM_DATE_KEY] = picked
    if picked != simulated:
        storage.set_setting(progress.SIMULATED_DATE, picked.isoformat())
    plan = schedule.get_plan(picked)
    st.success(f"{picked:%Y-%m-%d} → {schedule.ACTIVITY_LABELS[plan['activity']]}")
elif simulated is not None:
    st.session_state.pop(schedule.SIM_DATE_KEY, None)
    storage.set_setting(progress.SIMULATED_DATE, None)

# ---------- 초기화 ----------
st.subheader("진도 초기화")
st.caption("학습 기록, 테스트 점수, 오답 노트를 모두 지워요. 이름 등 설정은 남아요.")

if not st.session_state.get("confirm_reset"):
    st.button("진도 초기화", width="stretch", on_click=lambda: st.session_state.update(confirm_reset=True))
else:
    st.error("정말 모든 학습 기록을 지울까요? 되돌릴 수 없어요.")
    yes, no = st.columns(2)
    if yes.button("네, 지울게요", type="primary", width="stretch"):
        storage.reset()
        storage.set_setting(progress.WRONG_NOTE, {})
        for k in [k for k in st.session_state if str(k).startswith(("quiz_", "review_"))]:
            del st.session_state[k]
        st.session_state["confirm_reset"] = False
        st.toast("진도를 초기화했어요.")
        st.rerun()
    if no.button("취소", width="stretch"):
        st.session_state["confirm_reset"] = False
        st.rerun()

if auth.secret_pin():
    st.subheader("접속")
    st.caption("이 기기에 저장된 PIN 기억을 지우고 PIN 입력 화면으로 돌아가요.")
    if st.button("이 기기에서 로그아웃", width="stretch", icon=":material/logout:"):
        auth.logout()
        st.rerun()

st.divider()
if isinstance(storage, SupabaseStorage):
    st.caption("저장소: Supabase · 모든 기기에서 같은 진도가 보여요.")
else:
    st.caption(
        "저장소: 이 컴퓨터의 파일(SQLite) · 다른 기기와 동기화되지 않아요. "
        "배포할 때는 secrets에 Supabase를 설정하세요 (docs/supabase.sql 참고)."
    )
