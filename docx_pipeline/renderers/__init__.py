#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Renderers package for docx_pipeline.

Provides pre-processing utilities that transform Markdown content before
it reaches a converter (e.g. Mermaid diagram rendering).
"""

from __future__ import annotations

from .mermaid_renderer import (
    MermaidBlock,
    MermaidBlockError,
    MermaidRenderError,
    MermaidRenderer,
    MermaidRenderResult,
)

__all__ = [
    "MermaidBlock",
    "MermaidBlockError",
    "MermaidRenderError",
    "MermaidRenderer",
    "MermaidRenderResult",
]
