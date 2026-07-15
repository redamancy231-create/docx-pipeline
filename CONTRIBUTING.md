# Contributing to DOCX Pipeline

## 语言 | Language

English, 中文, or 正體中文 are all welcome. The primary documentation is in Chinese, but English contributions are encouraged for international accessibility.

## 流程 | Process

1. **Open an issue first** — discuss the change before writing code
2. **Fork the repo** and create a feature branch
3. **Write tests** — new features should include test coverage
4. **Run tests** — `python -m pytest tests/ -v` must pass
5. **Submit a PR** with a clear description of the change

## CLA | Contributor License Agreement

There is **no CLA**. Contributions are accepted under the same MIT license as the project.

## 审查 | Review

All PRs will be reviewed. Review may include:
- Code correctness and style consistency
- Test coverage adequacy
- Cross-platform compatibility (Windows / macOS / Linux)
- Configuration schema compatibility with existing templates

## 开发环境 | Development Setup

```bash
git clone https://github.com/redamancy231-create/docx-pipeline.git
cd docx-pipeline
pip install -e ".[dev]"
python -m pytest tests/ -v
```

Optional dependencies for full testing:
```bash
# pandoc backend
pandoc --version  # install from https://pandoc.org

# mermaid rendering
npm install -g @mermaid-js/mermaid-cli
```
