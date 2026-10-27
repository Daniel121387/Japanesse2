"""학습 진도 저장소 (PRD 8.4).

`get_storage()`는 st.secrets에 [supabase] 설정이 있으면 Supabase를, 없으면 로컬 SQLite를 쓴다.
Streamlit Community Cloud는 재시작 시 로컬 파일이 사라지므로 배포 환경에서는 Supabase를 써야 한다.
"""
from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from core.schedule import KST

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "progress.db"

STATUSES = ("new", "learned", "confused", "mastered")


def _now(at: datetime | None = None) -> str:
    return (at or datetime.now(KST)).isoformat(timespec="seconds")


class Storage(ABC):
    # progress
    @abstractmethod
    def get_progress(self) -> dict[int, dict]:
        """sentence_id → {sentence_id, learned_at, repeat_count, status}"""

    @abstractmethod
    def mark_learned(self, sentence_id: int, at: datetime | None = None) -> None:
        """처음 완료한 시각만 남긴다. at: 기록할 시각 (날짜 시뮬레이션 반영용)"""

    @abstractmethod
    def set_status(self, sentence_id: int, status: str) -> None: ...

    @abstractmethod
    def set_repeat_count(self, sentence_id: int, count: int) -> None: ...

    # test_results
    @abstractmethod
    def add_test_result(self, week: int, score: int, wrong_ids: list[int]) -> None: ...

    @abstractmethod
    def get_test_results(self, week: int | None = None) -> list[dict]: ...

    # settings
    @abstractmethod
    def get_setting(self, key: str, default: Any = None) -> Any: ...

    @abstractmethod
    def set_setting(self, key: str, value: Any) -> None: ...

    @abstractmethod
    def reset(self) -> None:
        """진도·테스트 기록 삭제 (설정은 유지)."""


class SQLiteStorage(Storage):
    def __init__(self, path: Path | str = DEFAULT_DB_PATH):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False) if self.path == ":memory:" else None
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS progress (
                    sentence_id  INTEGER PRIMARY KEY,
                    learned_at   TEXT,
                    repeat_count INTEGER NOT NULL DEFAULT 0,
                    status       TEXT NOT NULL DEFAULT 'new'
                );
                CREATE TABLE IF NOT EXISTS test_results (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    week      INTEGER NOT NULL,
                    score     INTEGER NOT NULL,
                    taken_at  TEXT NOT NULL,
                    wrong_ids TEXT NOT NULL DEFAULT '[]'
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    @contextmanager
    def _conn(self):
        # Streamlit은 세션마다 스레드가 달라서 작업마다 연결을 새로 연다
        conn = self._memory_conn or sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            if conn is not self._memory_conn:
                conn.close()

    def _ensure_row(self, conn, sentence_id: int) -> None:
        conn.execute("INSERT OR IGNORE INTO progress (sentence_id) VALUES (?)", (sentence_id,))

    def get_progress(self) -> dict[int, dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM progress").fetchall()
        return {r["sentence_id"]: dict(r) for r in rows}

    def mark_learned(self, sentence_id: int, at: datetime | None = None) -> None:
        with self._conn() as conn:
            self._ensure_row(conn, sentence_id)
            conn.execute(
                """UPDATE progress
                   SET learned_at = COALESCE(learned_at, ?),
                       status = CASE WHEN status = 'new' THEN 'learned' ELSE status END
                   WHERE sentence_id = ?""",
                (_now(at), sentence_id),
            )

    def set_status(self, sentence_id: int, status: str) -> None:
        if status not in STATUSES:
            raise ValueError(f"unknown status: {status}")
        with self._conn() as conn:
            self._ensure_row(conn, sentence_id)
            conn.execute("UPDATE progress SET status = ? WHERE sentence_id = ?", (status, sentence_id))

    def set_repeat_count(self, sentence_id: int, count: int) -> None:
        with self._conn() as conn:
            self._ensure_row(conn, sentence_id)
            conn.execute("UPDATE progress SET repeat_count = ? WHERE sentence_id = ?", (count, sentence_id))

    def add_test_result(self, week: int, score: int, wrong_ids: list[int]) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO test_results (week, score, taken_at, wrong_ids) VALUES (?, ?, ?, ?)",
                (week, score, _now(), json.dumps(wrong_ids)),
            )

    def get_test_results(self, week: int | None = None) -> list[dict]:
        sql = "SELECT * FROM test_results"
        params: tuple = ()
        if week is not None:
            sql += " WHERE week = ?"
            params = (week,)
        with self._conn() as conn:
            rows = conn.execute(sql + " ORDER BY id", params).fetchall()
        return [{**dict(r), "wrong_ids": json.loads(r["wrong_ids"])} for r in rows]

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def set_setting(self, key: str, value: Any) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, json.dumps(value, ensure_ascii=False)),
            )

    def reset(self) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM progress")
            conn.execute("DELETE FROM test_results")


