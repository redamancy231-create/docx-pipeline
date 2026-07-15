#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration dataclass definitions for docx_pipeline.

All configuration types are defined as @dataclass with field(default=...) so
they can be constructed from dicts (via DocxPipelineConfig.from_dict) or
programmatically.  Every field has a sensible default; no field is required.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Leaf / small configs
# ---------------------------------------------------------------------------

@dataclass
class ProjectConfig:
    """Project identity and root directory."""

    name: str = field(default="docx_pipeline_project")
    root: str = field(default=".")


@dataclass
class PathsConfig:
    """Input/output paths used by the pipeline.

    All paths are resolved relative to *project.root* at load time (see
    loader.py).  Absolute paths are left untouched.
    """

    md_source: str = field(default="output/markdown")
    docx_output: str = field(default="output/docx")
    json_source: str = field(default="output/json")
    work_dir: str = field(default="work")
    reference_docx: str = field(default="")


@dataclass
class FontSizesConfig:
    """Font sizes in points for different text elements."""

    body: float = field(default=10.5)
    table: float = field(default=9.0)
    code: float = field(default=8.5)
    headings: Dict[str, float] = field(default_factory=dict)

    # Convenience: default heading sizes if headings dict is empty
    # h1=22, h2=16, h3=14, h4=12, h5=10.5, h6=9


@dataclass
class FontColorsConfig:
    """Colour specification for font elements.

    Values should be hex strings (e.g. ``"#333333"``) or ``"auto"``.
    """

    body: str = field(default="auto")
    heading: str = field(default="auto")
    link: str = field(default="#0563C1")
    code: str = field(default="auto")
    code_block_bg: str = field(default="#F5F5F5")
    blockquote: str = field(default="#555555")
    horizontal_rule: str = field(default="#CCCCCC")


@dataclass
class FontsConfig:
    """Font families for different script ranges.

    *east_asian* ('ea') and *latin* are the two slots recognised by python-docx
    run-level font manipulation.  *symbol* maps to the ``<w:sym>`` family.
    """

    east_asian: str = field(default="微软雅黑")
    latin: str = field(default="微软雅黑")
    symbol: str = field(default="")


@dataclass
class PageMarginsConfig:
    """Page margins in **cm** (python-docx uses ``Cm()`` internally)."""

    top: float = field(default=2.54)
    bottom: float = field(default=2.54)
    left: float = field(default=3.18)
    right: float = field(default=3.18)


@dataclass
class PageConfig:
    """Page-level settings."""

    size: str = field(default="A4")                     # 'A4' | 'Letter' | ...
    orientation: str = field(default="portrait")        # 'portrait' | 'landscape'
    margins: PageMarginsConfig = field(default_factory=PageMarginsConfig)


# ---------------------------------------------------------------------------
# External-tool configs
# ---------------------------------------------------------------------------

@dataclass
class PandocConfig:
    """Pandoc invocation settings."""

    enabled: bool = field(default=True)
    extra_args: List[str] = field(default_factory=list)
    # Path to a reference docx for style import (passed as --reference-doc)
    reference_docx: str = field(default="")


@dataclass
class MermaidImageConfig:
    """Raster-image output settings for mermaid diagrams."""

    format: str = field(default="png")   # png | svg (png recommended for docx)
    dpi: int = field(default=300)
    scale: float = field(default=1.0)


@dataclass
class MermaidRenderConfig:
    """Settings for the mermaid-cli (mmdc) render process."""

    mmdc_path: str = field(default="mmdc")
    puppeteer_config: str = field(default="")
    timeout: int = field(default=60)          # seconds


@dataclass
class MermaidConfig:
    """Aggregate Mermaid diagram settings."""

    enabled: bool = field(default=False)
    image: MermaidImageConfig = field(default_factory=MermaidImageConfig)
    render: MermaidRenderConfig = field(default_factory=MermaidRenderConfig)


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

@dataclass
class VersionConfig:
    """Document version metadata injected into the generated docx."""

    number: str = field(default="1.0.0")
    label: str = field(default="")
    date: str = field(default="")


# ---------------------------------------------------------------------------
# Style sub-configs
# ---------------------------------------------------------------------------

@dataclass
class TocStylesConfig:
    """Table-of-contents style knobs."""

    enabled: bool = field(default=True)
    depth: int = field(default=3)              # heading levels to include
    title: str = field(default="目录")


@dataclass
class TableStylesConfig:
    """Default table styling."""

    style: str = field(default="Table Grid")   # built-in Word style name
    autofit: bool = field(default=True)
    header_bold: bool = field(default=True)
    header_shading: str = field(default="#D9E2F3")  # light blue


@dataclass
class ParagraphStylesConfig:
    """Paragraph-level defaults."""

    line_spacing: float = field(default=1.15)  # multiple
    space_after: float = field(default=6.0)    # pt
    first_line_indent: float = field(default=0.0)  # cm


@dataclass
class HeadingStylesConfig:
    """Per-heading-level overrides.

    Keys are ``"h1"`` … ``"h6"``; each value is a dict with optional keys
    ``font_east_asian``, ``font_latin``, ``size`` (pt), ``color`` (hex),
    ``bold``, ``italic``.
    """

    levels: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    space_before: Dict[str, float] = field(default_factory=lambda: {
        "h1": 14, "h2": 14, "h3": 8, "h4": 8, "h5": 8, "h6": 8,
    })
    space_after: float = 6.0  # pt, uniform for all heading levels


