import os
from pathlib import Path

from line_stock_chatbot.cli import load_dotenv


def test_load_dotenv_sets_missing_values(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("LINE_TO_ID", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("LINE_TO_ID=U123\n", encoding="utf-8")

    load_dotenv(env_file)

    assert os.environ["LINE_TO_ID"] == "U123"


def test_load_dotenv_keeps_existing_values(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LINE_TO_ID", "existing")
    env_file = tmp_path / ".env"
    env_file.write_text("LINE_TO_ID=from-file\n", encoding="utf-8")

    load_dotenv(env_file)

    assert os.environ["LINE_TO_ID"] == "existing"

