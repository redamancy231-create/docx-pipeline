#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared constants and helpers used by both PurePythonConverter and PandocConverter.

Extracted from duplicated code (~125 lines) across the two converters
(docx_pipeline Deferred item: "共享代码提取").
"""

from typing import Dict, Tuple

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# ---------------------------------------------------------------------------
# Page size lookup (cm)
# ---------------------------------------------------------------------------

_PAGE_SIZES_CM: Dict[str, Tuple[float, float]] = {
    "A4": (21.0, 29.7),
    "Letter": (21.59, 27.94),
    "Legal": (21.59, 35.56),
}

# Default heading font sizes when config.font_sizes.headings is empty
_DEFAULT_HEADING_SIZES: Dict[int, float] = {
    1: 22.0, 2: 16.0, 3: 14.0, 4: 12.0, 5: 10.5, 6: 9.0,
}

# Default heading colour (dark blue, same as reference implementation)
_DEFAULT_HEADING_RGB = (0x1A, 0x23, 0x7E)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Convert ``"#RRGGBB"`` or ``"RRGGBB"`` to ``(R, G, B)``."""
    h = hex_str.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Invalid hex colour: {hex_str!r}")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def set_cell_shading(cell, color_hex: str) -> None:
    """Set cell background colour via ``w:shd``."""
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), color_hex)
    shading.set(qn("w:val"), "clear")
    cell._tc.get_or_add_tcPr().append(shading)
