"""학습 문장 데이터(data/sentences.json) 로드와 조회."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import streamlit as st

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sentences.json"


@st.cache_data
def load_data() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def all_sentences() -> list[dict]:
    return load_data()["sentences"]


def all_weeks() -> list[dict]:
    return load_data()["weeks"]


def get_sentence(sentence_id: int) -> dict | None:
    return next((s for s in all_sentences() if s["id"] == sentence_id), None)


def sentences_for_week(week: int) -> list[dict]:
    return [s for s in all_sentences() if s["week"] == week]


def sentence_for_date(d: date) -> dict | None:
    iso = d.isoformat()
    return next((s for s in all_sentences() if s["date"] == iso), None)


def get_week(week: int) -> dict | None:
    return next((w for w in all_weeks() if w["week"] == week), None)
