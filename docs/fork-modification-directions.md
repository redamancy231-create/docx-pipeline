# docx-pipeline Fork 修改方向全景分析

> 版本: v1.2 · 生成日期: 2026-07-22 · 修订: 2026-07-22
> 模型 provenance: DeepSeek-V4-Pro (via Claude Code CLI) · 审查: GPT-5.6-Sol (via Codex CLI) — 35 条发现，7 阻断/24 重要/4 建议，全部修复
> 基于: 项目 README/CLAUDE.md/全量源码（20 .py / ~5,800 行）/52 tests/project_status.md + GitNexus MCP + 源码级交叉验证

## 项目现状速览

- **定位**: Markdown → 中文 DOCX 命令行转换工具，双后端架构（Pure Python 无需外部转换器 + Pandoc 高质量）
- **版本**: v1.1.0（包元数据版本；PyPI 发布状态见 `project_status.md` 待定项）
- **许可证**: MIT
- **代码规模**: 20 个 Python 源文件（docx_pipeline/ 下），物理行数合计约 5,800 行（不含测试/模板）
- **测试**: 52 tests，7 个测试文件，CI 绿色（Python 3.10-3.12 × Ubuntu/Windows/macOS）
- **审查**: 5 轮 GPT-5.6-Sol 独立审查（~45+16 项修复）+ GitNexus MCP 架构分析 + 本次 GPT-5.6-Sol 魔鬼代言人审查（35 条发现）
- **核心能力**:
  - 双后端转换（Pure Python 自研解析器 + Pandoc 子进程）
  - Mermaid 图表渲染（mmdc → PNG → DPI 注入 → 内嵌）
  - 4 套预设中文模板（default/academic/report/strategy）
  - 全 YAML 配置 + JSON Schema 文件（Draft-07；运行时采用手工校验——校验项含路径/字号/Pandoc/mmdc 可用性）
  - LaTeX 数学公式（Pandoc 后端在指定版本和 fixture 上通过视觉验证 / Pure Python 实验性原型）
- **已知限制**: Pure Python 数学 OMML 有缺陷、无批量转换、无 GUI、Mermaid PNG 无原生 DPI、Pandoc 长表格多余空白页、自动/手工目录冲突
- **明确排除**: 不做 PDF/DOCX→Markdown 反向提取（那是 MinerU 等工具的领域）、不是通用文档转换器（专为 CJK 排版优化）

---

## GitNexus 架构洞察（机器验证 + 源码交叉核验）

> 以下数据来自 GitNexus MCP 实时查询（2026-07-22）与源码级交叉验证。**注意**：GitNexus 索引器对同文件内部方法调用（CALLS 边）的捕获不完整——以下影响面数据以 IMPORT/EXTENDS 关系为主（置信度高），内部调用链数据以源码 grep 为补充。

### 影响面排名（改动风险量化——基于 IMPORT/EXTENDS 边）

| 符号 | 风险 | d=1 直接依赖 | d=2 间接依赖 | fork 含义 |
|------|------|-------------|-------------|----------|
| **`DocxPipelineConfig`** | 🟡 MEDIUM | **8** (loader/validator/base/pure_python/pandoc_converter/mermaid_renderer/__init__/reference_files) | 5 (cli/pipeline/bench/__init__×2) | 改名/改类型 → 13 处断裂，**是项目中影响面最广的符号** |
| **`AbstractConverter`** | 🟡 MEDIUM | **6** (PandocConverter/PurePythonConverter/__init__/reference_files/pure_python.py/pandoc_converter.py) | 3 (cli/pipeline/bench) | 改 `convert()` 返回值或 `save()` 签名 → 双后端同时受影响 |
| **`MarkdownParser`** | 🟢 LOW | **3** (__init__/reference_files/pure_python.py) | 3 (cli/pipeline/bench) | 只被 Pure Python 后端使用，改动隔离性好 |
| **`PurePythonConverter`** | 🟢 LOW | **2** (__init__/reference_files) | 3 (cli/pipeline/bench) | 36 个方法——**外部 IMPORT 依赖少但内部方法调用密集**（见下方源码分析） |
| **`MermaidRenderer`** | 🟢 LOW | **2** (__init__/reference_files) | 2 (pure_python/pandoc_converter) | 17 个方法 / 677 行——**外部暴露面窄但 render 方法内部有完整的管道调用链** |

### 内部调用链（源码级验证，补充 GitNexus 索引盲区）

> GitNexus 对同文件内方法调用（`f.filePath == g.filePath` 的 CALLS 边）的捕获不完整——例如 `pure_python.py` 的 `_latex_to_omml → _parse_math_sequence → _parse_math_atom → _parse_math_scripts` 链未被索引。以下数据来自源码 grep 交叉验证。

```
PurePythonConverter（36 方法，1,213 行）:
  convert → _create_document → _build_content → _add_paragraph_or_image / _add_display_math
  _add_display_math / _append_text_with_math → _latex_to_omml
  _latex_to_omml → _parse_math_sequence → _parse_math_atom / _parse_math_scripts / _parse_math_command
  _parse_math_atom → _parse_math_scripts / _parse_required_math_group / _parse_nary
  _parse_nary → _make_math_argument / _make_math_run
  → 数学子系统内部耦合紧密，但通过 `_latex_to_omml` 单一入口对外暴露——替换数学引擎需完整回归测试

MermaidRenderer（17 方法，677 行）:
  render → _check_mmdc / _find_mermaid_blocks / _resolve_work_dir / _render_block / _replace_blocks
  _render_block → _build_mmdc_args / _invoke_mmdc / _inject_dpi / _validate_output / _resize_to_target
  _replace_blocks → _build_image_refs / _split_image
  → render 方法是管道调度器，内部方法形成线性管道——外部暴露面窄但内部依赖链完整
```

