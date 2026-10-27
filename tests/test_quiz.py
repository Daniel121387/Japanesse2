import random

import pytest

from core import content, quiz


@pytest.fixture
def pool():
    return content.all_sentences()


def _check_question(q):
    assert len(set(q["choices"])) == len(q["choices"])
    if q["type"] == "build":
        assert "".join(q["choices"]) != q["answer"]  # 섞여서 나온다
        assert sorted(q["choices"]) == sorted(_chunks_of(q["answer"]))
    else:
        assert len(q["choices"]) == quiz.CHOICES_PER_QUESTION
        assert q["answer"] in q["choices"]


def _chunks_of(japanese):
    return next(s["chunks"] for s in content.all_sentences() if s["japanese"] == japanese)


@pytest.mark.parametrize("seed", range(20))
def test_weekly_test_basic(pool, seed):
    qs = quiz.weekly_test(3, pool, review_ids=set(), rng=random.Random(seed))
    assert len(qs) == 11
    assert {q["sentence_id"] for q in qs} == {11, 12, 13, 14, 15}
    assert sorted(q["type"] for q in qs) == ["build"] + ["japanese"] * 5 + ["meaning"] * 5
    for q in qs:
        _check_question(q)


def test_weekly_test_distractors_prefer_same_week(pool):
    q = quiz.make_question(pool[0], "meaning", pool, random.Random(0))
    same_week_meanings = {s["meaning"] for s in pool if s["week"] == 1}
    assert set(q["choices"]) <= same_week_meanings


def test_weekly_test_adds_previous_confused_only(pool):
    # 1, 2, 7, 8: 이전 주 / 12: 이번 주(3주차) / 40: 미래 주 → 이전 주에서 최대 3개만
    qs = quiz.weekly_test(3, pool, review_ids={1, 2, 7, 8, 12, 40}, rng=random.Random(1))
    review = [q for q in qs if q["type"] == "listen"]
    assert len(qs) == 14  # 10 + 문장 만들기 1 + 누적 3
    assert len(review) == quiz.MAX_REVIEW_QUESTIONS
    assert {q["sentence_id"] for q in review} <= {1, 2, 7, 8}


@pytest.mark.parametrize("seed", range(20))
def test_final_test(pool, seed):
    priority = {3, 17, 29}
    qs = quiz.final_test(pool, 11, priority, random.Random(seed))
    ids = [q["sentence_id"] for q in qs]
    assert len(qs) == quiz.FINAL_TEST_SIZE
    assert len(set(ids)) == len(ids)
    assert {51, 52, 53, 54, 55} <= set(ids)
    assert priority <= set(ids)
    for q in qs:
        _check_question(q)


def test_grade(pool):
    qs = quiz.weekly_test(1, pool, set(), random.Random(0))
    answers = {q["qid"]: q["answer"] for q in qs}
    assert quiz.grade(qs, answers)["score"] == 100

    # 두 문제 틀리고 한 문제는 안 풂
    wrong = [q for q in qs if q["type"] == "meaning"][:2]
    for q in wrong:
        answers[q["qid"]] = next(c for c in q["choices"] if c != q["answer"])
    skipped = next(q for q in qs if q not in wrong)
    answers[skipped["qid"]] = None
    result = quiz.grade(qs, answers)
    assert result["correct"] == 7
    assert result["score"] == 70
    assert result["wrong_ids"] == sorted({q["sentence_id"] for q in [*wrong, skipped]})


def test_accuracy_by_week(pool):
    qs = quiz.final_test(pool, 11, set(), random.Random(0))
    result = quiz.grade(qs, {q["qid"]: q["answer"] for q in qs})
    stats = quiz.accuracy_by_week(result["results"])
    assert sum(t for _, t in stats.values()) == 20
    assert all(c == t for c, t in stats.values())


def test_week1_has_no_build_question(pool):
    # 1주차는 한 단어 인사뿐이라 문장 만들기가 없다
    qs = quiz.weekly_test(1, pool, set(), random.Random(0))
    assert len(qs) == 10
    assert "build" not in {q["type"] for q in qs}


def test_build_question_grading(pool):
    s = next(x for x in pool if x["id"] == 21)  # これは / いくら / ですか
    q = quiz.make_question(s, "build", pool, random.Random(0))
    assert q["prompt"] == s["meaning"]
    right = quiz.grade([q], {q["qid"]: "".join(s["chunks"])})
    wrong = quiz.grade([q], {q["qid"]: "".join(reversed(s["chunks"]))})
    assert right["score"] == 100
    assert wrong["score"] == 0 and wrong["wrong_ids"] == [21]


def test_chunks_rebuild_sentence(pool):
    for s in pool:
        if s["chunks"]:
            assert "".join(s["chunks"]) == s["japanese"]
