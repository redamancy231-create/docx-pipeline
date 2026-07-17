"""Tests for Mermaid detection, image handling, and mmdc invocation.

Provenance: GPT-5.6-Sol (via Codex CLI), 2026-07-17.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from docx_pipeline.config.defaults import get_template
from docx_pipeline.config.schema import DocxPipelineConfig
from docx_pipeline.renderers.mermaid_renderer import (
    MermaidRenderError,
    MermaidRenderer,
)


FENCE = chr(96) * 3


@pytest.fixture()
def mermaid_config(tmp_path: Path) -> DocxPipelineConfig:
    """Build a report config with Mermaid enabled and isolated paths."""
    data = get_template("report")
    data["project"].update({"name": "Mermaid 测试", "root": str(tmp_path)})
    data["paths"].update(
        {
            "md_source": str(tmp_path / "输入.md"),
            "docx_output": str(tmp_path / "输出.docx"),
            "work_dir": str(tmp_path / "work"),
        }
    )
    data["mermaid"]["enabled"] = True
    data["mermaid"]["image"].update({"dpi": 300, "scale": 1.0})
    data["mermaid"]["render"].update(
        {"mmdc_path": "mmdc", "puppeteer_config": "", "timeout": 7}
    )
    return DocxPipelineConfig.from_dict(data)


def _single_mermaid_document() -> str:
    return (
        "## 处理流程\n\n"
        f"{FENCE}mermaid\n"
        "graph TD\n"
        "    A[开始] --> B[结束]\n"
        f"{FENCE}\n"
    )


def test_mermaid_block_detection_accepts_commonmark_indentation_only(
    mermaid_config: DocxPipelineConfig,
) -> None:
    markdown = (
        "# 一级标题不会作为图注\n\n"
        "## 第一部分\n"
        f"{FENCE}mermaid\n"
        "graph TD\nA --> B\n"
        f"{FENCE}\n\n"
        "### 第二部分\n"
        f"   {FENCE}mermaid   \n"
        "sequenceDiagram\nA->>B: 你好\n"
        f"   {FENCE}\n\n"
        "#### 四空格缩进不应匹配\n"
        f"    {FENCE}mermaid\n"
        "graph LR\nX --> Y\n"
        f"    {FENCE}\n\n"
        f"{FENCE}python\nprint('not mermaid')\n{FENCE}\n"
    )
    renderer = MermaidRenderer(mermaid_config)

    blocks = renderer._find_mermaid_blocks(markdown)

    assert len(blocks) == 2
    assert blocks[0].index == 0
    assert blocks[0].code == "graph TD\nA --> B"
    assert blocks[0].heading == "第一部分"
    assert blocks[1].index == 1
    assert blocks[1].code == "sequenceDiagram\nA->>B: 你好"
    assert blocks[1].heading == "第二部分"


def test_build_mmdc_args_uses_scale_width_and_puppeteer_config(
    mermaid_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    renderer = MermaidRenderer(mermaid_config)
    mermaid_config.mermaid.image.scale = 2.0
    puppeteer_config = tmp_path / "puppeteer 配置.json"
    mermaid_config.mermaid.render.puppeteer_config = str(puppeteer_config)
    input_path = tmp_path / "图表.mmd"
    output_path = tmp_path / "图表.png"

    with patch.object(renderer, "_compute_render_width", return_value=1440):
        args = renderer._build_mmdc_args(input_path, output_path)

    assert args == [
        "mmdc",
        "-i",
        str(input_path),
        "-o",
        str(output_path),
        "-w",
        "1440",
        "-b",
        "white",
        "-s",
        "2.0",
        "-p",
        str(puppeteer_config),
    ]


def test_render_mocks_mmdc_and_replaces_block_with_relative_image_reference(
    mermaid_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    renderer = MermaidRenderer(mermaid_config)
    markdown = _single_mermaid_document()
    fake_executable = str(tmp_path / "mmdc.exe")

    def fake_run(
        args: list[str],
        **_: object,
    ) -> subprocess.CompletedProcess[str]:
        output_path = Path(args[args.index("-o") + 1])
        output_path.write_bytes(b"not-a-real-png" + b"x" * 1100)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    with patch(
        "docx_pipeline.renderers.mermaid_renderer.shutil.which",
        return_value=fake_executable,
    ), patch(
        "docx_pipeline.renderers.mermaid_renderer.subprocess.run",
        side_effect=fake_run,
    ) as mocked_run, patch.object(
        renderer, "_resize_to_target"
    ), patch.object(
        renderer, "_inject_dpi"
    ):
        rendered = renderer.render(markdown, work_dir=tmp_path / "run")

    assert FENCE + "mermaid" not in rendered
    assert "![Mermaid: 处理流程](mermaid/diagram_000.png)" in rendered

    command = mocked_run.call_args.args[0]
    assert command[0] == fake_executable
    assert command[command.index("-i") + 1].endswith("diagram_000.mmd")
    assert command[command.index("-o") + 1].endswith("diagram_000.png")
    assert mocked_run.call_args.kwargs["shell"] is False


def test_inject_dpi_resaves_png_with_configured_metadata(
    mermaid_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    renderer = MermaidRenderer(mermaid_config)
    png_path = tmp_path / "diagram.png"
    image = MagicMock()

    with patch(
        "docx_pipeline.renderers.mermaid_renderer.Image.open",
        return_value=image,
    ) as mocked_open:
        renderer._inject_dpi(png_path, 300)

    mocked_open.assert_called_once_with(png_path)
    image.save.assert_called_once_with(str(png_path), "PNG", dpi=(300, 300))


def test_tall_image_is_split_with_overlap_and_dpi_reinjected(
    mermaid_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    renderer = MermaidRenderer(mermaid_config)
    mermaid_dir = tmp_path / "run" / "mermaid"
    mermaid_dir.mkdir(parents=True)
    png_path = mermaid_dir / "diagram_000.png"
    Image.new("RGB", (120, 2200), "white").save(png_path, "PNG")

    with patch.object(
        renderer,
        "_compute_usable_page_height_px",
        return_value=1000,
    ), patch.object(renderer, "_inject_dpi") as mocked_inject:
        refs = renderer._build_image_refs(
            png_path,
            "mermaid/diagram_000.png",
            "Mermaid: 超长图",
        )

    assert refs == [
        "![Mermaid: 超长图（1/3）](mermaid/diagram_000_part1.png)",
        "![Mermaid: 超长图（2/3）](mermaid/diagram_000_part2.png)",
        "![Mermaid: 超长图（3/3）](mermaid/diagram_000_part3.png)",
    ]

    part_paths = [
        mermaid_dir / "diagram_000_part1.png",
        mermaid_dir / "diagram_000_part2.png",
        mermaid_dir / "diagram_000_part3.png",
    ]
    dimensions = []
    for part_path in part_paths:
        assert part_path.exists()
        with Image.open(part_path) as part_image:
            dimensions.append(part_image.size)

    assert dimensions == [(120, 1000), (120, 1000), (120, 220)]
    assert mocked_inject.call_count == 3
    assert [call.args for call in mocked_inject.call_args_list] == [
        (part_paths[0], 300),
        (part_paths[1], 300),
        (part_paths[2], 300),
    ]


def test_render_raises_clear_error_when_mmdc_is_not_found(
    mermaid_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    renderer = MermaidRenderer(mermaid_config)

    with patch(
        "docx_pipeline.renderers.mermaid_renderer.shutil.which",
        return_value=None,
    ):
        with pytest.raises(MermaidRenderError, match="mmdc .* not found"):
            renderer.render(_single_mermaid_document(), work_dir=tmp_path)


def test_mmdc_timeout_leaves_original_block_in_output(
    mermaid_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    renderer = MermaidRenderer(mermaid_config)
    markdown = _single_mermaid_document()

    with patch(
        "docx_pipeline.renderers.mermaid_renderer.shutil.which",
        return_value=str(tmp_path / "mmdc.exe"),
    ), patch(
        "docx_pipeline.renderers.mermaid_renderer.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="mmdc", timeout=7),
    ) as mocked_run:
        rendered = renderer.render(markdown, work_dir=tmp_path / "timeout-run")

    assert rendered == markdown
    assert mocked_run.call_args.kwargs["timeout"] == 7
    assert mocked_run.call_args.kwargs["shell"] is False


def test_invoke_mmdc_enforces_shell_false(
    mermaid_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    renderer = MermaidRenderer(mermaid_config)
    args = ["mmdc", "-i", "input.mmd", "-o", "output.png"]
    resolved_executable = str(tmp_path / "mmdc.exe")
    completed = subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")

    with patch(
        "docx_pipeline.renderers.mermaid_renderer.shutil.which",
        return_value=resolved_executable,
    ), patch(
        "docx_pipeline.renderers.mermaid_renderer.subprocess.run",
        return_value=completed,
    ) as mocked_run:
        result = renderer._invoke_mmdc(args, timeout=9)

    assert result is completed
    assert mocked_run.call_args.args[0] == [
        resolved_executable,
        "-i",
        "input.mmd",
        "-o",
        "output.png",
    ]
    assert mocked_run.call_args.kwargs["shell"] is False
    assert mocked_run.call_args.kwargs["timeout"] == 9
    assert mocked_run.call_args.kwargs["env"]["PYTHONIOENCODING"] == "utf-8"