### 对 Fork 方案的关键校正

1. **`DocxPipelineConfig` 比 `AbstractConverter` 更危险**（GitNexus 验证）：Config 的 d=1 直接影响者（8 个）比 AbstractConverter（6 个）更多——因为它被 config/converters/renderers 三个子系统同时依赖。文献阅读容易误判 converter 是核心所以风险最高，数据纠正了这个假设。

2. **PurePythonConverter 的数学子系统不是"高度自包含"**（源码验证）：GitNexus 只捕获了 3 条同文件 CALLS 边（`flush_prose→process_prose`, `replace_*→new_placeholder`），但源码 grep 显示 `_latex_to_omml → _parse_math_sequence → _parse_math_atom → _parse_math_scripts → _parse_nary → _make_math_*` 是一条完整的 5 层调用链。**§3.1（LaTeX→OMML 完善）的隔离性被 GitNexus 不完整索引高估了——替换数学引擎需要完整的回归测试套件，不能仅凭"外部依赖少"断言低风险。**

3. **MermaidRenderer 外部暴露面窄但内部是有序管道**（源码验证）：GitNexus 显示 0 条同文件 CALLS，但源码中 `render → _render_block → _invoke_mmdc → _inject_dpi` 是明确的管道阶段。**§3.2（MathJax 渲染路径）可以安全地新增独立 renderer——MermaidRenderer 的线性管道结构支持并行替换而非修改现有代码。**

4. **CLI→pipeline→converters 调用链干净线性**（GitNexus 验证）：没有意外的跨层回环或循环依赖。新增 CLI 子命令（§6.3 watch mode、§7.1 Web UI）的风险在于契约兼容性（help 输出/退出码/stdout 契约）而非架构冲突——需补充 CLI 契约测试作为前置条件。

---

## 前置知识假设

| 层级 | 需要的知识/资源 | 涉及方向 |
|------|---------------|---------|
| 基础工具 | Git/fork/branch/PR、Python 3.10+、pip、Markdown/YAML | 全部 |
| Python 生态 | python-docx OOXML 对象模型、Click CLI、setuptools 打包 | §1/§2/§3/§11 |
| 排版/字体 | CJK 字体回退机制、OpenType 特性、Word/WPS/LibreOffice 差异、字体许可与分发 | §1（非中文语言）、§2.3 |
| 文档格式 | OOXML 规范（含 package/part/relationship）、LaTeX→OMML 转换、pandoc AST/filter | §3/§4/§5 |
| 前端/Web | Node.js、REST API 设计、浏览器沙箱、Office Add-in 部署模型 | §7/§8/§10 |
| 发布/生态 | PyPI 发布、GitHub Actions CI/CD、VS Code Extension API、Homebrew/Chocolatey 审核 | §9/§10/§11.4 |
| **新增** 测试环境 | Word/WPS/LibreOffice 多版本测试矩阵、CJK/日/韩字体安装与授权 | §1/§2/§5/§11.2 |

---

## 决策树（首次 fork 者从这里开始）

1. **你的目标是什么？**
   - 支持其他语言排版（日文/韩文/英文等） → 跳至 §1
   - 新增功能（批量/GUI/API） → 跳至 §2/§6/§7/§8
   - 修复或增强数学公式 → 跳至 §3.1
   - 做模板/样式生态 → 跳至 §5
   - 集成到 CI/CD 或自动化流程 → 跳至 §6
   - 扩展输出格式（LaTeX/Typst） → 跳至 §4
   - 发布为 VS Code 插件/在线服务 → 跳至 §9/§8.2
   - 改进工程质量（性能/测试/打包） → 跳至 §11

2. **你熟悉 python-docx / OOXML 吗？**
   - 是 → §2（Pure Python 后端增强）可以开工
   - 否 → 优先 §4（Pandoc 封装的新格式输出）、§5（模板）、§6（集成）——这些不需要深入 OOXML

3. **你的改动会影响 YAML 配置契约吗？**
   - 只加新字段 → 需定义未知字段策略 + 更新 JSON Schema + defaults.py + 4 个模板 + README 配置表
   - 改名/改类型 → **破坏性变更**，需引入 schema version + 弃用周期 + 迁移工具 + bump 主版本号
   - 不改配置 → 自由改动

---

## 一、多语言/区域排版支持

docx-pipeline 目前专为**简体中文**排版优化。扩展其他语言需要处理 `w:lang` 标记、Western/East Asia/Complex Script 字体槽分配、混合脚本 run、Unicode/OpenType 覆盖与字体回退、地区标点惯例、字体许可与 CI 安装，以及 Word/WPS/LibreOffice 与 Windows/macOS/Linux 的跨应用差异。

### 1.1 日文（ja-JP）

| 需要改动 | 说明 |
|---------|------|
| 新增 `templates/ja.yaml` | 日文默认字体：游ゴシック（Yu Gothic）+ 游明朝（Yu Mincho）；需处理字体许可与跨平台可用性 |
| 字体回退逻辑 | 日文优先使用 JIS 字体，fallback 到 MS PGothic/MS PMincho；需在 YAML 中支持 East Asia 字体槽 |
| OOXML 语言标记 | `w:lang` 需设置 `w:eastAsia="ja-JP"` 以触发正确的断行和标点行为 |
| 标点压缩 | 日文 `、。` 的缩进处理与中文不同 |
| 正文字号 | 日文公文标准 10.5pt，学术 12pt |
| 跨应用视觉验证 | Word/WPS/LibreOffice 对日文字体回退的差异需固定 fixture 测试 |

**工作量: 中-高**（新增 1 模板 + OOXML 语言标记逻辑 + 字体发现/许可文档 + 跨应用测试 fixture）

### 1.2 韩文（ko-KR）

