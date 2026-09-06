"""Filesystem helpers for session-scoped notes under $HOME."""

from __future__ import annotations

import os
import re
from pathlib import Path

_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


def notes_root() -> Path:
    """Resolve the notes root directory (Foundry session $HOME)."""
    home = os.environ.get("HOME")
    if home:
        return Path(home)
    return Path.home()


def sanitize_filename(name: str) -> str:
    """Return a safe basename under $HOME, defaulting extension to .txt.

    Rejects absolute paths, path separators, and ``..`` traversal. Allows only
    alphanumeric characters plus ``-``, ``_``, and ``.``.
    """
    raw = (name or "").strip()
    if not raw:
        raise ValueError("filename must not be empty")

    candidate = Path(raw)
    if candidate.is_absolute():
        raise ValueError("absolute paths are not allowed")

    parts = candidate.parts
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("path traversal is not allowed")
    if len(parts) != 1:
        raise ValueError("filename must be a single path segment")

    basename = parts[0]
    if not _SAFE_NAME.match(basename):
        raise ValueError("filename may only contain letters, digits, '-', '_', and '.'")
    if basename in (".", "..") or basename.startswith("."):
        raise ValueError("hidden or special filenames are not allowed")

    if Path(basename).suffix == "":
        basename = f"{basename}.txt"
    return basename


def _resolve_note_path(filename: str) -> Path:
    safe = sanitize_filename(filename)
    root = notes_root().resolve()
    path = (root / safe).resolve()
    if path.parent != root:
        raise ValueError("path escape outside $HOME is not allowed")
    return path


def save_note(filename: str, content: str) -> str:
    """Write UTF-8 note under $HOME (overwrite OK).

    Returns exactly ``saved note as {filename}`` using the final on-disk basename.
    """
    try:
        path = _resolve_note_path(filename)
    except ValueError as exc:
        return f"error: {exc}"

    path.write_text(content if content is not None else "", encoding="utf-8")
    return f"saved note as {path.name}"


def read_note(filename: str) -> str:
    """Read a UTF-8 note from $HOME, or a clear error message."""
    try:
        path = _resolve_note_path(filename)
    except ValueError as exc:
        return f"error: {exc}"

    if not path.is_file():
        return f"error: note not found: {path.name}"
    return path.read_text(encoding="utf-8")


_NOTE_SUFFIXES = {".txt", ".md"}


def list_notes() -> str:
    """List note filenames under $HOME (non-recursive, note files only)."""
    root = notes_root()
    if not root.is_dir():
        return "error: notes directory is not available"

    names = sorted(
        p.name
        for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in _NOTE_SUFFIXES
    )
    if not names:
        return "(no notes)"
    return "\n".join(names)
