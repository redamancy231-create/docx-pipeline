# CLAUDE.md — DOCX Pipeline

> **模型来源 Model provenance**: DeepSeek-V4-Pro (via Claude Code CLI), 2026-07-22
> **审查 Review**: GPT-5.6-Sol (Codex CLI) — 61/100 → 5 处事实错误已修正, 2026-07-21

## 项目定位

将 Markdown 转换为排版精美的中文 DOCX。双后端架构（Pure Python 零依赖 + Pandoc 高质量），支持 Mermaid 图表内嵌和 LaTeX 数学公式。

- 当前阶段：v1.1.0 已发布（见 `project_status.md`）
- 52 tests，CI 绿色（Python 3.10-3.12，Ubuntu/Windows/macOS）
- Pure Python 后端的数学公式支持为**实验性原型**（渲染效果不及 Pandoc）→ 面向用户的文档应推荐 Pandoc 后端

## Agent 边界

**可派**：
- 修改 `docx_pipeline/` 下的转换器/渲染器/配置代码
- 在 `tests/` 下新增或修改测试
- 更新 README/CHANGELOG/reference_files.md 等文档
- 运行测试、benchmark、CLI 命令验证功能

**禁止**：
- 修改 `.gitignore` 中排除的目录（`_review/`、`_pipeline_output/`、`_visual_check/`）
- 提交 `project_status.md`（已在 `.gitignore` 排除）
- 删除或重命名 `docx_pipeline/data/templates/*.yaml`（用户配置的模板引用可能断裂）
- 修改 `AbstractConverter` 的公共接口而不先做 impact analysis（影响 Pandoc + Pure Python 双后端）

## 关键命令

```bash
# 安装（开发模式）
pip install -e ".[dev]"

# CLI 入口
docx-pipeline init              # 创建 project.yaml
docx-pipeline convert           # 执行转换
docx-pipeline validate          # 校验配置
docx-pipeline info              # 显示项目信息

# 测试（Windows 必须加 PYTHONIOENCODING=utf-8）
PYTHONIOENCODING=utf-8 python -m pytest tests/ -v

# 单文件测试
PYTHONIOENCODING=utf-8 python -m pytest tests/test_smoke.py -v

# Benchmark（双后端性能对比）
python dev/bench.py

# 数学符号表重新生成（修改 dev/generate_math_symbols.py 后）
python dev/generate_math_symbols.py > docx_pipeline/data/math_symbols.py
```

## 架构约束

### 双后端设计

```
AbstractConverter (base.py)
    ├── PandocConverter   ← pandoc 必须已在 PATH，高质量
    └── PurePythonConverter ← 零外部依赖，实验性数学公式
```

- **Auto 模式**：`pandoc.enabled=true` 且 pandoc 在 PATH → Pandoc；否则 → Pure Python
- **Pandoc 后端**：通过 `--from markdown+tex_math_dollars+tex_math_single_backslash` 处理数学公式，表格经 `autofit` 后处理
- **Pure Python 后端**：自研 Markdown 解析器（`MarkdownParser`）+ 自研 LaTeX→OMML 引擎（`_latex_to_omml` 及 `_parse_math_*` 系列方法）→ **OMML 渲染有已知缺陷**（分式/根号/上下标/大型运算符），仅推荐在 pandoc 不可用时使用

### 不可修改的设计不变量

- `DocxPipelineConfig` 的字段名和类型是 YAML 模板的契约——改名会断裂所有用户 `project.yaml`
- `AbstractConverter.convert()` 返回 `Document` 对象，`save()` 返回 `str`（文件路径）——调用方依赖此签名
- `MermaidRenderer` 的 DPI 注入逻辑（`_inject_dpi`）依赖 Pillow —— mmdc 输出 PNG 不带 DPI 元数据
- `save()` 使用临时文件 + 原子替换写入，`_rotate_backups()` 负责备份轮换——不可改为直接覆盖

### 配置系统

```
project.yaml → load_config() → DocxPipelineConfig (@dataclass)
                                   ↓
                              validate_config()
```

