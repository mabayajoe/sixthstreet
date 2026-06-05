import importlib.util
from pathlib import Path

processor_path = Path(__file__).resolve().parents[1] / "lambda" / "processor.py"
spec = importlib.util.spec_from_file_location("processor", processor_path)
processor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(processor)


def test_parse_json_line():
    result = processor.parse_single_line('{"account_id":"123","amount":42}')
    assert result["format"] == "json"
    assert result["data"]["account_id"] == "123"


def test_parse_key_value_line():
    result = processor.parse_single_line("account_id=123, amount=42, status=NEW")
    assert result == {
        "format": "key_value",
        "data": {"account_id": "123", "amount": "42", "status": "NEW"},
    }


def test_parse_plain_text_line():
    result = processor.parse_single_line("hello-sixth-street")
    assert result == {"format": "plain_text", "data": "hello-sixth-street"}


def test_parse_empty_line_raises():
    try:
        processor.parse_single_line("   ")
    except ValueError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
