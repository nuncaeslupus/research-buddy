"""Shared file-I/O helpers: uniform encoding-error reporting + atomic writes.

Two concerns centralized here so every command behaves the same way:

- ``read_text_or_error`` reads a user-supplied text file as UTF-8 and turns a
  low-level ``UnicodeDecodeError`` into a ``FileReadError`` carrying a clean,
  uniform message. This mirrors the JSON-read paths (``build`` / ``validate`` /
  ``upgrade`` / ``migrate``) hardened in PR #93, which already caught
  ``UnicodeDecodeError`` alongside ``json.JSONDecodeError``. Without it, a
  ``.md`` source (or a ``theme.css``) with invalid UTF-8 bytes tracebacks
  instead of reporting cleanly.

- ``atomic_write`` writes text to a temp sibling then renames it into place,
  removing the temp file if the write fails partway. Previously each command
  open-coded ``tmp.write_text(...)`` → ``tmp.replace(...)`` with no cleanup, so
  a failed write left a ``.tmp`` sibling behind.
"""

from __future__ import annotations

from pathlib import Path


class FileReadError(Exception):
    """A text file could not be decoded as UTF-8.

    Carries a user-facing message; command handlers catch it, print the
    message to stderr, and return a non-zero exit code — matching how the
    JSON-read paths report malformed input.
    """


def read_text_or_error(path: Path) -> str:
    """Read ``path`` as UTF-8 text, raising ``FileReadError`` on bad bytes.

    Existence is assumed to be checked by the caller (every call site already
    guards it with its own message); this helper's job is to normalize the
    invalid-encoding failure that ``Path.read_text`` would otherwise raise as
    a bare ``UnicodeDecodeError`` traceback.
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise FileReadError(f"{path.name} has invalid UTF-8 encoding: {e}") from e


def atomic_write(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically (temp sibling + rename).

    Writes UTF-8 to ``<path>.tmp`` then renames it onto ``path`` in a single
    filesystem operation, so a reader never sees a half-written file. The temp
    file is removed if the write fails before the rename, so a crash never
    leaves a ``.tmp`` sibling behind. After a successful rename the temp path no
    longer exists, so the cleanup is a no-op on the happy path.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()
