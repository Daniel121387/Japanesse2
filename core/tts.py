"""일본어 발음 음성 (PRD 6.2).

gTTS(lang="ja")로 mp3를 만들어 .tts_cache/ 에 저장한다. 네트워크 등으로 실패하면
브라우저의 Web Speech API(ja-JP)로 읽어 주는 버튼으로 대체한다.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

CACHE_DIR = Path(__file__).resolve().parent.parent / ".tts_cache"


def _cache_path(text: str, slow: bool) -> Path:
    digest = hashlib.sha1(f"{text}|{slow}".encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"{digest}{'_slow' if slow else ''}.mp3"


def get_audio(text: str, slow: bool = False) -> bytes | None:
    path = _cache_path(text, slow)
    if path.exists():
        return path.read_bytes()
    try:
        from gtts import gTTS

        buf = io.BytesIO()
        gTTS(text, lang="ja", slow=slow).write_to_fp(buf)
    except Exception:
        return None
    data = buf.getvalue()
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        path.write_bytes(data)
    except OSError:
        pass  # 캐시 실패는 무시 (재생에는 지장 없음)
    return data


def _browser_tts(text: str, slow: bool) -> None:
    rate = 0.6 if slow else 0.9
    components.html(
        f"""
        <button id="speak" style="font-size:16px;padding:10px 18px;border-radius:8px;
                border:1px solid #ccc;background:#fff;cursor:pointer">🔊 발음 듣기</button>
        <script>
        document.getElementById("speak").onclick = () => {{
          const u = new SpeechSynthesisUtterance({json.dumps(text)});
          u.lang = "ja-JP"; u.rate = {rate};
          speechSynthesis.cancel(); speechSynthesis.speak(u);
        }};
        </script>
        """,
        height=56,
    )


def play(text: str, slow: bool = False, autoplay: bool = False) -> None:
    data = get_audio(text, slow)
    if data:
        st.audio(data, format="audio/mp3", autoplay=autoplay)
    else:
        _browser_tts(text, slow)


def play_many(texts: list[str], slow: bool = False) -> None:
    """여러 문장을 이어서 재생 (mp3 프레임은 그대로 이어 붙여도 재생된다)."""
    parts = [get_audio(t, slow) for t in texts]
    if all(parts):
        st.audio(b"".join(parts), format="audio/mp3")
    else:
        _browser_tts("。".join(texts), slow)
