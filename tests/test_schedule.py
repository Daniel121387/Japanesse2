from datetime import date, datetime, timezone

import pytest

from core import content, schedule
from core.schedule import get_plan


@pytest.mark.parametrize(
    "d, activity, week, sentence_id",
    [
        (date(2026, 10, 31), "before_start", None, None),
        (date(2026, 11, 1), "orientation", 0, None),
        (date(2026, 11, 2), "lesson", 1, 1),
        (date(2026, 11, 6), "lesson", 1, 5),
        (date(2026, 11, 7), "review", 1, None),
        (date(2026, 11, 8), "test", 1, None),
        (date(2026, 11, 9), "lesson", 2, 6),
        (date(2027, 1, 1), "lesson", 9, 45),
        (date(2027, 1, 10), "test", 10, None),
        (date(2027, 1, 15), "lesson", 11, 55),
        (date(2027, 1, 16), "final", 11, None),
        (date(2027, 1, 17), "pre_trip", None, None),
        (date(2027, 1, 18), "pre_trip", None, None),
        (date(2027, 1, 19), "trip", None, None),
        (date(2027, 1, 20), "trip", None, None),
        (date(2027, 1, 23), "trip", None, None),
        (date(2027, 1, 24), "after_trip", None, None),
    ],
)
def test_get_plan(d, activity, week, sentence_id):
    assert get_plan(d) == {"activity": activity, "week": week, "sentence_id": sentence_id}


def test_every_lesson_day_maps_to_unique_sentence():
    ids = []
    d = schedule.START
    while d <= schedule.END:
        plan = get_plan(d)
        if plan["activity"] == "lesson":
            ids.append(plan["sentence_id"])
            assert schedule.lesson_date(plan["sentence_id"]) == d
        d = d.fromordinal(d.toordinal() + 1)
    assert ids == list(range(1, schedule.TOTAL_SENTENCES + 1))


def test_kst_today_after_midnight():
    # 2026-11-02 00:30 KST == 2026-11-01 15:30 UTC (서버 시간으로는 전날)
    utc_now = datetime(2026, 11, 1, 15, 30, tzinfo=timezone.utc)
    assert schedule.kst_today(utc_now) == date(2026, 11, 2)


def test_days_until_trip():
    assert schedule.days_until_trip(date(2027, 1, 18)) == 1
    assert schedule.days_until_trip(date(2027, 1, 19)) == 0


def test_sentence_data_matches_schedule():
    sentences = content.all_sentences()
    assert [s["id"] for s in sentences] == list(range(1, 56))
    required = ("japanese", "reading", "korean_pron", "meaning", "tip", "words")
    for s in sentences:
        assert all(s[f] for f in required), s["id"]
        plan = get_plan(date.fromisoformat(s["date"]))
        assert plan["activity"] == "lesson"
        assert plan["sentence_id"] == s["id"]
        assert plan["week"] == s["week"]


def test_sentence_texts_are_unique():
    # 보기 텍스트가 겹치면 정답이 두 개처럼 보이는 문제가 생긴다
    sentences = content.all_sentences()
    for field in ("japanese", "meaning", "korean_pron"):
        values = [s[field] for s in sentences]
        assert len(values) == len(set(values)), field


def test_week_meta_matches_schedule():
    weeks = content.all_weeks()
    assert [w["week"] for w in weeks] == list(range(1, 12))
    for w in weeks:
        assert get_plan(date.fromisoformat(w["review_date"]))["activity"] in ("review", "final")
        if w["test_date"]:
            assert get_plan(date.fromisoformat(w["test_date"])) == {
                "activity": "test", "week": w["week"], "sentence_id": None,
            }