| 需要改动 | 说明 |
|---------|------|
| 新增 `templates/ko.yaml` | 韩文默认字体：맑은 고딕（Malgun Gothic）+ 바탕（Batang）；字体许可与跨平台可用性 |
| OOXML 语言标记 | `w:eastAsia="ko-KR"` |
| 正文字号 | 韩文公文标准 10pt（与本项目默认 10.5pt 略有差异） |
| 行距 | 韩文标准 1.6-1.8 倍（比本项目默认 1.15 大） |

**工作量: 中-高**（原因同日文，含跨应用视觉验证）

### 1.3 英文/拉丁字母

当前项目**不推荐**用于纯英文文档——README 明确写"中文排版功能专门针对 CJK 文档设计，英文建议直接用 Pandoc"。但如果 fork 者想支持：

| 需要改动 | 说明 |
|---------|------|
| 新增 `templates/en.yaml` | 英文默认字体：Times New Roman / Calibri / Arial |
| 首行缩进 | 英文通常不需要；段落间距替代缩进 |
| 连字符 | 英文长单词断行需考虑 |
| 字号体系 | 11pt-12pt（非中文五号 10.5pt） |

**工作量: 低-中**（主要配置工作，但"要不要做"是定位问题——README 已明确推荐 Pandoc 用于英文）

### 1.4 正體中文（zh-Hant）

本项目已有正體中文 README 翻译，但模板层面未区分。正體中文建议拆分为 `zh-TW` 和 `zh-HK` locale 层（字体和用字存在地区差异）：

| 需要改动 | 说明 |
|---------|------|
| 新增 `templates/zh-TW.yaml` / `zh-HK.yaml` | zh-TW 偏好 標楷體（DFKai-SB）或 新細明體（PMingLiU）；注意这些字体不是所有平台都有——需支持可配置字体栈 |
| 字号 | 与简中相同（五号 10.5pt / 小四 12pt） |
| 标点 | 正體中文标点 `「」『』` vs 简体 `""''` |
| OOXML 语言标记 | `w:eastAsia="zh-TW"` 或 `"zh-HK"` |
| 缺字体行为 | 需定义字体缺失时的诊断信息（而非静默回退） |

**工作量: 低-中**（新增 1-2 个模板 + 语言标记 + 缺字体诊断 + 跨应用截图 fixture）

---

## 二、Pure Python 后端增强

### 2.1 代码语法高亮

- **当前**: Pure Python 后端代码块无高亮，Pandoc 后端有
- **方案**: 集成 Pygments → 按语言词法分析 → python-docx 逐 token 设置颜色
- **入口**: `docx_pipeline/converters/pure_python.py` 代码块渲染段落
- **前置**: 需要处理行号/背景色/字体（等宽 Consolas 或 Source Code Pro）
- **工作量: 中**（Pygments 集成 + 样式配置 + 测试）

### 2.2 脚注/尾注支持

- **当前**: Pure Python 后端不处理 Markdown 脚注语法 `[^id]`；Pandoc 后端通过 pandoc 扩展标记 `+footnotes` 原生支持
- **实际约束**: python-docx（当前依赖 `>=0.8.11`）**没有公共脚注/尾注 API**。实现需要直接操作 OOXML package 层——创建 Footnotes part、维护关系（`word/footnotes.xml`）、插入 footnoteReference 和 footnote 元素、管理编号策略、处理 content type 和保存/读取兼容
- **工作量: 高**（不是调用一个现成方法——是 OOXML package/part/relationship 层面的扩展开发 + Word/WPS/LibreOffice 视觉验证）
- **替代方案**: 如果 pandoc 可用，委托给 Pandoc 后端——pandoc 已有成熟的脚注支持

### 2.3 CJK 禁则处理（kinsoku）

- **当前**: 未处理行首行尾禁则（如 `。` 不能出现在行首）
- **实际约束**: 转换器在生成 OOXML 时**无法知道 Word 的最终分页、字体回退和行宽计算结果**——禁则的最终判断发生在渲染引擎中，不是在 XML 生成阶段
- **可行目标**（降级后）: 设置正确的 OOXML 语言标记（`w:lang`）、kinsoku 兼容属性，以及必要的字符级约束，让 Word 的排版引擎自行处理禁则
- **不可行目标**: 在转换阶段"检测标点最终位置并插入软换行"——这要求预测 Word 的分页结果
- **工作量: 中**（研究 OOXML kinsoku 属性 + 跨应用视觉验证，不承诺完美禁则）

### 2.4 竖排/纵书支持

- **场景**: 日文/中文古籍/特殊排版
- **方案**: 利用 Word 的 `textDirection` 属性
- **工作量: 中-高**（小众需求，但 python-docx 原生不支持，需手写 OOXML）

---

## 三、数学公式增强

### 3.1 Pure Python LaTeX→OMML 完善（v1.2.0 路线）

- **当前**: 1,213 行 PurePythonConverter 中约一半为实验性 LaTeX→OMML 原型（`_latex_to_omml` + `_parse_math_*` 系列 10 个方法），**渲染有已知缺陷**（分式/根号/上下标/大型运算符）
- **v1.2.0 计划路线**: `latex2mathml` → MathML → OMML 桥接（替代直接 LaTeX→OMML）
- **内部耦合**（源码验证）: 数学方法不是独立孤岛——`_latex_to_omml → _parse_math_sequence → _parse_math_atom → _parse_math_scripts → _parse_nary → _make_math_*` 是一条完整的 5 层调用链。**替换数学引擎需要完整的回归测试套件 + 接口隔离层，不能仅凭"外部 IMPORT 依赖少"断言低风险。**
- **关键挑战**:
  - `latex2mathml` 本身覆盖率有限（LaTeX 数学方言极多）
  - MathML→OMML 转换需要 XSLT 或手写映射
  - Pandoc 已有成熟 LaTeX→OMML 路径——**评估"是否值得"很重要**
