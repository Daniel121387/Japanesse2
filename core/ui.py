"""여러 페이지에서 같이 쓰는 화면 조각. 스타일은 assets/style.css."""
from __future__ import annotations

import html

import streamlit as st

_PARTS = {
    "jp": ('<div class="jp" lang="ja">{}</div>', "japanese"),
    "reading": ('<div class="reading" lang="ja">{}</div>', "reading"),
    "pron": ('<div class="pron">{}</div>', "korean_pron"),
    "meaning": ('<div class="meaning">{}</div>', "meaning"),
}


def _html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def sentence_card(
    sentence: dict,
    parts: tuple[str, ...] = ("jp", "reading", "pron", "meaning"),
    css_class: str = "sentence-card",
) -> None:
    body = "".join(tpl.format(html.escape(sentence[field])) for tpl, field in (_PARTS[p] for p in parts))
    _html(f'<div class="{css_class}">{body}</div>')


def chip(text: str) -> None:
    _html(f'<span class="chip">{html.escape(text)}</span>')


def tip(text: str) -> None:
    _html(f'<div class="tip">💡 {html.escape(text)}</div>')


def empty_state(icon: str, title: str, description: str = "") -> None:
    _html(
        f'<div class="empty"><div class="icon">{icon}</div>'
        f'<div class="title">{html.escape(title)}</div>'
        f'<div>{html.escape(description)}</div></div>'
    )


def words(sentence: dict) -> None:
    for w in sentence["words"]:
        st.markdown(f"- **{w['word']}** : {w['meaning']}")


def go_to_sentence(sentence_id: int) -> None:
    """오늘의 문장 화면에서 특정 문장을 열도록 지정한 뒤 이동."""
    st.session_state["today_select"] = sentence_id
    st.switch_page("pages/today.py")
