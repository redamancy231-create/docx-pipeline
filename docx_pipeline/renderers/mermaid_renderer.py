#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mermaid diagram pre-renderer for Markdown documents.

Converts ```mermaid fenced code blocks into ``![caption](path.png)`` image
references so that downstream converters (pandoc, PurePythonConverter) can
embed rendered diagrams.

The renderer is a **standalone pre-processor** — it touches neither DOCX nor
pandoc.  It reads ``config.mermaid`` for rendering knobs and
``config.paths.work_dir`` for temporary storage.

Design reference: ``embed_mermaid_png.py`` from the AI 协作框架 project, whose
triple-check verification pattern (returncode + file existence + size > 1000)
is preserved.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from docx_pipeline.config.schema import DocxPipelineConfig

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class MermaidBlock:
    """A single Mermaid diagram discovered in source text.

    Attributes
    ----------
    index : int
        Zero-based occurrence order.
    code : str
        Raw Mermaid source inside the fence (without the ``` markers).
    start : int
        Character index of the opening `` ```mermaid ``.
    end : int
        Character index immediately after the closing `` ``` ``.
    heading : str
        Nearest preceding heading text (h2–h4), truncated to 60 chars, or
        ``"?"`` if no heading was found.
    """

    index: int
    code: str
    start: int
    end: int
    heading: str = "?"


@dataclass
class MermaidRenderResult:
    """Outcome of rendering a single Mermaid block.

    Attributes
    ----------
    block_index : int
        Corresponds to ``MermaidBlock.index``.
    success : bool
        ``True`` when the PNG was generated and validated.
    png_path : str or None
        Absolute path to the rendered PNG (only when *success*).
    image_ref : str or None
        Markdown image reference string, e.g.
        ``![Mermaid: 3.2 方法论](mermaid/diagram_002.png)``.
    error : str or None
        Error description when *success* is ``False``.
    """

    block_index: int
    success: bool
    png_path: Optional[str] = None
    image_ref: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class MermaidRenderError(Exception):
    """Fatal: the overall rendering process cannot proceed (mmdc not found,
    work_dir not writable, etc.)."""


class MermaidBlockError(Exception):
    """Non-fatal: a single diagram failed to render.  Carried inside a
    ``MermaidRenderResult(success=False)`` so other blocks can continue."""


# ---------------------------------------------------------------------------
# MermaidRenderer
# ---------------------------------------------------------------------------


class MermaidRenderer:
    """Pre-render `` ```mermaid `` blocks in Markdown text to PNG images.

    Parameters
    ----------
    config : DocxPipelineConfig
        Reads ``config.mermaid`` (render + image settings) and
        ``config.paths.work_dir``.
    """

    # Regex to find mermaid fenced code blocks.
    # Anchored to line start (with 0–3 spaces indentation per CommonMark),
    # closing fence must also be at line start.  Non-greedy, DOTALL.
    # Note: still not a full fence-aware parser — will match mermaid fences
    # that appear inside other code blocks as literal text (rare edge case).
    _MERMAID_RE = re.compile(
        r"(?m)^ {0,3}```mermaid\s*\n(.*?)\n {0,3}```", re.DOTALL
    )

    # Regex to find the nearest h2–h4 heading preceding a block
    _HEADING_RE = re.compile(r"^(#{2,4})\s+(.+)$", re.MULTILINE)

    def __init__(self, config: DocxPipelineConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, markdown_text: str, *, work_dir: Optional[Path] = None) -> str:
        """Find, render, and replace all Mermaid blocks in *markdown_text*.

        Parameters
        ----------
        markdown_text : str
            Raw Markdown source.
        work_dir : Path, optional
            Working directory for intermediate ``.mmd`` files and rendered
            PNGs.  Images are written to ``<work_dir>/mermaid/`` and
            references are returned relative to *work_dir*.  If *None*,
            a UUID-named directory is created under ``config.paths.work_dir``
            or the system temp directory.

        Returns
        -------
        str
            Markdown with successfully-rendered blocks replaced by
            ``![caption](path.png)`` references.  Failed blocks are left
            as-is (original ```mermaid fences).
        """
        # Fast no-op gate
        if not self.config.mermaid.enabled:
            return markdown_text

        # 1. Find blocks first (avoid unnecessary mmdc check)
        blocks = self._find_mermaid_blocks(markdown_text)
        if not blocks:
            return markdown_text

        # 2. Check mmdc availability (only when there are blocks to render)
        self._check_mmdc()

        logger.info("MermaidRenderer: found %d mermaid block(s)", len(blocks))

        # 3. Prepare work directory (owned by caller, or created here)
        base_work_dir = self._resolve_work_dir(work_dir)
        mermaid_dir = base_work_dir / "mermaid"
        mermaid_dir.mkdir(parents=True, exist_ok=True)

        # 4. Render each block
        results: Dict[int, MermaidRenderResult] = {}
        success_count = 0
        for block in blocks:
            logger.info(
                "Rendering diagram %03d/%d (caption: %s)",
                block.index + 1,
                len(blocks),
                block.heading,
            )
            result = self._render_block(block, mermaid_dir)
            results[block.index] = result
            if result.success:
                success_count += 1
                logger.info(
                    "Diagram %03d/%d OK", block.index + 1, len(blocks)
                )
            else:
                logger.warning(
                    "Diagram %03d/%d FAILED: %s",
                    block.index + 1,
                    len(blocks),
                    result.error,
                )

        if success_count < len(blocks):
            logger.warning(
                "%d/%d diagram(s) failed to render; "
                "output will contain raw mermaid blocks",
                len(blocks) - success_count,
                len(blocks),
            )

        # 5. Replace blocks (reverse-order to preserve offsets)
        return self._replace_blocks(markdown_text, blocks, results)

    # ------------------------------------------------------------------
    # Internal: mmdc check
    # ------------------------------------------------------------------

    def _check_mmdc(self) -> None:
        """Verify that mmdc is callable.

        Raises
        ------
        MermaidRenderError
            If mmdc is not found on PATH or at the configured path.
        """
        mmdc = self.config.mermaid.render.mmdc_path or "mmdc"
        if os.path.isabs(mmdc):
            if os.path.isfile(mmdc):
                return
            found = shutil.which(mmdc)
        else:
            found = shutil.which(mmdc)

        if found is None:
            raise MermaidRenderError(
                f"mmdc (mermaid-cli) not found. "
                f"Expected at: {mmdc!r}. "
                "Install with: npm install -g @mermaid-js/mermaid-cli"
            )

    # ------------------------------------------------------------------
    # Internal: block discovery
    # ------------------------------------------------------------------

    def _find_mermaid_blocks(self, text: str) -> List[MermaidBlock]:
        """Extract all ```mermaid fenced blocks from *text*.

        Empty blocks are skipped.  Blocks are indexed in order of appearance.
        """
        blocks: List[MermaidBlock] = []
        for idx, match in enumerate(self._MERMAID_RE.finditer(text)):
            code = match.group(1).strip()
            if not code:
                continue  # skip empty blocks
            heading = self._find_nearest_heading(text, match.start())
            blocks.append(
                MermaidBlock(
                    index=idx,
                    code=code,
                    start=match.start(),
                    end=match.end(),
                    heading=heading,
                )
            )
        return blocks

    def _find_nearest_heading(self, text: str, block_start: int) -> str:
        """Scan backwards from *block_start* for the nearest h2–h4 heading.

        Returns the heading text truncated to 60 chars, or ``"?"``.
        """
        best: Optional[str] = None
        best_end = -1
        for m in self._HEADING_RE.finditer(text):
            if m.end() > block_start:
                break
            if m.end() > best_end:
                best_end = m.end()
                best = m.group(2).strip()
        if best is None:
            return "?"
        return best[:60]

    # ------------------------------------------------------------------
    # Internal: rendering
    # ------------------------------------------------------------------

    def _resolve_work_dir(self, caller_work_dir: Optional[Path] = None) -> Path:
        """Return the work directory for mermaid outputs.

        If *caller_work_dir* is provided (the converter's own unique run
        directory), use it directly so that relative image references are
        resolvable by the caller.  Otherwise create a UUID-named directory.
        """
        if caller_work_dir is not None:
            p = caller_work_dir.resolve()
            p.mkdir(parents=True, exist_ok=True)
            return p
        import uuid
        wd = self.config.paths.work_dir
        if wd and wd.strip():
            p = (Path(wd) / f"mermaid_{uuid.uuid4().hex[:8]}").resolve()
        else:
            p = (Path(tempfile.gettempdir()) / f"docx_pipeline_mermaid_{uuid.uuid4().hex[:8]}").resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _compute_render_width(self) -> int:
        """Compute mmdc render width (px) from page geometry and DPI.

        Formula: ``usable_inches = (page_width - left_margin - right_margin)
        / 2.54``, then ``width_px = int(usable_inches * dpi)``, clamped to
        [800, 2880].
        """
        m = self.config.page.margins
        page_w = {
            "A4": 21.0,
            "Letter": 21.59,
            "Legal": 21.59,
        }.get(self.config.page.size, 21.0)

        usable_inches = (page_w - m.left - m.right) / 2.54
        width_px = int(usable_inches * self.config.mermaid.image.dpi)
        return max(800, min(width_px, 2880))

    def _build_mmdc_args(self, mmd_path: Path, png_path: Path) -> list:
        """Build mmdc argument list (safe — no shell injection).

        Returns a list of strings suitable for ``subprocess.run(..., shell=False)``.
        """
        mmdc = self.config.mermaid.render.mmdc_path or "mmdc"
        width = self._compute_render_width()
        args = [mmdc, "-i", str(mmd_path), "-o", str(png_path),
                "-w", str(width), "-b", "white"]

        scale = self.config.mermaid.image.scale
        if scale != 1.0:
            args += ["-s", str(scale)]

        puppeteer = self.config.mermaid.render.puppeteer_config
        if puppeteer:
            args += ["-p", str(puppeteer)]

        return args

    def _render_block(
        self, block: MermaidBlock, work_dir: Path
    ) -> MermaidRenderResult:
        """Render a single Mermaid block to PNG.

        1. Write ``.mmd`` file
        2. Invoke mmdc via subprocess
        3. Triple-check the output (returncode + existence + size > 1000)
        """
        mmd_path = work_dir / f"diagram_{block.index:03d}.mmd"
        png_path = work_dir / f"diagram_{block.index:03d}.png"

        # Write .mmd
        try:
            mmd_path.write_text(block.code, encoding="utf-8")
        except OSError as exc:
            return MermaidRenderResult(
                block.index, success=False, error=f"write .mmd failed: {exc}"
            )

        # Invoke mmdc
        args = self._build_mmdc_args(mmd_path, png_path)
        try:
            proc = self._invoke_mmdc(args, self.config.mermaid.render.timeout)
        except MermaidBlockError as exc:
            return MermaidRenderResult(
                block.index, success=False, error=str(exc)
            )

        # mmdc -w sets viewport width but Mermaid's intrinsic layout
        # can produce far narrower diagrams.  Resize UP to fill the
        # available page width before injecting DPI.
        target_w = self._compute_render_width()
        self._resize_to_target(png_path, target_w)

        # Inject DPI metadata so Word displays the image at the
        # correct physical size (300 DPI).  mmdc does not write DPI
        # headers; without them Word defaults to 96 DPI and images
        # are stretched ~3×, overflowing page boundaries.
        self._inject_dpi(png_path, self.config.mermaid.image.dpi)

        # Triple-check
        ok = proc.returncode == 0 and self._validate_output(png_path)
        if not ok:
            stderr_tail = (
                proc.stderr.strip()[-300:] if proc.stderr else "(no stderr)"
            )
            return MermaidRenderResult(
                block.index,
                success=False,
                error=f"mmdc exit={proc.returncode}, stderr: {stderr_tail}",
            )

        # Build image reference(s) relative to the base work_dir
        # (where preprocessed.md is written), not relative to mermaid_dir.
        # This ensures pandoc can resolve the path when run from work_dir.
        base_work_dir = work_dir.parent  # mermaid_dir → base work_dir
        try:
            rel_path = str(png_path.relative_to(base_work_dir)).replace("\\", "/")
        except ValueError:
            rel_path = str(png_path.resolve()).replace("\\", "/")

        caption = (
            f"Mermaid: {block.heading}"
            if block.heading != "?"
            else "Mermaid diagram"
        )

        # Check if image needs vertical splitting (Deferred #2)
        image_refs = self._build_image_refs(png_path, rel_path, caption)

        return MermaidRenderResult(
            block.index,
            success=True,
            png_path=str(png_path.resolve()),
            image_ref="\n\n".join(image_refs) if len(image_refs) > 1 else image_refs[0],
        )

    def _compute_usable_page_height_px(self) -> int:
        """Compute usable page height in pixels at the configured DPI.

        Formula: ``usable_inches = (page_height - top_margin - bottom_margin) / 2.54``.

        Returns an integer pixel count, with a small safety margin (-5%)
        to account for Word header/footer zones.
        """
        m = self.config.page.margins
        page_h = {
            "A4": 29.7,
            "Letter": 27.94,
            "Legal": 35.56,
        }.get(self.config.page.size, 29.7)

        # 0.75 safety factor: empirically calibrated against framework doc.
        # 0.60 was too conservative, leaving excessive blank space.
        # 0.75 provides a better balance between preventing truncation
        # and avoiding unnecessary splits.
        usable_inches = (page_h - m.top - m.bottom) / 2.54
        px = int(usable_inches * self.config.mermaid.image.dpi * 0.75)
        return max(1000, px)  # minimum 1000px

    def _build_image_refs(
        self,
        png_path: Path,
        img_path: str,
        caption: str,
    ) -> list:
        """Return one or more ``![caption](path)`` references for *png_path*.

        *img_path* should be relative to the preprocessed markdown file
        so that pandoc does not embed absolute paths in the output DOCX.
        """
        if not _HAS_PIL:
            return [f"![{caption}]({img_path})"]

        try:
            img = Image.open(png_path)
            w, h = img.size
        except Exception:
            logger.debug("Cannot open PNG for size check: %s", png_path)
            return [f"![{caption}]({img_path})"]

        max_h = self._compute_usable_page_height_px()
        if h <= max_h:
            return [f"![{caption}]({img_path})"]

        # Need to split
        logger.info(
            "Diagram %s is %dpx tall (limit %dpx) — splitting vertically",
            png_path.name, h, max_h,
        )
        return self._split_image(img, png_path, img_path, caption, w, h, max_h)

    def _split_image(
        self,
        img: "Image.Image",
        png_path: Path,
        img_path: str,
        caption: str,
        w: int,
        h: int,
        max_h: int,
    ) -> list:
        """Split a tall image into N parts and return markdown references."""
        refs = []
        overlap = 10
        effective_h = max_h - overlap
        n_parts = (h + effective_h - 1) // effective_h

        stem = png_path.stem
        parent = png_path.parent

        for i in range(n_parts):
            top = i * effective_h
            bottom = min(top + max_h, h)
            part = img.crop((0, top, w, bottom))

            part_path = parent / f"{stem}_part{i + 1}.png"
            part.save(str(part_path), "PNG")

            # Inject DPI into split parts — the original image has
            # DPI injected but PIL's crop()/save() does not preserve
            # DPI metadata, so Word would default to 96 DPI and
            # stretch the part ~3× wider than intended.
            dpi = self.config.mermaid.image.dpi
            self._inject_dpi(part_path, dpi)

            # Compute relative path for the part image
            try:
                part_rel = str(part_path.relative_to(png_path.parent.parent)).replace("\\", "/")
            except ValueError:
                part_rel = str(part_path.resolve()).replace("\\", "/")
            part_caption = (
                f"{caption}（{i + 1}/{n_parts}）"
                if n_parts > 1
                else caption
            )
            refs.append(f"![{part_caption}]({part_rel})")

        logger.info(
            "Split %s into %d part(s) (%dpx each, %dpx overlap)",
            png_path.name, n_parts, max_h, overlap,
        )
        return refs

    def _invoke_mmdc(
        self, args: list, timeout: int
    ) -> subprocess.CompletedProcess:
        """Run mmdc via subprocess with *shell=False* (argv list, no injection).

        Resolves the mmdc executable via ``shutil.which()`` so that the first
        element of *args* is an absolute path (or a bare command name that
        ``subprocess`` can locate on Windows).

        Raises
        ------
        MermaidBlockError
            On timeout.
        """
        # Resolve executable to avoid shell injection
        exe = args[0]
        resolved = shutil.which(exe)
        if resolved is not None:
            args = [resolved] + args[1:]
        elif not os.path.isabs(exe) and not os.path.isfile(exe):
            raise MermaidBlockError(
                f"mmdc not found: {exe!r}. "
                "Install with: npm install -g @mermaid-js/mermaid-cli"
            )

        # On Windows, npm's mmdc is a .cmd wrapper that goes through cmd.exe
        # even with shell=False.  cmd.exe expands %VAR% and !VAR!, so we
        # reject arguments containing those metacharacters.
        if sys.platform == "win32" and resolved and resolved.lower().endswith((".cmd", ".bat")):
            _BAD_CHARS = re.compile(r'[%!]')
            for i, arg in enumerate(args[1:], 1):
                if _BAD_CHARS.search(arg):
                    raise MermaidBlockError(
                        f"mmdc argument {i} contains batch metacharacters "
                        f"(% or !) which would be expanded by cmd.exe: {arg!r}"
                    )
        try:
            return subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
                encoding="utf-8",
                errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
        except subprocess.TimeoutExpired:
            raise MermaidBlockError(
                f"mmdc timed out after {timeout}s"
            ) from None

    @staticmethod
    def _validate_output(png_path: Path) -> bool:
        """Check that the rendered PNG exists and is non-trivial."""
        try:
            return png_path.exists() and png_path.stat().st_size > 1000
        except OSError:
            return False

    @staticmethod
    def _resize_to_target(png_path: Path, target_width_px: int) -> None:
        """Resize PNG to target pixel width, maintaining aspect ratio.

        mmdc ``-w`` sets only the viewport/background width; the actual
        diagram content width is determined by Mermaid's internal layout
        engine and can be far narrower for simple diagrams (e.g. a
        single-column flowchart).  This causes physically tiny images in
        DOCX at 300 DPI.  We resize UP to the target width (never down)
        with a 4× cap to avoid extreme pixelation.
        """
        if not _HAS_PIL:
            return
        try:
            img = Image.open(str(png_path))
            w, h = img.size
            if w <= 0 or target_width_px <= 0:
                return
            # Only resize if image is narrower than 85% of target
            if w >= target_width_px * 0.85:
                return
            # Cap enlargement at 6× to avoid extreme pixelation
            ratio = min(target_width_px / w, 6.0)
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            img.save(str(png_path), "PNG")
            logger.debug(
                "Resized %s: %dx%d → %dx%d (%.1f×)",
                png_path.name, w, h, new_w, new_h, ratio,
            )
        except Exception:
            logger.debug("Cannot resize %s", png_path)

    @staticmethod
    def _inject_dpi(png_path: Path, dpi: int) -> None:
        """Write DPI metadata into a PNG file so Word displays it at the
        correct physical size.  mmdc does not write DPI headers; without
        them Word defaults to 96 DPI and the image is stretched.
        """
        if not _HAS_PIL:
            return
        try:
            img = Image.open(png_path)
            img.save(str(png_path), "PNG", dpi=(dpi, dpi))
        except Exception:
            logger.debug("Cannot inject DPI into %s", png_path)

    # ------------------------------------------------------------------
    # Internal: replacement
    # ------------------------------------------------------------------

    def _replace_blocks(
        self,
        text: str,
        blocks: List[MermaidBlock],
        results: Dict[int, MermaidRenderResult],
    ) -> str:
        """Replace successfully-rendered blocks with image references.

        Blocks are processed in **reverse end-offset order** so that earlier
        replacements do not invalidate later character indices.
        """
        # Sort by end offset descending
        ordered = sorted(blocks, key=lambda b: b.end, reverse=True)

        for block in ordered:
            result = results.get(block.index)
            if result is None or not result.success:
                continue
            image_ref = result.image_ref or ""
            text = (
                text[: block.start]
                + f"\n{image_ref}\n\n"
                + text[block.end :]
            )

        return text
