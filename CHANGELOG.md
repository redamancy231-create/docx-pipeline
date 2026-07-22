# Changelog

## [1.2.0] — 2026-07-22

### Added

- **Math formula support (Pure Python backend)**: Replaced hand-written LaTeX→OMML parser with a `latex2mathml` → MathML→OMML bridge architecture (`mathml2omml.py`, 681 lines). The LaTeX parsing correctness is delegated to the mature `latex2mathml` library; docx-pipeline independently maintains the MathML→OMML mapping layer covering 14 formula structure types (fractions, radicals, scripts, n-ary operators, accents, matrices, fences, limits, and more). 21 automated tests with lxml XPath oracles. MathML→OMML mapping patterns independently verified against markdown2docx (TimeEtcher, MIT) — two independent reasoning chains converged on the same three-layer architecture. Graceful degradation: unsupported formulas render as literal LaTeX text.

## [1.1.0] — 2026-07-20

### Added

- **Math formula support (Pandoc backend)**: The Pandoc `markdown` reader already enabled `tex_math_dollars` by default, so `$...$` and `$$...$$` were already functional. This change explicitly fixes `tex_math_dollars` in the reader string to prevent regressions, and adds `tex_math_single_backslash` to support `\(...\)` (inline) and `\[...\]` (display) LaTeX delimiters.

## [1.0.0] — 2026-07-15

### Initial Release

- Dual backend: Pure Python (python-docx) + Pandoc subprocess
- Mermaid diagram pre-rendering with DPI injection and tall-image splitting
- 4 preset templates: default, academic, report, strategy
- YAML configuration with environment variable override support
- CLI: `init`, `convert`, `validate`, `info`
- Backup rotation with atomic file replacement
- Image embedding with automatic width constraint (Pure backend)
- Comprehensive Markdown parser (headings, tables, code blocks, lists, blockquotes, YAML frontmatter)
- Post-processing: font application, table borders, TOC field, code block shading, footer
- Chinese, English, and Traditional Chinese (正體中文) README
- 17 automated tests (config, parser, CLI, backup)
- 3-round GPT-5.6-Sol independent review closure (28 issues fixed)
- CI: GitHub Actions (Python 3.10–3.12, Ubuntu/Windows/macOS)
