import sys
from unittest.mock import patch

import pytest

from rex.cli.remember import remember_main
from rex.daemon.memory import init_db


def _fresh_db() -> object:
    return init_db(":memory:")


def test_remember_saves_fact(capsys: pytest.CaptureFixture[str]) -> None:
    db = _fresh_db()
    with (
        patch("rex.cli.remember._open_db", return_value=db),
        patch.object(sys, "argv", ["rex-remember", "my name is Vinod"]),
    ):
        remember_main()
    assert "Remembered" in capsys.readouterr().out


def test_remember_duplicate_prints_already_known(capsys: pytest.CaptureFixture[str]) -> None:
    db = _fresh_db()
    with (
        patch("rex.cli.remember._open_db", return_value=db),
        patch.object(sys, "argv", ["rex-remember", "same fact"]),
    ):
        remember_main()
        remember_main()
    assert "Already known" in capsys.readouterr().out


def test_remember_list_empty(capsys: pytest.CaptureFixture[str]) -> None:
    db = _fresh_db()
    with (
        patch("rex.cli.remember._open_db", return_value=db),
        patch.object(sys, "argv", ["rex-remember", "--list"]),
    ):
        remember_main()
    assert "No facts stored" in capsys.readouterr().out


def test_remember_list_shows_facts(capsys: pytest.CaptureFixture[str]) -> None:
    db = _fresh_db()
    with (
        patch("rex.cli.remember._open_db", return_value=db),
        patch.object(sys, "argv", ["rex-remember", "fact one"]),
    ):
        remember_main()
    with (
        patch("rex.cli.remember._open_db", return_value=db),
        patch.object(sys, "argv", ["rex-remember", "fact two"]),
    ):
        remember_main()
    with (
        patch("rex.cli.remember._open_db", return_value=db),
        patch.object(sys, "argv", ["rex-remember", "--list"]),
    ):
        remember_main()
    out = capsys.readouterr().out
    assert "fact one" in out
    assert "fact two" in out


def test_remember_forget_by_index(capsys: pytest.CaptureFixture[str]) -> None:
    db = _fresh_db()
    for fact in ["fact one", "fact two", "fact three"]:
        with (
            patch("rex.cli.remember._open_db", return_value=db),
            patch.object(sys, "argv", ["rex-remember", fact]),
        ):
            remember_main()
    capsys.readouterr()  # discard setup output
    with (
        patch("rex.cli.remember._open_db", return_value=db),
        patch.object(sys, "argv", ["rex-remember", "--forget", "2"]),
    ):
        remember_main()
    assert "Forgotten: fact two" in capsys.readouterr().out


def test_remember_forget_out_of_range_exits_1() -> None:
    db = _fresh_db()
    with (
        patch("rex.cli.remember._open_db", return_value=db),
        patch.object(sys, "argv", ["rex-remember", "only fact"]),
    ):
        remember_main()
    with (
        patch("rex.cli.remember._open_db", return_value=db),
        patch.object(sys, "argv", ["rex-remember", "--forget", "99"]),
        pytest.raises(SystemExit) as exc,
    ):
        remember_main()
    assert exc.value.code == 1


def test_remember_forget_not_a_number_exits_1() -> None:
    db = _fresh_db()
    with (
        patch("rex.cli.remember._open_db", return_value=db),
        patch.object(sys, "argv", ["rex-remember", "--forget", "some text"]),
        pytest.raises(SystemExit) as exc,
    ):
        remember_main()
    assert exc.value.code == 1


def test_remember_forget_zero_exits_1() -> None:
    db = _fresh_db()
    with (
        patch("rex.cli.remember._open_db", return_value=db),
        patch.object(sys, "argv", ["rex-remember", "--forget", "0"]),
        pytest.raises(SystemExit) as exc,
    ):
        remember_main()
    assert exc.value.code == 1


def test_remember_no_args_exits_1() -> None:
    with (
        patch.object(sys, "argv", ["rex-remember"]),
        pytest.raises(SystemExit) as exc,
    ):
        remember_main()
    assert exc.value.code == 1


def test_remember_forget_no_number_arg_exits_1() -> None:
    with (
        patch.object(sys, "argv", ["rex-remember", "--forget"]),
        pytest.raises(SystemExit) as exc,
    ):
        remember_main()
    assert exc.value.code == 1