- **工作量: 高**（需深入三种格式规范 + 大量边界测试 + 完整回归测试套件）
- **务实建议**: 先确定目标用户场景——如果用户环境可以安装 pandoc，Pure Python 数学是冗余工程；如果目标是无网络/无安装权限环境，才有独立价值

### 3.2 MathJax/KaTeX 渲染路径

- **方案**: 在转换前先用 MathJax/KaTeX 将公式渲染为 SVG/PNG，再嵌入 DOCX（类似 Mermaid 处理方式）
- **优势**: 绕过 OMML，公式渲染质量等同于浏览器
- **劣势**: 失去 Word 原生公式可编辑性；图片缩放与对齐问题；需要 Node 或浏览器运行时；需处理行内公式的基线对齐、DPI、缓存、超时、alt text 和错误清理
- **工作量: 中-高**（新增 MathRenderer + 渲染器运行时管理 + 缓存/超时/错误策略 + 行内/块级/长公式视觉验证）

### 3.3 Pandoc 数学 filter 增强

- **当前**: Pandoc 后端传 `tex_math_dollars` + `tex_math_single_backslash`，依赖 Pandoc 内置转换
- **扩展**: 自定义 Pandoc Lua/Python filter 处理 Pandoc 不支持的 LaTeX 宏包（如 `\si`、`\chemfig`）
- **工作量: 中**（Lua filter 编写 + 非标准宏包的 fallback 策略）

---

## 四、扩展输出格式

> **范围决策提示**：以下方向将项目从"Markdown → DOCX"扩展为多格式输出。这与 README 的"只做 Markdown → DOCX"定位存在张力。`AbstractConverter.convert()` 返回 `Document` 对象、`save()` 和 `paths.docx_output` 围绕 DOCX 文件设计。在实施以下方向之前，建议先设计 `Artifact/OutputFormat` 抽象层、输出路径映射、后端注册表和 CLI/API 契约——否则每个新格式会累积不对称的技术债。fork 者可选择"先做抽象层"或"只挑一个最需要的格式深度集成"。

### 4.1 WeasyPrint/Playwright PDF 输出

- **定位扩张**: 从"仅 DOCX"扩展到"含 PDF"
- **路线**: Markdown → HTML（模板渲染）→ WeasyPrint PDF
- **优势**: PDF 输出独立于 Microsoft Word，适合自动化部署
- **风险**: 定位蔓延——README 明确写"解决 Markdown→DOCX"。且 PDF 有独立的字体/分页/元数据/可访问性需求
- **工作量: 高**（新输出抽象层 + 新模板体系 + 新配置段 + CI 字体依赖 + PDF 可访问性验证）

### 4.2 Markdown → LaTeX 后端

- **路线**: Pandoc `--to latex` 封装
- **适用**: 学术用户需要论文 LaTeX 源码
- **注意**: python-docx **不提供**从文档对象导出 LaTeX 的 API——这个方向只能走 Pandoc writer 路径
- **工作量: 低-中**（Pandoc 封装 + 配置集成 + LaTeX 模板 + 测试 fixture）

### 4.3 Typst 后端

- **场景**: Typst 是 LaTeX 的现代替代品，2024 年后在学术界增长迅速
- **路线**: Markdown → Typst（Pandoc 3.1+ 支持 `--to typst`） → 配置封装
- **工作量: 低-中**（Pandoc 封装 + 模板设计 + 新的 `output_format` 配置）

---

## 五、批量转换

> v1.2 新增。README 将"无批量转换"列为已知限制，这是现有 CLI 最直接且需求量最大的 fork 方向。

### 5.1 批量转换语义

- **输入**: 目录递归（`--batch ./chapters/`）或 manifest 文件（`--manifest files.yaml`）
- **输出映射**: `./chapters/intro.md → ./output/intro.docx`（保持目录结构）或统一输出目录
- **失败策略**: `--fail-fast`（首个失败即停止）vs `--continue-on-error`（收集所有错误后汇总报告）
- **并发**: ThreadPoolExecutor 并行转换（注意 python-docx 的线程安全性 + mmdc 子进程的并发限制）
- **退出码**: 0 = 全部成功；1 = 部分/全部失败；汇总报告含每个文件的成功/失败/耗时

### 5.2 配置处理

- **单配置模式**: 所有文件共用同一个 `project.yaml`（默认）
- **逐文件覆盖**: manifest 中每个条目可覆盖 `md_source`/`docx_output`
- **缓存/幂等**: 基于 md5 的文件变更检测 → 只重新转换已修改的文件

### 5.3 备份与错误恢复

- 批量模式下 `_rotate_backups` 的行为：全局 max_backups 还是每文件独立？
- 临时文件隔离：批量转换的中间产物放在统一的 work_dir 子目录

**工作量: 中**（CLI 新增 `--batch` / `--manifest` + 错误汇总 + 并发控制 + 测试 fixture）

---

## 六、模板生态系统

### 6.1 第三方模板加载

- **当前**: 4 个内置模板。用户已可通过配置文件（`--config project.yaml`）加载自定义 YAML——真正缺少的是可安装、可发现、可版本化的模板包生态
- **方案**: 支持模板包目录结构（含 manifest、schema version、reference.docx、资源/字体/filters、最低版本、许可），CLI 新增别名或 `--template` 指向模板包
- **注意**: 与现有 `--config/-c` 入口的契约需对齐——不能引入互斥的入口模式
- **工作量: 中**（模板包规范 + CLI 兼容别名 + `loader.py` 改动 + 模板编写指南）

### 6.2 更多预设模板

