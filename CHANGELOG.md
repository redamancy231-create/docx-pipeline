# Changelog

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
- 3-round GPT-5.6-Sol independent review closure (29 issues fixed)
- CI: GitHub Actions (Python 3.10–3.12, Ubuntu/Windows/macOS)
