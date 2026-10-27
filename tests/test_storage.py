from core.storage import SQLiteStorage


def test_sqlite_roundtrip(tmp_path):
    s = SQLiteStorage(tmp_path / "t.db")

    s.mark_learned(1)
    s.set_repeat_count(1, 3)
    s.set_status(2, "confused")
    s.mark_learned(2)  # 이미 confused면 상태 유지
    progress = s.get_progress()
    assert progress[1]["status"] == "learned"
    assert progress[1]["repeat_count"] == 3
    assert progress[1]["learned_at"]
    assert progress[2]["status"] == "confused"

    s.add_test_result(1, 80, [3, 4])
    s.add_test_result(2, 100, [])
    assert [r["score"] for r in s.get_test_results()] == [80, 100]
    assert s.get_test_results(1)[0]["wrong_ids"] == [3, 4]

    s.set_setting("user_name", "キム")
    s.set_setting("user_name", "イ")
    assert s.get_setting("user_name") == "イ"
    assert s.get_setting("missing", "x") == "x"

    s.reset()
    assert s.get_progress() == {}
    assert s.get_test_results() == []
    assert s.get_setting("user_name") == "イ"


def test_mark_learned_records_given_time_once(tmp_path):
    from datetime import datetime

    from core.schedule import KST

    s = SQLiteStorage(tmp_path / "t.db")
    s.mark_learned(3, at=datetime(2026, 11, 4, 8, 30, tzinfo=KST))  # 날짜 시뮬레이션 중의 '지금'
    s.mark_learned(3, at=datetime(2026, 11, 9, 8, 30, tzinfo=KST))  # 다시 눌러도 처음 시각 유지
    assert s.get_progress()[3]["learned_at"] == "2026-11-04T08:30:00+09:00"