| 模板 | 适用场景 | 是否仅 YAML 可表达 | 关键差异 |
|------|---------|-------------------|---------|
| `thesis` | 硕博论文 | **否**——需 OOXML section 奇偶页、图表 caption 编号器 | 双面打印、奇偶页页眉、图表索引、盲审格式 |
| `proposal` | 项目申请书/基金申请 | **部分**——GB/T 7714 引用需 filter 支持 | 紧凑排版、经费表格、参考文献格式 |
| `newsletter` | 内部通讯/周报 | **否**——需多栏 OOXML section | 多栏布局、彩色分区、信息图嵌入 |
| `slides-notes` | 演讲备注/讲义 | 是（landscape page + 大字号） | 宽页（16:9）、简化标题层级 |
| `patent` | 专利申请 | **否**——需段落编号器 | 严格页边距、权利要求格式 |

**工作量: 每个模板低-高**（取决于"仅 YAML"还是"需要 parser/OOXML 扩展"——slides-notes 低，thesis/newsletter/patent 高）

### 6.3 样式在线预览/对比工具

- **方案**: 一个 Web 页面，加载多个 YAML 模板并排渲染预览
- **工作量: 中-高**（前端开发，非仓库核心）

---

## 七、集成与自动化

### 7.1 GitHub Actions 官方 Action

- **方案**: 封装为独立 Action 仓库，在 CI 中一键转换
- **实现**: `action.yml` + Dockerfile（需固定 pandoc/Node/mmdc/CJK 字体版本 + 容器体积控制 + 权限最小化）
- **限制**: 容器化意味着 Linux-only（无 Windows/macOS runner 上的本地字体环境）；需明确 outputs、失败日志和 artifact 上传路径
- **工作量: 中**（独立仓库 + Docker 镜像 + 版本固定 + CI 矩阵测试 + SBOM/签名 + 真实仓库示例）

### 7.2 pre-commit hook

- **方案**: `.pre-commit-hooks.yaml` 定义 docx-check hook
- **用例**: 每次 commit 前将 Markdown 真实转换到临时目录（**不是** `--dry-run`——当前 dry-run 只检查配置/路径/依赖，不解析 Markdown，不执行转换，不能发现语法/图片/Mermaid/Pandoc 错误）
- **考虑**: 转换耗时可能不适合每次 commit——建议作为 pre-push hook 或手动触发
- **工作量: 低-中**（临时目录隔离 + 退出码策略 + 外部工具不可用时的 grace 处理）

### 7.3 Watch mode（文件监听自动转换）

- **方案**: `docx-pipeline watch --config project.yaml`
- **实现**: `watchfiles` 库 + debounce + 输出目录隔离（避免输出文件变更触发自循环）+ 并发取消 + Windows/macOS 文件事件差异
- **工作量: 中**（事件去重/队列/取消语义 + 首次运行状态机 + 跨平台测试）

---

## 八、交互界面

### 8.1 简易 Web UI（Gradio/Streamlit）

- **方案**: `docx-pipeline ui` 命令启动本地 Web 界面
- **功能**: 上传 Markdown → 选择模板 → 下载 DOCX（浏览器不能原生预览 DOCX——需决定预览方案: HTML 渲染/截图/仅下载）
- **考虑**: 上传大小/类型限制、临时文件隔离和清理、错误展示、并发、超时、本地服务暴露策略（仅 localhost？局域网？）
- **工作量: 中**（demo 级低，可部署级中）

### 8.2 TUI（终端交互界面）

- **方案**: `docx-pipeline tui` 命令
- **技术**: Textual 或 Rich 的 live display
- **功能**: 模板选择、配置编辑、转换进度条
- **工作量: 中**

### 8.3 桌面 GUI（Electron/Tauri）

- **场景**: 非技术用户（行政/文书/学生）
- **方案**: 打包为独立桌面应用
- **工作量: 高**（基本是新项目，本仓库只提供 Python 后端 API）

---

## 九、API / Library Mode

### 9.1 Python SDK 改善

- **当前**: 可通过 `from docx_pipeline import ...` 编程调用，但 API 没有正式文档化
- **方案**: 稳定公共 API (`convert_markdown()`, `convert_markdown_to_docx()`) + 类型 stub + Sphinx 文档
- **工作量: 中**

### 9.2 REST API 服务

- **方案**: FastAPI 包装 → Docker 镜像 → 可作为微服务部署
- **工作量: 中-高**（新目录 `api/` + Dockerfile + 速率限制/安全/认证/并发模型）

---

## 十、VS Code 扩展

- **方案**: VS Code 插件——右键 Markdown 文件 → "Convert to DOCX"
- **实现**: 调用本地安装的 `docx-pipeline` CLI，读取 `.vscode/docx-pipeline.yaml` 项目配置
- **前置**: 需要发布到 VS Code Marketplace（独立于本仓库）
- **工作量: 中**（TypeScript extension + 本仓库增加配置发现 + CLI 契约测试）

---

## 十一、Word 插件（Office Add-in）

- **方案**: Word 任务窗格插件，直接在 Word 中导入并渲染 Markdown
- **关键前提**: Office Add-in 不能直接在沙箱中启动本地 Python CLI。需先选定部署模型（三选一）:
  - **Web-only**: 纯 JS Markdown 解析，不依赖本地 Python
  - **本地 helper**: 用户安装本地服务 → 插件通过 localhost 通信（需处理安装器、loopback/CORS、端口占用、证书）
  - **企业集中服务**: 服务端部署 → 企业审批/数据隐私/离线运行策略
- **工作量: 高**（跨技术栈 + 部署模型设计 + Office 版本兼容 + 商店审核，基本是新项目）

---

## 十二、工程改进

### 12.1 性能优化

