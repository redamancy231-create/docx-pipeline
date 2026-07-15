# 关键文件索引

> 最后更新: 2026-07-15

## 代码
- [cli.py](docx_pipeline/cli.py) — Click CLI 入口（init/convert/validate/info）
- [schema.py](docx_pipeline/config/schema.py) — 配置 dataclass 定义
- [defaults.py](docx_pipeline/config/defaults.py) — 4 个预设模板（default/academic/report/strategy）
- [loader.py](docx_pipeline/config/loader.py) — YAML 加载 + 环境变量覆盖
- [validator.py](docx_pipeline/config/validator.py) — 配置校验 + 依赖探测
- [base.py](docx_pipeline/converters/base.py) — AbstractConverter（含备份轮换）
- [shared.py](docx_pipeline/converters/shared.py) — 共享常量与工具函数
- [markdown_parser.py](docx_pipeline/converters/markdown_parser.py) — 逐行状态机 MD 解析器
- [pure_python.py](docx_pipeline/converters/pure_python.py) — Pure Python 转换器（含 Mermaid + 图片嵌入）
- [pandoc_converter.py](docx_pipeline/converters/pandoc_converter.py) — Pandoc 转换器
- [mermaid_renderer.py](docx_pipeline/renderers/mermaid_renderer.py) — Mermaid 预渲染器
- [encoding.py](docx_pipeline/utils/encoding.py) — Windows UTF-8 环境设置
- [paths.py](docx_pipeline/utils/paths.py) — 路径规范化

## 数据
- [project_config.schema.json](docx_pipeline/data/schemas/project_config.schema.json) — JSON Schema Draft-07
- [default.yaml](docx_pipeline/data/templates/default.yaml) — 通用中文文档
- [academic.yaml](docx_pipeline/data/templates/academic.yaml) — 学术论文
- [report.yaml](docx_pipeline/data/templates/report.yaml) — 技术报告（含 Mermaid）
- [strategy.yaml](docx_pipeline/data/templates/strategy.yaml) — 量化策略文档

## 测试
- [test_basic.py](tests/test_basic.py) — 基础测试（配置/解析/CLI/备份）

## 文档
- [README.md](README.md) — 使用文档（中文）
- [project_status.md](project_status.md) — 项目状态
