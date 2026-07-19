"""Tests for math formula support in the Pandoc converter.

Provenance: DeepSeek-V4-Pro (via Claude Code), 2026-07-19.
Review: GPT-5.6-Sol (via Codex CLI), 2026-07-19 — F01–F02 fixes applied.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from docx_pipeline.config.defaults import get_template
from docx_pipeline.config.schema import DocxPipelineConfig
from docx_pipeline.converters.pandoc_converter import PandocConverter

# OMML math namespace for XPath queries
OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _count_omml_elements(doc_xml: str, local_name: str) -> int:
    """Count OMML elements by local name in DOCX XML using lxml XPath."""
    from lxml import etree
    root = etree.fromstring(doc_xml.encode("utf-8"))
    return len(root.findall(f".//{{{OMML_NS}}}{local_name}"))


def _get_doc_xml(docx_path: Path) -> str:
    """Extract word/document.xml from a DOCX file."""
    import zipfile
    with zipfile.ZipFile(str(docx_path), "r") as zf:
        return zf.read("word/document.xml").decode("utf-8")


@pytest.fixture()
def math_config(tmp_path: Path) -> DocxPipelineConfig:
    """Build a config pointing at the math test fixture."""
    fixture_md = (
        Path(__file__).parent / "fixtures" / "math_test.md"
    ).resolve()

    data = get_template("default")
    data["project"].update({"name": "数学测试", "root": str(tmp_path)})
    data["paths"].update(
        {
            "md_source": str(fixture_md),
            "docx_output": str(tmp_path / "math_output.docx"),
            "work_dir": str(tmp_path / "work"),
            "reference_docx": "",
        }
    )
    data["pandoc"].update(
        {"enabled": True, "extra_args": [], "reference_docx": ""}
    )
    data["mermaid"]["enabled"] = False
    return DocxPipelineConfig.from_dict(data)


@pytest.fixture()
def no_math_config(tmp_path: Path) -> DocxPipelineConfig:
    """Build a config for a Markdown file with no math formulas (negative test)."""
    md_path = tmp_path / "plain.md"
    md_path.write_text(
        "# 纯文本文档\n\n这是没有任何数学公式的普通段落。\n\n"
        "只有标题、正文和**粗体**文本。\n",
        encoding="utf-8",
    )

    data = get_template("default")
    data["project"].update({"name": "纯文本测试", "root": str(tmp_path)})
    data["paths"].update(
        {
            "md_source": str(md_path),
            "docx_output": str(tmp_path / "plain_output.docx"),
            "work_dir": str(tmp_path / "work"),
            "reference_docx": "",
        }
    )
    data["pandoc"].update(
        {"enabled": True, "extra_args": [], "reference_docx": ""}
    )
    data["mermaid"]["enabled"] = False
    return DocxPipelineConfig.from_dict(data)


# ---------------------------------------------------------------------------
# F01 fix: test that the reader args include both extensions
# ---------------------------------------------------------------------------

def test_pandoc_reader_includes_tex_math_extensions(
    math_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    """Verify `tex_math_dollars` (explicitly fixed) and
    `tex_math_single_backslash` (new addition) are in the --from argument."""
    work_dir = tmp_path / "work" / "run_math"
    work_dir.mkdir(parents=True)
    md_path = work_dir / "preprocessed.md"
    converter = PandocConverter(math_config)
    args = converter._build_pandoc_args(md_path)

    from_value = args[args.index("--from") + 1]
    assert "+tex_math_dollars" in from_value, (
        f"Expected +tex_math_dollars in --from, got: {from_value}"
    )
    assert "+tex_math_single_backslash" in from_value, (
        f"Expected +tex_math_single_backslash in --from, got: {from_value}"
    )


# ---------------------------------------------------------------------------
# F01 + F02 fix: verify single-backslash delimiters produce OMML
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    shutil.which("pandoc") is None,
    reason="pandoc not installed",
)
def test_single_backslash_delimiters_produce_omml(
    math_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    r"""\(...\) and \[...\] (the real new capability) produce OMML elements."""
    converter = PandocConverter(math_config)
    output_path = tmp_path / "math_output.docx"
    converter.save(str(output_path))

    doc_xml = _get_doc_xml(output_path)

    # The fixture now contains \(a^2+b^2=c^2\) and \[...\]
    # which should produce OMML elements
    omath_count = _count_omml_elements(doc_xml, "oMath")
    assert omath_count > 0, (
        f"Expected at least one m:oMath element "
        f"(from \\\\(...\\\\) / \\\\[...\\\\]), got {omath_count}"
    )


# ---------------------------------------------------------------------------
# F02 fix: strong oracles — count OMML structural elements
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    shutil.which("pandoc") is None,
    reason="pandoc not installed",
)
def test_omml_element_counts_match_fixture(
    math_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    """Verify OMML element counts match expected formula structures in fixture."""
    converter = PandocConverter(math_config)
    output_path = tmp_path / "math_output.docx"
    converter.save(str(output_path))

    doc_xml = _get_doc_xml(output_path)

    omath_count = _count_omml_elements(doc_xml, "oMath")
    frac_count = _count_omml_elements(doc_xml, "f")
    rad_count = _count_omml_elements(doc_xml, "rad")
    m_count = _count_omml_elements(doc_xml, "m")

    # Fixture contains: E=mc^2, a^2+b^2=c^2 (×2), Greek α+β=γ,
    # Δx→0, λ, μ, sum, integral, a/b inline, sqrt inline, limit,
    # aligned (2 equations), ^2 inside, \(...\) inline, \[...\] block
    # + fraction (quadratic formula) and frac blocks
    assert omath_count >= 10, (
        f"Expected >=10 m:oMath elements, got {omath_count}"
    )
    assert frac_count >= 3, (
        f"Expected >=3 m:f (fraction) elements, got {frac_count}"
    )
    assert rad_count >= 2, (
        f"Expected >=2 m:rad (radical) elements, got {rad_count}"
    )
    assert m_count >= 1, (
        f"Expected >=1 m:m (matrix) element, got {m_count}"
    )


# ---------------------------------------------------------------------------
# F02 fix: negative test — plain document without formulas
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    shutil.which("pandoc") is None,
    reason="pandoc not installed",
)
def test_plain_document_without_formulas_produces_no_omath(
    no_math_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    """A Markdown file with no math should produce zero OMML math elements."""
    converter = PandocConverter(no_math_config)
    output_path = tmp_path / "plain_output.docx"
    converter.save(str(output_path))

    doc_xml = _get_doc_xml(output_path)

    omath_count = _count_omml_elements(doc_xml, "oMath")
    assert omath_count == 0, (
        f"Expected 0 m:oMath elements in plain document, got {omath_count}"
    )


# ---------------------------------------------------------------------------
# F02 fix: verify specific formula structures (sub/sup, nary, etc.)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    shutil.which("pandoc") is None,
    reason="pandoc not installed",
)
def test_formula_structures_contain_expected_omml_elements(
    math_config: DocxPipelineConfig,
    tmp_path: Path,
) -> None:
    """Verify that superscripts, subscripts, and n-ary operators produce
    corresponding OMML elements."""
    converter = PandocConverter(math_config)
    output_path = tmp_path / "math_output.docx"
    converter.save(str(output_path))

    doc_xml = _get_doc_xml(output_path)

    # Fixture contains superscripts (^2, ^{i\pi}, e^{-x^2})
    ssup_count = _count_omml_elements(doc_xml, "sSup")
    # Fixture contains subscripts (\sum_{i=1}^{n}, \lim_{x \to \infty})
    ssub_count = _count_omml_elements(doc_xml, "sSub")
    # Fixture contains \sum and \int
    nary_count = _count_omml_elements(doc_xml, "nary")

    assert ssup_count >= 3, (
        f"Expected >=3 m:sSup elements, got {ssup_count}"
    )
    assert ssub_count >= 2, (
        f"Expected >=2 m:sSub elements, got {ssub_count}"
    )
    assert nary_count >= 2, (
        f"Expected >=2 m:nary elements (sum+int), got {nary_count}"
    )
