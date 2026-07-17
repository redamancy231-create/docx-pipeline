"""DOCX Pipeline CLI — ``docx-pipeline`` top-level command group.

Phase 1 implements four subcommands: **init**, **convert**, **validate**,
**info**.  Three further subcommands are reserved for later phases
(``template``, ``serve``, ``watch``).

Windows notes
-------------
* ``setup_windows_encoding()`` is called at import time so that stdout/stderr
  use UTF-8 even when the console codepage is not 65001.
* Every ``print()`` is followed by ``sys.stdout.flush()`` to avoid garbled
  output on Git Bash / mintty.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

import click
import yaml

from docx_pipeline import __version__
from docx_pipeline.utils import setup_windows_encoding, normalize_path

# ---------------------------------------------------------------------------
# Windows encoding – must happen before any user-visible output
# ---------------------------------------------------------------------------
setup_windows_encoding()


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------
class ConfigError(Exception):
    """Raised when the project configuration is invalid or missing."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _flush_print(*args, **kwargs) -> None:
    """Print and immediately flush stdout (critical on Windows/Git Bash)."""
    print(*args, **kwargs)
    sys.stdout.flush()


_TEMPLATE_CHOICES = ["default", "academic", "report", "strategy"]


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------
@click.group(name="docx-pipeline")
@click.version_option(
    version=__version__,
    prog_name="docx-pipeline",
    message="docx-pipeline %(version)s",
)
def cli() -> None:
    """DOCX Pipeline — 从 Markdown + YAML 配置生成 DOCX 文档。

    Phase 2: Pure Python 转换器 + Pandoc 转换器 + Mermaid 渲染，CLI 脚手架，配置校验。
    """


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------
@cli.command("init")
@click.option(
    "-d", "--project-dir",
    required=True,
    type=click.Path(file_okay=False, writable=True),
    help="项目根目录 (必需)。",
)
@click.option(
    "-n", "--name",
    default=None,
    help="项目名称 (默认使用目录名)。",
)
@click.option(
    "-t", "--template",
    "template_name",
    type=click.Choice(_TEMPLATE_CHOICES),
    default="default",
    show_default=True,
    help="文档模板 (决定默认字体/页边距/样式等)。",
)
@click.option(
    "--md-file",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="入口 Markdown 文件路径。",
)
@click.option(
    "-f", "--force",
    is_flag=True,
    default=False,
    help="覆盖已存在的 project.yaml。",
)
def init_cmd(
    project_dir: str,
    name: Optional[str],
    template_name: str,
    md_file: Optional[str],
    force: bool,
) -> None:
    """初始化项目，生成 project.yaml 配置文件。

    根据所选模板展开全部默认值后写入 YAML，确保配置文件自包含、
    后续 convert/validate 无需再指定 --template。
    """
    project_dir = normalize_path(project_dir)
    config_path = os.path.join(project_dir, "project.yaml")

    if os.path.exists(config_path) and not force:
        raise click.ClickException(
            f"配置文件已存在: {config_path}\n"
            f"使用 --force 覆盖，或手动删除后重试。"
        )

    if name is None:
        name = os.path.basename(project_dir.rstrip("/").rstrip("\\")) or "untitled"

    # --- Load template defaults, then override with user args ---
    try:
        from docx_pipeline.config.defaults import get_template
    except ImportError as exc:
        raise click.ClickException(
            f"无法加载模板系统: {exc}\n"
            "请确认 docx_pipeline 已正确安装。"
        ) from exc

    data = get_template(template_name)

    # project section
    data.setdefault("project", {})["name"] = name
    data["project"]["root"] = project_dir

    # paths section
    paths = data.setdefault("paths", {})
    if md_file:
        paths["md_source"] = normalize_path(md_file)
        docx_name = os.path.splitext(os.path.basename(md_file))[0] + ".docx"
    else:
        docx_name = f"{name}.docx"
    paths["docx_output"] = os.path.join(project_dir, "output", docx_name).replace("\\", "/")

    # Record provenance
    data.setdefault("version", {})["number"] = __version__
    data["_pipeline"] = {
        "template": template_name,
        "generated_by": f"docx-pipeline {__version__}",
    }

    # --- Write ---
    os.makedirs(project_dir, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as fh:
        yaml.dump(
            data,
            fh,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )

    _flush_print(f"✓ 项目初始化完成: {normalize_path(config_path)}")
    _flush_print(f"  名称       : {name}")
    _flush_print(f"  模板       : {template_name}")
    _flush_print(f"  项目目录   : {project_dir}")
    if md_file:
        _flush_print(f"  Markdown   : {normalize_path(md_file)}")


# ---------------------------------------------------------------------------
# Helper functions for convert command
# ---------------------------------------------------------------------------

def _check_pandoc_available() -> tuple:
    """Check if pandoc is on PATH. Returns (available: bool, path: str|None)."""
    import shutil
    path = shutil.which("pandoc")
    return (path is not None, path)


def _detect_mermaid_blocks(md_path: str) -> bool:
    """Scan the markdown file for ```mermaid fences. Returns True if found.

    Regex is kept consistent with ``MermaidRenderer._MERMAID_RE`` opening
    fence pattern: line start, 0–3 spaces indentation, `` ```mermaid ``.
    """
    import re
    try:
        with open(md_path, "r", encoding="utf-8") as fh:
            content = fh.read()
        return bool(re.search(r'(?m)^ {0,3}```mermaid', content))
    except Exception:
        return False


def _check_mmdc_available(config) -> tuple:
    """Check if mmdc is available per config. Returns (available: bool, path: str|None)."""
    import os
    import shutil
    mmdc = config.mermaid.render.mmdc_path or "mmdc"
    if os.path.isabs(mmdc):
        path = mmdc if os.path.isfile(mmdc) else shutil.which(mmdc)
    else:
        path = shutil.which(mmdc)
    return (path is not None, path)


# ---------------------------------------------------------------------------
# convert
# ---------------------------------------------------------------------------
@cli.command("convert")
@click.option(
    "-c", "--config",
    "config_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="project.yaml 配置文件路径 (必需)。",
)
@click.option(
    "-m", "--method",
    type=click.Choice(["pure", "pandoc", "auto"]),
    default="auto",
    show_default=True,
    help="转换引擎。pure=Python原生, pandoc=Pandoc后端, auto=自动选择。",
)
@click.option(
    "-o", "--output",
    "output_path",
    default=None,
    type=click.Path(dir_okay=False, writable=True),
    help="输出 .docx 路径 (默认使用配置文件中的 paths.docx_output)。",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="仅打印将要执行的操作，不实际生成文件。",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="输出详细日志。",
)
@click.option(
    "--pandoc-args",
    default=None,
    type=str,
    help="传递给 pandoc 的额外命令行参数（空格分隔，追加到 config.pandoc.extra_args 之后）。",
)
def convert_cmd(
    config_path: str,
    method: str,
    output_path: Optional[str],
    dry_run: bool,
    verbose: bool,
    pandoc_args: Optional[str],
) -> None:
    """执行 Markdown → DOCX 转换。"""
    # --- load config FIRST (needed for method resolution) ---
    try:
        from docx_pipeline.config import load_config
    except ImportError as exc:
        raise click.ClickException(
            f"无法加载配置系统: {exc}\n"
            "请确认 docx_pipeline 已正确安装。"
        ) from exc

    try:
        cfg = load_config(config_path)
    except FileNotFoundError as exc:
        raise click.ClickException(f"配置文件不存在: {exc}") from exc
    except (TypeError, ValueError, yaml.YAMLError) as exc:
        raise click.ClickException(f"配置加载失败: {exc}") from exc

    # --- configure logging for verbose mode ---
    if verbose:
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(name)s [%(levelname)s] %(message)s",
        )

    if verbose:
        _flush_print(f"[INFO] 配置文件已加载: {normalize_path(config_path)}")
        _flush_print(f"[INFO] 项目名称: {cfg.project.name}")
        _flush_print(f"[INFO] md_source: {cfg.paths.md_source}")
        _flush_print(f"[INFO] docx_output: {cfg.paths.docx_output}")

    # --- resolve method (respects cfg.pandoc.enabled) ---
    pandoc_available, pandoc_path = _check_pandoc_available()

    if method == "pandoc":
        if not pandoc_available:
            raise click.ClickException(
                "pandoc 方法需要 pandoc 但未在 PATH 中找到。\n"
                "安装 pandoc: https://pandoc.org/installing.html\n"
                "或使用 --method pure 切换到 Pure Python 转换器。"
            )
        effective_method = "pandoc"
    elif method == "auto":
        # Respect config: only auto-select pandoc if config says so AND it's installed
        if cfg.pandoc.enabled and pandoc_available:
            effective_method = "pandoc"
        else:
            effective_method = "pure"
    else:
        effective_method = method

    if verbose:
        _flush_print(f"[INFO] 解析后的转换方法: {effective_method}")
        if effective_method == "pandoc":
            _flush_print(f"[INFO] pandoc 路径: {pandoc_path}")
        elif method == "auto":
            if not cfg.pandoc.enabled:
                _flush_print("[INFO] pandoc 在配置中被禁用，回退至 pure")
            elif not pandoc_available:
                _flush_print("[INFO] pandoc 未安装，回退至 pure")

    # --- determine output path ---
    resolved_output = output_path or cfg.paths.docx_output
    if not resolved_output:
        raise click.ClickException(
            "未指定输出路径。请通过 --output 指定，"
            "或在配置文件的 paths.docx_output 中设置。"
        )
    resolved_output = normalize_path(resolved_output)

    if dry_run:
        _flush_print(f"[DRY-RUN] 方法      : {effective_method}")
        _flush_print(f"[DRY-RUN] 配置文件  : {normalize_path(config_path)}")
        _flush_print(f"[DRY-RUN] 项目名称  : {cfg.project.name}")
        _flush_print(f"[DRY-RUN] Markdown   : {normalize_path(cfg.paths.md_source)}")
        _flush_print(f"[DRY-RUN] 输出文件  : {resolved_output}")
        return

    # --- parse pandoc-args override ---
    import shlex
    extra_pandoc_args = (
        shlex.split(pandoc_args, posix=(os.name != "nt"))
        if pandoc_args else []
    )

    # --- import converter lazily ---
    if effective_method == "pandoc":
        # Pre-conversion mermaid check (respect mermaid.enabled)
        if cfg.mermaid.enabled:
            has_mermaid = _detect_mermaid_blocks(cfg.paths.md_source)
            if has_mermaid:
                mmdc_available, mmdc_path = _check_mmdc_available(cfg)
                if mmdc_available:
                    if verbose:
                        _flush_print(f"[INFO] 检测到 Mermaid 代码块，mmdc 路径: {mmdc_path}")
                        _flush_print("[INFO] Mermaid 图表将在转换前预渲染")
                else:
                    _flush_print(
                        "⚠ 警告: 检测到 Mermaid 代码块但 mmdc 不可用。\n"
                        "  Mermaid 图表将作为代码块保留在输出中。\n"
                        "  安装 mmdc: npm install -g @mermaid-js/mermaid-cli\n"
                        "  或在 project.yaml 中设置 mermaid.render.mmdc_path。"
                    )

        try:
            from docx_pipeline.converters import PandocConverter
        except ImportError as exc:
            raise click.ClickException(
                f"无法加载 PandocConverter: {exc}\n"
                "请确认 docx_pipeline.converters.pandoc 模块已安装。"
            ) from exc

        converter = PandocConverter(cfg, extra_args=extra_pandoc_args)
    else:
        try:
            from docx_pipeline.converters import PurePythonConverter
        except ImportError as exc:
            raise click.ClickException(
                f"无法加载 PurePythonConverter: {exc}\n"
                "请确认 docx_pipeline.converters 模块已安装。"
            ) from exc

        converter = PurePythonConverter(cfg)

    try:
        saved_path = converter.save(resolved_output)
    except (RuntimeError, FileNotFoundError, OSError, ValueError) as exc:
        raise click.ClickException(f"转换失败: {exc}") from exc

    if verbose and effective_method == "pandoc":
        _flush_print(f"[INFO] pandoc 命令: {' '.join(converter.last_command)}")

    _flush_print(f"✓ 转换完成: {saved_path}")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------
