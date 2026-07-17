"""Command-line contract tests for docx-pipeline.

Provenance: GPT-5.6-Sol (via Codex CLI), 2026-07-17.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from docx_pipeline import __version__
from docx_pipeline.cli import cli


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _write_valid_config(
    root: Path,
    *,
    project_name: str = "中文项目 Ω",
    markdown_name: str = "输入 文档（终稿）.md",
    output_name: str = "输出 报告✓.docx",
) -> tuple[Path, Path, Path]:
    """Create a minimal UTF-8 project config and its Markdown input."""
    root.mkdir(parents=True, exist_ok=True)
    markdown_path = root / markdown_name
    output_path = root / output_name
    work_dir = root / "临时 工作目录"
    config_path = root / "项目 配置.yaml"

    markdown_path.write_text("# 中文标题\n\nUnicode 正文：你好，世界。\n", encoding="utf-8")
    config_text = f"""project:
  name: "{project_name}"
  root: "{root.as_posix()}"
paths:
  md_source: "{markdown_path.as_posix()}"
  docx_output: "{output_path.as_posix()}"
  work_dir: "{work_dir.as_posix()}"
pandoc:
  enabled: false
  extra_args: []
  reference_docx: ""
mermaid:
  enabled: false
version:
  number: "1.0.0"
  label: ""
  date: ""
"""
    config_path.write_text(config_text, encoding="utf-8")
    return config_path, markdown_path, output_path


def test_help_exits_zero_and_lists_public_commands(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert result.stderr == ""
    assert "Usage: docx-pipeline" in result.stdout
    for command in ("init", "convert", "validate", "info"):
        assert command in result.stdout


def test_version_exits_zero_and_writes_only_stdout(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert result.stdout == f"docx-pipeline {__version__}\n"
    assert result.stderr == ""


def test_missing_config_file_is_usage_error_on_stderr(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "不存在.yaml"

    result = runner.invoke(
        cli,
        ["convert", "--config", str(missing), "--dry-run"],
    )

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "Error:" in result.stderr
    assert missing.name in result.stderr


def test_invalid_config_file_fails_without_polluting_stdout(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    invalid = tmp_path / "损坏配置.yaml"
    invalid.write_text("project: [unterminated\n", encoding="utf-8")

    result = runner.invoke(
        cli,
        ["convert", "--config", str(invalid), "--dry-run"],
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Error: 配置加载失败:" in result.stderr


def test_dry_run_has_stable_five_line_output_format(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    root = tmp_path / "含 空格的项目目录"
    config_path, markdown_path, output_path = _write_valid_config(root)

    with patch(
        "docx_pipeline.cli._check_pandoc_available",
        return_value=(False, None),
    ):
        result = runner.invoke(
            cli,
            [
                "convert",
                "--config",
                str(config_path),
                "--method",
                "pure",
                "--dry-run",
            ],
        )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "[DRY-RUN] 方法      : pure",
        f"[DRY-RUN] 配置文件  : {config_path.resolve().as_posix()}",
        "[DRY-RUN] 项目名称  : 中文项目 Ω",
        f"[DRY-RUN] Markdown   : {markdown_path.resolve().as_posix()}",
        f"[DRY-RUN] 输出文件  : {output_path.resolve().as_posix()}",
    ]


def test_success_exit_code_preserves_chinese_and_unicode_paths(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    root = tmp_path / "中文 路径 Ω"
    config_path, _, output_path = _write_valid_config(root)
    returned_path = output_path.resolve().as_posix()

    with patch(
        "docx_pipeline.cli._check_pandoc_available",
        return_value=(False, None),
    ), patch(
        "docx_pipeline.converters.PurePythonConverter.save",
        return_value=returned_path,
    ) as mocked_save:
        result = runner.invoke(
            cli,
            ["convert", "--config", str(config_path), "--method", "pure"],
        )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout == f"✓ 转换完成: {returned_path}\n"
    saved_argument = mocked_save.call_args.args[0]
    assert saved_argument.replace("\\", "/") == returned_path


def test_conversion_failure_is_non_zero_and_written_only_to_stderr(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    config_path, _, _ = _write_valid_config(tmp_path / "失败案例")

    with patch(
        "docx_pipeline.cli._check_pandoc_available",
        return_value=(False, None),
    ), patch(
        "docx_pipeline.converters.PurePythonConverter.save",
        side_effect=RuntimeError("模拟转换失败"),
    ):
        result = runner.invoke(
            cli,
            ["convert", "--config", str(config_path), "--method", "pure"],
        )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr == "Error: 转换失败: 模拟转换失败\n"