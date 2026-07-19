## 项目状态: DOCX Pipeline

- 当前阶段: **v1.0.0 已发布**（2026-07-15）+ 2026-07-17 重大更新
- 测试: 17→38 tests（新增 test_pandoc_converter/test_cli_contract/test_mermaid_renderer/test_smoke）
- CI: GitHub Actions (Python 3.10-3.12, Ubuntu/Windows/macOS) ✅

### 会话备注 (2026-07-17, Claude Code DeepSeek-V4-Pro + GPT-5.6-Sol)

**GPT-5.6-Sol 执行 4 项改进 + 审查 + 修复：**
- 新增 Python API (`docx_pipeline/pipeline.py` — DocxPipeline 类)
- 测试覆盖扩展 (21 tests: pandoc converter + CLI contract + mermaid renderer)
- 开发者 benchmark (`dev/bench.py` 553行)
- README 后端能力矩阵 + "何时选择" + 已知限制 + 计划改进
- 三语 README 同步(简/英/正体) + 截图预览
- **8 bug 修复**(GPT-5.6-Sol 审计发现): 扩展名缺失/Pandoc默认值/CWD路径/首行缩进/tblW重复/init无md_file/裸config路径
- report 模板页边距收紧至 1.8cm、默认 Pandoc→False
- 已知限制扩展至 6 条(含 Pandoc 空白页/Mermaid 尺寸/页边距偏好)
- gh CLI 中文文件名教训: Windows 上 release upload 须用英文名

### 审查闭合

| 轮次 | 审查后端 | 发现数 | 状态 |
|------|---------|--------|------|
| R1 | GPT-5.6-Sol (Codex CLI) | 19 (7 MAJOR + 8 MEDIUM + 4 MINOR) | ✅ 全部修复 |
| R2 | GPT-5.6-Sol (Codex CLI) | 8 (2 MAJOR + 5 MEDIUM + 1 MINOR) | ✅ 全部修复 |
| R3 | GPT-5.6-Sol (Codex CLI) | 2 (backup 断号 + landscape 宽度) | ✅ 全部修复 |
| 页面审查 | GPT-5.6-Sol (Codex CLI) | 12 项改进建议 | ✅ 全部修复 |

### 本次会话完成（2026-07-15）

- 从 `_tools/` 迁移到 `projects/`，独立开源
- 配置契约统一：外部 YAML 模板 + JSON Schema + README 对齐运行时 dataclass 格式
- Mermaid shell=False 注入修复 + Windows .cmd 批处理变量展开检测
- Pure Python 后端 Mermaid + 图片嵌入
- 粗体/斜体保留（bold/italic 默认为 None）
- TOC 插入只删除 TOC 条目（正则匹配），保留正文段落
- 备份轮换实现（临时文件 + 原子替换 + max_backups=0 支持 + 断号清理）
- 15 个 MEDIUM/MINOR 修复（CLI 短参数、validate exit code、package-data、并发安全、真值判断、异常捕获、.docx 扩展名、注释、死代码等）
- 三语 README（简/英/正） + Mermaid 架构图 + 5 枚徽章 + OG 图片
- GitHub Actions CI + CHANGELOG + SECURITY + Issue 模板
- 15 个 GitHub Topics
- 7 仓库互链矩阵全满
- 6 个旧仓库补齐 CHANGELOG（etf-pattern-match-pybind11 + claude-skills 额外补齐 SECURITY + Issue 模板）
- 2 个 awesome-list PR 提交（awesome-scientific-writing #89 + awesome-markdown #135）

### 待定

- PyPI 发布（当前 `pip install git+...` 可用）

## Next Steps

- 等待 awesome-list PR 审核结果 → 如合并则代表外部生态认可
- 第一个外部 star/issue → 触发 PyPI 发布决策
- 图片切分阈值校准 → P2 → 当前 0.75 安全系数，目视确认后可能需要进一步调低