| 优化项 | 当前 | 目标 | 注意 |
|--------|------|------|------|
| 大文件（>10K 行） | 全量加载到内存 | 先 benchmark 分解 Markdown/图片/Mermaid/Pandoc/OOXML 的耗时与峰值内存 | python-docx 最终要在内存中持有完整 DOM——流式解析的收益有限 |
| Mermaid 渲染 | 串行单图渲染 | 并行渲染（ThreadPoolExecutor）+ 并发上限控制 | |
| Pandoc 调用 | 同步 subprocess.run | asyncio 不能降低单次 Pandoc 耗时——收益在取消/并发调度/服务集成 | 先明确性能基线和目标再选择方案 |

**工作量: 中-高**（需先建立 benchmark baseline，再逐项优化）

### 12.2 测试扩展

- **当前**: 52 tests，覆盖基本功能。缺失：
  - 边界/错误路径测试（损坏 YAML、缺失字体、Pandoc crash、mmdc 超时）
  - 视觉回归测试（固定 fixture DOCX → 截图对比——跨平台和 Word 版本差异大）
  - 性能 benchmark CI（检测回归——注意 GitHub Actions VM 的 CPU 与本地差距巨大）
  - 跨平台兼容测试（pandoc 版本差异、字体可用性矩阵）
  - CLI 契约测试（golden help 输出、退出码、stdout/stderr 快照）
- **工作量: 中**（持续投入，非一次性）

### 12.3 可观测性

- **方案**: 结构化日志（`structlog`）、转换耗时追踪、渲染失败率统计
- **工作量: 低-中**

### 12.4 打包改进

- **当前**: `pip install git+...` + `pyproject.toml` 包元数据
- **扩展**:
  - `pipx install docx-pipeline`（独立环境隔离——可能无需代码改动，先验证 `console_scripts` 在 pipx 下的可用性）
  - Homebrew formula（需独立仓库/公式、校验和、审核、自动更新、维护者 + pandoc/mmdc 外部依赖策略）
  - Chocolatey package（同上，另需 Windows 特定测试）
- **工作量: 低-高**（pipx 低，Homebrew/Chocolatey 高——不是"每个平台主要是打包元数据"）

---

## 十三、文档语义与引用

> v1.2 新增。当前方案在模板中提到 GB/T 7714 和图表编号，但没有完整的引用和交叉引用方向。

### 13.1 参考文献管理

- **当前**: 无 CSL/GB/T 7714 支持；Pandoc 可通过 `--citeproc` 处理，但 Pure Python 后端无此能力
- **方向**: 定义 Markdown 扩展语法或 Pandoc AST 输入 → CSL 处理器 → 编号与引用渲染
- **决策点**: 是作为核心转换器功能（双后端都支持）还是纯 Pandoc filter（仅一边）？

### 13.2 图表编号与交叉引用

- **当前**: 无自动图表 caption 编号、无交叉引用（"见图 X"不会自动更新）
- **方向**: 中间表示层增加语义标注 → 编号器 → DOCX 书签/超链接

### 13.3 可访问性（Accessibility）

- **当前**: 未处理图片 alt text、标题层级语义、表格表头、语言标记、公式替代文本、颜色对比
- **方向**: 在中间表示或渲染接口中保留 alt/语言/标题语义 → 输出时映射到 DOCX 无障碍属性
- **标准**: DOCX 辅助功能检查器、PDF/UA 基础要求

**综合工作量: 高**（需要中间表示层设计 + 跨后端一致性——建议作为长期架构演进方向，非单次 fork 任务）

---

## 十四、可插拔扩展架构

> v1.2 新增。当前功能累积方式是在 `PurePythonConverter`/CLI 中不断加条件分支——继续这样会导致后端不对称和测试矩阵爆炸。

### 14.1 建议的架构演进

```
预处理器链 → 中间表示（IR）→ 渲染器注册表 → 后处理器链 → 输出
   (filters)    (AST/nodes)   (registry)    (passes)    (artifact)
```

- **预处理器**: Pandoc filters、Mermaid 检测、变量替换
- **中间表示**: 统一的文档 AST（而非 Markdown 字符串直传）
- **渲染器注册表**: 模板/语言/数学/图表通过注册机制接入，而非硬编码 if-else
- **后处理器**: DPI 注入、字体回退、TOC 插入

**工作量: 高**（架构级重构——建议在累积 2-3 个具体 fork 需求后，用实际用例驱动抽象设计，而非提前过度工程化）

---

## 十五、反模式（不要做的事）

> 基于本仓库实际设计决策和踩过的坑。

1. **不要把 DOCX Pipeline 扩展为通用文档转换器**——定位是"Markdown → 中文 DOCX"，方向是垂直深入而非水平扩展。
2. **不要尝试替代 Pandoc**——Pandoc 有 15 年积累的 Markdown 解析和格式转换能力。Pure Python 后端是"零外部转换器"场景的补充，不是替代品。
3. **不要改动 `DocxPipelineConfig` 字段名或类型**——GitNexus 确认 8 个直接依赖者。改名 = 断裂所有 `project.yaml`。如需演进，引入 schema version + 字段弃用周期 + 迁移工具。
4. **不要把实验性功能当稳定特性宣传**——Pure Python 数学 OMML 原型有已知缺陷，README 已诚实标注。如果完善了，更新标注；不要让用户在不稳定地基上建立依赖。
5. **不要在模板中硬编码系统路径或绝对字体名**——YAML 模板是用户可编辑的契约，应保持环境无关。
6. **不要删除失败的审查记录**——`_review/` 目录记录了这个项目的方法论验证过程（5 轮 GPT-5.6-Sol 审查记录 + GitNexus 分析），删除后无法证明"经独立审查"的声明。注意 `_review/`（工作审查材料）与 `_reviews/`（回顾记录）的目录职责区分。
7. **不要在 `MermaidRenderer` 中跳过 DPI 注入**——mmdc 输出的 PNG 不带 DPI 元数据，跳过注入会导致 Word 中图片约 3 倍拉伸。这是 2026-06 实际踩过的坑。
8. **不要自动发布未目视验证的渲染效果变更**——DOCX 的视觉效果（字体回退、表格宽度、分页、图片比例）不能用自动化测试完全覆盖。改动 `pure_python.py` 或 `pandoc_converter.py` 的渲染逻辑后，必须在 Word/WPS/LibreOffice 中打开输出文件确认——并固定目标应用版本和字体环境。
9. **不要把一次查询快照写成实时事实**（新增）——GitNexus 统计数字、性能数字、文件行数和 PyPI 状态都有时效性。标注快照日期、工具版本、命令和已知边界；将事实、观察、推断和建议分栏，后续重跑时只更新对应快照。
10. **新增 CLI 子命令前先建立 CLI 契约测试**（新增）——golden help 输出、退出码、stdout/stderr 快照。新命令即使不改现有函数也可能破坏用户脚本的解析逻辑。

