#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""State-machine Markdown parser that produces a flat list of semantic blocks.

Designed as the front-end for ``PurePythonConverter``.  It handles the
structural elements (headings, code fences, tables, blockquotes, horizontal
rules, lists) and inline formatting (bold, inline code) — images, links, and
HTML are left as plain text since they are handled downstream (or by pandoc
when used as an alternative converter).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Union

# ═══════════════════════════════════════════════════════════════════════
# Format tokens (inline)
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class Bold:
    """Bold-formatted text span (originates from ``**text**``)."""

    text: str


@dataclass
class InlineCode:
    """Inline code span (originates from `` `code` ``)."""

    text: str


@dataclass
class PlainText:
    """Plain (unformatted) text span."""

    text: str


# Union of all inline format tokens
Format = Union[Bold, InlineCode, PlainText]


# ═══════════════════════════════════════════════════════════════════════
# Block types (structural)
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class HeadingBlock:
    """A heading at *level* 1-6."""

    level: int
    text: str


@dataclass
class ParagraphBlock:
    """A normal paragraph with optional inline formatting.

    *formats* is a list of ``Format`` tokens.  If empty, the paragraph has
    no runs (equivalent to an empty ``<w:p/>``).
    """

    text: str = ""
    formats: List[Format] = field(default_factory=list)


@dataclass
class CodeBlock:
    """A fenced code block.

    *language* is the tag after the opening fence (``python``, ``bash``, …),
    or an empty string if none was given.
    """

    lines: List[str]
    language: str = ""


@dataclass
class TableBlock:
    """A Markdown table.  *rows* includes the header row; separator rows
    (``|---|---|``) are **not** included."""

    rows: List[List[str]]


@dataclass
class BlockquoteBlock:
    """A blockquote line (``> text``).  Inline formatting is preserved in the
    raw text string and parsed at render time."""

    text: str


@dataclass
class ListBlock:
    """A contiguous group of list items.

    *items* holds the raw text of each item (the bullet / number prefix is
    already stripped).  Inline formatting is parsed at render time.
    """

    items: List[str]
    ordered: bool = False
    indent: int = 0          # leading whitespace // 2


@dataclass
class HorizontalRuleBlock:
    """A thematic break (``---`` or ``***`` on its own line)."""

    pass


@dataclass
class EmptyBlock:
    """An explicit empty line (preserved for spacing decisions)."""

    pass


# Convenience union
Block = Union[
    HeadingBlock,
    ParagraphBlock,
    CodeBlock,
    TableBlock,
    BlockquoteBlock,
    ListBlock,
    HorizontalRuleBlock,
    EmptyBlock,
]


# ═══════════════════════════════════════════════════════════════════════
# Inline format parser
# ═══════════════════════════════════════════════════════════════════════