class SupabaseStorage(Storage):
    """Supabase(PostgreSQL) 저장소. 테이블은 docs/supabase.sql 로 만든다.

    PostgREST upsert는 보낸 컬럼만 갱신하므로, 부분 갱신도 upsert 한 번으로 처리한다.
    설정은 화면마다 여러 번 읽으므로 한 번에 모두 불러와 메모리에 둔다
    (1인용 앱이고 설정은 이 앱에서만 바뀌므로 캐시가 어긋나지 않는다).
    """

    def __init__(self, url: str, key: str):
        from supabase import create_client

        self.client = create_client(url, key)
        self._settings: dict[str, Any] | None = None

    def _progress(self):
        return self.client.table("progress")

    def get_progress(self) -> dict[int, dict]:
        rows = self._progress().select("*").execute().data
        return {r["sentence_id"]: r for r in rows}

    def mark_learned(self, sentence_id: int, at: datetime | None = None) -> None:
        current = self._progress().select("*").eq("sentence_id", sentence_id).execute().data
        row = current[0] if current else {"learned_at": None, "status": "new"}
        self._progress().upsert({
            "sentence_id": sentence_id,
            "learned_at": row["learned_at"] or _now(at),
            "status": "learned" if row["status"] == "new" else row["status"],
        }).execute()

    def set_status(self, sentence_id: int, status: str) -> None:
        if status not in STATUSES:
            raise ValueError(f"unknown status: {status}")
        self._progress().upsert({"sentence_id": sentence_id, "status": status}).execute()

    def set_repeat_count(self, sentence_id: int, count: int) -> None:
        self._progress().upsert({"sentence_id": sentence_id, "repeat_count": count}).execute()

    def add_test_result(self, week: int, score: int, wrong_ids: list[int]) -> None:
        self.client.table("test_results").insert(
            {"week": week, "score": score, "taken_at": _now(), "wrong_ids": wrong_ids}
        ).execute()

    def get_test_results(self, week: int | None = None) -> list[dict]:
        query = self.client.table("test_results").select("*")
        if week is not None:
            query = query.eq("week", week)
        return query.order("id").execute().data

    def get_setting(self, key: str, default: Any = None) -> Any:
        if self._settings is None:
            rows = self.client.table("settings").select("key, value").execute().data
            self._settings = {r["key"]: r["value"] for r in rows}
        value = self._settings.get(key)
        return default if value is None else value

    def set_setting(self, key: str, value: Any) -> None:
        self.client.table("settings").upsert({"key": key, "value": value}).execute()
        if self._settings is not None:
            self._settings[key] = value

    def reset(self) -> None:
        # PostgREST는 조건 없는 delete를 막으므로 항상 참인 조건을 붙인다
        self._progress().delete().gte("sentence_id", 0).execute()
        self.client.table("test_results").delete().gte("id", 0).execute()


def _supabase_secrets() -> dict | None:
    try:
        conf = st.secrets.get("supabase")
    except Exception:  # secrets.toml이 없으면 예외
        return None
    if conf and conf.get("url") and conf.get("key"):
        return dict(conf)
    return None


@st.cache_resource
def get_storage() -> Storage:
    conf = _supabase_secrets()
    if conf:
        return SupabaseStorage(conf["url"], conf["key"])
    return SQLiteStorage()