---

## 按实现门槛与外部依赖排序

> 排序逻辑: 先按"可直接开工"分组，组内按改动量排序。改动量已根据 GPT-5.6-Sol 审查意见上调了低估项。**本表为优先级子集——未列全的方向（如 §2.4 竖排、§8.2 TUI、§8.3 桌面 GUI、§6.3 样式预览、§14 扩展架构）在正文中均有描述，因工作量高或需求小众未纳入"可直接开工"清单。**

### 可直接开工（无需外部资源或仅需标准工具链）

| 方向 | 改动量 | 入口文件 | 独立价值 |
|------|--------|---------|---------|
| 正體中文模板（§1.4） | 低-中 | `docx_pipeline/data/templates/` | 中 |
| Markdown→LaTeX 后端（§4.2） | 低-中 | Pandoc 封装 | 中 |
| Typst 后端（§4.3） | 低-中 | Pandoc 封装 | 中 |
| Watch mode（§7.3） | 中 | `cli.py` + `watchfiles` | 中 |
| 可观测性（§12.3） | 低-中 | 分散 | 中 |
| 英文模板（§1.3） | 低-中 | `docx_pipeline/data/templates/` | 中 |
| 模板包生态（§6.1） | 中 | `cli.py` + `config/loader.py` | 高 |
| 新增预设模板·纯 YAML 型（§6.2 中 slides-notes） | 低-中 | `docx_pipeline/data/templates/` | 中 |
| 批量转换（§5） | 中 | `cli.py` + `pipeline.py` | **高** |
| Python SDK 文档化（§9.1） | 中 | Sphinx/mkdocs | 中 |
| 测试扩展·错误路径（§12.2） | 中 | `tests/` | 高 |
| 测试扩展·CLI 契约（§12.2） | 中 | `tests/` | 高 |
| pre-commit hook（§7.2） | 低-中 | 新建 `.pre-commit-hooks.yaml` | 中 |

### 需要外部依赖或工具链

| 方向 | 改动量 | 外部依赖 | 阻塞项 |
|------|--------|---------|--------|
| GitHub Actions Action（§7.1） | 中 | Docker + pandoc/Node/CJK 字体 | 容器化 → Linux-only 限制 |
| MathJax/KaTeX 渲染（§3.2） | 中-高 | Node.js + MathJax/KaTeX | 渲染器运行时管理 + 基线对齐 |
| 日文模板（§1.1） | 中-高 | 日文字体 + 日语排版知识 | 字体许可 + 跨应用验证 |
| 韩文模板（§1.2） | 中-高 | 韩文字体 + 韩语排版知识 | 字体许可 + 跨应用验证 |
| 代码高亮（§2.1） | 中 | Pygments | python-docx token 颜色 API |
| 新增预设模板·OOXML 型（§6.2 中 thesis/newsletter/patent） | 中-高 | OOXML section/caption/编号器 | 需扩展 converter 而非仅 YAML |
| REST API（§9.2） | 中-高 | FastAPI + Docker | 速率限制/安全/并发模型 |
| 简易 Web UI（§8.1） | 中 | Gradio/Streamlit | 预览方案 + 安全边界 |
| Pandoc 数学 filter（§3.3） | 中 | Pandoc Lua filter 知识 | 特定宏包需求 |
| VS Code 扩展（§10） | 中 | TypeScript + VS Code API | 需独立仓库 |

### 需要架构级改动

| 方向 | 改动量 | 核心挑战 |
|------|--------|---------|
| 脚注支持（§2.2） | 高 | OOXML package/part/relationship 扩展 + 跨应用验证 |
| Pure Python LaTeX→OMML（§3.1） | 高 | 三种格式规范 + 边界测试 + 完整回归套件 + **"是否值得"评估** |
| CJK 禁则处理（§2.3） | 中-高 | 研究 OOXML kinsoku 属性——不承诺完美禁则 |
| WeasyPrint PDF 输出（§4.1） | 高 | 新输出抽象层 + 定位蔓延风险 |
| 文档语义与引用（§13） | 高 | 中间表示层设计 + CSL 集成 + 可访问性 |
| 大文件流式解析（§12.1） | 高 | 需先 benchmark 定位瓶颈——流式对 python-docx DOM 的收益有限 |
| Word 插件（§11） | 高 | 跨技术栈 + 部署模型设计，基本是新项目 |
| 可插拔扩展架构（§14） | 高 | 架构级重构——建议用实际用例驱动，非提前抽象 |

---

## 关键约束与注意点

### 配置契约稳定性

