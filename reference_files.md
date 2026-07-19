# 关键文件索引

> 最后更新: 2026-07-20

## 代码
- [cli.py](docx_pipeline/cli.py) — Click CLI 入口（init/convert/validate/info）
- [pipeline.py](docx_pipeline/pipeline.py) — Python API（DocxPipeline 类）
- [schema.py](docx_pipeline/config/schema.py) — 配置 dataclass 定义
- [defaults.py](docx_pipeline/config/defaults.py) — 4 个预设模板（default/academic/report/strategy）
- [loader.py](docx_pipeline/config/loader.py) — YAML 加载 + 环境变量覆盖
- [validator.py](docx_pipeline/config/validator.py) — 配置校验 + 依赖探测
- [base.py](docx_pipeline/converters/base.py) — AbstractConverter（含备份轮换）
- [shared.py](docx_pipeline/converters/shared.py) — 共享常量与工具函数
- [markdown_parser.py](docx_pipeline/converters/markdown_parser.py) — 逐行状态机 MD 解析器
- [pure_python.py](docx_pipeline/converters/pure_python.py) — Pure Python 转换器（含 Mermaid + 图片 + 数学公式原型）
- [pandoc_converter.py](docx_pipeline/converters/pandoc_converter.py) — Pandoc 转换器（含 tex_math 扩展）
- [mermaid_renderer.py](docx_pipeline/renderers/mermaid_renderer.py) — Mermaid 预渲染器
- [encoding.py](docx_pipeline/utils/encoding.py) — Windows UTF-8 环境设置
- [paths.py](docx_pipeline/utils/paths.py) — 路径规范化

## 数据
- [project_config.schema.json](docx_pipeline/data/schemas/project_config.schema.json) — JSON Schema Draft-07
- [math_symbols.py](docx_pipeline/data/math_symbols.py) — 数学符号映射表（81 符号，可复现生成）
- [default.yaml](docx_pipeline/data/templates/default.yaml) — 通用中文文档
- [academic.yaml](docx_pipeline/data/templates/academic.yaml) — 学术论文
- [report.yaml](docx_pipeline/data/templates/report.yaml) — 技术报告（含 Mermaid）
- [strategy.yaml](docx_pipeline/data/templates/strategy.yaml) — 量化策略文档

## 开发者工具
- [bench.py](dev/bench.py) — 性能 benchmark 脚本
- [generate_math_symbols.py](dev/generate_math_symbols.py) — 数学符号表生成器（来源：TeXbook/CTAN/Unicode）

## 测试
- [test_basic.py](tests/test_basic.py) — 基础测试（配置/解析/CLI/备份）
- [test_pandoc_converter.py](tests/test_pandoc_converter.py) — Pandoc 转换器测试
- [test_cli_contract.py](tests/test_cli_contract.py) — CLI 契约测试
- [test_mermaid_renderer.py](tests/test_mermaid_renderer.py) — Mermaid 渲染测试
- [test_smoke.py](tests/test_smoke.py) — 冒烟测试（模板/双后端）
- [test_math.py](tests/test_math.py) — Pandoc 数学公式测试（5 个）
- [test_pure_python_math.py](tests/test_pure_python_math.py) — Pure Python 数学测试（4 个）

## 文档
- [README.md](README.md) — 使用文档（中文）
- [en/README.md](en/README.md) — 使用文档（英文）
- [zh-Hant/README.md](zh-Hant/README.md) — 使用文档（正體中文）
- [project_status.md](project_status.md) — 项目状态
- [CHANGELOG.md](CHANGELOG.md) — 变更日志
- [CONTRIBUTING.md](CONTRIBUTING.md) — 贡献指南（含代码来源条款）
