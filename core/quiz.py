"""테스트 문제 생성·채점 (PRD 6.4, 6.5).

Streamlit에 의존하지 않는 순수 함수로 두고, 문제·보기 순서를 rerun 사이에 고정하는 일은
페이지(pages/test.py)에서 session_state에 결과를 저장해 처리한다.
"""
from __future__ import annotations

import random

QUESTION_TYPES = ("meaning", "japanese", "listen")
TYPE_LABELS = {
    "meaning": "뜻 고르기",
    "japanese": "일본어 고르기",
    "listen": "듣고 고르기",
    "build": "문장 만들기",
}

CHOICES_PER_QUESTION = 4
MAX_REVIEW_QUESTIONS = 3
FINAL_TEST_SIZE = 20


def make_choices(target: dict, pool: list[dict], field: str, rng: random.Random) -> list[str]:
    """정답 1개 + 오답 3개. 오답은 같은 주차(주제)에서 먼저 뽑고, 부족하면 다른 주차에서 뽑는다."""
    answer = target[field]
    same = [s for s in pool if s["week"] == target["week"] and s["id"] != target["id"]]
    other = [s for s in pool if s["week"] != target["week"]]
    rng.shuffle(same)
    rng.shuffle(other)
    distractors: list[str] = []
    for s in same + other:
        value = s[field]
        if value != answer and value not in distractors:
            distractors.append(value)
        if len(distractors) == CHOICES_PER_QUESTION - 1:
            break
    choices = [answer, *distractors]
    rng.shuffle(choices)
    return choices


def can_build(sentence: dict) -> bool:
    return len(sentence.get("chunks", [])) >= 3


def _shuffled_chunks(sentence: dict, rng: random.Random) -> list[str]:
    chunks = list(sentence["chunks"])
    while chunks == sentence["chunks"]:  # 처음부터 정답 순서로 나오지 않게
        rng.shuffle(chunks)
    return chunks


def make_question(sentence: dict, qtype: str, pool: list[dict], rng: random.Random) -> dict:
    # meaning: 일본어 → 뜻 / japanese: 뜻 → 일본어 / listen: 음성 → 뜻
    # build: 뜻을 보고 조각을 순서대로 골라 일본어 문장 만들기 (보기 = 섞은 조각, 정답 = 이어 붙인 문장)
    if qtype == "build":
        return {
            "qid": f"{sentence['id']}-build",
            "type": "build",
            "sentence_id": sentence["id"],
            "week": sentence["week"],
            "prompt": sentence["meaning"],
            "choices": _shuffled_chunks(sentence, rng),
            "answer": sentence["japanese"],
        }
    field = "japanese" if qtype == "japanese" else "meaning"
    prompt = sentence["meaning"] if qtype == "japanese" else sentence["japanese"]
    return {
        "qid": f"{sentence['id']}-{qtype}",
        "type": qtype,
        "sentence_id": sentence["id"],
        "week": sentence["week"],
        "prompt": prompt,
        "choices": make_choices(sentence, pool, field, rng),
        "answer": sentence[field],
    }


def weekly_test(
    week: int,
    pool: list[dict],
    review_ids: set[int],
    rng: random.Random,
) -> list[dict]:
    """그 주 5문장 × (뜻 고르기, 일본어 고르기)
    + 문장 만들기 1문항 (조각이 있는 문장이 있는 주만)
    + 이전 주 헷갈린 문장 최대 3개(듣고 고르기)."""
    targets = [s for s in pool if s["week"] == week]
    questions = [make_question(s, qtype, pool, rng) for s in targets for qtype in ("meaning", "japanese")]

    buildable = [s for s in targets if can_build(s)]
    if buildable:
        questions.append(make_question(rng.choice(buildable), "build", pool, rng))

    review = [s for s in pool if s["id"] in review_ids and s["week"] < week]
    rng.shuffle(review)
    questions += [make_question(s, "listen", pool, rng) for s in review[:MAX_REVIEW_QUESTIONS]]

    rng.shuffle(questions)
    return questions


def final_test(
    pool: list[dict],
    last_week: int,
    priority_ids: set[int],
    rng: random.Random,
    size: int = FINAL_TEST_SIZE,
) -> list[dict]:
    """마지막 주 5문장 필수 + 오답 노트 문장 우선 + 나머지 무작위. 문장당 1문항, 유형은 무작위
    (조각이 있는 문장은 문장 만들기도 후보)."""
    must = [s for s in pool if s["week"] == last_week]
    chosen_ids = {s["id"] for s in must}
    priority = [s for s in pool if s["id"] in priority_ids and s["id"] not in chosen_ids]
    rest = [s for s in pool if s["id"] not in priority_ids and s["id"] not in chosen_ids]
    rng.shuffle(priority)
    rng.shuffle(rest)
    targets = (must + priority + rest)[:size]
    questions = [
        make_question(s, rng.choice(QUESTION_TYPES + (("build",) if can_build(s) else ())), pool, rng)
        for s in targets
    ]
    rng.shuffle(questions)
    return questions


def grade(questions: list[dict], answers: dict[str, str | None]) -> dict:
    """answers: qid → 고른 보기 (안 고르면 None, 오답 처리)."""
    results = []
    for q in questions:
        chosen = answers.get(q["qid"])
        results.append({"question": q, "chosen": chosen, "correct": chosen == q["answer"]})
    correct = sum(r["correct"] for r in results)
    total = len(questions)
    wrong_ids = sorted({r["question"]["sentence_id"] for r in results if not r["correct"]})
    return {
        "score": round(correct / total * 100) if total else 0,
        "correct": correct,
        "total": total,
        "wrong_ids": wrong_ids,
        "results": results,
    }


def accuracy_by_week(results: list[dict]) -> dict[int, tuple[int, int]]:
    """주차 → (맞힌 수, 문항 수). 최종 테스트의 주제별 정답률 표시에 사용."""
    stats: dict[int, list[int]] = {}
    for r in results:
        s = stats.setdefault(r["question"]["week"], [0, 0])
        s[0] += r["correct"]
        s[1] += 1
    return {week: (c, t) for week, (c, t) in sorted(stats.items())}