@dataclass
class StylesConfig:
    """Aggregate document-styling configuration."""

    toc: TocStylesConfig = field(default_factory=TocStylesConfig)
    table: TableStylesConfig = field(default_factory=TableStylesConfig)
    paragraph: ParagraphStylesConfig = field(default_factory=ParagraphStylesConfig)
    heading: HeadingStylesConfig = field(default_factory=HeadingStylesConfig)


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

@dataclass
class BackupConfig:
    """Backup behaviour for existing output files."""

    enabled: bool = field(default=True)
    max_backups: int = field(default=5)
    suffix: str = field(default=".bak")


# ---------------------------------------------------------------------------
# Root config
# ---------------------------------------------------------------------------

# Map from top-level config key -> dataclass constructor for recursive building
_SUB_CONFIG_MAP: Dict[str, type] = {
    "project": ProjectConfig,
    "paths": PathsConfig,
    "fonts": FontsConfig,
    "font_sizes": FontSizesConfig,
    "font_colors": FontColorsConfig,
    "page": PageConfig,
    "pandoc": PandocConfig,
    "mermaid": MermaidConfig,
    "version": VersionConfig,
    "styles": StylesConfig,
    "backup": BackupConfig,
}

# Nested sub-configs (keys that are themselves dataclasses inside a parent)
_NESTED_CONFIG_MAP: Dict[str, Dict[str, type]] = {
    "page": {"margins": PageMarginsConfig},
    "mermaid": {
        "image": MermaidImageConfig,
        "render": MermaidRenderConfig,
    },
    "styles": {
        "toc": TocStylesConfig,
        "table": TableStylesConfig,
        "paragraph": ParagraphStylesConfig,
        "heading": HeadingStylesConfig,
    },
}


@dataclass
class DocxPipelineConfig:
    """Root configuration object for the docx generation pipeline.

    Usage::

        # From a dict (e.g. YAML-loaded)
        cfg = DocxPipelineConfig.from_dict(data)

        # Programmatic
        cfg = DocxPipelineConfig(
            project=ProjectConfig(name="my_project", root="."),
            paths=PathsConfig(md_source="chapters"),
        )
    """

    project: ProjectConfig = field(default_factory=ProjectConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    fonts: FontsConfig = field(default_factory=FontsConfig)
    font_sizes: FontSizesConfig = field(default_factory=FontSizesConfig)
    font_colors: FontColorsConfig = field(default_factory=FontColorsConfig)
    page: PageConfig = field(default_factory=PageConfig)
    pandoc: PandocConfig = field(default_factory=PandocConfig)
    mermaid: MermaidConfig = field(default_factory=MermaidConfig)
    version: VersionConfig = field(default_factory=VersionConfig)
    styles: StylesConfig = field(default_factory=StylesConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)

    # ------------------------------------------------------------------
    # from_dict classmethod
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocxPipelineConfig":
        """Recursively build a ``DocxPipelineConfig`` from a plain dict.

        Parameters
        ----------
        data : dict
            Top-level dict whose keys correspond to the dataclass field names
            of ``DocxPipelineConfig``.  Each value may itself be a dict that
            is recursively converted to the matching sub-dataclass.

        Returns
        -------
        DocxPipelineConfig
        """
        if not isinstance(data, dict):
            raise TypeError(f"from_dict expects a dict, got {type(data).__name__}")

        kwargs: Dict[str, Any] = {}

        for key, sub_cls in _SUB_CONFIG_MAP.items():
            value = data.get(key)
            if value is None:
                kwargs[key] = sub_cls()
            elif isinstance(value, dict):
                kwargs[key] = cls._build_sub_config(key, sub_cls, value)
            elif isinstance(value, sub_cls):
                kwargs[key] = value
            else:
                raise TypeError(
                    f"Expected dict or {sub_cls.__name__} for key '{key}', "
                    f"got {type(value).__name__}"
                )

        return cls(**kwargs)

    @staticmethod
    def _build_sub_config(
        key: str, cls_: type, raw: Dict[str, Any]
    ) -> Any:
        """Recursively instantiate a sub-dataclass from a dict, resolving
        nested sub-configs registered in ``_NESTED_CONFIG_MAP``."""
        kwargs: Dict[str, Any] = {}
        nested_map = _NESTED_CONFIG_MAP.get(key, {})

        for f in fields(cls_):
            fname = f.name
            fvalue = raw.get(fname)

            if fname in nested_map and isinstance(fvalue, dict):
                kwargs[fname] = nested_map[fname](**fvalue)
            elif fvalue is not None:
                kwargs[fname] = fvalue
            # else: use the field's default (omit from kwargs)

        return cls_(**kwargs)

    # ------------------------------------------------------------------
    # Convenience: export back to dict
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the full config tree back to a plain dict (for debugging
        or writing out a resolved YAML)."""
        result: Dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            result[f.name] = DocxPipelineConfig._value_to_dict(value)
        return result

    @staticmethod
    def _value_to_dict(value: Any) -> Any:
        if hasattr(value, "__dataclass_fields__"):
            return {
                f.name: DocxPipelineConfig._value_to_dict(getattr(value, f.name))
                for f in fields(value)
            }
        if isinstance(value, list):
            return [DocxPipelineConfig._value_to_dict(v) for v in value]
        return value
