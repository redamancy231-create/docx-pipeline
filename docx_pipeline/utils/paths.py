"""Cross-platform path helpers."""

import os


def normalize_path(p: str) -> str:
    """Return an absolute path using forward slashes.

    Calls ``os.path.abspath`` first so that relative paths are resolved
    against the current working directory, then replaces all backslashes
    with forward slashes (safe on Windows — the NT kernel accepts both).

    >>> normalize_path("foo/bar")
    'C:/Users/.../foo/bar'   # (exact prefix depends on cwd)
    """
    return os.path.abspath(p).replace("\\", "/")
