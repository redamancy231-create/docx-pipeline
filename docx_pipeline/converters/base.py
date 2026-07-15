#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Abstract base class for docx_pipeline converters.

All converters inherit from ``AbstractConverter`` and implement ``convert()``.
The base class handles config binding, output path resolution, and the
``save()`` convenience method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from docx import Document as DocxDocument

from docx_pipeline.config.schema import DocxPipelineConfig


class AbstractConverter(ABC):
    """Abstract base for all Markdown→DOCX converters.

    Subclasses must implement :meth:`convert` which returns a populated
    ``python-docx`` :class:`~docx.document.Document` object.

    Parameters
    ----------
    config : DocxPipelineConfig
        The fully-resolved pipeline configuration.  The converter reads
        ``config.paths.md_source``, ``config.paths.docx_output``,
        ``config.page``, ``config.fonts``, ``config.styles``, etc.
    """

    def __init__(self, config: DocxPipelineConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Abstract contract
    # ------------------------------------------------------------------

    @abstractmethod
    def convert(self) -> DocxDocument:
        """Parse Markdown input and assemble a ``Document``.

        Returns
        -------
        docx.document.Document
            A fully-built document ready for post-processing or saving.
        """
        ...

    # ------------------------------------------------------------------
    # save
    # ------------------------------------------------------------------

    def save(self, output_path: Optional[str] = None) -> str:
        """Call :meth:`convert` and persist the result to disk.

        Parameters
        ----------
        output_path : str, optional
            Destination file path.  If *None*, the path is derived from
            ``config.paths.docx_output``.  When that value is a directory,
            the output filename is inferred from ``config.paths.md_source``
            (stem + ``.docx``).

        Returns
        -------
        str
            The absolute path the document was saved to.
        """
        # 1. Convert
        doc = self.convert()

        # 2. Resolve output path
        resolved = self._resolve_output_path(output_path)

        # 3. Ensure parent directory exists
        out = Path(resolved)
        out.parent.mkdir(parents=True, exist_ok=True)

        # 3.5. Backup existing output (if backup is enabled)
        if self.config.backup.enabled and out.exists():
            self._rotate_backups(out)

        # 4. Save to temp file, then atomically replace
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            dir=str(out.parent), prefix=".docx_tmp_", suffix=".docx",
            delete=False,
        )
        try:
            tmp.close()
            doc.save(tmp.name)
            # Atomic replace on same filesystem
            tmp_path = Path(tmp.name)
            tmp_path.replace(out)
        except Exception:
            Path(tmp.name).unlink(missing_ok=True)
            raise

        return str(out.resolve())

    def _rotate_backups(self, out: Path) -> None:
        """Rotate existing backups, keeping at most ``max_backups`` copies.

        When *max_backups* is 0, no backups are kept and all existing
        numbered backups for this output are removed.  When the limit is
        lowered, backups beyond the new limit are cleaned up.
        Handles non-consecutive numbering (e.g. .bak1, .bak3, .bak100).
        """
        import shutil as _shutil
        import re as _re
        import glob as _glob
        suffix = self.config.backup.suffix or ".bak"
        max_backups = self.config.backup.max_backups

        # Enumerate all existing numbered backups (handles gaps)
        pattern = _re.escape(str(out)) + _re.escape(suffix) + r"(\d+)$"
        existing = []
        for p_str in _glob.glob(str(out) + suffix + "*"):
            m = _re.match(pattern, p_str)
            if m:
                existing.append((int(m.group(1)), Path(p_str)))
        existing.sort(key=lambda x: x[0])

        if max_backups == 0:
            for _, p in existing:
                p.unlink(missing_ok=True)
            return

        # Remove backups beyond the new limit
        for num, p in existing:
            if num > max_backups:
                p.unlink(missing_ok=True)

        # Shift remaining backups: highest first to avoid overwrites
        remaining = [n for n, _ in existing if n <= max_backups]
        if remaining:
            for num in sorted(remaining, reverse=True):
                src = out.parent / f"{out.name}{suffix}{num}"
                if num < max_backups:
                    dst = out.parent / f"{out.name}{suffix}{num + 1}"
                    if src.exists():
                        src.replace(dst)
                elif num == max_backups:
                    src.unlink(missing_ok=True)

        # Copy current file to .bak.1
        first_bak = out.parent / f"{out.name}{suffix}1"
        _shutil.copy2(str(out), str(first_bak))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_output_path(self, output_path: Optional[str]) -> str:
        """Determine the concrete output file path.  Enforces ``.docx`` extension."""
        def _ensure_docx(p: Path) -> str:
            if p.suffix and p.suffix.lower() != ".docx":
                raise ValueError(
                    f"Output path must have .docx extension, got: {p.suffix}"
                )
            return str(p.resolve())

        if output_path:
            return _ensure_docx(Path(output_path))

        base = Path(self.config.paths.docx_output)
        if base.suffix:                     # looks like a file path
            return _ensure_docx(base)

        # base is a directory — derive filename from md_source
        md_path = Path(self.config.paths.md_source)
        stem = md_path.stem or "output"
        return str((base / f"{stem}.docx").resolve())
