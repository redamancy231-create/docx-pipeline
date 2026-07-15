#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Converters layer for the docx generation pipeline.

Exports:
    * **AbstractConverter** – ABC defining the converter contract.
    * **PandocConverter** – pandoc-based Markdown→DOCX converter (Phase 2).
    * **PurePythonConverter** – config-driven pure-Python Markdown→DOCX converter (Phase 1).
    * **MarkdownParser** – state-machine Markdown→Block list parser.
"""

from .base import AbstractConverter
from .markdown_parser import MarkdownParser
from .pandoc_converter import PandocConverter
from .pure_python import PurePythonConverter

__all__ = [
    "AbstractConverter",
    "MarkdownParser",
    "PandocConverter",
    "PurePythonConverter",
]
