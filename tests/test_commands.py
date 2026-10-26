import pytest
from services.commands import is_command, parse_command, execute_command

def test_is_command():
    assert is_command("/help") is True
    assert is_command("/ask something") is True
    assert is_command("Hello Sara") is False
    assert is_command("") is False
    assert is_command("   /date") is True

def test_parse_command():
    parsed = parse_command("/translate Spanish | Good morning")
    assert parsed["is_command"] is True
    assert parsed["command"] == "translate"
    assert parsed["args"] == "Spanish | Good morning"

def test_command_help():
    res = execute_command("/help")
    assert res["success"] is True
    assert "Sara AI Command Guide" in res["text"]
    assert "/summarize" in res["text"]

def test_command_time_and_date():
    res_time = execute_command("/time")
    assert res_time["success"] is True
    assert "Current Local Time" in res_time["text"]

    res_date = execute_command("/date")
    assert res_date["success"] is True
    assert "Current Date" in res_date["text"]

def test_command_provider():
    res = execute_command("/provider")
    assert res["success"] is True
    assert "Sara AI Provider Status" in res["text"]

def test_command_missing_arguments_no_crash():
    """Verify commands with missing arguments do not crash and return helpful hints."""
    res_ask = execute_command("/ask")
    assert res_ask["success"] is False
    assert "Missing question" in res_ask["text"]

    res_sum = execute_command("/summarize")
    assert res_sum["success"] is False
    assert "Missing text" in res_sum["text"]

    res_trans = execute_command("/translate")
    assert res_trans["success"] is False
    assert "Missing arguments" in res_trans["text"]

def test_unknown_command():
    res = execute_command("/unknowncommand123")
    assert res["success"] is False
    assert "Unknown command" in res["text"]
