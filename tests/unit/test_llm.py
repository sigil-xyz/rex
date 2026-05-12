import pytest

from rex.daemon.llm import respond


def test_responds_to_time() -> None:
    response = respond("what time is it")
    assert ":" in response


def test_responds_to_date() -> None:
    response = respond("what day is it today")
    assert len(response) > 0


def test_responds_to_hello() -> None:
    assert respond("hello there") == "Hello. How can I help?"


def test_responds_to_help() -> None:
    assert respond("I need help") == "I can tell you the time, date, or just say hello."


def test_fallback_on_no_match() -> None:
    response = respond("the quick brown fox")
    assert response == "I didn't catch that. For now try asking for the time or date."


def test_case_insensitive() -> None:
    assert respond("HELLO") == respond("hello")


def test_empty_string_returns_fallback() -> None:
    response = respond("")
    assert response == "I didn't catch that. For now try asking for the time or date."
