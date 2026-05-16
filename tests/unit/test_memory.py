import sqlite3

from rex.daemon.memory import (
    delete_fact,
    get_facts,
    get_history,
    get_recent_tool_calls,
    init_db,
    save_fact,
    save_tool_call,
    save_turn,
)


def _db() -> sqlite3.Connection:
    return init_db(":memory:")


def test_save_turn_returns_id() -> None:
    db = _db()
    turn_id = save_turn(db, "user", "hello")
    assert turn_id > 0


def test_get_history_empty() -> None:
    db = _db()
    assert get_history(db, 10) == []


def test_get_history_returns_turns_in_order() -> None:
    db = _db()
    save_turn(db, "user", "ping")
    save_turn(db, "assistant", "pong")
    history = get_history(db, 10)
    assert [(m["role"], m["content"]) for m in history] == [  # type: ignore[typeddict-item]
        ("user", "ping"),
        ("assistant", "pong"),
    ]


def test_get_history_limits_to_n() -> None:
    db = _db()
    for i in range(5):
        save_turn(db, "user", f"msg {i}")
    history = get_history(db, 3)
    assert len(history) == 3
    assert history[-1]["content"] == "msg 4"  # type: ignore[typeddict-item]


def test_save_tool_call_stores_record() -> None:
    db = _db()
    turn_id = save_turn(db, "user", "run ls")
    save_tool_call(db, turn_id, "shell", '{"command": "ls"}', "file1\nfile2", "completed")
    rows = get_recent_tool_calls(db, 10)
    assert len(rows) == 1
    row = rows[0]
    assert row["tool_name"] == "shell"
    assert row["args"] == '{"command": "ls"}'
    assert row["result"] == "file1\nfile2"
    assert row["status"] == "completed"


def test_save_tool_call_null_result() -> None:
    db = _db()
    turn_id = save_turn(db, "user", "run something")
    save_tool_call(db, turn_id, "shell", '{"command": "ls"}', None, "cancelled")
    rows = get_recent_tool_calls(db, 10)
    assert rows[0]["result"] is None
    assert rows[0]["status"] == "cancelled"


def test_get_recent_tool_calls_returns_ordered() -> None:
    db = _db()
    turn_id = save_turn(db, "user", "test")
    save_tool_call(db, turn_id, "read_file", '{"path": "/tmp/a.txt"}', "content a", "completed")
    save_tool_call(db, turn_id, "shell", '{"command": "ls"}', "file1", "completed")
    save_tool_call(db, turn_id, "clipboard_read", "{}", None, "cancelled")

    # limit 2 → latest 2, returned oldest-first among those
    rows = get_recent_tool_calls(db, 2)
    assert len(rows) == 2
    assert rows[0]["tool_name"] == "shell"
    assert rows[1]["tool_name"] == "clipboard_read"


def test_get_recent_tool_calls_empty() -> None:
    db = _db()
    assert get_recent_tool_calls(db, 10) == []


# --- facts CRUD ---


def test_save_fact_returns_true_on_insert() -> None:
    db = _db()
    assert save_fact(db, "my name is Vinod") is True


def test_save_fact_persists() -> None:
    db = _db()
    save_fact(db, "uses Arch Linux")
    assert get_facts(db) == ["uses Arch Linux"]


def test_save_fact_returns_false_on_duplicate() -> None:
    db = _db()
    save_fact(db, "duplicate fact")
    assert save_fact(db, "duplicate fact") is False
    assert len(get_facts(db)) == 1


def test_get_facts_ordered_by_insertion() -> None:
    db = _db()
    save_fact(db, "B")
    save_fact(db, "A")
    assert get_facts(db) == ["B", "A"]


def test_get_facts_empty_db() -> None:
    db = _db()
    assert get_facts(db) == []


def test_delete_fact_returns_true_on_match() -> None:
    db = _db()
    save_fact(db, "to delete")
    assert delete_fact(db, "to delete") is True
    assert get_facts(db) == []


def test_delete_fact_returns_false_on_miss() -> None:
    db = _db()
    assert delete_fact(db, "nonexistent") is False


def test_facts_table_survives_reinit(tmp_path: object) -> None:
    import os

    db_path = os.path.join(str(tmp_path), "memory.db")  # type: ignore[arg-type]
    db1 = init_db(db_path)
    save_fact(db1, "persisted fact")
    db1.close()
    db2 = init_db(db_path)
    assert get_facts(db2) == ["persisted fact"]


def test_get_recent_tool_calls_caps_at_n() -> None:
    db = _db()
    turn_id = save_turn(db, "user", "test")
    save_tool_call(db, turn_id, "shell", '{"command":"ls"}', "a", "completed")
    save_tool_call(db, turn_id, "shell", '{"command":"pwd"}', "b", "completed")
    save_tool_call(db, turn_id, "read_file", '{"path":"/tmp/x"}', "c", "completed")
    rows = get_recent_tool_calls(db, 2)
    assert len(rows) == 2
    assert rows[0]["args"] == '{"command":"pwd"}'
    assert rows[1]["args"] == '{"path":"/tmp/x"}'