@cli.command("validate")
@click.option(
    "--config",
    "config_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="project.yaml 配置文件路径 (必需)。",
)
def validate_cmd(config_path: str) -> None:
    """校验 project.yaml 配置文件的完整性与正确性。

    检查项包括：md_source 是否存在、输出目录是否可写、
    字体大小范围、外部依赖 (pandoc/mmdc) 是否可用等。
    """
    try:
        from docx_pipeline.config import load_config, validate_config
    except ImportError as exc:
        raise click.ClickException(
            f"无法加载配置/校验系统: {exc}\n"
            "请确认 docx_pipeline 已正确安装。"
        ) from exc

    try:
        cfg = load_config(config_path)
    except (FileNotFoundError, TypeError, ValueError, yaml.YAMLError) as exc:
        raise click.ClickException(f"配置加载失败: {exc}") from exc

    issues: list = validate_config(cfg)

    if not issues:
        _flush_print("✓ 配置校验通过，未发现问题。")
    else:
        _flush_print(f"⚠ 配置校验发现 {len(issues)} 个问题:\n")
        for i, msg in enumerate(issues, 1):
            _flush_print(f"  {i}. {msg}")
        _flush_print()
        raise click.ClickException(
            f"配置校验未通过 ({len(issues)} 个问题)，请修复后重试。"
        )


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------
@cli.command("info")
@click.option(
    "--config",
    "config_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="project.yaml 配置文件路径 (必需)。",
)
def info_cmd(config_path: str) -> None:
    """打印配置摘要信息。"""
    try:
        from docx_pipeline.config import load_config
    except ImportError as exc:
        raise click.ClickException(
            f"无法加载配置系统: {exc}\n"
            "请确认 docx_pipeline 已正确安装。"
        ) from exc

    try:
        cfg = load_config(config_path)
    except (FileNotFoundError, TypeError, ValueError, yaml.YAMLError) as exc:
        raise click.ClickException(f"配置加载失败: {exc}") from exc

    _flush_print("=" * 58)
    _flush_print("  DOCX Pipeline — 项目配置摘要")
    _flush_print("=" * 58)
    _flush_print(f"  配置文件      : {normalize_path(config_path)}")
    _flush_print(f"  项目名称      : {cfg.project.name}")
    _flush_print(f"  项目根目录    : {normalize_path(cfg.project.root)}")
    _flush_print("-" * 58)
    _flush_print(f"  md_source     : {cfg.paths.md_source}")
    _flush_print(f"  docx_output   : {cfg.paths.docx_output}")
    _flush_print(f"  json_source   : {cfg.paths.json_source}")
    _flush_print(f"  work_dir      : {cfg.paths.work_dir}")
    _flush_print("-" * 58)
    _flush_print(f"  中文字体      : {cfg.fonts.east_asian}")
    _flush_print(f"  拉丁字体      : {cfg.fonts.latin}")
    _flush_print(f"  正文字号      : {cfg.font_sizes.body} pt")
    _flush_print(f"  表格字号      : {cfg.font_sizes.table} pt")
    _flush_print(f"  代码字号      : {cfg.font_sizes.code} pt")
    _flush_print("-" * 58)
    _flush_print(f"  页面尺寸      : {cfg.page.size}")
    _flush_print(f"  页边距 (cm)   : 上={cfg.page.margins.top} 下={cfg.page.margins.bottom}"
                 f" 左={cfg.page.margins.left} 右={cfg.page.margins.right}")
    _flush_print("-" * 58)
    _flush_print(f"  Pandoc        : {'启用' if cfg.pandoc.enabled else '禁用'}")
    _flush_print(f"  Mermaid       : {'启用' if cfg.mermaid.enabled else '禁用'}")
    _flush_print(f"  版本号        : {cfg.version.number}")
    if cfg.version.label:
        _flush_print(f"  版本标签      : {cfg.version.label}")
    if cfg.version.date:
        _flush_print(f"  版本日期      : {cfg.version.date}")
    _flush_print("=" * 58)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Programmatic entry point (also used by ``pyproject.toml`` scripts)."""
    try:
        cli(standalone_mode=False)
    except click.ClickException as exc:
        exc.show()
        sys.exit(exc.exit_code)
    except ConfigError as exc:
        _flush_print(f"配置错误: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
