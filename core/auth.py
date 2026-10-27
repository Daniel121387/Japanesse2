"""PIN 접속 보호와 '이 기기 기억하기' (PRD 7장 보안).

로그인 상태는 세션에만 있어서 새로고침하면 사라진다. '기억하기'를 고르면 PIN 해시를 쿠키에 넣고,
다음 접속 때 st.context.cookies 로 읽어 PIN을 다시 묻지 않는다.
Streamlit은 서버에서 쿠키를 쓸 수 없으므로 components.html 의 스크립트로 쓴다
(srcdoc iframe은 앱과 같은 출처라 document.cookie 가 앱 도메인에 저장된다).
"""
from __future__ import annotations

import hashlib

import streamlit as st
import streamlit.components.v1 as components

COOKIE = "jp_study_auth"
REMEMBER_DAYS = 90


def secret_pin() -> str | None:
    try:
        pin = st.secrets.get("pin")
    except Exception:  # secrets.toml이 없으면 PIN 없이 사용
        return None
    return str(pin) if pin else None


def _token(pin: str) -> str:
    return hashlib.sha256(f"jp-study:{pin}".encode("utf-8")).hexdigest()


def _write_cookie(value: str, max_age: int) -> None:
    components.html(
        f"<script>document.cookie = '{COOKIE}={value}; max-age={max_age}; path=/; SameSite=Lax';</script>",
        height=0,
    )


def remembered(pin: str) -> bool:
    # 로그아웃한 세션에서는 접속할 때 받은 (지워지기 전) 쿠키를 무시한다
    if st.session_state.get("logged_out"):
        return False
    return st.context.cookies.get(COOKIE) == _token(pin)


def remember_device(pin: str) -> None:
    _write_cookie(_token(pin), REMEMBER_DAYS * 24 * 60 * 60)


def forget_device() -> None:
    _write_cookie("", 0)


def gate() -> None:
    """PIN이 설정돼 있으면 인증될 때까지 PIN 입력 화면을 보여 주고 멈춘다."""
    pin = secret_pin()
    if not pin or st.session_state.get("authenticated"):
        return
    if remembered(pin):
        st.session_state["authenticated"] = True
        return

    if st.session_state.pop("forget_device", False):
        forget_device()

    st.title("🗾 하루 한 문장 일본어")
    with st.form("pin_form"):
        entered = st.text_input("PIN", type="password")
        keep = st.checkbox(f"이 기기에서 {REMEMBER_DAYS}일 동안 기억하기", value=True)
        if st.form_submit_button("들어가기", width="stretch"):
            if entered == pin:
                st.session_state["authenticated"] = True
                st.session_state["logged_out"] = False
                st.session_state["remember_pending"] = keep
                st.rerun()
            st.error("PIN이 맞지 않아요.")
    st.stop()


def finish_login() -> None:
    """인증 직후 실행에서 쿠키를 쓴다 (PIN 화면에서 바로 rerun 하면 스크립트가 실행되지 않으므로)."""
    pin = secret_pin()
    if pin and st.session_state.pop("remember_pending", False):
        remember_device(pin)


def logout() -> None:
    st.session_state["authenticated"] = False
    st.session_state["logged_out"] = True
    st.session_state["forget_device"] = True
