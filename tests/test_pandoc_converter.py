"""Tests for the Pandoc converter subprocess boundary.

Provenance: GPT-5.6-Sol (via Codex CLI), 2026-07-17.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from docx_pipeline.config.defaults import get_template
from docx_pipeline.config.schema import DocxPipelineConfig
from docx_pipeline.converters.pandoc_converter import PandocConverter


@pytest.fixture()
def pandoc_config(tmp_path: Path) -> DocxPipelineConfig:
    """Build a fully populated config with paths isolated under tmp_path."""
    source_dir = tmp_path / "来源"
    source_dir.mkdir()
    markdown_path = source_dir / "输入文档.md"
    markdown_path.write_text("# 标题\n\n正文。\n", encoding="utf-8")

    data = get_template("default")
    data["project"].update({"name": "转换测试", "root": str(tmp_path)})
    data["paths"].update(
        {
            "md_source": str(markdown_path),
            "docx_output": str(tmp_path / "输出.docx"),
            "work_dir": str(tmp_path / "work"),
            "reference_docx": "",
        }
    )
    data["pandoc"].update(
        {"enabled": True, "extra_args": [], "reference_docx": ""}
    )
    data["mermaid"]["enabled"] = False
    data["version"].update(
        {"number": "2.0.0", "label": "", "date": "2026-07-17"}
    )
    return DocxPipelineConfig.from_dict(data)


def test_build_pandoc_args_constructs_expected_resource_and_metadata_args(
    pandoc_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    work_dir = tmp_path / "work" / "run_12345678"
    work_dir.mkdir(parents=True)
    markdown_path = work_dir / "preprocessed.md"
    converter = PandocConverter(pandoc_config)

    args = converter._build_pandoc_args(markdown_path)

    expected_reader = (
        "markdown+pipe_tables+grid_tables+fenced_code_blocks"
        "+backtick_code_blocks+yaml_metadata_block+raw_html"
        "+superscript+subscript+strikeout+footnotes"
        "+definition_lists+example_lists+task_lists"
        "+multiline_tables+simple_tables"
    )
    assert args[:3] == ["pandoc", "--from", expected_reader]
    assert args[args.index("--to") + 1] == "docx"
    assert "--standalone" in args
    assert args[args.index("--wrap") + 1] == "preserve"

    resource_value = args[args.index("--resource-path") + 1]
    resource_dirs = resource_value.split(os.pathsep)
    assert resource_dirs == [
        str(Path(pandoc_config.paths.md_source).parent.resolve()),
        str(Path(pandoc_config.project.root).resolve()),
        str(work_dir.resolve()),
    ]

    assert ["--metadata", "title=转换测试"] == args[
        args.index("--metadata") : args.index("--metadata") + 2
    ]
    assert "date=2026-07-17" in args


def test_build_pandoc_args_appends_reference_docx_and_extra_args_in_order(
    pandoc_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    preferred_reference = tmp_path / "模板" / "参考样式.docx"
    fallback_reference = tmp_path / "fallback.docx"
    pandoc_config.pandoc.reference_docx = str(preferred_reference)
    pandoc_config.paths.reference_docx = str(fallback_reference)
    pandoc_config.pandoc.extra_args = ["--toc", "--number-sections"]
    converter = PandocConverter(
        pandoc_config,
        extra_args=["--top-level-division=chapter", "--fail-if-warnings"],
    )

    args = converter._build_pandoc_args(tmp_path / "run" / "preprocessed.md")

    reference_index = args.index("--reference-doc")
    assert args[reference_index + 1] == str(preferred_reference.resolve())
    assert str(fallback_reference.resolve()) not in args
    assert args[-4:] == [
        "--toc",
        "--number-sections",
        "--top-level-division=chapter",
        "--fail-if-warnings",
    ]


def test_run_pandoc_uses_argument_list_and_utf8_environment(
    pandoc_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    markdown_path = tmp_path / "工作目录" / "preprocessed.md"
    markdown_path.parent.mkdir()
    output_path = markdown_path.parent / "pandoc_output.docx"
    converter = PandocConverter(pandoc_config, extra_args=["--toc"])
    completed = subprocess.CompletedProcess(
        args=["pandoc"], returncode=0, stdout="", stderr=""
    )

    with patch(
        "docx_pipeline.converters.pandoc_converter.shutil.which",
        return_value=str(tmp_path / "pandoc.exe"),
    ), patch(
        "docx_pipeline.converters.pandoc_converter.subprocess.run",
        return_value=completed,
    ) as mocked_run:
        converter._run_pandoc(markdown_path, output_path)

    expected_command = converter._build_pandoc_args(markdown_path) + [
        str(markdown_path),
        "-o",
        str(output_path),
    ]
    assert converter.last_command == expected_command
    assert mocked_run.call_args.args[0] == expected_command

    kwargs = mocked_run.call_args.kwargs
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["timeout"] == 120
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert kwargs["cwd"] == str(markdown_path.parent)
    assert kwargs["env"]["PYTHONIOENCODING"] == "utf-8"
    assert "shell" not in kwargs


def test_run_pandoc_raises_when_pandoc_is_not_found(
    pandoc_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    converter = PandocConverter(pandoc_config)
    markdown_path = tmp_path / "preprocessed.md"
    output_path = tmp_path / "out.docx"

    with patch(
        "docx_pipeline.converters.pandoc_converter.shutil.which",
        return_value=None,
    ), patch(
        "docx_pipeline.converters.pandoc_converter.subprocess.run"
    ) as mocked_run:
        with pytest.raises(FileNotFoundError, match="pandoc 未安装"):
            converter._run_pandoc(markdown_path, output_path)

    mocked_run.assert_not_called()
    assert converter.last_command == []


def test_run_pandoc_reports_non_zero_exit_and_stderr(
    pandoc_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    converter = PandocConverter(pandoc_config)
    markdown_path = tmp_path / "preprocessed.md"
    output_path = tmp_path / "out.docx"
    completed = subprocess.CompletedProcess(
        args=["pandoc"],
        returncode=23,
        stdout="",
        stderr="输入格式无效: bad option",
    )

    with patch(
        "docx_pipeline.converters.pandoc_converter.shutil.which",
        return_value=str(tmp_path / "pandoc.exe"),
    ), patch(
        "docx_pipeline.converters.pandoc_converter.subprocess.run",
        return_value=completed,
    ):
        with pytest.raises(RuntimeError) as exc_info:
            converter._run_pandoc(markdown_path, output_path)

    message = str(exc_info.value)
    assert "退出码 23" in message
    assert "输入格式无效: bad option" in message


def test_cleanup_removes_owned_temporary_directory(
    pandoc_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    converter = PandocConverter(pandoc_config)
    temp_dir = tempfile.TemporaryDirectory(dir=tmp_path)
    temp_path = Path(temp_dir.name)
    (temp_path / "intermediate.txt").write_text("临时文件", encoding="utf-8")
    converter._tempdir = temp_dir

    converter.cleanup()

    assert converter._tempdir is None
    assert not temp_path.exists()

    # cleanup() is intentionally idempotent.
    converter.cleanup()