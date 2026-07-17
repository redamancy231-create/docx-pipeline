#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-built configuration templates for common document scenarios.

Each template is a plain ``dict`` that can be fed to
:meth:`DocxPipelineConfig.from_dict` or merged with a user-provided YAML.
"""

from __future__ import annotations

from typing import Any, Dict

# ============================================================================
# Template: DEFAULT
#   General-purpose, suitable for most informal documents.
#   - 微软雅黑 body at 10.5 pt
#   - Standard A4 margins
# ============================================================================

DEFAULT: Dict[str, Any] = {
    "project": {
        "name": "default_project",
        "root": ".",
    },
    "paths": {
        "md_source": "output/markdown",
        "docx_output": "output/document.docx",
        "json_source": "output/json",
        "work_dir": "work",
        "reference_docx": "",
    },
    "fonts": {
        "east_asian": "微软雅黑",
        "latin": "微软雅黑",
        "symbol": "",
    },
    "font_sizes": {
        "body": 10.5,
        "table": 9.0,
        "code": 8.5,
        "headings": {
            "h1": 22.0,
            "h2": 16.0,
            "h3": 14.0,
            "h4": 12.0,
            "h5": 10.5,
            "h6": 9.0,
        },
    },
    "font_colors": {
        "body": "auto",
        "heading": "auto",
        "link": "#0563C1",
        "code": "auto",
    },
    "page": {
        "size": "A4",
        "orientation": "portrait",
        "margins": {
            "top": 2.54,
            "bottom": 2.54,
            "left": 3.18,
            "right": 3.18,
        },
    },
    "pandoc": {
        "enabled": False,
        "extra_args": [],
        "reference_docx": "",
    },
    "mermaid": {
        "enabled": False,
        "image": {"format": "png", "dpi": 300, "scale": 1.0},
        "render": {"mmdc_path": "mmdc", "puppeteer_config": "", "timeout": 60},
    },
    "version": {
        "number": "1.0.0",
        "label": "",
        "date": "",
    },
    "styles": {
        "toc": {"enabled": True, "depth": 3, "title": "目录"},
        "table": {
            "style": "Table Grid",
            "autofit": True,
            "header_bold": True,
            "header_shading": "#D9E2F3",
        },
        "paragraph": {
            "line_spacing": 1.15,
            "space_after": 6.0,
            "first_line_indent": 0.0,
        },
        "heading": {"levels": {}},
    },
    "backup": {
        "enabled": True,
        "max_backups": 5,
        "suffix": ".bak",
    },
}

# ============================================================================
# Template: ACADEMIC
#   Designed for theses, papers, and formal academic documents.
#   - 宋体 (SimSun) body + 黑体 (SimHei) headings at 12 pt
#   - 1.25× line spacing
#   - First‑line indent for paragraphs
#   - Pandoc disabled, Mermaid disabled
# ============================================================================

ACADEMIC: Dict[str, Any] = {
    "project": {
        "name": "academic_project",
        "root": ".",
    },
    "paths": {
        "md_source": "output/markdown",
        "docx_output": "output/document.docx",
        "json_source": "output/json",
        "work_dir": "work",
        "reference_docx": "",
    },
    "fonts": {
        "east_asian": "宋体",
        "latin": "Times New Roman",
        "symbol": "",
    },
    "font_sizes": {
        "body": 12.0,
        "table": 10.0,
        "code": 9.0,
        "headings": {
            "h1": 22.0,   # 黑体
            "h2": 16.0,
            "h3": 14.0,
            "h4": 12.0,
            "h5": 12.0,
            "h6": 12.0,
        },
    },
    "font_colors": {
        "body": "auto",
        "heading": "auto",
        "link": "#0563C1",
        "code": "auto",
    },
    "page": {
        "size": "A4",
        "orientation": "portrait",
        "margins": {
            "top": 2.54,
            "bottom": 2.54,
            "left": 3.18,
            "right": 3.18,
        },
    },
    "pandoc": {
        "enabled": False,
        "extra_args": [],
        "reference_docx": "",
    },
    "mermaid": {
        "enabled": False,
        "image": {"format": "png", "dpi": 300, "scale": 1.0},
        "render": {"mmdc_path": "mmdc", "puppeteer_config": "", "timeout": 60},
    },
    "version": {
        "number": "1.0.0",
        "label": "",
        "date": "",
    },
    "styles": {
        "toc": {"enabled": True, "depth": 3, "title": "目录"},
        "table": {
            "style": "Table Grid",
            "autofit": True,
            "header_bold": True,
            "header_shading": "#D9E2F3",
        },
        "paragraph": {
            "line_spacing": 1.25,
            "space_after": 0.0,
            "first_line_indent": 0.74,  # ~2 chars at 12pt
        },
        "heading": {
            "levels": {
                "h1": {"font_east_asian": "黑体", "bold": True},
                "h2": {"font_east_asian": "黑体", "bold": True},
                "h3": {"font_east_asian": "黑体", "bold": True},
            }
        },
    },
    "backup": {
        "enabled": True,
        "max_backups": 5,
        "suffix": ".bak",
    },
}

# ============================================================================
# Template: REPORT
#   Corporate / project report style.
#   - 微软雅黑 body, pandoc + mermaid both enabled
#   - Slightly tighter margins than default
# ============================================================================

REPORT: Dict[str, Any] = {
    "project": {
        "name": "report_project",
        "root": ".",
    },
    "paths": {
        "md_source": "output/markdown",
        "docx_output": "output/document.docx",
        "json_source": "output/json",
        "work_dir": "work",
        "reference_docx": "",
    },
    "fonts": {
        "east_asian": "微软雅黑",
        "latin": "微软雅黑",
        "symbol": "",
    },
    "font_sizes": {
        "body": 10.5,
        "table": 9.0,
        "code": 8.5,
        "headings": {
            "h1": 22.0,
            "h2": 16.0,
            "h3": 14.0,
            "h4": 12.0,
            "h5": 10.5,
            "h6": 9.0,
        },
    },
    "font_colors": {
        "body": "auto",
        "heading": "auto",
        "link": "#0563C1",
        "code": "auto",
    },
    "page": {
        "size": "A4",
        "orientation": "portrait",
        "margins": {
            "top": 1.8,
            "bottom": 1.8,
            "left": 1.8,
            "right": 1.8,
        },
    },
    "pandoc": {
        "enabled": True,
        "extra_args": [],
        "reference_docx": "",
    },
    "mermaid": {
        "enabled": True,
        "image": {"format": "png", "dpi": 300, "scale": 1.0},
        "render": {"mmdc_path": "mmdc", "puppeteer_config": "", "timeout": 60},
    },
    "version": {
        "number": "1.0.0",
        "label": "",
        "date": "",
    },
    "styles": {
        "toc": {"enabled": True, "depth": 3, "title": "目录"},
        "table": {
            "style": "Table Grid",
            "autofit": True,
            "header_bold": True,
            "header_shading": "#D9E2F3",
        },
        "paragraph": {
            "line_spacing": 1.15,
            "space_after": 6.0,
            "first_line_indent": 0.0,
        },
        "heading": {"levels": {}},
    },
    "backup": {
        "enabled": True,
        "max_backups": 5,
        "suffix": ".bak",
    },
}

# ============================================================================
# Template: STRATEGY
#   Clean, modern strategy-document look.
#   - 等线 (DengXian) body at 10.5 pt
#   - 1.15× line spacing, no first‑line indent
#   - Pandoc disabled, Mermaid disabled
# ============================================================================

STRATEGY: Dict[str, Any] = {
    "project": {
        "name": "strategy_project",
        "root": ".",
    },
    "paths": {
        "md_source": "output/markdown",
        "docx_output": "output/document.docx",
        "json_source": "output/json",
        "work_dir": "work",
        "reference_docx": "",
    },
    "fonts": {
        "east_asian": "等线",
        "latin": "等线",
        "symbol": "",
    },
    "font_sizes": {
        "body": 10.5,
        "table": 9.0,
        "code": 8.5,
        "headings": {
            "h1": 22.0,
            "h2": 16.0,
            "h3": 14.0,
            "h4": 12.0,
            "h5": 10.5,
            "h6": 9.0,
        },
    },
    "font_colors": {
        "body": "auto",
        "heading": "auto",
        "link": "#0563C1",
        "code": "auto",
    },
    "page": {
        "size": "A4",
        "orientation": "portrait",
        "margins": {
            "top": 2.54,
            "bottom": 2.54,
            "left": 3.18,
            "right": 3.18,
        },
    },
    "pandoc": {
        "enabled": False,
        "extra_args": [],
        "reference_docx": "",
    },
    "mermaid": {
        "enabled": False,
        "image": {"format": "png", "dpi": 300, "scale": 1.0},
        "render": {"mmdc_path": "mmdc", "puppeteer_config": "", "timeout": 60},
    },
    "version": {
        "number": "1.0.0",
        "label": "",
        "date": "",
    },
    "styles": {
        "toc": {"enabled": True, "depth": 3, "title": "目录"},
        "table": {
            "style": "Table Grid",
            "autofit": True,
            "header_bold": True,
            "header_shading": "#D9E2F3",
        },
        "paragraph": {
            "line_spacing": 1.15,
            "space_after": 6.0,
            "first_line_indent": 0.0,
        },
        "heading": {"levels": {}},
    },
    "backup": {
        "enabled": True,
        "max_backups": 5,
        "suffix": ".bak",
    },
}

# ============================================================================
# Template registry
# ============================================================================

TEMPLATES: Dict[str, Dict[str, Any]] = {
    "default": DEFAULT,
    "academic": ACADEMIC,
    "report": REPORT,
    "strategy": STRATEGY,
}


def get_template(name: str) -> Dict[str, Any]:
    """Return a **deep copy** of the named template dict.

    Parameters
    ----------
    name : str
        One of ``"default"``, ``"academic"``, ``"report"``, ``"strategy"``
        (case-insensitive).

    Returns
    -------
    dict
        Deep-copied template suitable for merging / passing to ``from_dict``.

    Raises
    ------
    KeyError
        If *name* is not a registered template.
    """
    import copy

    key = name.lower()
    if key not in TEMPLATES:
        raise KeyError(
            f"Unknown template '{name}'. Available: {sorted(TEMPLATES.keys())}"
        )
    return copy.deepcopy(TEMPLATES[key])
