from datetime import date

from core import progress
from core.storage import SQLiteStorage


def _storage(tmp_path):
    return SQLiteStorage(tmp_path / "t.db")


def test_personalize_name(tmp_path):
    s = _storage(tmp_path)
    assert progress.sentences(s)[6]["japanese"] == "私はキムです"

    s.set_setting(progress.NAME_JP, "パク")
    s.set_setting(progress.NAME_PRON, "파쿠")
    s.set_setting(progress.NAME_KO, "박")
    intro = progress.sentences(s)[6]
    assert intro["japanese"] == "私はパクです"
    assert intro["reading"] == "わたしはパクです"
    assert intro["korean_pron"] == "와타시와 파쿠데스"
    assert intro["meaning"] == "저는 박입니다"
    assert intro["chunks"] == ["私は", "パク", "です"]
    assert "パクで予約" in progress.sentences(s)[45]["tip"]


def test_available_and_overdue(tmp_path):
    s = _storage(tmp_path)
    sentences = progress.sentences(s)
    wed = date(2026, 11, 4)

    available = progress.available_sentences(sentences, wed, unlock=False)
    assert [x["id"] for x in available] == [1, 2, 3]
    assert len(progress.available_sentences(sentences, wed, unlock=True)) == 55

    s.mark_learned(1)
    overdue = progress.overdue_sentences(sentences, s.get_progress(), wed)
    assert [x["id"] for x in overdue] == [2]  # 오늘(3번)은 밀린 학습이 아님


def test_available_tests():
    assert progress.available_tests(date(2026, 11, 7), unlock=False) == []
    assert progress.available_tests(date(2026, 11, 8), unlock=False) == ["w1"]
    assert progress.available_tests(date(2027, 1, 15), unlock=False)[-1] == "w10"
    assert progress.available_tests(date(2027, 1, 16), unlock=False)[-1] == "final"
    assert len(progress.available_tests(date(2026, 11, 1), unlock=True)) == 11


def test_record_test_updates_wrong_note(tmp_path):
    s = _storage(tmp_path)
    progress.record_test(s, "w1", {"score": 60, "wrong_ids": [2, 4]})
    progress.record_test(s, "w1", {"score": 90, "wrong_ids": [2]})

    assert progress.score_summary(s, "w1") == {"first": 60, "best": 90, "attempts": 2}
    assert progress.open_wrong_ids(s) == {2, 4}
    assert progress.confused_ids(s.get_progress()) == {2, 4}

    progress.resolve_wrong(s, 4)
    assert progress.open_wrong_ids(s) == {2}

    # 해결한 문장도 다시 틀리면 오답 노트에 다시 올라온다
    progress.record_test(s, progress.FINAL_KEY, {"score": 95, "wrong_ids": [4]})
    assert progress.open_wrong_ids(s) == {2, 4}
    assert s.get_test_results(progress.FINAL_TEST_WEEK)[0]["score"] == 95
