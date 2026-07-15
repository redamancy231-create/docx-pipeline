#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration layer for the docx generation pipeline.

Provides:

* **schema** – ``@dataclass`` definitions for every config node.
* **defaults** – pre-built templates (DEFAULT, ACADEMIC, REPORT, STRATEGY).
* **loader** – YAML loading + env-var override ``DOCX_PIPELINE_*``.
* **validator** – configuration sanity checks + runtime dependency probing.

Quick start::

    from docx_pipeline.config import load_config, validate_config

    cfg = load_config("pipeline.yaml", template="academic")
    issues = validate_config(cfg)
    if issues:
        for i in issues:
            print(f"  - {i}")
    else:
        print("Config is valid.")
"""

# ---- schema ---------------------------------------------------------------
from .schema import (
    # Top-level
    DocxPipelineConfig,
    # Sub-configs (in dependency order)
    ProjectConfig,
    PathsConfig,
    FontSizesConfig,
    FontColorsConfig,
    FontsConfig,
    PageMarginsConfig,
    PageConfig,
    PandocConfig,
    MermaidImageConfig,
    MermaidRenderConfig,
    MermaidConfig,
    VersionConfig,
    TocStylesConfig,
    TableStylesConfig,
    ParagraphStylesConfig,
    HeadingStylesConfig,
    StylesConfig,
    BackupConfig,
)

# ---- defaults -------------------------------------------------------------
from .defaults import (
    DEFAULT,
    ACADEMIC,
    REPORT,
    STRATEGY,
    TEMPLATES,
    get_template,
)

# ---- loader ---------------------------------------------------------------
from .loader import (
    load_config,
    load_config_from_dict,
)

# ---- validator ------------------------------------------------------------
from .validator import (
    validate_config,
    check_dependencies,
)

# ---------------------------------------------------------------------------
__all__ = [
    # schema
    "DocxPipelineConfig",
    "ProjectConfig",
    "PathsConfig",
    "FontSizesConfig",
    "FontColorsConfig",
    "FontsConfig",
    "PageMarginsConfig",
    "PageConfig",
    "PandocConfig",
    "MermaidImageConfig",
    "MermaidRenderConfig",
    "MermaidConfig",
    "VersionConfig",
    "TocStylesConfig",
    "TableStylesConfig",
    "ParagraphStylesConfig",
    "HeadingStylesConfig",
    "StylesConfig",
    "BackupConfig",
    # defaults
    "DEFAULT",
    "ACADEMIC",
    "REPORT",
    "STRATEGY",
    "TEMPLATES",
    "get_template",
    # loader
    "load_config",
    "load_config_from_dict",
    # validator
    "validate_config",
    "check_dependencies",
]
