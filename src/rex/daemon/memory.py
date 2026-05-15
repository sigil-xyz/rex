import sqlite3
import time
from pathlib import Path
from typing import cast

from openai.types.chat import ChatCompletionMessageParam

DEFAULT_DB_PATH = str(Path.home() / ".local" / "share" / "rex" / "memory.db")


def init_db(path: str) -> sqlite3.Connection:
    turns_table = """
        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role Text NOT NULL,
            content TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(turns_table)
    conn.commit()
    return conn


def save_turn(db: sqlite3.Connection, role: str, content: str) -> None:
    update_data = """INSERT INTO turns (role, content,created_at) VALUES(?, ?, ?) """
    db.execute(
        update_data,
        (role, content, int(time.time())),
    )
    db.commit()


def get_history(db: sqlite3.Connection, n: int) -> list[ChatCompletionMessageParam]:
    history = """SELECT role,content FROM turns ORDER BY id DESC LIMIT ? """
    cursor = db.execute(
        history,
        (n,),
    )
    rows = cursor.fetchall()
    rows.reverse()
    return cast(
        list[ChatCompletionMessageParam],
        [{"role": row[0], "content": row[1]} for row in rows],
    )