_INLINE_CODE_RE = re.compile(r"(`[^`]+`)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def parse_inline_formats(text: str) -> List[Format]:
    """Split *text* into a sequence of ``Format`` tokens.

    Recognises ``**bold**`` and `` `inline code` ``.  Nested formatting is
    **not** supported (bold inside code, code inside bold, etc.).
    """
    if not text:
        return []

    tokens: List[Format] = []

    # Split by inline code first, then by bold within each segment
    code_segments = _INLINE_CODE_RE.split(text)
    for seg in code_segments:
        if not seg:
            continue
        if seg.startswith("`") and seg.endswith("`") and len(seg) >= 2:
            tokens.append(InlineCode(text=seg[1:-1]))
            continue

        # Bold within this non-code segment
        bold_parts = _BOLD_RE.split(seg)
        for idx, part in enumerate(bold_parts):
            if not part:
                continue
            if idx % 2 == 1:          # odd index = text that was between ** **
                tokens.append(Bold(text=part))
            else:
                tokens.append(PlainText(text=part))

    return tokens


# ═══════════════════════════════════════════════════════════════════════
# Heading detection
# ═══════════════════════════════════════════════════════════════════════

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")


def _parse_heading(line: str) -> Optional[HeadingBlock]:
    m = _HEADING_RE.match(line)
    if m:
        return HeadingBlock(level=len(m.group(1)), text=m.group(2).strip())
    return None


# ═══════════════════════════════════════════════════════════════════════
# List detection
# ═══════════════════════════════════════════════════════════════════════

_LIST_RE = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")


def _parse_list_item(line: str) -> Optional[tuple]:
    """Return (indent, ordered, text) or None."""
    m = _LIST_RE.match(line)
    if m:
        indent = len(m.group(1)) // 2
        ordered = m.group(2) not in ("-", "*")
        text = m.group(3)
        return indent, ordered, text
    return None


# ═══════════════════════════════════════════════════════════════════════
# Horizontal-rule detection
# ═══════════════════════════════════════════════════════════════════════

_HR_RE = re.compile(r"^[-*]{3,}\s*$")


def _is_horizontal_rule(line: str) -> bool:
    return bool(_HR_RE.match(line))


# ═══════════════════════════════════════════════════════════════════════
# MarkdownParser
# ═══════════════════════════════════════════════════════════════════════


class MarkdownParser:
    """Line-by-line state-machine Markdown parser.

    Parameters
    ----------
    content : str
        The raw Markdown source text (including newlines).
    """

    def __init__(self, content: str) -> None:
        if not isinstance(content, str):
            raise TypeError(
                f"MarkdownParser expects str, got {type(content).__name__}"
            )
        self.content = content

    # ------------------------------------------------------------------
    # parse
    # ------------------------------------------------------------------

    def parse(self) -> List[Block]:
        """Parse the full Markdown document into a flat list of ``Block`` s.

        Returns
        -------
        list of Block
            Ordered blocks representing the document structure.

        Raises
        ------
        ValueError
            If the Markdown contains a malformed structure (e.g. unclosed
            code fence).
        """
        lines = self.content.splitlines()
        blocks: List[Block] = []
        i = 0
        n = len(lines)

        # --- state ---
        in_yaml_frontmatter = False
        yaml_fence_count = 0
        frontmatter_checked = False  # only check at very beginning (skip blank lines)

        in_code_block = False
        code_language = ""
        code_lines: List[str] = []

        in_table = False
        table_lines: List[str] = []

        # list-item accumulator (consecutive items of same indent+ordered form a block)
        pending_list_items: List[str] = []
        pending_list_ordered: Optional[bool] = None
        pending_list_indent: int = 0

        def flush_list():
            """Emit a ListBlock from accumulated items, if any."""
            nonlocal pending_list_items, pending_list_ordered, pending_list_indent
            if pending_list_items:
                blocks.append(
                    ListBlock(
                        items=pending_list_items[:],
                        ordered=bool(pending_list_ordered),
                        indent=pending_list_indent,
                    )
                )
                pending_list_items.clear()
                pending_list_ordered = None
                pending_list_indent = 0

        def flush_table():
            """Emit a TableBlock from accumulated table lines, if any."""
            nonlocal in_table, table_lines
            if not table_lines:
                in_table = False
                return
            rows = self._parse_table_rows(table_lines)
            if rows:
                blocks.append(TableBlock(rows=rows))
            table_lines.clear()
            in_table = False

        # --- main loop ---
        while i < n:
            line = lines[i]
            stripped = line.strip()

            # ── YAML frontmatter ──────────────────────────────────
            if not in_yaml_frontmatter and not frontmatter_checked:
                if not stripped:
                    i += 1
                    continue  # skip leading blank lines before frontmatter
                frontmatter_checked = True
                if stripped == "---":
                    in_yaml_frontmatter = True
                    yaml_fence_count = 1
                    i += 1
                    continue
            if in_yaml_frontmatter:
                if stripped == "---":
                    yaml_fence_count += 1
                    if yaml_fence_count >= 2:
                        in_yaml_frontmatter = False
                i += 1
                continue

            # ── code fence ────────────────────────────────────────
            if stripped.startswith("```"):
                if in_code_block:
                    # close code block
                    blocks.append(
                        CodeBlock(lines=code_lines[:], language=code_language)
                    )
                    code_lines.clear()
                    code_language = ""
                    in_code_block = False
                    flush_list()
                else:
                    # open code block
                    flush_list()
                    flush_table()
                    in_code_block = True
                    code_language = stripped[3:].strip()
                    code_lines = []
                i += 1
                continue

            if in_code_block:
                code_lines.append(line)
                i += 1
                continue

            # ── table row ─────────────────────────────────────────
            if stripped.startswith("|") and stripped.endswith("|"):
                if not in_table:
                    flush_list()
                    in_table = True
                table_lines.append(stripped)
                i += 1
                continue

            # ── end in-progress table ─────────────────────────────
            if in_table:
                flush_table()

            # ── empty line ────────────────────────────────────────
            if not stripped:
                flush_list()
                flush_table()
                # Only emit EmptyBlock if we want to preserve spacing;
                # the converter can handle this but for now we skip
                # standalone empties to avoid noise.
                i += 1
                continue

            # ── horizontal rule ───────────────────────────────────
            if _is_horizontal_rule(stripped):
                flush_list()
                flush_table()
                blocks.append(HorizontalRuleBlock())
                i += 1
                continue

            # ── headings ──────────────────────────────────────────
            heading = _parse_heading(stripped)
            if heading:
                flush_list()
                flush_table()
                blocks.append(heading)
                i += 1
                continue

            # ── list item ─────────────────────────────────────────
            li = _parse_list_item(stripped)
            if li is not None:
                flush_table()
                item_indent, item_ordered, item_text = li
                if (
                    pending_list_items
                    and pending_list_ordered is not None
                    and (
                        item_ordered != pending_list_ordered
                        or item_indent != pending_list_indent
                    )
                ):
                    flush_list()
                pending_list_items.append(item_text)
                pending_list_ordered = item_ordered
                pending_list_indent = item_indent
                i += 1
                continue

            # ── blockquote ────────────────────────────────────────
            if stripped.startswith("> "):
                flush_list()
                flush_table()
                blocks.append(BlockquoteBlock(text=stripped[2:]))
                i += 1
                continue

            # ── normal paragraph ──────────────────────────────────
            flush_list()
            flush_table()
            fmts = parse_inline_formats(stripped)
            blocks.append(ParagraphBlock(text=stripped, formats=fmts))
            i += 1

        # --- end of input: flush any pending accumulators ---
        if in_yaml_frontmatter:
            # tolerate unclosed frontmatter — just warn but continue
            pass
        if in_code_block:
            raise ValueError(
                "Unclosed code fence at end of document "
                f"(language='{code_language}', {len(code_lines)} lines buffered)"
            )
        flush_list()
        flush_table()

        return blocks

    # ------------------------------------------------------------------
    # Table row parser
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_table_rows(raw_lines: List[str]) -> List[List[str]]:
        """Convert raw ``| cell | cell |`` lines into a list of rows,
        discarding separator rows (``|---|---|``)."""
        rows: List[List[str]] = []
        for line in raw_lines:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            # Skip separator rows: every cell consists only of :, -, space
            if all(
                set(cell) <= set(" :-") or cell == ""
                for cell in cells
            ):
                continue
            rows.append(cells)
        return rows
