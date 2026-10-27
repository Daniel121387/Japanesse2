"""저장소 위에서 동작하는 학습 규칙: 이름 반영, 잠금, 밀린 학습, 오답 노트, 테스트 기록."""
from __future__ import annotations

from datetime import date

from core import content, schedule
from core.storage import Storage

FINAL_TEST_WEEK = 99  # test_results.week 에 저장하는 최종 테스트 번호
FINAL_KEY = "final"
CONFUSED_DECK = 0  # 복습 화면에서 주차 대신 고르는 '헷갈리는 문장 모음'

# settings 키
NAME_JP = "user_name_jp"
NAME_PRON = "user_name_pron"
NAME_KO = "user_name_ko"
UNLOCK_FUTURE = "unlock_future"
TTS_SLOW = "tts_slow"
FONT_SCALE = "font_scale"
SIMULATED_DATE = "simulated_date"
WRONG_NOTE = "wrong_note"

DEFAULT_NAMES = {NAME_JP: "キム", NAME_PRON: "키무", NAME_KO: "김"}


# ---------- 문장 (사용자 이름 반영) ----------

def user_names(storage: Storage) -> dict[str, str]:
    return {k: storage.get_setting(k, v) or v for k, v in DEFAULT_NAMES.items()}


def personalize(sentence: dict, names: dict[str, str]) -> dict:
    """기본 이름(キム/키무/김)을 사용자 이름으로 바꾼 사본."""
    jp, pron, ko = names[NAME_JP], names[NAME_PRON], names[NAME_KO]
    defaults = DEFAULT_NAMES
    s = dict(sentence)
    for field in ("japanese", "reading", "tip"):
        s[field] = s[field].replace(defaults[NAME_JP], jp)
    s["chunks"] = [c.replace(defaults[NAME_JP], jp) for c in s.get("chunks", [])]
    s["korean_pron"] = s["korean_pron"].replace(defaults[NAME_PRON], pron)
    s["meaning"] = s["meaning"].replace(f"{defaults[NAME_KO]}입니다", f"{ko}입니다")
    return s


def sentences(storage: Storage) -> list[dict]:
    names = user_names(storage)
    return [personalize(s, names) for s in content.all_sentences()]


# ---------- 잠금 / 이용 가능 범위 ----------

def unlocked(storage: Storage) -> bool:
    return bool(storage.get_setting(UNLOCK_FUTURE, False))


def available_sentences(all_sentences: list[dict], today: date, unlock: bool) -> list[dict]:
    if unlock:
        return all_sentences
    iso = today.isoformat()
    return [s for s in all_sentences if s["date"] <= iso]


def overdue_sentences(all_sentences: list[dict], progress: dict[int, dict], today: date) -> list[dict]:
    """학습일이 지났는데 '학습 완료'를 누르지 않은 문장."""
    iso = today.isoformat()
    return [
        s for s in all_sentences
        if s["date"] < iso and not progress.get(s["id"], {}).get("learned_at")
    ]


def available_tests(today: date, unlock: bool) -> list[str]:
    """응시 가능한 테스트 키 목록: 'w1' ~ 'w10', 'final'."""
    iso = today.isoformat()
    keys = [
        f"w{w['week']}" for w in content.all_weeks()
        if w["test_date"] and (unlock or w["test_date"] <= iso)
    ]
    if unlock or today >= schedule.END:
        keys.append(FINAL_KEY)
    return keys


def test_week(key: str) -> int:
    return FINAL_TEST_WEEK if key == FINAL_KEY else int(key[1:])


def test_label(key: str) -> str:
    if key == FINAL_KEY:
        return "최종 테스트 (55문장 종합)"
    week = content.get_week(test_week(key))
    return f"{week['week']}주차 · {week['theme']}"


# ---------- 상태 ----------

def confused_ids(progress: dict[int, dict]) -> set[int]:
    return {sid for sid, p in progress.items() if p["status"] == "confused"}


def learned_count(progress: dict[int, dict]) -> int:
    return sum(1 for p in progress.values() if p.get("learned_at"))


# ---------- 오답 노트 ----------

def wrong_note(storage: Storage) -> dict[int, str]:
    """sentence_id → 'open' | 'resolved'"""
    raw = storage.get_setting(WRONG_NOTE, {}) or {}
    return {int(k): v for k, v in raw.items()}


def _save_wrong_note(storage: Storage, note: dict[int, str]) -> None:
    storage.set_setting(WRONG_NOTE, {str(k): v for k, v in sorted(note.items())})


def open_wrong_ids(storage: Storage) -> set[int]:
    return {sid for sid, state in wrong_note(storage).items() if state == "open"}


def resolve_wrong(storage: Storage, sentence_id: int) -> None:
    note = wrong_note(storage)
    if sentence_id in note:
        note[sentence_id] = "resolved"
        _save_wrong_note(storage, note)


# ---------- 테스트 기록 ----------

def record_test(storage: Storage, key: str, result: dict) -> None:
    """점수 저장 + 틀린 문장을 오답 노트(open)에 올리고 '헷갈려요' 상태로 바꾼다."""
    storage.add_test_result(test_week(key), result["score"], result["wrong_ids"])
    if result["wrong_ids"]:
        note = wrong_note(storage)
        for sid in result["wrong_ids"]:
            note[sid] = "open"
            storage.set_status(sid, "confused")
        _save_wrong_note(storage, note)


def score_summary(storage: Storage, key: str) -> dict | None:
    results = storage.get_test_results(test_week(key))
    if not results:
        return None
    return {
        "first": results[0]["score"],
        "best": max(r["score"] for r in results),
        "attempts": len(results),
    }
