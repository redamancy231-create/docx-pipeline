## 项目状态: DOCX Pipeline 泛化工具

- 当前阶段: **Phase 2 完成 + 审查闭合**
- Phase 1: 纯 python-docx 路径（21文件~2200行）✅
- Phase 2: PandocConverter + MermaidRenderer + CLI --method pandoc/auto ✅
- 审查: Codex GPT-5.5 两轮交叉验证（17项发现全部修复）✅
- 收尾: 旧脚本归档（8文件）+ 新旧 docx 对比 ✅

### Phase 2 产出

| 文件 | 类型 | 行数 | 说明 |
|------|------|------|------|
| `renderers/__init__.py` | 新建 | ~25 | 包索引 |
| `renderers/mermaid_renderer.py` | 新建 | ~310 | Mermaid 预渲染器 |
| `converters/pandoc_converter.py` | 新建 | ~540 | PandocConverter（6阶段管线+后处理） |
| `converters/__init__.py` | 修改 | +2行 | 导出 PandocConverter |
| `cli.py` | 修改 | +100行 | 3辅助函数 + --pandoc-args + method解析 + logging |

### 已修复 Bug（17项）

| 级别 | 数量 | 来源 |
|------|------|------|
| MAJOR | 5 | 实现中暴露 3 + Codex 审查 4（1 重合） |
| MEDIUM | 10 | Codex 两轮审查 |
| MINOR | 2 | Codex 审查 |

### 已归档旧脚本

`_archive/docx_legacy_scripts/`（8 个文件，详见 README.md）

### 新旧 docx 对比

| 指标 | 旧版 | 新版 | 说明 |
|------|------|------|------|
| 文件大小 | 857.9 KB | 763.4 KB | -11%（少图+不重复TOC） |
| 表格数 | 93 | 93 | 完全一致 |
| 图片数 | 9 | 6 | 旧版 PIL 拆分多出 3 张分片 |
| 标题数 | 160 | 160 | 完全一致 |

### Deferred（P3，触发式执行）

| 项 | 触发条件 | 状态 |
|----|---------|------|
| 共享代码提取（~125行重复） | 下次改 pure_python.py 或 pandoc_converter.py 时顺手提 | ✅ 已完成（2026-06-21） |
| 高 Mermaid 图 PIL 切分 | 遇到渲染高度 >7 英寸的图时 | ✅ 已完成（2026-06-21） |
| 更完整样式后处理（代码块底纹等） | pandoc 默认高亮不满足需求时 | ✅ 已完成（2026-06-21） |

**Deferred 闭合备注（2026-06-21）**：
- 共享代码提取：新增 `converters/shared.py`（`_PAGE_SIZES_CM` / `_DEFAULT_HEADING_SIZES` / `_DEFAULT_HEADING_RGB` / `hex_to_rgb()` / `set_cell_shading()`），pandoc_converter.py 和 pure_python.py 均已改为导入。删除了两处 ~50 行重复代码。
- Mermaid 切分：新增 `MermaidRenderer._build_image_refs()` + `_split_image()` + `_compute_usable_page_height_px()`。PIL 检测高度 → 超过可用页高则水平切分为多张 PNG（10px 重叠防接缝），markdown 中生成 `![caption（1/N）](part1.png)` 序列。
- 代码块底纹：新增 `PandocConverter._apply_code_block_shading()`，对 `Source Code` 样式段落应用 `config.font_colors.code_block_bg` 背景色。框架文档实测：42 个代码段落全部着色。
- 附带修复：TOC 域插入逻辑修复——pandoc `--number-sections` 导致标题文本为 `1.1\t目录` 而非 `目录`，原精确匹配失效。改为 `endswith("\t" + toc_title)` 兼容。TOC 域后新增灰色提示段落（"右键目录 → 更新域 或按 F9 以显示页码"）。

### 生产运行记录

| 日期 | 项目 | md大小 | 产出大小 | 表格 | Mermaid | 耗时 | 备注 |
|------|------|--------|---------|------|---------|------|------|
| 2026-06-21 | AI协作项目全生命周期框架 v1.6.2 | ~297KB | 799KB | 100 | 7 | ~2min | 首次真实项目全量重生成，pandoc后端，§7.7+§9.11完整渲染 |
| 2026-06-21 | 同上（修复版） | ~297KB | 781KB | 100 | 7 | ~2min | 三Deferred闭合：代码块底纹(42段)+TOC页码提示+图片切分就绪；TOC编号标题匹配bug修复 |

### 会话备注

- 2026-06-21 模型：DeepSeek-V4-Pro；审查后端：GPT-5.5 (Codex CLI v0.138.0)
- 项目目录：`docx_pipeline/`
- 首次生产运行触发：框架 v1.6.2 写入被动观测后三件套同步，需全量重生成 docx
- 2026-06-21 三 Deferred 闭合 + 附带修复（选择性 keep_with_next/Block Text→Normal/边距对齐 v1.6.1/TOC 编号标题匹配）

## Next Steps

- 图片切分阈值校准 → P1 → 当前 0.60 安全系数（2035→1744px），目视确认后可能需要进一步调低
- 文字宽度（page 1 效果） → P1 → 考虑自定义 pandoc reference docx 替代 Block Text→Normal 后处理
- 图片段落"段前分页"可选策略 → P2 → 大图前是否主动加分页符，避免 Word 自动分页的不确定性
