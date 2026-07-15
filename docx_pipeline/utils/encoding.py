"""Windows console encoding helpers.

On win32 the default stdout/stderr codec is often not UTF-8, which breaks
Chinese-character output.  Call ``setup_windows_encoding()`` early in CLI
entry points to force UTF-8 wrappers.
"""

import os
import sys
import io


def setup_windows_encoding() -> None:
    """Force UTF-8 encoding on stdout/stderr when running under Windows.

    Sets ``PYTHONIOENCODING=utf-8`` in the process environment (child
    processes inherit it) and replaces ``sys.stdout`` / ``sys.stderr``
    with ``io.TextIOWrapper`` wrappers that use UTF-8 and replace bad
    characters rather than raising ``UnicodeEncodeError``.

    On non-Windows platforms and under pytest this is a no-op (pytest
    manages its own stream capture and wrapping stdout breaks it).
    """
    if sys.platform != "win32":
        return

    # Under pytest the capture mechanism owns stdout/stderr; wrapping
    # them causes "I/O operation on closed file" on teardown.
    if "pytest" in sys.modules:
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        return

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if stream is None:
            continue
        # Skip already-wrapped streams to avoid double-wrapping
        if isinstance(stream, io.TextIOWrapper):
            continue
        try:
            utf8_wrapper = io.TextIOWrapper(
                stream.buffer,
                encoding="utf-8",
                errors="replace",
                line_buffering=True,
            )
            setattr(sys, stream_name, utf8_wrapper)
        except (AttributeError, OSError, ValueError):
            # If the stream has no .buffer (e.g. it is already wrapped or
            # redirected) or the OS refuses the operation, keep the original.
            pass
