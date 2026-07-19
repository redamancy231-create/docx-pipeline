## 项目状态: DOCX Pipeline

- 当前阶段: **v1.1.0 已发布**（2026-07-20）
- 测试: 52 tests（新增 9 个数学公式测试 + 5 个 Pure Python 测试）
- CI: GitHub Actions (Python 3.10-3.12, Ubuntu/Windows/macOS) ✅

### 会话备注 (2026-07-19/20, Claude Code DeepSeek-V4-Pro + GPT-5.6-Sol)

**数学公式支持 v1.1.0：**
- Pandoc 后端：显式固定 `tex_math_dollars` + 新增 `tex_math_single_backslash`（`\(...\)`/`\[...\]` 分隔符）
- Pure Python 后端：GPT-5.6-Sol 独立实现 563 行 LaTeX→OMML 原型（6 种公式结构）
- 符号表可复现生成管线：`dev/generate_math_symbols.py` → `data/math_symbols.py`（81 符号）
- 9 个数学测试（Pandoc 5 + Pure Python 4），含 lxml XPath oracle
- 目视验证：Pandoc 效果完美，Pure Python 标为实验性原型
- CONTRIBUTING.md 新增代码来源条款
- 三语 README 同步（推荐 Pandoc 后端用于数学公式）

**MinerU 分析 + GPT-5.6-Sol 审查：**
- Phase 1-3 全量架构对比分析（MinerU vs docx-pipeline）
- 判定：不是重复造轮子（方向相反，天然互补）
- 版权意见（GPT-5.6-Sol）：独立实现，风险低
- GPT-5.6-Sol 审查 16 项发现，全部修复
- 改进方案 + 来源备忘录 + 三种长期策略写入 `项目改进计划/docx-pipeline/`

### 审查闭合

| 轮次 | 审查后端 | 发现数 | 状态 |
|------|---------|--------|------|
| R1 | GPT-5.6-Sol (Codex CLI) | 19 (7 MAJOR + 8 MEDIUM + 4 MINOR) | ✅ 全部修复 |
| R2 | GPT-5.6-Sol (Codex CLI) | 8 (2 MAJOR + 5 MEDIUM + 1 MINOR) | ✅ 全部修复 |
| R3 | GPT-5.6-Sol (Codex CLI) | 2 (backup 断号 + landscape 宽度) | ✅ 全部修复 |
| 页面审查 | GPT-5.6-Sol (Codex CLI) | 12 项改进建议 | ✅ 全部修复 |
| **R4** | **GPT-5.6-Sol (Codex CLI)** | **16 (1 阻断 + 13 需修复 + 1 建议)** | **✅ 全部修复** |

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

### 会话备注 (2026-07-19, Claude Code DeepSeek-V4-Pro)

**数学公式 + MinerU 方向定位：**
- 三语 README 已知限制新增第7条：数学公式不支持
- 三语 README 计划改进新增：Pandoc `tex_math_dollars` → OMML 方案
- README 加 Markdown→DOCX 定位声明，与 MinerU（PDF→MD）区分方向
- 移除已完成的示例 gallery 计划项 + project_status.md 截图待办

### 待定

- PyPI 发布（当前 `pip install git+...` 可用）

### 会话备注 (2026-07-19/20, Claude Code DeepSeek-V4-Pro + GPT-5.6-Sol)

见上方主条目。

## 发现的问题

- Pure Python 数学原型 OMML 渲染效果不及 Pandoc（目视验证）：分式/根号/上下标/大型运算符有不同程度渲染问题 → 务实方案：文档推荐 Pandoc，Pure Python 标实验性原型
- `tex_math_dollars` 在 pandoc 3.1+ 默认已启用（GPT-5.6-Sol F01 发现）→ 已修正归因

## Next Steps

```
等 awesome-list PR 审核结果 → P1 → 等外部审核
启动 v1.2.0 long-term（latex2mathml MathML→OMML 桥接）→ P2 → 等 Pure Python 用户数学需求足够 + pandoc 不可用场景明确
批量转换 --batch → P2 → 等有明确用户场景
PyPI 发布 → P2 → 等第一个外部 star/issue
```

- 等待 awesome-list PR 审核结果 → 如合并则代表外部生态认可
- 第一个外部 star/issue → 触发 PyPI 发布决策
- 图片切分阈值校准 → P2 → 当前 0.75 安全系数，目视确认后可能需要进一步调低
