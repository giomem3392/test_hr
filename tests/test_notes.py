"""Unit tests for session $HOME note helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "src" / "notes-agent"
sys.path.insert(0, str(ROOT))

import notes  # noqa: E402


@pytest.fixture()
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def test_save_happy_path(home: Path) -> None:
    assert notes.save_note("meeting", "hello") == "saved note as meeting.txt"
    assert (home / "meeting.txt").read_text(encoding="utf-8") == "hello"


def test_overwrite(home: Path) -> None:
    assert notes.save_note("note.txt", "v1") == "saved note as note.txt"
    assert notes.save_note("note.txt", "v2") == "saved note as note.txt"
    assert (home / "note.txt").read_text(encoding="utf-8") == "v2"


def test_default_txt_extension(home: Path) -> None:
    assert notes.sanitize_filename("agenda") == "agenda.txt"
    assert notes.save_note("agenda", "x") == "saved note as agenda.txt"
    assert (home / "agenda.txt").is_file()


def test_reject_traversal(home: Path) -> None:
    result = notes.save_note("../x", "no")
    assert result.startswith("error:")
    assert not any(home.iterdir())


def test_reject_absolute(home: Path) -> None:
    result = notes.save_note("/etc/passwd", "no")
    assert result.startswith("error:")


def test_read_missing(home: Path) -> None:
    result = notes.read_note("missing.txt")
    assert "not found" in result.lower() or result.startswith("error:")


def test_list_notes_filters_non_notes(home: Path) -> None:
    notes.save_note("a.txt", "1")
    (home / "secret.bin").write_bytes(b"\x00\x01")
    (home / "readme.md").write_text("md", encoding="utf-8")
    listed = notes.list_notes()
    assert "a.txt" in listed
    assert "readme.md" in listed
    assert "secret.bin" not in listed