- 4 个内置模板：`default` / `academic` / `report` / `strategy`
- 环境变量覆盖：`DOCX_PIPELINE__*` 前缀（双下划线分隔层级，如 `DOCX_PIPELINE__FONTS__EAST_ASIAN=SimSun`）
- JSON Schema：`docx_pipeline/data/schemas/project_config.schema.json`

## 环境要求

- **Python**: ≥3.10（CI 测试 3.10/3.11/3.12）
- **必需依赖**: python-docx, PyYAML, click, Pillow
- **可选依赖**:
  - `pandoc` — Pandoc 后端（推荐，数学公式支持好）
  - `mmdc` / `mermaid-cli` — Mermaid 图表渲染
- **Windows**: 含中文输出的 Python 命令须加 `PYTHONIOENCODING=utf-8`（如 pytest），路径用正斜杠
- **平台**: OS Independent（CI 覆盖 Ubuntu/Windows/macOS）

## 已知坑位

### 数学公式
- **Pure Python 数学渲染有缺陷**：分式/根号/上下标/大型运算符的 OMML 输出不正确 → 文档和 README 推荐 Pandoc 后端，Pure Python 标为实验性
- Pandoc 后端的 `tex_math_dollars` 在 pandoc 3.1+ 默认启用，无需额外配置

### Mermaid 图表
- **mmdc 渲染 PNG 不带 DPI 元数据** → `_inject_dpi` 必须执行，否则 Word 中图片 ~3 倍拉伸
- **大图 keep_with_next 反效果**：标题段落设置 `keep_with_next` + 紧随大尺寸 Mermaid 图 → "一行标题 + 整页空白"
- **图片切分**：`_split_image` 使用 0.75 安全系数，长图可能仍需手动调

### Pandoc 特有
- 表格 autofit 行为：Pandoc 生成 `w:tblW w:type="auto"`，Pure Python 用 `table.autofit = True`——两者渲染结果不对称
- `--toc` 自动目录与手动 TOC 字段插入冲突 → 当前使用手动 `_apply_toc_field`

### Windows 编码
- Python subprocess + 中文 = 必须 `PYTHONIOENCODING=utf-8`
- gh CLI release upload 中文文件名在 Windows Git Bash 下截断 → 发布资产用英文文件名

### 模板默认值
- `defaults.py` 中的模板默认值变更会影响所有 `docx-pipeline init` 新项目
- 模板文件（`data/templates/*.yaml`）与 `ProjectConfig` dataclass 必须保持字段名一致

## 审查追溯

| 轮次 | 模型 | 角度 | 关键发现 |
|------|------|------|---------|
| R1-R4 | GPT-5.6-Sol (Codex CLI) | 代码审查 + 页面审查 | ~45 项修复（含 backup 断号/landscape 宽度/Mermaid shell=False 注入等） |
| R5 | GPT-5.6-Sol (Codex CLI) | v1.1.0 数学公式 + MinerU | 16 项发现全部修复 |
| 目视验证 | 用户 | 实际运行 | Pandoc 数学完美，Pure Python 渲染缺陷；Pandoc 表格后空白页；默认路径缺扩展名 |
| R-CLAUDE.md | GPT-5.6-Sol (Codex CLI) | write-claude-md Step 5 审查 | 12 项事实核验：8 ✅ / 2 ⚠ / 2 ❌；5 处事实错误已修正（61/100→修复后） |
| R-分析 | DeepSeek-V4-Pro (Claude Code) | GitNexus MCP 架构分析 | 992 节点/1755 边/34 社区/69 流程 — `_review/gitnexus_analysis_20260722.{md,json}` |

## 关联项目

| 项目 | 关系 |
|------|------|
| [AI 协作框架](https://github.com/redamancy231-create/ai-collaboration-framework) | 方法论上游——多后端审查、被动观测记录、session-end 协议均源自该框架 |
| [GitNexus](https://github.com/redamancy231-create/etf-pattern-match-pybind11) | GitNexus MCP 首次实测项目——CLI 准确率 100%，FTS 墙内不可用 |

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **docx-pipeline** (992 symbols, 1755 relationships, 69 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

<!-- gitnexus:end -->
