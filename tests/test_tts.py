import sys
import types

from core import tts


def test_get_audio_returns_none_when_gtts_fails(tmp_path, monkeypatch):
    """네트워크 오류 등으로 gTTS가 실패하면 None → 페이지는 브라우저 음성으로 대체한다."""

    class FailingTTS:
        def __init__(self, *args, **kwargs):
            raise ConnectionError("offline")

    monkeypatch.setitem(sys.modules, "gtts", types.SimpleNamespace(gTTS=FailingTTS))
    monkeypatch.setattr(tts, "CACHE_DIR", tmp_path)
    assert tts.get_audio("こんにちは") is None


def test_get_audio_uses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(tts, "CACHE_DIR", tmp_path)
    tts._cache_path("こんにちは", False).write_bytes(b"cached-mp3")
    # 캐시가 있으면 gTTS를 부르지 않는다
    monkeypatch.setitem(sys.modules, "gtts", None)
    assert tts.get_audio("こんにちは") == b"cached-mp3"
    assert tts._cache_path("こんにちは", True) != tts._cache_path("こんにちは", False)
