"""날짜 → 그날의 학습 활동 판정 (PRD 4장, 8.3).

모든 날짜는 한국 시간(Asia/Seoul) 기준이다. Streamlit Cloud 서버는 UTC로 동작하므로
`datetime.now()`나 `date.today()`를 직접 쓰지 말고 `today()`를 사용한다.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TypedDict
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

START = date(2026, 11, 1)          # 오리엔테이션 (일)
WEEK1_MONDAY = date(2026, 11, 2)
END = date(2027, 1, 16)            # 11주차 복습 + 최종 테스트 (토)
TRIP_START = date(2027, 1, 19)
TRIP_END = date(2027, 1, 23)

TOTAL_WEEKS = 11
SENTENCES_PER_WEEK = 5
TOTAL_SENTENCES = TOTAL_WEEKS * SENTENCES_PER_WEEK

# 설정 화면의 날짜 시뮬레이션 값이 저장되는 session_state 키
SIM_DATE_KEY = "simulated_date"

ACTIVITY_LABELS = {
    "before_start": "학습 시작 전",
    "orientation": "오리엔테이션",
    "lesson": "오늘의 문장",
    "review": "토요일 복습",
    "test": "주간 테스트",
    "final": "복습 + 최종 테스트",
    "pre_trip": "여행 전 집중 복습",
    "trip": "여행 모드",
    "after_trip": "전체 복습",
}


class DayPlan(TypedDict):
    activity: str
    week: int | None
    sentence_id: int | None


def kst_today(now: datetime | None = None) -> date:
    """현재 시각(또는 주어진 aware datetime)의 한국 날짜."""
    now = now or datetime.now(KST)
    return now.astimezone(KST).date()


def today() -> date:
    """앱에서 쓰는 '오늘'. 날짜 시뮬레이션 값이 있으면 그것을 우선한다."""
    try:
        import streamlit as st

        simulated = st.session_state.get(SIM_DATE_KEY)
    except Exception:
        simulated = None
    return simulated or kst_today()


def now() -> datetime:
    """앱에서 쓰는 '지금'. 날짜 시뮬레이션 중이면 그 날짜에 현재 시각을 붙인다."""
    current = datetime.now(KST)
    d = today()
    return current if d == current.date() else datetime.combine(d, current.timetz())


def get_plan(d: date) -> DayPlan:
    if d < START:
        return {"activity": "before_start", "week": None, "sentence_id": None}
    if d == START:
        return {"activity": "orientation", "week": 0, "sentence_id": None}
    if d <= END:
        week = (d - WEEK1_MONDAY).days // 7 + 1
        weekday = d.weekday()  # 월=0 ... 일=6
        if weekday <= 4:
            sentence_id = (week - 1) * SENTENCES_PER_WEEK + weekday + 1
            return {"activity": "lesson", "week": week, "sentence_id": sentence_id}
        if weekday == 5:
            activity = "final" if week == TOTAL_WEEKS else "review"
            return {"activity": activity, "week": week, "sentence_id": None}
        # 일요일: 월~토를 마친 그 주의 테스트
        return {"activity": "test", "week": week, "sentence_id": None}
    if d < TRIP_START:
        return {"activity": "pre_trip", "week": None, "sentence_id": None}
    if d <= TRIP_END:
        return {"activity": "trip", "week": None, "sentence_id": None}
    return {"activity": "after_trip", "week": None, "sentence_id": None}


def days_until_trip(d: date) -> int:
    return (TRIP_START - d).days


def lesson_date(sentence_id: int) -> date:
    week, day = divmod(sentence_id - 1, SENTENCES_PER_WEEK)
    return WEEK1_MONDAY + timedelta(weeks=week, days=day)


def current_week(d: date) -> int | None:
    """d가 속한 학습 주차 (1~11). 학습 기간 밖이면 None."""
    if not (WEEK1_MONDAY <= d <= END):
        return None
    return (d - WEEK1_MONDAY).days // 7 + 1