1. **`DocxPipelineConfig` 字段名不可变**（GitNexus 验证——8 个直接依赖者，影响面最广）。如需演进，引入 schema version + 字段弃用周期（旧名保留一个版本 + 警告）+ 迁移工具 + 未知字段策略。
2. **4 个内置模板 YAML 与 Schema 必须同步**：改了 `schema.py`（dataclass）→ 必须更新 `docx_pipeline/data/schemas/project_config.schema.json` → 必须更新 4 个 `docx_pipeline/data/templates/*.yaml` 模板 → 必须更新 README 配置表。
3. **环境变量覆盖前缀**：`DOCX_PIPELINE__*` 双下划线层级分隔。改动配置层级需同步更新 `loader.py` 中的 env var 解析逻辑。

### 后端对称性

4. **Pure Python 与 Pandoc 后端不是功能等价的**：Pure Python 无代码高亮、数学公式有缺陷。新增功能时需明确"双后端都支持？仅一边？"
5. **Auto 模式决策逻辑**：`pandoc.enabled=true` AND `pandoc` 在 PATH → Pandoc；否则 Pure Python。改这个逻辑会影响用户体验。
6. **`AbstractConverter` 接口不可变**（GitNexus 验证——6 个直接依赖者，含两个子类）。改 `convert()` 返回值或 `save()` 签名 → 双后端同时断裂。如果扩展输出格式（§4），需先设计不依赖 `Document` 返回值的输出抽象。

### 视觉正确性

7. **自动化测试覆盖不到渲染效果**：字体回退、表格宽度、分页位置、图片缩放——这些只能目视验证。改动渲染逻辑后必须在 Word/WPS/LibreOffice 中打开输出文件确认，并固定目标应用版本和字体环境。
8. **Mermaid PNG DPI 注入不可跳过**（反模式 #7）。

### 定位边界

9. **核心定位是 Markdown → DOCX**，扩展输出格式（§4）需先设计输出抽象层，避免定位蔓延。
10. **CJK 排版优化是核心差异化**——如果变成通用文档转换器，与 Pandoc 正面竞争没有优势。

---

## 关联文件

### 核心源码
- `docx_pipeline/cli.py` — Click CLI 入口（init/convert/validate/info）
- `docx_pipeline/pipeline.py` — 转换流水线编排
- `docx_pipeline/config/schema.py` — `DocxPipelineConfig` dataclass 定义（**配置契约核心**）
- `docx_pipeline/config/defaults.py` — 4 个预设模板默认值
- `docx_pipeline/config/loader.py` — YAML 加载 + 环境变量覆盖
- `docx_pipeline/config/validator.py` — 手工配置校验（路径/字号/依赖探测；JSON Schema 文件不参与运行时校验）
- `docx_pipeline/converters/base.py` — `AbstractConverter` 基类（含备份轮换）
- `docx_pipeline/converters/markdown_parser.py` — 自研逐行状态机 MD 解析器
- `docx_pipeline/converters/pure_python.py` — Pure Python 转换器（1,213 行，含实验性 LaTeX→OMML）
- `docx_pipeline/converters/pandoc_converter.py` — Pandoc 转换器
- `docx_pipeline/converters/shared.py` — 共享常量与工具函数
- `docx_pipeline/renderers/mermaid_renderer.py` — Mermaid 预渲染器（677 行，含 DPI 注入 + 图片切分）
- `docx_pipeline/data/math_symbols.py` — LaTeX 数学符号表（81 符号，`dev/generate_math_symbols.py` 可复现生成）
- `docx_pipeline/utils/encoding.py` — Windows UTF-8 环境设置
- `docx_pipeline/utils/paths.py` — 路径规范化

### 模板与 Schema
- `docx_pipeline/data/templates/default.yaml` — 通用中文文档
- `docx_pipeline/data/templates/academic.yaml` — 学术论文
- `docx_pipeline/data/templates/report.yaml` — 技术报告（Pandoc + Mermaid 启用）
- `docx_pipeline/data/templates/strategy.yaml` — 量化策略
- `docx_pipeline/data/schemas/project_config.schema.json` — JSON Schema (Draft-07；契约参考文件，运行时未接入 jsonschema 库)

### 开发工具
- `dev/generate_math_symbols.py` — LaTeX 符号表生成器
- `dev/bench.py` — 双后端性能 benchmark

### 测试
- `tests/test_basic.py` — 基础测试（配置/解析/CLI/备份）
- `tests/test_smoke.py` — 烟雾测试（完整转换管线）
- `tests/test_math.py` — 数学公式测试（Pandoc OMML 验证）
- `tests/test_pure_python_math.py` — Pure Python 数学测试
- `tests/test_mermaid_renderer.py` — Mermaid 渲染器测试
- `tests/test_pandoc_converter.py` — Pandoc 转换器测试
- `tests/test_cli_contract.py` — CLI 契约测试

### 项目治理
- `CLAUDE.md` — AI 协作指南（Agent 边界 + 架构约束 + GitNexus 块）
- `CONTRIBUTING.md` — 贡献指南（含 GPT-5.6-Sol 代码来源条款）
- `CHANGELOG.md` — 版本历史
- `pyproject.toml` — 打包配置（元数据版本 1.1.0）
- `reference_files.md` — 文件索引
- `project_status.md` — 项目状态（含 PyPI 待定项）
- `_review/` — 5 轮 GPT-5.6-Sol 审查记录 + GitNexus 分析 + Fork 方案审查（本次）
- `_reviews/` — 回顾记录

### 外部参考（不在本仓库内）

- [MinerU](https://github.com/opendatalab/MinerU) — PDF/DOCX→Markdown 提取工具，与本项目方向相反、天然互补
- [Pandoc](https://pandoc.org/) — 通用文档转换器，本项目 Pandoc 后端的基础设施
- [python-docx](https://python-docx.readthedocs.io/) — Pure Python 后端的底层库（注意：无公共脚注 API）
- `../项目改进计划/docx-pipeline/` — 改进计划 + MinerU 对比分析 + 来源备忘录（相对路径基准为仓库根目录）
