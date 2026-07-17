# Retrospect: LLM 代码审查的三类盲区

> 2026-07-17 · 本轮 docx-pipeline 大规模改进中被实证

## 背景

GPT-5.6-Sol 对 docx-pipeline 进行了多轮代码审查（改进方案审查 + 翻译审查 + smoke-test 审计）。审查发现了 8 个代码级 bug。但在实际使用中，仍有两个 bug 仅通过"目视确认"发现：

| Bug | 审查阶段 | 发现阶段 |
|-----|:--:|:--:|
| `output/docx` 无扩展名 | 未发现 | 用户实际运行 init→convert |
| Pandoc 表格未经 autofit | 未发现 | 用户打开 DOCX 目视确认 |
| Pandoc 表格后空白页 | 未发现 | 用户打开 DOCX 目视确认 |

## 发现

### 盲区 1: 默认路径 vs 实际路径

代码审查时，LLM 会沿"正常使用路径"（已有 project.yaml → convert）追踪。但"裸模板默认值 → init → convert"这条路径不走已有配置，暴露了 `defaults.py` 的 `output/docx` 无扩展名 bug。

**教训**：审查提示词应显式要求验证模板默认值的端到端可用性，而非仅检查已知调用链。

### 盲区 2: 渲染效果

Pandoc 转换器的代码中，`autofit` 配置字段存在、被传递、被存储——审查者看不出问题。但实际渲染结果中，Pandoc 生成的是 `w:tblW w:type="auto"`(自动宽度)，Pure Python 生成的是 `table.autofit = True`(python-docx API)。代码结构对称，渲染结果不对称。

**教训**：UI/文档类项目的审查必须包含"目视确认"步骤，LLM 审代码无法替代。

### 盲区 3: 终端编码

GitHub Release 中文文件名上传在 Windows Git Bash 环境下反复失败。gh CLI 的 `release upload` 命令会截断非 ASCII 字符。Python API 的 `urllib.request` 同样受影响。根因是 Windows 终端层面的 GBK/UTF-8 编码转换。

**教训**：跨平台 CLI 工具的上传操作须验证目标平台编码行为。中文文件名在 Windows gh CLI 上不可靠，应使用英文名。

## 影响

- **docx-pipeline**: 新增 `tests/test_smoke.py` 覆盖默认路径 + 双后端对等检查
- **通用**: 文档类项目的改进方案中应包含"目视确认"步骤（截图/输出样本）
- **通用**: CLI 工具发布资产应使用英文文件名

## 未解决问题

- Mermaid 图表尺寸/比例自适应（仍为已知限制，难度过高暂不修）
- gh CLI 中文文件名上传（GitHub 上游限制，暂无 workaround）
