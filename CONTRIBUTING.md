# Contributing to DOCX Pipeline

## 语言 | Language

English, 中文, or 正體中文 are all welcome. The primary documentation is in Chinese, but English contributions are encouraged for international accessibility.

## 流程 | Process

1. **Open an issue first** — discuss the change before writing code
2. **Fork the repo** and create a feature branch
3. **Write tests** — new features should include test coverage
4. **Run tests** — `python -m pytest tests/ -v` must pass
5. **Submit a PR** with a clear description of the change

## 代码来源 | Code Provenance

- 提交的代码必须是**原创作品**或**兼容许可的代码**。
- **禁止**从 MinerU（`github.com/opendatalab/MinerU`）或其他非 MIT 许可的项目复制代码、数据、测试用例到本仓库。
- 如果你在 Issue/PR 中引用外部代码片段，请标注来源和许可。
- 本项目的数学公式相关代码为独立实现——请勿将 MinerU 的 OMML/LaTeX 代码粘贴到 PR 中。

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
