#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration validator and dependency checker for docx_pipeline.

``validate_config`` returns a list of human-readable issue strings (empty =
valid).  ``check_dependencies`` probes the runtime environment for required
external tools.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from .schema import DocxPipelineConfig


# ---------------------------------------------------------------------------
# Public: validate_config
# ---------------------------------------------------------------------------

def validate_config(config: DocxPipelineConfig) -> List[str]:
    """Validate a ``DocxPipelineConfig`` and return a list of issues.

    An empty list means the configuration is valid and ready to use.

    Checks performed
    ----------------
    1. ``md_source`` exists (file).
    2. ``docx_output`` parent directory is writable (or can be created).
    3. ``work_dir`` parent is writable.
    4. Font-size values are in a sane range (4–72 pt).
    5. If ``mermaid.enabled``, ``mmdc`` is on ``PATH``.
    6. If ``pandoc.enabled``, ``pandoc`` is on ``PATH``.
    7. ``reference_docx`` (if set) points to an existing file.

    Parameters
    ----------
    config : DocxPipelineConfig

    Returns
    -------
    list[str]
        Issue descriptions.  Empty list = valid.
    """
    issues: List[str] = []

    # ---- paths ----------------------------------------------------------
    issues.extend(_check_paths(config))

    # ---- font sizes -----------------------------------------------------
    issues.extend(_check_font_sizes(config))

    # ---- external tools -------------------------------------------------
    if config.pandoc.enabled:
        issues.extend(_check_pandoc())

    if config.mermaid.enabled:
        issues.extend(_check_mermaid(config))

    # ---- reference_docx -------------------------------------------------
    if config.pandoc.reference_docx:
        ref = Path(config.pandoc.reference_docx)
        if not ref.is_file():
            issues.append(
                f"pandoc.reference_docx does not exist: {config.pandoc.reference_docx}"
            )

    if config.paths.reference_docx:
        ref = Path(config.paths.reference_docx)
        if not ref.is_file():
            issues.append(
                f"paths.reference_docx does not exist: {config.paths.reference_docx}"
            )

    return issues


# ---------------------------------------------------------------------------
# Public: check_dependencies
# ---------------------------------------------------------------------------

def check_dependencies(config: DocxPipelineConfig) -> Dict[str, Any]:
    """Probe the runtime environment and return a dependency-status dict.

    Returns a dict with keys like ``"pandoc"``, ``"mmdc"``, ``"python"``,
    each mapping to a sub-dict::

        {
            "available": bool,
            "path": str or None,
            "version": str or None,
        }

    Parameters
    ----------
    config : DocxPipelineConfig
        Used to determine which tools are *required* (e.g. mermaid only
        checked if ``mermaid.enabled``).

    Returns
    -------
    dict
    """
    result: Dict[str, Any] = {}

    # Python (always checked)
    result["python"] = _probe_python()

    # Pandoc
    result["pandoc"] = _probe_tool(
        "pandoc", required=config.pandoc.enabled
    )

    # mmdc
    mmdc_path = (
        config.mermaid.render.mmdc_path
        if config.mermaid.render.mmdc_path
        else "mmdc"
    )
    result["mmdc"] = _probe_tool(
        mmdc_path, required=config.mermaid.enabled
    )

    # yaml (library)
    result["pyyaml"] = _probe_pyyaml()

    # python-docx
    result["python_docx"] = _probe_python_docx()

    return result


# ====================================================================
# Internal check helpers
# ====================================================================

def _check_paths(config: DocxPipelineConfig) -> List[str]:
    issues: List[str] = []

    # md_source
    md = Path(config.paths.md_source)
    if not md.exists():
        issues.append(f"md_source does not exist: {config.paths.md_source}")
    elif not md.is_file():
        issues.append(f"md_source is not a file: {config.paths.md_source}")

    # docx_output parent writable
    docx = Path(config.paths.docx_output)
    _check_writable(issues, docx, "docx_output", config.paths.docx_output)

    # work_dir parent writable
    work = Path(config.paths.work_dir)
    _check_writable(issues, work, "work_dir", config.paths.work_dir)

    return issues


def _check_writable(
    issues: List[str],
    path: Path,
    label: str,
    raw: str,
) -> None:
    """Check that *path* (or its parent if the path doesnʼt exist yet) is
    writable.  Append any problem to *issues*."""
    # If path exists, check it directly
    if path.exists():
        if not os.access(path, os.W_OK):
            issues.append(f"{label} is not writable: {raw}")
        return

    # Otherwise walk up to find the nearest existing ancestor
    ancestor = path.parent
    while ancestor != ancestor.parent:
        if ancestor.exists():
            break
        ancestor = ancestor.parent

    if not ancestor.exists() or not os.access(ancestor, os.W_OK):
        issues.append(f"Cannot create {label} — parent not writable: {raw}")


def _check_font_sizes(config: DocxPipelineConfig) -> List[str]:
    issues: List[str] = []
    fs = config.font_sizes

    for attr in ("body", "table", "code"):
        val = getattr(fs, attr)
        if not (4.0 <= val <= 72.0):
            issues.append(
                f"font_sizes.{attr}={val} is out of sane range [4, 72] pt"
            )

    for level, val in fs.headings.items():
        if not (4.0 <= val <= 72.0):
            issues.append(
                f"font_sizes.headings.{level}={val} is out of sane range [4, 72] pt"
            )

    return issues


def _check_pandoc() -> List[str]:
    if shutil.which("pandoc") is None:
        return ["pandoc is enabled but 'pandoc' was not found on PATH"]
    return []


def _check_mermaid(config: DocxPipelineConfig) -> List[str]:
    mmdc = config.mermaid.render.mmdc_path or "mmdc"
    # If it's a full path, check existence; otherwise use which
    if os.path.isabs(mmdc):
        if not os.path.isfile(mmdc) and shutil.which(mmdc) is None:
            return [f"mermaid is enabled but mmdc not found: {mmdc}"]
    else:
        if shutil.which(mmdc) is None:
            return [
                f"mermaid is enabled but '{mmdc}' was not found on PATH. "
                f"Install via: npm install -g @mermaid-js/mermaid-cli"
            ]
    return []


# ====================================================================
# Probe helpers
# ====================================================================

def _probe_tool(exe: str, *, required: bool) -> Dict[str, Any]:
    """Try to locate an executable and get its --version output."""
    result: Dict[str, Any] = {
        "available": False,
        "path": None,
        "version": None,
        "required": required,
    }

    exe_path = shutil.which(exe)
    if exe_path is None and os.path.isabs(exe) and os.path.isfile(exe):
        exe_path = exe

    if exe_path is None:
        return result

    result["path"] = exe_path
    result["available"] = True

    try:
        proc = subprocess.run(
            [exe_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
        version_output = proc.stdout.strip() or proc.stderr.strip()
        if version_output:
            result["version"] = version_output.split("\n")[0][:200]
    except Exception:
        result["version"] = "(could not determine)"

    return result


def _probe_python() -> Dict[str, Any]:
    import sys as _sys

    return {
        "available": True,
        "path": _sys.executable,
        "version": _sys.version.split()[0],
        "required": True,
    }


def _probe_pyyaml() -> Dict[str, Any]:
    try:
        import yaml as _yaml
        return {"available": True, "version": getattr(_yaml, "__version__", "installed")}
    except ImportError:
        return {"available": False, "version": None}


def _probe_python_docx() -> Dict[str, Any]:
    try:
        import docx as _docx
        return {"available": True, "version": getattr(_docx, "__version__", "installed")}
    except ImportError:
        return {"available": False, "version": None}
