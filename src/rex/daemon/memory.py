import sqlite3
import time
from pathlib import Path
from typing import Any, cast

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
    tool_calls_table = """
      CREATE TABLE IF NOT EXISTS tool_calls (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          turn_id INTEGER REFERENCES turns(id),
          tool_name TEXT NOT NULL,
          args TEXT NOT NULL,
          result TEXT,
          status TEXT NOT NULL,
          created_at INTEGER NOT NULL
          );
    """
    conn.execute(tool_calls_table)
    conn.commit()
    return conn


def save_turn(db: sqlite3.Connection, role: str, content: str) -> int:
    cursor = db.execute(
        "INSERT INTO turns (role, content, created_at) VALUES (?, ?, ?)",
        (role, content, int(time.time())),
    )
    db.commit()
    return cursor.lastrowid or 0


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


def save_tool_call(
    db: sqlite3.Connection,
    turn_id: int,
    tool_name: str,
    args: str,
    result: str | None,
    status: str,
) -> None:
    db.execute(
        """INSERT INTO tool_calls (turn_id, tool_name, args, result, status, created_at) VALUES (?, ?, ?, ?, ?, ?)""",
        (turn_id, tool_name, args, result, status, int(time.time())),
    )
    db.commit()


def get_recent_tool_calls(db: sqlite3.Connection, n: int) -> list[dict[str, Any]]:
    cursor = db.execute(
        "SELECT tool_name, args, result, status FROM tool_calls ORDER BY id DESC LIMIT  ?",
        (n,),
    )
    rows = cursor.fetchall()
    rows.reverse()
    return [
        {"tool_name": r[0], "args": r[1], "result": r[2], "status": r[3]} for r in rows
    ]
