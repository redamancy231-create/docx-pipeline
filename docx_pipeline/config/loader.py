#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAML configuration loader with environment-variable override support.

Typical usage::

    from docx_pipeline.config.loader import load_config
    cfg = load_config("pipeline.yaml")
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from collections.abc import Mapping

import yaml

from .schema import DocxPipelineConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deep_merge(base: Dict[str, Any], override: Mapping) -> Dict[str, Any]:
    """Recursively merge *override* into *base*, returning a new dict.

    Dict values are merged recursively; scalar values are replaced.
    Lists are replaced wholesale (no concatenation).
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, Mapping):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_env_overrides(data: Dict[str, Any]) -> Dict[str, Any]:
    """Read ``DOCX_PIPELINE_*`` environment variables and merge them into *data*.

    Naming convention — use ``__`` (double underscore) for nesting levels::

        DOCX_PIPELINE__PROJECT__NAME=my_project
          → data["project"]["name"] = "my_project"

        DOCX_PIPELINE__FONT_SIZES__BODY=12.0
          → data["font_sizes"]["body"] = 12.0

        DOCX_PIPELINE__FONTS__EAST_ASIAN=SimSun
          → data["fonts"]["east_asian"] = "SimSun"

    The env-var name is split on ``__`` (after the ``DOCX_PIPELINE__`` prefix)
    and walked into nested dicts.  Only existing dict paths are traversed;
    new keys are appended at the deepest dict level reached.

    Scalar values are coerced: ``"true"/"false"`` → bool, integer strings →
    int, float strings → float.
    """
    prefix = "DOCX_PIPELINE__"
    overrides: Dict[str, Any] = {}

    for var_name, var_value in os.environ.items():
        if not var_name.startswith(prefix):
            # Also check legacy single-underscore prefix for backward compat
            if not var_name.startswith("DOCX_PIPELINE_"):
                continue
            # Legacy: skip (warn about deprecated format)
            continue

        # Strip prefix, split on double underscore for nesting levels
        path_str = var_name[len(prefix):]
        if not path_str:
            continue
        keys = [k.lower() for k in path_str.split("__")]

        # Coerce value
        coerced = _coerce_str(var_value)

        # Walk / create the nested dict
        node = overrides
        for i, key in enumerate(keys):
            if i == len(keys) - 1:
                node[key] = coerced
            else:
                node = node.setdefault(key, {})

    if overrides:
        return _deep_merge(data, overrides)
    return data


def _coerce_str(value: str) -> Any:
    """Try to convert a string to bool / int / float; return str if ambiguous."""
    lower = value.strip().lower()

    # bool
    if lower in ("true", "yes", "1"):
        return True
    if lower in ("false", "no", "0"):
        return False

    # int
    try:
        return int(value)
    except ValueError:
        pass

    # float
    try:
        return float(value)
    except ValueError:
        pass

    return value


def _resolve_relative_paths(
    config: DocxPipelineConfig,
    base_dir: Optional[Path] = None,
) -> DocxPipelineConfig:
    """Resolve relative paths under ``config.paths`` against ``config.project.root``.

    When ``base_dir`` is given (the YAML file's parent directory), a relative
    ``project.root`` is resolved against it first.  Otherwise CWD is used.

    Only paths that are non-empty and not already absolute are resolved.
    """
    project_root = Path(config.project.root)
    if not project_root.is_absolute() and base_dir is not None:
        project_root = (base_dir / project_root).resolve()
    else:
        project_root = project_root.resolve()

    for attr in ("md_source", "docx_output", "json_source", "work_dir", "reference_docx"):
        raw = getattr(config.paths, attr, None)
        if raw and isinstance(raw, str):
            p = Path(raw)
            if not p.is_absolute():
                setattr(config.paths, attr, str((project_root / p).resolve()))

    # Also resolve pandoc.reference_docx if set
    if config.pandoc.reference_docx:
        p = Path(config.pandoc.reference_docx)
        if not p.is_absolute():
            config.pandoc.reference_docx = str((project_root / p).resolve())

    return config


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_config(
    path: Optional[str] = None,
    *,
    template: Optional[str] = None,
) -> DocxPipelineConfig:
    """Load pipeline configuration from a YAML file, optionally layered over a
    named template, with ``DOCX_PIPELINE_*`` environment-variable overrides.

    Parameters
    ----------
    path : str or None
        Path to a YAML configuration file.  If ``None``, the template alone
        (or an empty default) is used.
    template : str or None
        Name of a pre-built template to use as the base layer (see
        :mod:`docx_pipeline.config.defaults`).  The YAML file (if given) is
        deep-merged on top of the template.

    Returns
    -------
    DocxPipelineConfig
        Fully-resolved, validated-ready configuration object.
    """
    # --- 1. Start from template or empty dict ---
    if template:
        from .defaults import get_template
        data = get_template(template)
    else:
        data: Dict[str, Any] = {}

    # --- 2. Layer YAML on top ---
    config_dir: Optional[Path] = None
    if path:
        yaml_path = Path(path)
        config_dir = yaml_path.parent.resolve()
        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(yaml_path, "r", encoding="utf-8") as fh:
            yaml_data = yaml.safe_load(fh)
        if yaml_data is None:
            yaml_data = {}
        if not isinstance(yaml_data, dict):
            raise TypeError(
                f"YAML root must be a mapping, got {type(yaml_data).__name__}"
            )
        data = _deep_merge(data, yaml_data)

    # --- 3. Apply env-var overrides ---
    data = _apply_env_overrides(data)

    # --- 4. Build config tree ---
    config = DocxPipelineConfig.from_dict(data)

    # --- 5. Resolve relative paths ---
    config = _resolve_relative_paths(config, base_dir=config_dir)

    return config


def load_config_from_dict(
    data: Dict[str, Any],
    *,
    resolve_paths: bool = True,
    root: Optional[str] = None,
) -> DocxPipelineConfig:
    """Build a ``DocxPipelineConfig`` directly from a dict (no file I/O).

    Parameters
    ----------
    data : dict
        Raw configuration dict.
    resolve_paths : bool
        If ``True``, resolve relative paths against ``project.root``.
    root : str or None
        Override ``project.root`` for path resolution.

    Returns
    -------
    DocxPipelineConfig
    """
    if root is not None:
        data.setdefault("project", {})["root"] = root

    config = DocxPipelineConfig.from_dict(data)

    if resolve_paths:
        config = _resolve_relative_paths(config)

    return config
